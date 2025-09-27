#!/usr/bin/env python3
"""
Metadata Refresh Script for env-agents

Updates external metadata files and caches:
- Earth Engine asset catalog and metadata
- Service parameter lists and capabilities
- Unified service discovery information

Usage:
    python scripts/refresh_metadata.py [--service SERVICE_NAME] [--force]
"""

import argparse
import sys
import logging
from pathlib import Path
import json
import requests
from datetime import datetime

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.config import get_config, get_metadata_manager
from env_agents.core.router import EnvRouter


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def refresh_earth_engine_metadata(metadata_manager, force: bool = False):
    """Refresh Earth Engine asset catalog and metadata"""
    logger = logging.getLogger(__name__)
    
    ee_paths = metadata_manager.paths['earth_engine_metadata']
    catalog_file = ee_paths / "catalog.json"
    metadata_file = ee_paths / "asset_metadata.json"
    
    # Check if refresh is needed
    if not force and catalog_file.exists() and metadata_file.exists():
        if not metadata_manager.needs_refresh("earth_engine"):
            logger.info("Earth Engine metadata is up to date")
            return
    
    logger.info("Refreshing Earth Engine metadata...")
    
    # Try to copy from parent directory first (our existing files)
    parent_dir = metadata_manager.config.base_dir.parent
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
    
    # Create discovery file
    create_earth_engine_discovery(metadata_manager)


def create_earth_engine_discovery(metadata_manager):
    """Create Earth Engine service discovery file"""
    logger = logging.getLogger(__name__)
    
    catalog = metadata_manager.get_earth_engine_catalog()
    rich_metadata = metadata_manager.get_earth_engine_rich_metadata()
    
    if not catalog:
        logger.warning("No Earth Engine catalog found")
        return
    
    # Create discovery information
    discovery_data = {
        "last_updated": datetime.now().isoformat(),
        "total_assets": len(catalog),
        "featured_assets": [],
        "categories": {},
        "searchable_assets": {}
    }
    
    # Process featured assets from config
    ee_config = metadata_manager.config.get_earth_engine_config()
    featured = ee_config.get('featured_assets', [])
    
    for asset_info in featured:
        asset_id = asset_info['asset_id']
        
        # Find matching catalog entry
        catalog_entry = None
        for entry in catalog:
            if entry.get('id') == asset_id:
                catalog_entry = entry
                break
        
        if catalog_entry:
            discovery_data['featured_assets'].append({
                'service_id': f"GEE/{asset_id.replace('/', '_')}",
                'asset_id': asset_id,
                'title': asset_info.get('title', catalog_entry.get('title', asset_id)),
                'category': asset_info.get('category', 'general'),
                'bands': asset_info.get('bands', []),
                'description': catalog_entry.get('description', '')[:200] + '...' if catalog_entry.get('description') else None
            })
    
    # Categorize all assets
    categories = ee_config.get('asset_categories', {})
    for category, patterns in categories.items():
        discovery_data['categories'][category] = []
        
        for entry in catalog:
            asset_id = entry.get('id', '')
            if any(pattern in asset_id for pattern in patterns):
                discovery_data['categories'][category].append({
                    'service_id': f"GEE/{asset_id.replace('/', '_')}",
                    'asset_id': asset_id,
                    'title': entry.get('title', asset_id),
                    'description': entry.get('description', '')[:100] + '...' if entry.get('description') else None
                })
        
        # Limit per category
        max_per_category = ee_config.get('discovery', {}).get('max_assets_per_category', 50)
        discovery_data['categories'][category] = discovery_data['categories'][category][:max_per_category]
    
    # Save discovery file
    discovery_file = metadata_manager.paths['earth_engine_metadata'] / "asset_discovery.json"
    with open(discovery_file, 'w') as f:
        json.dump(discovery_data, f, indent=2)
    
    logger.info(f"Created Earth Engine discovery file with {len(discovery_data['featured_assets'])} featured assets")


def refresh_service_metadata(metadata_manager, service_name: str, force: bool = False):
    """Refresh metadata for a specific service"""
    logger = logging.getLogger(__name__)
    
    if not force and not metadata_manager.needs_refresh(service_name):
        logger.info(f"{service_name} metadata is up to date")
        return
    
    logger.info(f"Refreshing {service_name} metadata...")
    
    try:
        # Initialize router to get service capabilities
        router = EnvRouter(base_dir=metadata_manager.config.base_dir)
        
        # This would trigger capability refresh for the service
        capabilities = router.capabilities()
        
        if service_name in capabilities:
            service_caps = capabilities[service_name]
            
            # Create enhanced metadata
            metadata = {
                'service_name': service_name,
                'last_updated': datetime.now().isoformat(),
                'capabilities': service_caps,
                'status': 'active' if 'error' not in service_caps else 'error'
            }
            
            metadata_manager.save_metadata(service_name, metadata)
            logger.info(f"Updated {service_name} metadata")
        else:
            logger.warning(f"No capabilities found for {service_name}")
            
    except Exception as e:
        logger.error(f"Failed to refresh {service_name} metadata: {e}")


def create_unified_catalog(metadata_manager):
    """Create unified service catalog combining env-agents and Earth Engine"""
    logger = logging.getLogger(__name__)
    
    unified_path = metadata_manager.paths['unified_metadata'] / "all_services.json"
    
    unified_catalog = {
        'last_updated': datetime.now().isoformat(),
        'env_agents_services': [],
        'earth_engine_assets': [],
        'total_services': 0
    }
    
    # Add env-agents services
    services_path = metadata_manager.paths['services_metadata']
    if services_path.exists():
        for metadata_file in services_path.glob("*_metadata.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                unified_catalog['env_agents_services'].append({
                    'service_id': metadata['service_name'],
                    'type': 'env_agent',
                    'status': metadata.get('status', 'unknown'),
                    'last_updated': metadata.get('last_updated'),
                    'capabilities': metadata.get('capabilities', {})
                })
            except Exception as e:
                logger.error(f"Failed to load {metadata_file}: {e}")
    
    # Add Earth Engine assets
    ee_discovery = metadata_manager.paths['earth_engine_metadata'] / "asset_discovery.json"
    if ee_discovery.exists():
        try:
            with open(ee_discovery, 'r') as f:
                discovery_data = json.load(f)
                
            # Add featured assets
            for asset in discovery_data.get('featured_assets', []):
                unified_catalog['earth_engine_assets'].append({
                    'service_id': asset['service_id'],
                    'type': 'earth_engine',
                    'asset_id': asset['asset_id'],
                    'title': asset.get('title'),
                    'category': asset.get('category'),
                    'status': 'active'
                })
                
        except Exception as e:
            logger.error(f"Failed to load Earth Engine discovery: {e}")
    
    unified_catalog['total_services'] = (
        len(unified_catalog['env_agents_services']) + 
        len(unified_catalog['earth_engine_assets'])
    )
    
    # Save unified catalog
    with open(unified_path, 'w') as f:
        json.dump(unified_catalog, f, indent=2)
    
    logger.info(f"Created unified catalog with {unified_catalog['total_services']} services")


def main():
    parser = argparse.ArgumentParser(description="Refresh env-agents metadata")
    parser.add_argument('--service', help="Refresh specific service only")
    parser.add_argument('--force', action='store_true', help="Force refresh even if cache is fresh")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose logging")
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting metadata refresh...")
    
    # Initialize managers
    config = get_config()
    metadata_manager = get_metadata_manager()
    
    try:
        if args.service:
            # Refresh specific service
            if args.service.upper() == 'EARTH_ENGINE':
                refresh_earth_engine_metadata(metadata_manager, args.force)
            else:
                refresh_service_metadata(metadata_manager, args.service, args.force)
        else:
            # Refresh all
            logger.info("Refreshing all metadata...")
            
            # Refresh Earth Engine
            refresh_earth_engine_metadata(metadata_manager, args.force)
            
            # Refresh env-agents services
            services = ['NASA_POWER', 'US_EIA', 'EPA_AQS', 'SoilGrids', 'GBIF', 'OpenAQ', 'OSM_Overpass', 'USGS_NWIS']
            for service in services:
                refresh_service_metadata(metadata_manager, service, args.force)
        
        # Create unified catalog
        create_unified_catalog(metadata_manager)
        
        logger.info("Metadata refresh completed successfully")
        
    except Exception as e:
        logger.error(f"Metadata refresh failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()