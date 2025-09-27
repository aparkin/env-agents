#!/usr/bin/env python3
"""
Test SURGO fix - using working legacy parameters
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Test locations
SALINAS_CA = [-121.6555, 36.6777]
DAVIS_CA = [-121.74, 38.54]

def test_surgo_fix():
    print("🌱 Testing SURGO Fix")
    print("=" * 30)
    
    router = EnvRouter(base_dir=".")
    
    # Import fixed SURGO
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    
    print("✅ SURGO adapter registered")
    
    # Test with different parameter patterns
    test_cases = [
        {
            "name": "Single parameter",
            "variables": ["soil:clay_content_percent"], 
            "location": DAVIS_CA,
            "description": "Request only clay content"
        },
        {
            "name": "Multiple parameters",
            "variables": ["soil:clay_content_percent", "soil:sand_content_percent", "soil:ph_h2o"],
            "location": SALINAS_CA,
            "description": "Request 3 soil properties"
        },
        {
            "name": "All available",
            "variables": ["*"],  # This should get all available
            "location": DAVIS_CA,
            "description": "Request all available parameters"
        },
        {
            "name": "Legacy-style names", 
            "variables": ["soil:clay_pct", "soil:ph_h2o"],  # Legacy naming
            "location": SALINAS_CA,
            "description": "Using legacy variable names"
        }
    ]
    
    # Show capabilities first
    try:
        caps = surgo_adapter.capabilities()
        variables = caps.get('variables', [])
        print(f"\n📊 SURGO Capabilities: {len(variables)} variables")
        print("Available variables:")
        for i, var in enumerate(variables[:5], 1):
            canonical = var.get('canonical', 'N/A')
            platform = var.get('platform', 'N/A')  
            unit = var.get('unit', 'N/A')
            print(f"  {i}. {canonical} (platform: {platform}, unit: {unit})")
        if len(variables) > 5:
            print(f"     ... and {len(variables) - 5} more")
    except Exception as e:
        print(f"❌ Capabilities failed: {e}")
        return
    
    # Test each case
    for i, case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {case['name']}")
        print(f"📝 {case['description']}")
        print(f"📍 Location: {case['location']}")
        print(f"🔬 Variables: {case['variables']}")
        
        try:
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=case['location']),
                variables=case['variables']
            )
            
            df = router.fetch("USDA_SURGO", spec)
            
            if df is not None and len(df) > 0:
                print(f"✅ SUCCESS: {len(df)} rows × {len(df.columns)} columns")
                
                # Show variables returned
                if 'variable' in df.columns:
                    vars_returned = df['variable'].unique()
                    print(f"   Variables returned: {list(vars_returned)}")
                
                # Show sample values
                if 'value' in df.columns:
                    values = df['value'].dropna()
                    if len(values) > 0:
                        print(f"   Value range: {values.min():.2f} to {values.max():.2f}")
                        
                # Show sample data
                display_cols = ["variable", "value", "unit", "depth_top_cm", "depth_bottom_cm"]
                available_cols = [col for col in display_cols if col in df.columns]
                if available_cols and len(df) > 0:
                    print("   Sample data:")
                    sample = df[available_cols].head(2)
                    for _, row in sample.iterrows():
                        var = row.get('variable', 'N/A')
                        val = row.get('value', 'N/A')
                        unit = row.get('unit', 'N/A')
                        depth = f"{row.get('depth_top_cm', 'N/A')}-{row.get('depth_bottom_cm', 'N/A')}cm"
                        print(f"     {var}: {val} {unit} at {depth}")
            else:
                print(f"ℹ️  No data returned (may be no SURGO coverage for this location)")
                
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            
            # Show more detail for debugging
            if "400 Client Error" in str(e):
                print("   This is likely a URL or query format issue")
            elif "timeout" in str(e).lower():
                print("   Service timeout - may be overloaded")
            else:
                print(f"   Error type: {type(e).__name__}")

    print(f"\n🎯 SURGO testing complete!")

if __name__ == "__main__":
    test_surgo_fix()