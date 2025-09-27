#!/usr/bin/env python3
"""
Quick test script to validate unified router setup
"""

import sys
import logging
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent))

def test_unified_router():
    print("🧪 Testing Unified Router Setup")
    print("=" * 40)
    
    try:
        # Test configuration loading
        print("\n1. Testing Configuration...")
        from env_agents.core.config import get_config
        config = get_config()
        print(f"   ✅ Config loaded: {config.base_dir}")
        
        # Test metadata manager
        print("\n2. Testing Metadata Manager...")
        metadata_manager = config.get_metadata_manager()
        print(f"   ✅ Metadata manager created")
        
        # Check Earth Engine files
        ee_catalog = metadata_manager.get_earth_engine_catalog()
        ee_discovery = metadata_manager.get_earth_engine_discovery()
        
        if ee_catalog:
            print(f"   ✅ Earth Engine catalog: {len(ee_catalog)} assets")
        else:
            print(f"   ⚠️  Earth Engine catalog: Not found")
            
        if ee_discovery:
            featured_count = len(ee_discovery.get('featured_assets', []))
            print(f"   ✅ Earth Engine discovery: {featured_count} featured assets")
            
            # Show featured assets
            for i, asset in enumerate(ee_discovery.get('featured_assets', [])[:3]):
                print(f"      {i+1}. {asset['service_id']}: {asset['title']}")
        else:
            print(f"   ⚠️  Earth Engine discovery: Not found")
        
        # Test unified router creation
        print("\n3. Testing Unified Router Creation...")
        from env_agents.core.unified_router import get_unified_router
        
        # Create without Earth Engine first
        router_no_ee = get_unified_router(include_earth_engine=False)
        print(f"   ✅ Router without EE: {len(router_no_ee.adapters)} adapters")
        
        # Create with Earth Engine
        router_with_ee = get_unified_router(include_earth_engine=True)
        print(f"   ✅ Router with EE: {len(router_with_ee.adapters)} adapters")
        
        # Show registered adapters
        print(f"\n4. Registered Adapters:")
        for adapter_name in sorted(router_with_ee.adapters.keys()):
            print(f"   • {adapter_name}")
        
        # Test capabilities
        print(f"\n5. Testing Capabilities...")
        capabilities = router_with_ee.capabilities()
        unified_info = capabilities.get('unified_router', {})
        
        print(f"   📊 Total Services: {unified_info.get('total_services', 0)}")
        print(f"   🌐 env-agents Services: {unified_info.get('env_agents_services', 0)}")
        print(f"   🛰️  Earth Engine Services: {unified_info.get('earth_engine_services', 0)}")
        
        # Test service discovery
        print(f"\n6. Testing Service Discovery...")
        env_services = router_with_ee.list_services('env_agent')
        ee_services = router_with_ee.list_services('earth_engine')
        
        print(f"   🌐 Found {len(env_services)} env-agent services")
        print(f"   🛰️  Found {len(ee_services)} Earth Engine services")
        
        if ee_services:
            example_ee = ee_services[0]['service_id']
            print(f"\n7. Testing Service Info for: {example_ee}")
            try:
                ee_info = router_with_ee.get_service_info(example_ee)
                print(f"   ✅ Service info retrieved")
                print(f"   Title: {ee_info.get('title', 'N/A')}")
                print(f"   Type: {ee_info.get('service_type', 'unknown')}")
                print(f"   Status: {ee_info.get('status', 'unknown')}")
            except Exception as e:
                print(f"   ❌ Service info failed: {e}")
        
        print(f"\n✅ Unified Router Test Complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Unified Router Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_unified_router()
    sys.exit(0 if success else 1)