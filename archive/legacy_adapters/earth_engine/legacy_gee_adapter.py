"""
Google Earth Engine Adapter for env-agents framework

Treats individual Earth Engine assets as discoverable services,
returning data in the standardized env-agents format.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, date

from ..base import BaseAdapter, RequestSpec
from ...core.config import get_config

logger = logging.getLogger(__name__)


class EarthEngineAdapter(BaseAdapter):
    """
    Earth Engine adapter that provides access to individual GEE assets
    as separate services within the env-agents framework.
    """
    
    DATASET = "EARTH_ENGINE"
    SOURCE_URL = "https://earthengine.google.com"
    SOURCE_VERSION = "1.0"
    LICENSE = "Various - see individual asset licenses"
    REQUIRES_API_KEY = True  # Earth Engine requires service account authentication
    
    def __init__(self, asset_id: Optional[str] = None):
        """
        Initialize adapter for a specific Earth Engine asset
        
        Args:
            asset_id: Specific GEE asset ID (e.g., "LANDSAT/LC08/C02/T1")
                     If None, provides discovery of all available assets
        """
        super().__init__()
        self.asset_id = asset_id
        self.config = get_config()
        self.metadata_manager = self.config.get_metadata_manager()
        
        # Load Earth Engine configuration
        self.ee_config = self._load_earth_engine_config()
        
        # Initialize Earth Engine if credentials are available
        self.ee_initialized = False
        try:
            self._initialize_earth_engine()
        except Exception as e:
            logger.warning(f"Earth Engine initialization failed: {e}")
    
    def _load_earth_engine_config(self) -> Dict[str, Any]:
        """Load Earth Engine specific configuration"""
        try:
            services_config = self.config.get_services_config()
            return services_config.get('EARTH_ENGINE', {})
        except Exception as e:
            logger.warning(f"Failed to load Earth Engine config: {e}")
            return {}
    
    def _initialize_earth_engine(self):
        """Initialize Earth Engine authentication using unified authentication system"""
        try:
            import ee

            # Check if already initialized globally
            try:
                # Test if EE is already initialized
                ee.data.getProjects()
                logger.info("Earth Engine already initialized globally")
                self.ee_initialized = True
                return
            except:
                # Not initialized yet, proceed with authentication
                pass

            # Use unified authentication system
            try:
                from ...core.auth import AuthenticationManager
                auth_manager = AuthenticationManager(self.config.config_manager)
                auth_context = auth_manager.authenticate_service('EARTH_ENGINE')

                if auth_context['authenticated'] and 'ee_auth_config' in auth_context:
                    ee_config = auth_context['ee_auth_config']

                    if 'service_account_path' in ee_config and ee_config['service_account_path']:
                        # Service account authentication
                        service_account_path = ee_config['service_account_path']
                        project_id = ee_config.get('project_id')

                        if Path(service_account_path).exists():
                            logger.info(f"Authenticating Earth Engine with service account from {service_account_path}")

                            # Load service account info to get email
                            with open(service_account_path, 'r') as f:
                                service_account_info = json.load(f)

                            service_account_email = service_account_info.get('client_email')
                            credentials = ee.ServiceAccountCredentials(service_account_email, service_account_path)

                            if project_id:
                                ee.Initialize(credentials, project=project_id)
                            else:
                                ee.Initialize(credentials)

                            self.ee_initialized = True
                            logger.info(f"Earth Engine authenticated successfully for {service_account_email}")
                            return
                        else:
                            logger.warning(f"Service account file not found: {service_account_path}")

                    elif ee_config.get('use_user_auth'):
                        # User authentication (requires manual ee.Authenticate())
                        logger.info("Attempting Earth Engine user authentication")
                        try:
                            ee.Initialize()
                            self.ee_initialized = True
                            logger.info("Earth Engine user authentication successful")
                            return
                        except Exception as e:
                            logger.warning(f"User authentication failed: {e}")
                            logger.info("Please run 'earthengine authenticate' manually")

            except Exception as e:
                logger.warning(f"Unified authentication failed: {e}")

            # Fallback: Development environment paths (for backward compatibility)
            logger.info("Trying fallback development paths")
            service_account = 'gee-agent@ecognita-470619.iam.gserviceaccount.com'
            dev_paths = [
                'ecognita-470619-e9e223ea70a7.json',  # Current directory first
                '/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/ecognita-470619-e9e223ea70a7.json',
                '../ecognita-470619-e9e223ea70a7.json'
            ]

            for key_path in dev_paths:
                if Path(key_path).exists():
                    try:
                        logger.info(f"Using fallback Earth Engine credentials from {key_path}")
                        credentials = ee.ServiceAccountCredentials(service_account, key_path)
                        ee.Initialize(credentials)
                        self.ee_initialized = True
                        logger.info(f"Earth Engine authenticated successfully for {service_account}")
                        return
                    except Exception as e:
                        logger.warning(f"Authentication failed for {key_path}: {e}")
                        continue

            # Final fallback: discovery mode only (no authentication)
            logger.info("Earth Engine authentication not available - discovery mode only")
            self.ee_initialized = False

        except ImportError:
            logger.warning("Google Earth Engine library not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize Earth Engine: {e}")
    
    def capabilities(self, asset_id: str = None, extra: dict = None) -> Dict[str, Any]:
        """
        Uniform capabilities interface for Earth Engine meta-service.

        Args:
            asset_id: Specific asset ID for detailed capabilities (optional)
            extra: Additional parameters (optional)

        Returns:
            For asset_id=None: Asset discovery response
            For asset_id="LANDSAT/...": Detailed asset capabilities
        """
        # Use provided asset_id or fall back to instance asset_id
        target_asset_id = asset_id or self.asset_id

        if target_asset_id:
            # Detailed asset capabilities mode
            return self._get_asset_capabilities(target_asset_id)
        else:
            # Asset discovery mode
            return self._get_asset_discovery()
    
    def _get_asset_capabilities(self, asset_id: str) -> Dict[str, Any]:
        """Get capabilities for a specific Earth Engine asset"""
        catalog = self.metadata_manager.get_earth_engine_catalog()
        rich_metadata = self.metadata_manager.get_earth_engine_rich_metadata()
        
        # Find asset in catalog
        asset_info = None
        for entry in catalog:
            if entry.get('id') == asset_id:
                asset_info = entry
                break
        
        if not asset_info:
            return {
                "error": f"Asset {asset_id} not found in catalog",
                "available_assets": len(catalog)
            }
        
        # Get rich metadata if available
        rich_info = rich_metadata.get(asset_id, {})
        
        # Extract available bands/variables
        variables = []
        bands = rich_info.get('bands', [])
        if isinstance(bands, list):
            for band in bands:
                if isinstance(band, dict):
                    variables.append({
                        'id': band.get('id', band.get('name', 'unknown')),
                        'name': band.get('description', band.get('name', band.get('id', 'Unknown'))),
                        'units': band.get('units'),
                        'type': band.get('data_type', {}).get('type', 'unknown'),
                        'scale': band.get('scale'),
                        'offset': band.get('offset'),
                        'no_data_value': band.get('no_data_value')
                    })
        
        # If no band info, create generic variable
        if not variables:
            variables = [{
                'id': 'value',
                'name': asset_info.get('title', asset_id),
                'units': None,
                'type': 'unknown'
            }]
        
        # Use uniform response format for asset-specific capabilities
        return self._create_uniform_response(
            service_type="meta",
            variables=variables,
            asset_id=asset_id,
            title=asset_info.get('title', asset_id),
            description=asset_info.get('description', ''),
            asset_type=asset_info.get('type', rich_info.get('type')),
            temporal_coverage=self._extract_temporal_info(rich_info),
            spatial_coverage=self._extract_spatial_info(rich_info),
            provider=asset_info.get('provider', rich_info.get('provider', 'Google Earth Engine')),
            license=asset_info.get('license', rich_info.get('license')),
            tags=asset_info.get('tags', rich_info.get('tags', [])),
            ee_available=self.ee_initialized,
            last_updated=datetime.now().isoformat()
        )
    
    def _get_asset_discovery(self) -> Dict[str, Any]:
        """
        Get asset discovery for Earth Engine meta-service.
        Returns standardized list of available assets (not variables).
        """
        catalog = self.metadata_manager.get_earth_engine_catalog()
        discovery = self.metadata_manager.get_earth_engine_discovery()

        # Get all available assets from discovery
        featured_assets = discovery.get('featured_assets', [])
        categories = discovery.get('categories', {})

        # Create standardized asset list
        assets = []

        # Add featured assets first (these have rich metadata)
        for asset_info in featured_assets:
            asset = {
                'asset_id': asset_info.get('asset_id'),
                'title': asset_info.get('title'),
                'category': asset_info.get('category', 'unknown'),
                'description': asset_info.get('description', ''),
                'bands': asset_info.get('bands', []),
                'band_count': len(asset_info.get('bands', [])),
                'featured': True,
                'temporal_coverage': self._extract_temporal_info(asset_info),
                'spatial_coverage': self._extract_spatial_info(asset_info)
            }
            assets.append(asset)

        # Add sample assets from each category (non-featured)
        for category_name, category_assets in categories.items():
            for asset_info in category_assets[:3]:  # Max 3 per category
                asset_id = asset_info.get('asset_id')
                # Skip if already in featured assets
                if any(a['asset_id'] == asset_id for a in assets):
                    continue

                asset = {
                    'asset_id': asset_id,
                    'title': asset_info.get('title', asset_id),
                    'category': category_name,
                    'description': asset_info.get('description', ''),
                    'bands': asset_info.get('bands', []),
                    'band_count': len(asset_info.get('bands', [])),
                    'featured': False,
                    'temporal_coverage': {},
                    'spatial_coverage': {}
                }
                assets.append(asset)

        # Use uniform response format
        return self._create_uniform_response(
            service_type="meta",
            assets=assets,
            categories=list(categories.keys()),
            ee_available=self.ee_initialized,
            last_catalog_update=discovery.get('last_updated'),
            temporal_coverage={
                'start_date': '1972-07-23',  # Landsat 1 launch
                'end_date': 'present',
                'update_frequency': 'varies_by_asset'
            },
            spatial_coverage={
                'global': True,
                'resolution_range': '30m - 25km',
                'coverage': 'Global coverage with varying temporal frequency'
            }
        )
    
    def _extract_temporal_info(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal coverage information from metadata"""
        temporal_info = {}
        
        if 'start_date' in metadata:
            temporal_info['start_date'] = metadata['start_date']
        if 'end_date' in metadata:
            temporal_info['end_date'] = metadata['end_date']
        
        # Handle different temporal formats
        period = metadata.get('period', {})
        if isinstance(period, dict):
            if 'start' in period:
                temporal_info['start_date'] = period['start']
            if 'end' in period:
                temporal_info['end_date'] = period['end']
        
        # Extract cadence/frequency
        cadence = metadata.get('cadence')
        if cadence:
            temporal_info['cadence'] = cadence
        
        return temporal_info
    
    def _extract_spatial_info(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract spatial coverage information from metadata"""
        spatial_info = {}
        
        # Bounding box
        bbox = metadata.get('extent', {}).get('coordinates')
        if bbox:
            spatial_info['bbox'] = bbox
        
        # Resolution
        gsd = metadata.get('gsd')
        if gsd:
            spatial_info['resolution_m'] = gsd
            
        # CRS information
        crs = metadata.get('crs') or metadata.get('coordinate_reference_system')
        if crs:
            spatial_info['crs'] = crs
        
        return spatial_info
    
    def harvest(self) -> Dict[str, Any]:
        """
        Harvest available Earth Engine assets and their metadata
        
        This provides comprehensive discovery information for the registry.
        """
        catalog = self.metadata_manager.get_earth_engine_catalog()
        discovery = self.metadata_manager.get_earth_engine_discovery()
        rich_metadata = self.metadata_manager.get_earth_engine_rich_metadata()
        
        harvest_data = {
            'harvest_timestamp': datetime.now().isoformat(),
            'service_name': self.DATASET,
            'total_assets': len(catalog),
            'assets': []
        }
        
        # Process featured assets first
        featured_assets = discovery.get('featured_assets', [])
        processed_ids = set()
        
        for asset_info in featured_assets:
            asset_id = asset_info['asset_id']
            processed_ids.add(asset_id)
            
            # Get detailed capabilities
            capabilities = self._get_asset_capabilities(asset_id)
            
            harvest_data['assets'].append({
                'service_id': asset_info['service_id'],
                'asset_id': asset_id,
                'title': asset_info.get('title', asset_id),
                'category': asset_info.get('category', 'general'),
                'description': capabilities.get('description', ''),
                'variables': capabilities.get('variables', []),
                'featured': True,
                'temporal_coverage': capabilities.get('temporal_coverage', {}),
                'spatial_coverage': capabilities.get('spatial_coverage', {}),
                'provider': capabilities.get('provider'),
                'license': capabilities.get('license'),
                'tags': capabilities.get('tags', [])
            })
        
        # Add remaining assets from categories (limited sample)
        categories = discovery.get('categories', {})
        max_per_category = 5  # Limit to avoid huge harvest files
        
        for category, assets in categories.items():
            count = 0
            for asset_info in assets:
                if count >= max_per_category:
                    break
                    
                asset_id = asset_info['asset_id']
                if asset_id in processed_ids:
                    continue
                    
                processed_ids.add(asset_id)
                count += 1
                
                # Get basic info
                harvest_data['assets'].append({
                    'service_id': asset_info['service_id'],
                    'asset_id': asset_id,
                    'title': asset_info.get('title', asset_id),
                    'category': category,
                    'description': asset_info.get('description', ''),
                    'featured': False,
                    'variables': [{'id': 'value', 'name': asset_info.get('title', asset_id)}]  # Minimal info
                })
        
        return harvest_data
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """
        Fetch data from Earth Engine asset
        
        This requires Earth Engine to be properly initialized.
        """
        if not self.ee_initialized:
            raise RuntimeError(
                "Earth Engine not initialized. Please configure credentials and install earthengine-api package."
            )
        
        if not self.asset_id:
            raise ValueError("Asset ID must be specified for data fetching")
        
        try:
            import ee
            
            # Get the Earth Engine asset
            ee_object = self._get_ee_object(self.asset_id)
            
            # Apply spatial and temporal filters based on spec
            filtered_object = self._apply_filters(ee_object, spec)
            
            # Extract data based on spatial specification
            if hasattr(spec, 'geometry') and spec.geometry:
                # Point-based extraction
                return self._extract_point_data(filtered_object, spec)
            elif hasattr(spec, 'bbox') and spec.bbox:
                # Region-based extraction (sample points)
                return self._extract_region_data(filtered_object, spec)
            else:
                raise ValueError("Either geometry (point) or bbox (region) must be specified for Earth Engine queries")
                
        except ImportError:
            raise RuntimeError("Google Earth Engine library not installed")
        except Exception as e:
            logger.error(f"Failed to fetch Earth Engine data: {e}")
            raise
    
    def _get_ee_object(self, asset_id: str):
        """Get appropriate Earth Engine object for asset"""
        import ee
        
        # Determine asset type and create appropriate object
        if 'ImageCollection' in asset_id or any(pattern in asset_id for pattern in ['LANDSAT', 'MODIS', 'COPERNICUS']):
            return ee.ImageCollection(asset_id)
        else:
            return ee.Image(asset_id)
    
    def _apply_filters(self, ee_object, spec: RequestSpec):
        """Apply temporal and other filters to Earth Engine object"""
        import ee
        
        filtered = ee_object
        
        # Apply temporal filter if specified
        if hasattr(spec, 'start_date') and spec.start_date:
            if hasattr(filtered, 'filterDate'):  # ImageCollection
                end_date = getattr(spec, 'end_date', spec.start_date)
                filtered = filtered.filterDate(spec.start_date, end_date)
        
        # Apply bounds filter if applicable
        if hasattr(spec, 'bbox') and spec.bbox and hasattr(filtered, 'filterBounds'):
            # Create geometry from bbox
            bbox_geom = ee.Geometry.Rectangle(spec.bbox)
            filtered = filtered.filterBounds(bbox_geom)
        
        return filtered
    
    def _extract_point_data(self, ee_object, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Extract data at specific point(s)"""
        import ee
        
        rows = []
        geometry = spec.geometry
        
        # Create Earth Engine geometry
        if hasattr(geometry, 'x') and hasattr(geometry, 'y'):  # Point
            ee_point = ee.Geometry.Point([geometry.x, geometry.y])
            scale = self.ee_config.get('default_scale', 1000)
            
            # Sample the image/collection at the point
            if hasattr(ee_object, 'getRegion'):  # ImageCollection
                # For collections, get time series
                region_data = ee_object.getRegion(ee_point, scale).getInfo()
                
                # Process region data
                if region_data and len(region_data) > 1:
                    headers = region_data[0]
                    for data_row in region_data[1:]:
                        row_dict = dict(zip(headers, data_row))
                        rows.append(self._format_ee_row(row_dict, geometry, spec))
            else:
                # For single images
                sample = ee_object.sample(ee_point, scale).getInfo()
                if sample and sample['features']:
                    for feature in sample['features']:
                        props = feature['properties']
                        rows.append(self._format_ee_row(props, geometry, spec))
        
        return rows
    
    def _extract_region_data(self, ee_object, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Extract sample data from region"""
        import ee
        
        rows = []
        bbox = spec.bbox
        
        # Create sampling geometry
        region = ee.Geometry.Rectangle(bbox)
        scale = self.ee_config.get('default_scale', 1000)
        max_pixels = self.ee_config.get('max_pixels', 1000)
        
        # Sample the region
        if hasattr(ee_object, 'sample'):
            sample = ee_object.sample(
                region=region,
                scale=scale,
                numPixels=max_pixels,
                geometries=True
            ).getInfo()
            
            if sample and sample['features']:
                for feature in sample['features']:
                    # Extract coordinates from geometry
                    coords = feature['geometry']['coordinates']
                    geometry_point = type('Point', (), {'x': coords[0], 'y': coords[1]})()
                    
                    props = feature['properties']
                    rows.append(self._format_ee_row(props, geometry_point, spec))
        
        return rows
    
    def _format_ee_row(self, properties: Dict[str, Any], geometry, spec: RequestSpec) -> Dict[str, Any]:
        """Format Earth Engine data into standard env-agents row format"""
        
        # Get asset capabilities for variable mapping
        capabilities = self._get_asset_capabilities(self.asset_id)
        variables = capabilities.get('variables', [])
        
        # Create base row
        base_row = {
            'observation_id': '',  # Will be set by router
            'dataset': f"GEE/{self.asset_id.replace('/', '_')}",
            'source_url': f"https://earthengine.google.com/catalog/{self.asset_id}",
            'source_version': self.SOURCE_VERSION,
            'license': capabilities.get('license', self.LICENSE),
            'retrieval_timestamp': datetime.now().isoformat(),
            'geometry_type': 'POINT',
            'latitude': geometry.y,
            'longitude': geometry.x,
            'geom_wkt': f"POINT({geometry.x} {geometry.y})",
            'spatial_id': None,
            'site_name': None,
            'admin': None,
            'elevation_m': properties.get('elevation'),
            'time': properties.get('system:time_start'),  # EE timestamp
            'temporal_coverage': None,
            'qc_flag': None,
            'attributes': {
                'asset_id': self.asset_id,
                'ee_properties': properties,
                'scale_m': self.ee_config.get('default_scale', 1000)
            },
            'provenance': {
                'adapter': 'EarthEngineAdapter',
                'asset_id': self.asset_id,
                'extraction_method': 'point_sample',
                'scale': self.ee_config.get('default_scale', 1000)
            }
        }
        
        rows = []
        
        # Create one row per variable/band
        for var_info in variables:
            var_id = var_info['id']
            
            if var_id in properties:
                row = base_row.copy()
                row.update({
                    'variable': var_info.get('name', var_id),
                    'value': properties[var_id],
                    'unit': var_info.get('units'),
                    'depth_top_cm': None,
                    'depth_bottom_cm': None
                })
                
                # Handle temporal information
                if 'system:time_start' in properties:
                    # Convert EE timestamp to ISO format
                    timestamp_ms = properties['system:time_start']
                    if timestamp_ms:
                        row['time'] = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
                
                rows.append(row)
        
        # If no specific variables found, create a generic row
        if not rows and properties:
            row = base_row.copy()
            row.update({
                'variable': capabilities.get('title', self.asset_id),
                'value': list(properties.values())[0] if properties else None,
                'unit': None,
                'depth_top_cm': None,
                'depth_bottom_cm': None
            })
            rows.append(row)
        
        return rows[0] if len(rows) == 1 else rows


def create_asset_adapters() -> List[EarthEngineAdapter]:
    """
    Create adapter instances for featured Earth Engine assets

    Returns:
        List of configured EarthEngineAdapter instances
    """
    config = get_config()
    metadata_manager = config.get_metadata_manager()

    discovery = metadata_manager.get_earth_engine_discovery()
    featured_assets = discovery.get('featured_assets', [])

    adapters = []
    for asset_info in featured_assets:
        adapter = EarthEngineAdapter(asset_id=asset_info['asset_id'])
        adapters.append(adapter)

    return adapters

def get_asset_specific_adapter(asset_id: str) -> EarthEngineAdapter:
    """
    Create an Earth Engine adapter for a specific asset

    Args:
        asset_id: Earth Engine asset ID (e.g., "LANDSAT/LC08/C02/T1_L2")

    Returns:
        EarthEngineAdapter configured for the specific asset
    """
    return EarthEngineAdapter(asset_id=asset_id)

def get_available_assets() -> List[Dict[str, Any]]:
    """
    Get list of available Earth Engine assets with metadata

    Returns:
        List of asset information dictionaries
    """
    config = get_config()
    metadata_manager = config.get_metadata_manager()

    discovery = metadata_manager.get_earth_engine_discovery()
    return discovery.get('featured_assets', [])