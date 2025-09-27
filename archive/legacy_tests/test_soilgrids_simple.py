#!/usr/bin/env python3
"""
Simple SoilGrids Test - Check Basic Functionality
===============================================
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

def test_soilgrids_simple():
    """Test SoilGrids basic functionality without data fetching"""
    print("\n🧪 TESTING SoilGrids - BASIC FUNCTIONALITY")
    print("=" * 40)

    try:
        adapter = SoilGrids()
        print(f"  ✅ Adapter created: {adapter.__class__.__name__}")

        # Test capabilities without fetching data
        caps = adapter.capabilities()
        print(f"  ✅ Capabilities retrieved: {len(caps.get('variables', []))} variables")

        # Test a very small point request (single pixel)
        geometry = Geometry(type="point", coordinates=[-60.0, -3.0])  # Single point in Amazon
        spec = RequestSpec(
            geometry=geometry,
            time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"),
            variables=["clay"],  # Single variable
            extra={"max_pixels": 1}  # Minimal request
        )

        print(f"  📍 Location: Single point {geometry.coordinates}")
        print(f"  🔧 Variables: clay only")
        print(f"  📊 Max pixels: 1")

        start_time = time.time()
        print("  🔄 Making minimal SoilGrids request...")
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SUCCESS: {len(result)} rows, {duration:.2f}s")
            sample = result[0]
            print(f"  📊 Sample variable: {sample.get('parameter', 'N/A')}")
            print(f"  📊 Sample value: {sample.get('value', 'N/A')}")
            print(f"  📊 Sample unit: {sample.get('unit', 'N/A')}")
            return {"status": "success", "rows": len(result), "duration": duration}
        else:
            print(f"  ❌ FAILED: No data returned")
            return {"status": "failure", "rows": 0, "duration": duration}

    except Exception as e:
        print(f"  🚨 ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("🔧 SoilGrids SIMPLE FUNCTIONALITY TEST")
    result = test_soilgrids_simple()

    if result.get("status") == "success":
        print(f"\n🏆 SoilGrids WORKING: {result['rows']} observations")
        print("✅ Basic functionality confirmed")
    else:
        print(f"\n🔴 SoilGrids ISSUE DETECTED")
        if "error" in result:
            print(f"❌ Error: {result['error']}")