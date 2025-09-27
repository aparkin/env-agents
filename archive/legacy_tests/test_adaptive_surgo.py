#!/usr/bin/env python3
"""
Test SURGO Adaptive Approach (Option 2)
Tests dynamic queries with fallback to fixed queries
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec

# Test locations
SALINAS_CA = [-121.6555, 36.6777]
DAVIS_CA = [-121.74, 38.54]
BERKELEY_CA = [-122.27, 37.87]

def test_adaptive_surgo():
    print("🌱 Testing SURGO Adaptive Approach (Option 2)")
    print("=" * 50)
    
    router = EnvRouter(base_dir=".")
    
    # Import adaptive SURGO
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    surgo_adapter = UsdaSurgoAdapter()
    router.register(surgo_adapter)
    
    print("✅ SURGO adaptive adapter registered")
    
    # Test different scenarios that should trigger different paths
    test_scenarios = [
        {
            "name": "Single property (should use dynamic)",
            "variables": ["soil:clay_content_percent"], 
            "location": DAVIS_CA,
            "expected_path": "dynamic"
        },
        {
            "name": "Multiple valid properties (should use dynamic)", 
            "variables": ["soil:clay_content_percent", "soil:ph_h2o", "soil:organic_matter_percent"],
            "location": SALINAS_CA,
            "expected_path": "dynamic"
        },
        {
            "name": "Many properties (should use dynamic, limited to 8)",
            "variables": ["soil:clay_content_percent", "soil:sand_content_percent", 
                         "soil:silt_content_percent", "soil:ph_h2o", "soil:ph_cacl2",
                         "soil:organic_matter_percent", "soil:bulk_density_g_cm3", 
                         "soil:cation_exchange_capacity", "soil:effective_cec", "soil:field_capacity_percent"],
            "location": BERKELEY_CA,
            "expected_path": "dynamic"
        },
        {
            "name": "All properties (*)",
            "variables": ["*"],
            "location": DAVIS_CA,
            "expected_path": "fallback_likely"
        },
        {
            "name": "Legacy variable names",
            "variables": ["soil:clay_pct", "soil:ph_h2o", "soil:bulk_density"],
            "location": SALINAS_CA,
            "expected_path": "dynamic"
        },
        {
            "name": "Invalid/unknown properties (should fallback to defaults)",
            "variables": ["soil:unknown_property", "soil:invalid_param"],
            "location": DAVIS_CA,
            "expected_path": "fallback"
        }
    ]
    
    # Show capabilities first
    try:
        caps = surgo_adapter.capabilities()
        variables = caps.get('variables', [])
        print(f"\n📊 SURGO Capabilities: {len(variables)} variables")
        print("Sample variables:")
        for i, var in enumerate(variables[:3], 1):
            canonical = var.get('canonical', 'N/A')
            unit = var.get('unit', 'N/A')
            print(f"  {i}. {canonical} ({unit})")
        print(f"     ... and {len(variables) - 3} more")
    except Exception as e:
        print(f"❌ Capabilities failed: {e}")
        return
    
    # Test each scenario
    results_summary = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test {i}: {scenario['name']}")
        print(f"📝 Expected path: {scenario['expected_path']}")
        print(f"📍 Location: {scenario['location']}")  
        print(f"🔬 Variables: {scenario['variables']}")
        
        try:
            spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=scenario['location']),
                variables=scenario['variables']
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
                        
                # Detect which path was likely used based on returned data
                actual_path = "unknown"
                if len(vars_returned) == len(scenario['variables']) and "*" not in scenario['variables']:
                    actual_path = "dynamic"
                elif len(vars_returned) > len(scenario['variables']) or "*" in scenario['variables']:
                    actual_path = "fallback"
                elif 'soil:unknown_property' in scenario['variables'] and len(vars_returned) > 0:
                    actual_path = "fallback"
                    
                print(f"   Detected path: {actual_path}")
                
                results_summary.append({
                    "test": scenario['name'],
                    "expected": scenario['expected_path'],
                    "actual": actual_path,
                    "success": True,
                    "rows": len(df),
                    "variables": len(vars_returned)
                })
                
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
                print(f"ℹ️  No data returned")
                results_summary.append({
                    "test": scenario['name'],
                    "expected": scenario['expected_path'],
                    "actual": "no_data",
                    "success": False,
                    "rows": 0,
                    "variables": 0
                })
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED: {error_msg}")
            
            # Analyze error type
            if "Dynamic SURGO query failed" in error_msg:
                print("   → Dynamic query failed, fallback should have been used")
            elif "400 Client Error" in error_msg:
                print("   → API request format issue")
            elif "timeout" in error_msg.lower():
                print("   → Service timeout")
            else:
                print(f"   → Error type: {type(e).__name__}")
            
            results_summary.append({
                "test": scenario['name'],
                "expected": scenario['expected_path'],
                "actual": "error",
                "success": False,
                "error": error_msg[:100],
                "rows": 0,
                "variables": 0
            })

    # Summary report
    print(f"\n📊 ADAPTIVE SURGO TEST SUMMARY")
    print("=" * 40)
    
    successful_tests = sum(1 for r in results_summary if r['success'])
    total_tests = len(results_summary)
    total_rows = sum(r['rows'] for r in results_summary)
    
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    print(f"📊 Total data rows retrieved: {total_rows}")
    
    for result in results_summary:
        status = "✅" if result['success'] else "❌"
        expected = result['expected']
        actual = result.get('actual', 'unknown')
        
        print(f"{status} {result['test']}")
        print(f"     Expected: {expected} | Actual: {actual}")
        if result['success']:
            print(f"     Data: {result['rows']} rows, {result['variables']} variables")
        elif 'error' in result:
            print(f"     Error: {result['error']}")
    
    # Analysis of adaptive behavior
    print(f"\n🔍 ADAPTIVE BEHAVIOR ANALYSIS:")
    
    dynamic_attempts = [r for r in results_summary if 'dynamic' in r['expected']]
    fallback_triggers = [r for r in results_summary if r['actual'] == 'fallback']
    
    print(f"• Tests designed for dynamic queries: {len(dynamic_attempts)}")
    print(f"• Tests that triggered fallback: {len(fallback_triggers)}")
    
    if fallback_triggers:
        print("• Fallback was triggered for:")
        for r in fallback_triggers:
            print(f"  - {r['test']}")
    
    print(f"\n💡 METADATA FORMAT ISSUE EXPLANATION:")
    print(f"The METADATA format fails because it adds column metadata rows to the response.")
    print(f"Example: JSON+COLUMNNAME returns: [['col1','col2'], ['val1','val2']]")
    print(f"But JSON+COLUMNNAME+METADATA returns: [['col1','col2'], ['metadata_row'], ['val1','val2']]") 
    print(f"This breaks parsing logic expecting data immediately after headers.")
    print(f"Our adaptive approach avoids this by using only JSON+COLUMNNAME format.")
    
    print(f"\n🎯 Adaptive SURGO testing complete!")

if __name__ == "__main__":
    test_adaptive_surgo()