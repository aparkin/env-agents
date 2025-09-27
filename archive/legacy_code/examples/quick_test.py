#!/usr/bin/env python3
"""
Quick test script to validate the five services are working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🧪 Quick Service Validation")
print("=" * 40)

# Test imports
services_to_test = [
    ("USGS NWIS", "env_agents.adapters.nwis.adapter", "UsgsNwisLiveAdapter"),
    ("OpenAQ", "env_agents.adapters.openaq.adapter", "OpenaqV3Adapter"), 
    ("NASA POWER", "env_agents.adapters.power.adapter", "NasaPowerDailyAdapter"),
    ("USDA SURGO", "env_agents.adapters.soil.surgo_adapter", "UsdaSurgoAdapter"),
    ("ISRIC SoilGrids", "env_agents.adapters.soil.soilgrids_adapter", "IsricSoilGridsAdapter")
]

results = {}

for service_name, module_path, class_name in services_to_test:
    try:
        print(f"\n🔍 Testing {service_name}...")
        
        # Import
        module = __import__(module_path, fromlist=[class_name])
        adapter_class = getattr(module, class_name)
        
        # Instantiate
        adapter = adapter_class()
        print(f"  ✅ Import and instantiation OK")
        
        # Test capabilities
        caps = adapter.capabilities()
        variables = caps.get('variables', [])
        print(f"  ✅ Capabilities OK: {len(variables)} variables")
        
        # Test harvest if available
        if hasattr(adapter, 'harvest'):
            harvested = adapter.harvest()
            print(f"  ✅ Harvest OK: {len(harvested)} parameters")
        else:
            print(f"  ⚠️  No harvest() method")
        
        results[service_name] = {
            'status': 'OK',
            'variables': len(variables),
            'harvested': len(harvested) if hasattr(adapter, 'harvest') else 0
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results[service_name] = {
            'status': 'ERROR',
            'error': str(e)
        }

# Summary
print(f"\n📊 Summary:")
passed = sum(1 for r in results.values() if r['status'] == 'OK')
total = len(results)
print(f"Services: {passed}/{total} passed ({passed/total:.1%})")

for service, result in results.items():
    if result['status'] == 'OK':
        print(f"  ✅ {service}: {result['variables']} vars, {result['harvested']} harvested")
    else:
        print(f"  ❌ {service}: {result['error']}")

sys.exit(0 if passed == total else 1)