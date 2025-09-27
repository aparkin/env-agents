#!/usr/bin/env python3
"""
Test SURGO "all parameters" behavior specifically
Debug why * (all parameters) didn't return data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

def test_all_parameters_debug():
    print("🔍 Debugging SURGO 'All Parameters' Behavior")
    print("=" * 50)
    
    router = EnvRouter(base_dir=".")
    
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    
    # Get all available properties
    caps = surgo_adapter.capabilities()
    all_properties = [v['canonical'] for v in caps.get('variables', [])]
    print(f"📊 Total available properties: {len(all_properties)}")
    print(f"Properties: {all_properties}")
    
    # Test location
    davis_ca = [-121.74, 38.54]
    
    # Test scenarios with different property counts
    test_cases = [
        {
            "name": "All properties (*)",
            "variables": ["*"],
            "description": "Request all 15 properties"
        },
        {
            "name": "First 8 properties (under dynamic limit)",
            "variables": all_properties[:8],
            "description": "Request first 8 properties directly"
        },
        {
            "name": "All 15 properties explicitly", 
            "variables": all_properties,
            "description": "Request all 15 properties by name"
        },
        {
            "name": "First 5 properties",
            "variables": all_properties[:5], 
            "description": "Request first 5 properties"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {case['name']}")
        print(f"📝 {case['description']}")
        print(f"🔢 Property count: {len(case['variables'])}")
        
        try:
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=davis_ca),
                variables=case['variables']
            )
            
            df = router.fetch("USDA_SURGO", spec)
            
            if df is not None and len(df) > 0:
                variables_returned = df['variable'].unique() if 'variable' in df.columns else []
                print(f"✅ SUCCESS: {len(df)} rows")
                print(f"   Variables returned ({len(variables_returned)}): {list(variables_returned)}")
                
                # Check if this used dynamic path (returned exactly what was requested)
                requested_count = len(case['variables']) if case['variables'] != ["*"] else len(all_properties)
                if len(variables_returned) == requested_count and len(variables_returned) <= 8:
                    print(f"   🚀 Likely used DYNAMIC path (exact match, ≤8 properties)")
                elif len(variables_returned) == 6:  # Fixed properties from fallback 
                    print(f"   🔄 Likely used FALLBACK path (fixed property set)")
                else:
                    print(f"   ❓ Path unclear (returned {len(variables_returned)} of {requested_count} requested)")
                
            else:
                print(f"❌ FAILED: No data returned")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            
            # Check if this was a dynamic query failure
            if "Dynamic SURGO query failed" in str(e):
                print("   → Dynamic query failed, fallback should have activated")
            elif "400" in str(e):
                print("   → API rejected query format")

    print(f"\n💡 ANALYSIS:")
    print(f"If 'all parameters (*)' fails but smaller subsets work, it suggests:")
    print(f"  • SURGO API may have limits on query complexity/column count")  
    print(f"  • 15 properties in one query may be too many")
    print(f"  • Dynamic path works but has practical limits")
    print(f"  • Need to implement chunking for large property sets")

if __name__ == "__main__":
    test_all_parameters_debug()