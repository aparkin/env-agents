"""
Unified Configuration Management System for env-agents

Handles all configuration including:
- Service credentials (API keys, tokens)
- Service-specific parameters 
- Earth Engine assets and authentication
- Metadata refresh and caching settings
- Default values and fallbacks
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConfigManager:
    """Centralized configuration manager for env-agents framework"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            base_dir: Base directory for env-agents (defaults to project root)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Find project root by looking for setup.py or pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                    self.base_dir = current
                    break
                current = current.parent
            else:
                # Fallback to current working directory if no project root found
                self.base_dir = Path.cwd()
        
        self.config_dir = self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "metadata").mkdir(exist_ok=True)
        (self.data_dir / "cache").mkdir(exist_ok=True)
        (self.data_dir / "auth").mkdir(exist_ok=True)
        
        # Load configuration
        self._credentials = {}
        self._services_config = {}
        self._earth_engine_config = {}
        self._defaults = {}
        
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        try:
            # Load defaults first
            self._defaults = self._load_yaml_config("defaults.yaml", {})
            
            # Load service configurations
            self._services_config = self._load_yaml_config("services.yaml", {})
            
            # Load Earth Engine config
            self._earth_engine_config = self._load_yaml_config("earth_engine.yaml", {})
            
            # Load credentials (may not exist initially)
            self._credentials = self._load_yaml_config("credentials.yaml", {})
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Continue with empty configs - will use environment variables as fallback
    
    def _load_yaml_config(self, filename: str, default: Dict = None) -> Dict[str, Any]:
        """Load YAML configuration file with fallback to default"""
        if default is None:
            default = {}
            
        config_path = self.config_dir / filename
        if not config_path.exists():
            logger.warning(f"Config file {filename} not found, using defaults")
            return default
            
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or default
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return default
    
    def get_service_credentials(self, service_name: str) -> Dict[str, Any]:
        """Get credentials for a specific service
        
        Falls back to environment variables if not in config files
        """
        service_creds = self._credentials.get(service_name, {})
        
        # Common credential mapping
        env_mappings = {
            'NASA_POWER': {'email': 'NOAA_EMAIL', 'key': 'NOAA_KEY'},
            'US_EIA': {'api_key': 'EIA_API_KEY'},
            'EPA_AQS': {'email': 'EPA_AQS_EMAIL', 'key': 'EPA_AQS_KEY'},
            'OpenAQ': {'api_key': 'OPENAQ_API_KEY'},
            'EARTH_ENGINE': {'service_account_path': 'GEE_SERVICE_ACCOUNT_PATH'}
        }
        
        # Merge with environment variables
        if service_name in env_mappings:
            for config_key, env_var in env_mappings[service_name].items():
                if config_key not in service_creds:
                    env_value = os.getenv(env_var)
                    if env_value:
                        service_creds[config_key] = env_value
        
        return service_creds
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration parameters for a specific service"""
        service_config = self._services_config.get(service_name, {})
        
        # Merge with defaults
        defaults = self._defaults.get('services', {}).get(service_name, {})
        return {**defaults, **service_config}
    
    def get_credentials_file(self) -> Path:
        """Get path to credentials file"""
        return self.config_dir / "credentials.yaml"
    
    def get_services_config_file(self) -> Path:
        """Get path to services config file"""
        return self.config_dir / "services.yaml"
    
    def get_services_config(self) -> Dict[str, Any]:
        """Get all services configuration"""
        return self._services_config
    
    def get_earth_engine_config(self) -> Dict[str, Any]:
        """Get Earth Engine configuration"""
        defaults = self._defaults.get('earth_engine', {})
        return {**defaults, **self._earth_engine_config}
    
    def get_metadata_config(self) -> Dict[str, Any]:
        """Get metadata management configuration"""
        return self._defaults.get('metadata', {
            'refresh_interval_hours': 24,
            'cache_ttl_hours': 6,
            'auto_refresh': True
        })
    
    def get_data_paths(self) -> Dict[str, Path]:
        """Get standardized data directory paths"""
        return {
            'metadata': self.data_dir / "metadata",
            'cache': self.data_dir / "cache", 
            'auth': self.data_dir / "auth",
            'earth_engine_metadata': self.data_dir / "metadata" / "earth_engine",
            'services_metadata': self.data_dir / "metadata" / "services",
            'unified_metadata': self.data_dir / "metadata" / "unified"
        }
    
    def ensure_data_directories(self):
        """Ensure all required data directories exist"""
        paths = self.get_data_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, credentials: Dict[str, Any]):
        """Save credentials to config file (creates if doesn't exist)"""
        creds_path = self.config_dir / "credentials.yaml"
        
        try:
            with open(creds_path, 'w') as f:
                yaml.safe_dump(credentials, f, default_flow_style=False)
            self._credentials = credentials
            logger.info("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate current configuration and return any issues"""
        issues = {
            'missing_credentials': [],
            'missing_config': [],
            'missing_files': []
        }
        
        # Check for required service credentials
        required_services = ['US_EIA', 'EPA_AQS', 'OpenAQ']
        for service in required_services:
            creds = self.get_service_credentials(service)
            if not creds:
                issues['missing_credentials'].append(service)
        
        # Check for Earth Engine service account
        ee_config = self.get_earth_engine_config()
        service_account_path = ee_config.get('service_account_path')
        if service_account_path and not Path(service_account_path).exists():
            issues['missing_files'].append(f"GEE service account: {service_account_path}")
        
        return issues


class MetadataManager:
    """Manages external metadata refresh and local caching"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.paths = config_manager.get_data_paths()
        self.metadata_config = config_manager.get_metadata_config()
        
        # Ensure directories exist
        config_manager.ensure_data_directories()
    
    def needs_refresh(self, service_name: str) -> bool:
        """Check if service metadata needs refreshing"""
        if not self.metadata_config.get('auto_refresh', True):
            return False
            
        metadata_file = self.paths['services_metadata'] / f"{service_name.lower()}_metadata.json"
        if not metadata_file.exists():
            return True
        
        # Check age
        refresh_interval = timedelta(hours=self.metadata_config.get('refresh_interval_hours', 24))
        file_age = datetime.now() - datetime.fromtimestamp(metadata_file.stat().st_mtime)
        
        return file_age > refresh_interval
    
    def get_cached_metadata(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for a service"""
        metadata_file = self.paths['services_metadata'] / f"{service_name.lower()}_metadata.json"
        
        if not metadata_file.exists():
            return None
            
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load cached metadata for {service_name}: {e}")
            return None
    
    def save_metadata(self, service_name: str, metadata: Dict[str, Any]):
        """Save metadata to local cache"""
        metadata_file = self.paths['services_metadata'] / f"{service_name.lower()}_metadata.json"
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info(f"Saved metadata for {service_name}")
        except Exception as e:
            logger.error(f"Failed to save metadata for {service_name}: {e}")
    
    def get_earth_engine_catalog(self) -> Optional[List[Dict[str, Any]]]:
        """Get Earth Engine asset catalog"""
        catalog_file = self.paths['earth_engine_metadata'] / "catalog.json"
        
        if not catalog_file.exists():
            # Try to copy from parent directory if it exists
            parent_catalog = self.config.base_dir.parent / "earthengine_catalog.json"
            if parent_catalog.exists():
                import shutil
                shutil.copy2(parent_catalog, catalog_file)
                logger.info(f"Copied Earth Engine catalog from {parent_catalog}")
        
        if catalog_file.exists():
            try:
                with open(catalog_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load Earth Engine catalog: {e}")
        
        return None
    
    def get_earth_engine_rich_metadata(self) -> Optional[Dict[str, Any]]:
        """Get Earth Engine rich scraped metadata"""
        metadata_file = self.paths['earth_engine_metadata'] / "asset_metadata.json"
        
        if not metadata_file.exists():
            # Try to copy from parent directory if it exists
            parent_metadata = self.config.base_dir.parent / "all_metadata.json"
            if parent_metadata.exists():
                import shutil
                shutil.copy2(parent_metadata, metadata_file)
                logger.info(f"Copied Earth Engine metadata from {parent_metadata}")
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load Earth Engine metadata: {e}")
        
        return None
    
    def get_earth_engine_discovery(self) -> Dict[str, Any]:
        """Get Earth Engine asset discovery information"""
        discovery_file = self.paths['earth_engine_metadata'] / "asset_discovery.json"
        
        if discovery_file.exists():
            with open(discovery_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    def get_last_update_timestamp(self) -> Optional[str]:
        """Get timestamp of last metadata update"""
        # Check for most recent update across all metadata files
        latest_timestamp = None
        
        for metadata_dir in [self.paths['services_metadata'], self.paths['earth_engine_metadata']]:
            if metadata_dir.exists():
                for file_path in metadata_dir.glob("*.json"):
                    try:
                        mtime = file_path.stat().st_mtime
                        timestamp = datetime.fromtimestamp(mtime).isoformat()
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                    except Exception:
                        continue
        
        return latest_timestamp
    
    def standardize_metadata_format(self, service_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize metadata format across all services
        
        Ensures consistent structure for both env-agents services and Earth Engine assets
        """
        standardized = {
            'service_id': service_id,
            'service_type': 'earth_engine' if service_id.startswith('GEE/') else 'env_agent',
            'title': metadata.get('title', service_id),
            'description': metadata.get('description', ''),
            'provider': metadata.get('provider', 'Unknown'),
            'license': metadata.get('license', 'Unknown'),
            'last_updated': metadata.get('last_updated', datetime.now().isoformat()),
            'status': metadata.get('status', 'unknown'),
            'variables': self._standardize_variables(metadata.get('variables', [])),
            'temporal_coverage': self._standardize_temporal_coverage(metadata.get('temporal_coverage', {})),
            'spatial_coverage': self._standardize_spatial_coverage(metadata.get('spatial_coverage', {})),
            'capabilities': metadata.get('capabilities', {}),
            'attributes': {}
        }
        
        # Add service-specific attributes
        if service_id.startswith('GEE/'):
            standardized['attributes'].update({
                'asset_id': metadata.get('asset_id'),
                'asset_type': metadata.get('type'),
                'tags': metadata.get('tags', []),
                'bands': metadata.get('variables', []),  # For EE, variables are bands
                'ee_available': metadata.get('ee_available', False)
            })
        else:
            standardized['attributes'].update({
                'dataset': metadata.get('dataset', service_id),
                'rate_limits': metadata.get('rate_limits', {}),
                'source_url': metadata.get('source_url'),
                'api_version': metadata.get('api_version')
            })
        
        return standardized
    
    def _standardize_variables(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize variable/parameter format"""
        standardized_vars = []
        
        for var in variables:
            if isinstance(var, dict):
                std_var = {
                    'id': var.get('id', var.get('name', 'unknown')),
                    'name': var.get('name', var.get('id', 'Unknown')),
                    'description': var.get('description', ''),
                    'units': var.get('units', var.get('unit')),
                    'data_type': var.get('data_type', var.get('type', 'unknown')),
                    'canonical_mapping': var.get('canonical', var.get('canonical_mapping')),
                    'uri': var.get('uri')
                }
                
                # Add Earth Engine specific fields if present
                if 'scale' in var:
                    std_var['scale'] = var['scale']
                if 'offset' in var:
                    std_var['offset'] = var['offset']
                if 'no_data_value' in var:
                    std_var['no_data_value'] = var['no_data_value']
                
                standardized_vars.append(std_var)
        
        return standardized_vars
    
    def _standardize_temporal_coverage(self, temporal: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize temporal coverage format"""
        return {
            'start_date': temporal.get('start_date'),
            'end_date': temporal.get('end_date'),
            'cadence': temporal.get('cadence', temporal.get('frequency')),
            'resolution': temporal.get('resolution'),
            'is_ongoing': temporal.get('is_ongoing', temporal.get('end_date') is None)
        }
    
    def _standardize_spatial_coverage(self, spatial: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize spatial coverage format"""
        return {
            'bbox': spatial.get('bbox'),
            'geometry': spatial.get('geometry'),
            'crs': spatial.get('crs', spatial.get('coordinate_reference_system')),
            'resolution_m': spatial.get('resolution_m', spatial.get('gsd')),
            'coverage_type': spatial.get('coverage_type', 'global' if not spatial.get('bbox') else 'regional')
        }
    
    def refresh_earth_engine_metadata(self, force: bool = False):
        """Refresh Earth Engine metadata from parent directory"""
        logger.info("Refreshing Earth Engine metadata...")
        
        ee_paths = self.paths['earth_engine_metadata']
        catalog_file = ee_paths / "catalog.json"
        metadata_file = ee_paths / "asset_metadata.json"
        
        # Check if refresh is needed
        if not force and catalog_file.exists() and metadata_file.exists():
            if not self.needs_refresh("earth_engine"):
                logger.info("Earth Engine metadata is up to date")
                return
        
        # Try to copy from parent directory (our existing files)
        parent_dir = self.config.base_dir.parent
        parent_catalog = parent_dir / "earthengine_catalog.json"
        parent_metadata = parent_dir / "all_metadata.json"
        
        if parent_catalog.exists():
            import shutil
            shutil.copy2(parent_catalog, catalog_file)
            logger.info(f"Copied Earth Engine catalog: {len(json.load(open(catalog_file)))} assets")
        
        if parent_metadata.exists():
            import shutil
            shutil.copy2(parent_metadata, metadata_file)
            logger.info(f"Copied Earth Engine metadata: {len(json.load(open(metadata_file)))} assets")
    
    def export_unified_metadata(self, format: str = 'json') -> Union[str, Dict[str, Any]]:
        """
        Export all service metadata in unified format
        
        Args:
            format: Export format ('json', 'yaml')
            
        Returns:
            Unified metadata in specified format
        """
        unified_metadata = {
            'metadata_version': '1.0.0',
            'generated_at': datetime.now().isoformat(),
            'total_services': 0,
            'services': {}
        }
        
        # Add env-agents services
        services_path = self.paths['services_metadata']
        if services_path.exists():
            for metadata_file in services_path.glob("*_metadata.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        raw_metadata = json.load(f)
                    
                    service_id = raw_metadata.get('service_name', metadata_file.stem.replace('_metadata', ''))
                    standardized = self.standardize_metadata_format(service_id, raw_metadata)
                    unified_metadata['services'][service_id] = standardized
                    
                except Exception as e:
                    logger.error(f"Failed to process {metadata_file}: {e}")
        
        # Add Earth Engine services
        ee_discovery = self.get_earth_engine_discovery()
        for asset_info in ee_discovery.get('featured_assets', []):
            service_id = asset_info['service_id']
            standardized = self.standardize_metadata_format(service_id, asset_info)
            unified_metadata['services'][service_id] = standardized
        
        unified_metadata['total_services'] = len(unified_metadata['services'])
        
        if format == 'json':
            return json.dumps(unified_metadata, indent=2)
        elif format == 'yaml':
            return yaml.dump(unified_metadata, default_flow_style=False)
        else:
            return unified_metadata


# Global configuration instance
_global_config = None

def get_config(base_dir: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(base_dir)
    return _global_config

def get_metadata_manager(base_dir: Optional[str] = None) -> MetadataManager:
    """Get metadata manager instance"""
    config = get_config(base_dir)
    return MetadataManager(config)


# Add method to ConfigManager
ConfigManager.get_metadata_manager = lambda self: MetadataManager(self)