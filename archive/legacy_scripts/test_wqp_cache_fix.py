#!/usr/bin/env python3
"""
Test WQP Adapter with Cache Invalidation
"""
import sys
import importlib
from datetime import datetime

# Step 1: Clear all WQP related modules from cache
print('🔧 CLEARING MODULE CACHE FOR WQP ADAPTER')
print('=' * 45)

modules_to_clear = [
    'env_agents.adapters.wqp.enhanced_adapter',
    'env_agents.adapters.wqp',
    'env_agents.adapters',
    'env_agents'
]

for module_name in modules_to_clear:
    if module_name in sys.modules:
        print(f'  Clearing {module_name}')
        del sys.modules[module_name]
    else:
        print(f'  {module_name} (not loaded)')

print('✅ Cache cleared\n')

# Step 2: Fresh import and test
print('🧪 TESTING WQP WITH FRESH MODULE')
print('=' * 35)

from env_agents.adapters.wqp.enhanced_adapter import EnhancedWQPAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_wqp_fresh():
    """Test WQP with fresh module - no cache"""
    
    adapter = EnhancedWQPAdapter()
    print('✅ Fresh WQP adapter initialized')
    
    # Test locations that should find data
    test_locations = [
        {'name': 'Washington DC', 'coords': [-77.0369, 38.9072], 'time_range': ('2023-01-01', '2024-08-31')},
        {'name': 'Denver CO', 'coords': [-104.9903, 39.7392], 'time_range': ('2023-01-01', '2024-08-31')},
        {'name': 'San Francisco Bay', 'coords': [-122.25, 37.8], 'time_range': ('2023-01-01', '2024-08-31')}
    ]
    
    successful_tests = 0
    total_records = 0
    
    for location in test_locations:
        print(f'\n🧪 Testing {location["name"]}:')
        
        geometry = Geometry(type='point', coordinates=location['coords'])
        spec = RequestSpec(
            geometry=geometry,
            time_range=location['time_range'],
            variables=['Temperature']
        )
        
        start_time = datetime.now()
        rows = adapter._fetch_rows(spec)
        fetch_time = (datetime.now() - start_time).total_seconds()
        
        if rows and len(rows) > 0:
            print(f'  ✅ Success: {len(rows)} records in {fetch_time:.2f}s')
            print(f'  Sample: {rows[0].get("variable")} = {rows[0].get("value")} {rows[0].get("unit")}')
            successful_tests += 1
            total_records += len(rows)
        else:
            print(f'  ⚠️ No data: 0 records in {fetch_time:.2f}s')
    
    print(f'\n📊 FRESH MODULE TEST RESULTS:')
    print(f'  Successful locations: {successful_tests}/{len(test_locations)}')
    print(f'  Total records retrieved: {total_records}')
    
    if successful_tests > 0:
        print('✅ WQP adapter is working with fresh module!')
        return True
    else:
        print('⚠️ WQP adapter still not finding data')
        return False

# Run the test
if __name__ == "__main__":
    success = test_wqp_fresh()
    
    print(f'\n🎯 FINAL RESULT:')
    if success:
        print('🚀 WQP adapter fix confirmed working')
        print('💡 Notebook will need to restart kernel or clear cache to see changes')
    else:
        print('🔧 WQP adapter still needs debugging')