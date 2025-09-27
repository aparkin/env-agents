#!/usr/bin/env python3
"""
Test NASA_POWER Fix - Service Recovery Test 1/9
==============================================
"""

import os
import sys
import time

os.chdir("/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")
sys.path.insert(0, "/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")

try:
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters.power.adapter import NASAPowerAdapter
    print("✅ NASA_POWER imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_nasa_power():
    """Test NASA_POWER with bbox geometry (previous failure case)"""
    print("\n🧪 TESTING NASA_POWER - BBOX GEOMETRY")
    print("=" * 45)
    print("🎯 Target: 552 observations (Amazon Basin)")

    try:
        adapter = NASAPowerAdapter()

        # Use EXACT working pattern from complete_system_validation_final.py
        geometry = Geometry(type="bbox", coordinates=[-60.0, -3.0, -59.0, -2.0])  # Amazon Basin
        spec = RequestSpec(
            geometry=geometry,
            time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"),
            variables=None
        )

        print(f"  📍 Location: Amazon Basin {geometry.coordinates}")
        print(f"  📅 Time: {spec.time_range[0]} to {spec.time_range[1]}")

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SUCCESS: {len(result)} rows, {duration:.2f}s")
            print(f"  🎯 Target: 552 rows")

            # Sample data
            sample = result[0]
            print(f"  📊 Sample variable: {sample.get('variable', 'N/A')}")
            print(f"  📊 Sample value: {sample.get('value', 'N/A')}")
            print(f"  📊 Sample unit: {sample.get('unit', 'N/A')}")

            return {"status": "success", "rows": len(result), "duration": duration}
        else:
            print(f"  ❌ FAILED: No data returned")
            return {"status": "failure", "rows": 0, "duration": duration}

    except Exception as e:
        print(f"  🚨 ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("🔧 NASA_POWER GEOMETRY FIX TEST")
    result = test_nasa_power()

    if result.get("status") == "success":
        print(f"\n🏆 NASA_POWER RESTORED: {result['rows']} observations")
        print("✅ Service 1/9 WORKING")
    else:
        print(f"\n🔴 NASA_POWER STILL BROKEN")
        if "error" in result:
            print(f"❌ Error: {result['error']}")