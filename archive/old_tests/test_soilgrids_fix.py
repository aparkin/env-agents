#!/usr/bin/env python3
"""
Test SoilGrids Fix - Service Recovery Test 2/9
==============================================
"""

import os
import sys
import time

os.chdir("/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")
sys.path.insert(0, "/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")

try:
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters import SoilGrids
    print("✅ SoilGrids imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_soilgrids():
    """Test SoilGrids with working pattern"""
    print("\n🧪 TESTING SoilGrids - WCS ADAPTER")
    print("=" * 40)
    print("🎯 Target: 488 observations (Amazon Basin)")

    try:
        adapter = SoilGrids()

        # Use smaller working pattern to avoid timeout
        geometry = Geometry(type="bbox", coordinates=[-60.0, -3.0, -59.8, -2.8])  # Small Amazon area
        spec = RequestSpec(
            geometry=geometry,
            time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"),
            variables=None,
            extra={"max_pixels": 10000}  # Limit to prevent timeout
        )

        print(f"  📍 Location: Amazon Basin {geometry.coordinates}")
        print(f"  🧬 Adapter: {adapter.__class__.__name__}")

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SUCCESS: {len(result)} rows, {duration:.2f}s")
            print(f"  🎯 Target: 488 rows")

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
    print("🔧 SoilGrids WCS ADAPTER TEST")
    result = test_soilgrids()

    if result.get("status") == "success":
        print(f"\n🏆 SoilGrids WORKING: {result['rows']} observations")
        print("✅ Service 2/9 WORKING")
    else:
        print(f"\n🔴 SoilGrids STILL BROKEN")
        if "error" in result:
            print(f"❌ Error: {result['error']}")