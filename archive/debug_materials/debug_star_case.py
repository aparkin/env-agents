#!/usr/bin/env python3
"""
Debug the specific '*' (all parameters) case step by step
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
from env_agents.core.models import Geometry, RequestSpec

def debug_star_case():
    print("🔍 Debugging '*' (All Parameters) Case")
    print("=" * 40)
    
    adapter = UsdaSurgoAdapter()
    
    # Test the property mapping pipeline step by step
    print("🔧 Testing property mapping pipeline:")
    
    # Step 1: Test _get_requested_properties with "*"
    variables_star = ["*"]
    properties = adapter._get_requested_properties(variables_star)
    print(f"1. _get_requested_properties(['*']) → {properties}")
    print(f"   Count: {len(properties)}")
    print(f"   First few: {properties[:5]}")
    
    # Step 2: Test _fetch_dynamic_optimized property mapping
    print(f"\n2. Testing property mapping in _fetch_dynamic_optimized:")
    
    valid_properties = []
    for prop in properties:
        # Simulate the mapping logic
        if prop in adapter.SOIL_PROPERTIES:
            valid_properties.append(prop)
            print(f"   ✅ {prop} → direct SURGO property")
        else:
            # Try reverse lookup 
            found = False
            for surgo_prop, canonical in adapter.SOIL_PROPERTIES.items():
                if prop == canonical:
                    valid_properties.append(surgo_prop)
                    print(f"   ✅ {prop} → {surgo_prop} (canonical lookup)")
                    found = True
                    break
            if not found:
                print(f"   ❌ {prop} → no mapping found")
    
    print(f"\n   Valid properties after mapping: {len(valid_properties)}")
    print(f"   After 8-property limit: {valid_properties[:8]}")
    
    # Step 3: Test actual query execution  
    print(f"\n3. Testing actual query execution:")
    try:
        davis_ca = [-121.74, 38.54]
        geometry = Geometry(type="point", coordinates=davis_ca)
        
        # Try to call _query_surgo_database directly
        soil_data = adapter._query_surgo_database(geometry, properties)
        print(f"   Raw soil data returned: {len(soil_data)} records")
        if soil_data:
            print(f"   Sample record keys: {list(soil_data[0].keys()) if soil_data else 'None'}")
        
        # Try full pipeline
        spec = RequestSpec(
            geometry=geometry,
            variables=["*"]
        )
        
        rows = adapter._fetch_rows(spec)
        print(f"   Final rows returned: {len(rows)}")
        
        if rows:
            print(f"   Sample row variables: {[r.get('variable') for r in rows[:3]]}")
        else:
            print(f"   No final rows - parsing issue?")
            
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

    print(f"\n💡 DIAGNOSIS:")
    print(f"If valid_properties is populated but final rows is empty,")
    print(f"the issue is likely in _parse_surgo_data() variable mapping.")

if __name__ == "__main__":
    debug_star_case()