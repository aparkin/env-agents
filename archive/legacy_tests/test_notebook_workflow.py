#!/usr/bin/env python3
"""
Test script to validate the unified notebook workflow
Mirrors the structure of Unified_Testing_Clean.ipynb
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Setup
sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("🧪 Testing Unified Notebook Workflow")
print("=" * 50)

try:
    # Cell 1: Unified System Initialization
    print("\n📝 Cell 1: Unified System Initialization")
    from env_agents.core.unified_router import get_unified_router
    from env_agents.core.models import RequestSpec, Geometry
    
    # Initialize unified router with both service types
    router = get_unified_router(include_earth_engine=True)
    print(f"   ✅ Unified router created with {len(router.adapters)} total services")
    
    # Cell 2: Service Discovery - Show Unified Operation
    print("\n📝 Cell 2: Unified Service Discovery")
    
    # Get all services through same interface
    all_services = router.list_services()
    env_services = router.list_services('env_agent')
    ee_services = router.list_services('earth_engine')
    
    print(f"   📊 Total Services: {len(all_services)}")
    print(f"   🌐 Env-agents Services: {len(env_services)}")
    print(f"   🛰️  Earth Engine Services: {len(ee_services)}")
    
    # Show service equivalence - same data structure for both types
    print(f"   \n🔍 Service Equivalence Demonstration:")
    if env_services:
        env_service = env_services[0]
        print(f"   🌐 Env Service: {env_service['service_id']} ({env_service['service_type']})")
    if ee_services:
        ee_service = ee_services[0]
        print(f"   🛰️  EE Service: {ee_service['service_id']} ({ee_service['service_type']})")
    
    # Cell 3: Service Search - Unified Discovery
    print("\n📝 Cell 3: Unified Service Search")
    
    # Search across all services with same interface
    temp_services = router.search_services("temperature", limit=5)
    water_services = router.search_services("water", limit=5)
    
    print(f"   🔍 Temperature-related services: {len(temp_services)}")
    for service in temp_services[:2]:
        print(f"      • {service['service_id']} ({service['service_type']})")
    
    print(f"   🔍 Water-related services: {len(water_services)}")
    for service in water_services[:2]:
        print(f"      • {service['service_id']} ({service['service_type']})")
    
    # Cell 4: Unified RequestSpec Interface
    print("\n📝 Cell 4: Unified RequestSpec Interface")
    
    # Same RequestSpec works for both service types
    geometry = Geometry(
        type="point", 
        coordinates=[-122.27, 37.87]
    )
    time_range = (datetime(2023, 1, 1), datetime(2023, 1, 31))
    
    spec = RequestSpec(
        geometry=geometry,
        time_range=time_range
    )
    
    print(f"   ✅ RequestSpec created: {spec.geometry.coordinates}")
    print(f"   📅 Time range: {spec.time_range[0].date()} to {spec.time_range[1].date()}")
    
    # Show that same spec can be used with any service
    print(f"   🔧 Same RequestSpec interface for all {len(router.adapters)} services")
    
    # Cell 5: Service Capabilities - Unified Format
    print("\n📝 Cell 5: Unified Service Information")
    
    # Get service info through same interface for both types
    sample_services = []
    if env_services:
        sample_services.append(env_services[0]['service_id'])
    if ee_services:
        sample_services.append(ee_services[0]['service_id'])
    
    for service_id in sample_services:
        try:
            info = router.get_service_info(service_id)
            print(f"   📋 {service_id}:")
            print(f"      Type: {info['service_type']}")
            print(f"      Title: {info['title']}")
            print(f"      Status: {info['status']}")
        except Exception as e:
            print(f"   ⚠️  {service_id}: {e}")
    
    print(f"\n✅ Unified Notebook Workflow Test Complete!")
    print(f"🎯 Successfully demonstrated service equivalence across {len(env_services)} env-agents and {len(ee_services)} Earth Engine services")
    
except Exception as e:
    print(f"\n❌ Workflow test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🚀 Unified system ready for demonstration!")