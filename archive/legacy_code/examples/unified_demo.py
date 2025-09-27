#!/usr/bin/env python3
"""
Unified Environmental Data Platform Demo

Demonstrates the complete unified system that integrates:
1. 7+ env-agents services (weather, soil, water quality, etc.)
2. 997+ Earth Engine assets as individual discoverable services
3. Unified configuration, metadata, and discovery system
4. Ecognita-ready interface

This is the culmination of our comprehensive configuration and integration work.
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.unified_router import get_unified_router
from env_agents.core.config import get_config


def demonstrate_unified_platform():
    """Demonstrate the complete unified environmental data platform"""
    
    print("🌍 Unified Environmental Data Platform Demo")
    print("=" * 50)
    
    # Initialize unified router with configuration system
    print("\n1. Initializing Unified Router...")
    try:
        router = get_unified_router(include_earth_engine=True)
        config = get_config()
        print(f"   ✅ Router initialized with base directory: {config.base_dir}")
        print(f"   📁 Configuration directory: {config.config_dir}")
        print(f"   📊 Data directory: {config.data_dir}")
    except Exception as e:
        print(f"   ❌ Failed to initialize router: {e}")
        return
    
    # Display unified capabilities
    print("\n2. Unified Service Capabilities...")
    try:
        capabilities = router.capabilities()
        unified_info = capabilities.get('unified_router', {})
        
        print(f"   🔧 Total Services: {unified_info.get('total_services', 0)}")
        print(f"   🏢 env-agents Services: {unified_info.get('env_agents_services', 0)}")
        print(f"   🛰️  Earth Engine Services: {unified_info.get('earth_engine_services', 0)}")
        
        # Show service types
        discovery = unified_info.get('service_discovery', {})
        service_types = discovery.get('service_types', [])
        print(f"   📋 Service Types: {', '.join(service_types)}")
        
    except Exception as e:
        print(f"   ⚠️  Could not retrieve capabilities: {e}")
    
    # List available services
    print("\n3. Service Discovery...")
    try:
        # List env-agents services
        env_services = router.list_services('env_agent')
        print(f"   🌐 env-agents Services ({len(env_services)}):")
        for service in env_services[:5]:  # Show first 5
            status = "✅" if service.get('status') == 'active' else "⚠️"
            print(f"      {status} {service['service_id']}: {service.get('title', 'N/A')}")
        
        if len(env_services) > 5:
            print(f"      ... and {len(env_services) - 5} more")
        
        # List Earth Engine services
        ee_services = router.list_services('earth_engine')
        print(f"\n   🛰️  Earth Engine Featured Assets ({len(ee_services)}):")
        for service in ee_services[:5]:  # Show first 5
            category = service.get('category', 'general')
            print(f"      🌍 {service['service_id']}: {service.get('title', 'N/A')} ({category})")
        
        if len(ee_services) > 5:
            print(f"      ... and {len(ee_services) - 5} more")
            
    except Exception as e:
        print(f"   ⚠️  Service discovery failed: {e}")
    
    # Demonstrate search functionality
    print("\n4. Service Search Capabilities...")
    try:
        # Search for climate/weather related services
        climate_services = router.search_services("climate", limit=5)
        print(f"   🔍 Climate-related services ({len(climate_services)}):")
        for service in climate_services:
            score = service.get('search_score', 0)
            service_type = service.get('service_type', 'unknown')
            icon = "🛰️" if service_type == 'earth_engine' else "🌐"
            print(f"      {icon} {service['service_id']} (score: {score})")
        
        # Search for soil-related services  
        soil_services = router.search_services("soil", limit=5)
        print(f"\n   🔍 Soil-related services ({len(soil_services)}):")
        for service in soil_services:
            score = service.get('search_score', 0)
            service_type = service.get('service_type', 'unknown')
            icon = "🛰️" if service_type == 'earth_engine' else "🌐"
            print(f"      {icon} {service['service_id']} (score: {score})")
            
    except Exception as e:
        print(f"   ⚠️  Search failed: {e}")
    
    # Show detailed service information
    print("\n5. Detailed Service Information...")
    try:
        # Get info for a specific service
        service_list = router.list_adapters()
        if service_list:
            example_service = service_list[0]
            service_info = router.get_service_info(example_service)
            
            print(f"   📋 Example Service: {example_service}")
            print(f"      Title: {service_info.get('title', 'N/A')}")
            print(f"      Type: {service_info.get('service_type', 'unknown')}")
            print(f"      Status: {service_info.get('status', 'unknown')}")
            print(f"      Variables: {len(service_info.get('example_variables', []))}")
            print(f"      Provider: {service_info.get('provider', 'N/A')}")
            
    except Exception as e:
        print(f"   ⚠️  Service info failed: {e}")
    
    # Demonstrate configuration management
    print("\n6. Configuration Management...")
    try:
        metadata_manager = config.get_metadata_manager()
        
        # Show configuration status
        print(f"   📁 Credentials file: {'✅ Found' if config.get_credentials_file().exists() else '❌ Missing'}")
        print(f"   📁 Services config: {'✅ Found' if config.get_services_config_file().exists() else '❌ Missing'}")
        
        # Show Earth Engine status
        ee_catalog = metadata_manager.get_earth_engine_catalog()
        ee_discovery = metadata_manager.get_earth_engine_discovery()
        
        if ee_catalog:
            print(f"   🛰️  Earth Engine catalog: ✅ {len(ee_catalog)} assets")
        else:
            print(f"   🛰️  Earth Engine catalog: ❌ Not found")
            
        if ee_discovery:
            featured_count = len(ee_discovery.get('featured_assets', []))
            categories_count = len(ee_discovery.get('categories', {}))
            print(f"   🛰️  Earth Engine discovery: ✅ {featured_count} featured, {categories_count} categories")
        else:
            print(f"   🛰️  Earth Engine discovery: ❌ Not found")
        
    except Exception as e:
        print(f"   ⚠️  Configuration check failed: {e}")
    
    # Export unified catalog
    print("\n7. Unified Catalog Export...")
    try:
        # Export in different formats
        catalog_json = router.export_unified_catalog('json')
        catalog_df = router.export_unified_catalog('pandas')
        catalog_stac = router.export_unified_catalog('stac')
        
        print(f"   📄 JSON catalog: {len(catalog_json)} characters")
        print(f"   📊 DataFrame catalog: {len(catalog_df)} services")
        print(f"   🌐 STAC catalog: {catalog_stac.get('summaries', {}).get('total_services', 0)} services")
        
        # Save JSON catalog for reference
        catalog_file = Path("unified_catalog.json")
        with open(catalog_file, 'w') as f:
            f.write(catalog_json)
        print(f"   💾 Saved catalog to: {catalog_file}")
        
    except Exception as e:
        print(f"   ⚠️  Catalog export failed: {e}")
    
    # Show metadata standardization
    print("\n8. Metadata Standardization...")
    try:
        metadata_manager = config.get_metadata_manager()
        
        # Export unified metadata
        unified_metadata = metadata_manager.export_unified_metadata('json')
        
        # Parse and show summary
        metadata_dict = json.loads(unified_metadata) if isinstance(unified_metadata, str) else unified_metadata
        total_services = metadata_dict.get('total_services', 0)
        services = metadata_dict.get('services', {})
        
        print(f"   📋 Total standardized services: {total_services}")
        
        # Count by service type
        env_agents_count = len([s for s in services.values() if s.get('service_type') == 'env_agent'])
        earth_engine_count = len([s for s in services.values() if s.get('service_type') == 'earth_engine'])
        
        print(f"   🌐 env-agents services: {env_agents_count}")
        print(f"   🛰️  Earth Engine services: {earth_engine_count}")
        
        # Save unified metadata
        metadata_file = Path("unified_metadata.json")
        with open(metadata_file, 'w') as f:
            f.write(unified_metadata if isinstance(unified_metadata, str) else json.dumps(unified_metadata, indent=2))
        print(f"   💾 Saved metadata to: {metadata_file}")
        
    except Exception as e:
        print(f"   ⚠️  Metadata standardization failed: {e}")
    
    print("\n✅ Unified Platform Demo Complete!")
    print("\nThis demonstration shows:")
    print("• Unified configuration management with centralized credentials")
    print("• Integration of env-agents services and Earth Engine assets") 
    print("• Consistent metadata format across all 1000+ services")
    print("• Service discovery, search, and detailed information retrieval")
    print("• Multiple export formats (JSON, DataFrame, STAC)")
    print("• Ecognita-ready interface for environmental data integration")


if __name__ == "__main__":
    demonstrate_unified_platform()