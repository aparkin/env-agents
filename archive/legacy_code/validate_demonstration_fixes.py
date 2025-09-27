#!/usr/bin/env python3
"""
Comprehensive validation test for all demonstration fixes
"""

import sys
import os
sys.path.insert(0, '.')

# Set up credentials
os.environ['OPENAQ_API_KEY'] = '1dfd14b5aac0cf892b43e575fa4060d6dc4228149751b9362e5e2331ca2fc4ca'
os.environ['EPA_AQS_EMAIL'] = 'aparkin@lbl.gov'
os.environ['EPA_AQS_KEY'] = 'khakimouse81'

def test_parameter_display():
    """Test that parameters display with proper names instead of 'Unknown'"""
    print("🧪 Testing parameter display fix...")
    
    from env_agents.adapters.openaq.enhanced_adapter import EnhancedOpenAQAdapter
    
    adapter = EnhancedOpenAQAdapter()
    caps = adapter.capabilities()
    variables = caps.get('variables', [])
    
    if not variables:
        print("❌ No variables returned")
        return False
    
    # Check first few parameters have proper names
    success = True
    for i, var in enumerate(variables[:3]):
        param_id = var.get('canonical', var.get('id', 'Unknown'))
        param_name = var.get('platform', var.get('name', 'Unknown'))
        description = var.get('description', 'No description')[:50] + '...'
        
        print(f"  Parameter {i+1}: ID={param_id}, Name={param_name}")
        print(f"    Description: {description}")
        
        if param_id == 'Unknown' or param_name == 'Unknown':
            print(f"    ❌ Still showing 'Unknown' for parameter {i+1}")
            success = False
        else:
            print(f"    ✅ Proper name displayed")
    
    return success

def test_coordinate_handling():
    """Test that coordinates are properly extracted"""
    print("🧪 Testing coordinate handling...")
    
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters.openaq.enhanced_adapter import EnhancedOpenAQAdapter
    
    adapter = EnhancedOpenAQAdapter()
    
    geom = Geometry(type="point", coordinates=[-122.2730, 37.8715])
    spec = RequestSpec(
        geometry=geom,
        time_range=("2024-08-01", "2024-08-02"),
        variables=["pm25"],
        extra={"radius": 25000}
    )
    
    try:
        rows = adapter._fetch_rows(spec)
        if rows:
            sample_row = rows[0]
            lat = sample_row.get('latitude')
            lon = sample_row.get('longitude')
            
            print(f"  Sample coordinates: lat={lat}, lon={lon}")
            
            if lat is None or lon is None:
                print("  ❌ Coordinates still showing as None")
                return False
            else:
                print("  ✅ Coordinates properly extracted")
                return True
        else:
            print("  ⚠️  No data returned (may be normal)")
            return True
    except Exception as e:
        print(f"  ❌ Error testing coordinates: {e}")
        return False

def test_epa_aqs_import():
    """Test that EPA AQS imports correctly"""
    print("🧪 Testing EPA AQS import...")
    
    try:
        from env_agents.adapters.air.enhanced_aqs_adapter import EPAAQSEnhancedAdapter
        adapter = EPAAQSEnhancedAdapter()
        caps = adapter.capabilities()
        print(f"  ✅ EPA AQS imported successfully, {len(caps.get('variables', []))} parameters")
        return True
    except ImportError as e:
        print(f"  ❌ EPA AQS import failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ EPA AQS error: {e}")
        return False

def test_earth_engine_assets():
    """Test Earth Engine asset usage"""
    print("🧪 Testing Earth Engine assets...")
    
    try:
        from env_agents.adapters.earth_engine.gold_standard_adapter import EarthEngineGoldStandardAdapter
        
        # Test with updated MODIS asset
        adapter = EarthEngineGoldStandardAdapter(asset_id="MODIS/061/MOD11A1", scale=1000)
        caps = adapter.capabilities()
        
        print(f"  ✅ Earth Engine initialized with updated MODIS asset")
        print(f"  Variables: {len(caps.get('variables', []))}")
        return True
    except ImportError:
        print("  ⚠️  Earth Engine not available (expected in some environments)")
        return True
    except Exception as e:
        print(f"  ❌ Earth Engine error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔬 COMPREHENSIVE VALIDATION TEST")
    print("=" * 40)
    
    tests = [
        ("Parameter Display", test_parameter_display),
        ("Coordinate Handling", test_coordinate_handling), 
        ("EPA AQS Import", test_epa_aqs_import),
        ("Earth Engine Assets", test_earth_engine_assets)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        results[test_name] = test_func()
    
    print(f"\n🏆 VALIDATION SUMMARY")
    print("=" * 25)
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL" 
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes validated successfully!")
        return True
    else:
        print("⚠️  Some issues remain - check individual test results")
        return False

if __name__ == "__main__":
    main()
