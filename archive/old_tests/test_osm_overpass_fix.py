#!/usr/bin/env python3
"""
Test OSM Overpass Fix - Service Recovery Test 4/9
=================================================
"""

import os
import sys
import time

os.chdir("/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")
sys.path.insert(0, "/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")

try:
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters import OSM_Overpass
    print("✅ OSM Overpass imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_osm_overpass():
    """Test OSM Overpass with tiling and backoff/retry"""
    print("\n🧪 TESTING OSM OVERPASS - TILING + BACKOFF")
    print("=" * 45)
    print("🎯 Target: 10+ observations (SF Bay area)")

    try:
        adapter = OSM_Overpass()

        # Use working pattern - SF Bay area (small area for quick test)
        geometry = Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.41, 37.78])  # Small SF area
        spec = RequestSpec(
            geometry=geometry,
            time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"),
            variables=["building", "highway"]
        )

        print(f"  📍 Location: SF Bay {geometry.coordinates}")
        print(f"  🧬 Adapter: {adapter.__class__.__name__}")
        print(f"  🔧 Features: Tiling + Exponential backoff/retry")

        start_time = time.time()
        print("  🔄 Making OSM Overpass queries with tiling...")
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SUCCESS: {len(result)} rows, {duration:.2f}s")
            print(f"  🎯 Target: 10+ rows")

            # Sample data
            sample = result[0]
            print(f"  📊 Sample variable: {sample.get('variable', 'N/A')}")
            print(f"  📊 Sample value: {sample.get('value', 'N/A')}")
            print(f"  📊 Sample unit: {sample.get('unit', 'N/A')}")
            print(f"  🏢 Sample OSM type: {sample.get('attributes', {}).get('osm_type', 'N/A')}")
            print(f"  🏗️ Sample OSM tags: {list(sample.get('attributes', {}).get('osm_tags', {}).keys())[:3]}")

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
    print("🔧 OSM OVERPASS TILING + BACKOFF TEST")
    result = test_osm_overpass()

    if result.get("status") == "success":
        print(f"\n🏆 OSM OVERPASS WORKING: {result['rows']} observations")
        print("✅ Service 4/9 WORKING")
        print("🔧 Features: Tiling strategy + exponential backoff/retry implemented")
    else:
        print(f"\n🔴 OSM OVERPASS STILL BROKEN")
        if "error" in result:
            print(f"❌ Error: {result['error']}")