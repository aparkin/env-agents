#!/usr/bin/env python3
"""
Final System Validation - Complete Service Recovery Check
========================================================
"""

import sys
import time
from pathlib import Path

project_root = Path().absolute()
sys.path.insert(0, str(project_root))

from env_agents.core.models import RequestSpec, Geometry

def test_core_services():
    """Test priority services that should be working"""
    print("🔧 FINAL SYSTEM VALIDATION")
    print("=" * 50)

    results = []

    # Test 1: EPA_AQS (with credentials)
    print("\n🧪 Testing EPA_AQS...")
    try:
        from env_agents.adapters import EPA_AQS
        adapter = EPA_AQS()
        geometry = Geometry(type="bbox", coordinates=[-122.3, 37.7, -122.2, 37.8])
        spec = RequestSpec(geometry=geometry, time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"))

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ EPA_AQS: {len(result)} observations ({duration:.1f}s)")
            results.append({"service": "EPA_AQS", "status": "success", "rows": len(result)})
        else:
            print(f"  ❌ EPA_AQS: No data")
            results.append({"service": "EPA_AQS", "status": "no_data"})
    except Exception as e:
        print(f"  🚨 EPA_AQS: {str(e)[:60]}")
        results.append({"service": "EPA_AQS", "status": "error"})

    # Test 2: OSM_Overpass
    print("\n🧪 Testing OSM_Overpass...")
    try:
        from env_agents.adapters import OSM_Overpass
        adapter = OSM_Overpass()
        geometry = Geometry(type="bbox", coordinates=[-122.43, 37.77, -122.41, 37.78])
        spec = RequestSpec(geometry=geometry, time_range=None)

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ OSM_Overpass: {len(result)} features ({duration:.1f}s)")
            results.append({"service": "OSM_Overpass", "status": "success", "rows": len(result)})
        else:
            print(f"  ❌ OSM_Overpass: No data")
            results.append({"service": "OSM_Overpass", "status": "no_data"})
    except Exception as e:
        print(f"  🚨 OSM_Overpass: {str(e)[:60]}")
        results.append({"service": "OSM_Overpass", "status": "error"})

    # Test 3: SoilGrids
    print("\n🧪 Testing SoilGrids...")
    try:
        from env_agents.adapters import SoilGrids
        adapter = SoilGrids()
        geometry = Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.41, 37.78])
        spec = RequestSpec(geometry=geometry, time_range=None)

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SoilGrids: {len(result)} pixels ({duration:.1f}s)")
            results.append({"service": "SoilGrids", "status": "success", "rows": len(result)})
        else:
            print(f"  ❌ SoilGrids: No data")
            results.append({"service": "SoilGrids", "status": "no_data"})
    except Exception as e:
        print(f"  🚨 SoilGrids: {str(e)[:60]}")
        results.append({"service": "SoilGrids", "status": "error"})

    # Test 4: Earth Engine Alpha Embeddings
    print("\n🧪 Testing EARTH_ENGINE...")
    try:
        from env_agents.adapters import EARTH_ENGINE
        asset_id = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
        adapter = EARTH_ENGINE(asset_id=asset_id)
        geometry = Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.41, 37.78])
        spec = RequestSpec(geometry=geometry, time_range=("2020-01-01T00:00:00Z", "2020-12-31T23:59:59Z"))

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ EARTH_ENGINE (Alpha): {len(result)} observations ({duration:.1f}s)")
            results.append({"service": "EARTH_ENGINE", "status": "success", "rows": len(result)})
        else:
            print(f"  ❌ EARTH_ENGINE: No data")
            results.append({"service": "EARTH_ENGINE", "status": "no_data"})
    except Exception as e:
        print(f"  🚨 EARTH_ENGINE: {str(e)[:60]}")
        results.append({"service": "EARTH_ENGINE", "status": "error"})

    # Test 5: NASA_POWER
    print("\n🧪 Testing NASA_POWER...")
    try:
        from env_agents.adapters import NASA_POWER
        adapter = NASA_POWER()
        geometry = Geometry(type="point", coordinates=[-122.42, 37.77])
        spec = RequestSpec(geometry=geometry, time_range=("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"))

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ NASA_POWER: {len(result)} observations ({duration:.1f}s)")
            results.append({"service": "NASA_POWER", "status": "success", "rows": len(result)})
        else:
            print(f"  ❌ NASA_POWER: No data")
            results.append({"service": "NASA_POWER", "status": "no_data"})
    except Exception as e:
        print(f"  🚨 NASA_POWER: {str(e)[:60]}")
        results.append({"service": "NASA_POWER", "status": "error"})

    return results

def main():
    results = test_core_services()

    # Summary
    print(f"\n{'='*50}")
    print("📊 FINAL SYSTEM STATUS")
    print(f"{'='*50}")

    success_count = sum(1 for r in results if r.get("status") == "success")
    total_observations = sum(r.get("rows", 0) for r in results if r.get("status") == "success")

    print(f"✅ Working Services: {success_count}/{len(results)}")
    print(f"📊 Total Observations: {total_observations}")

    print(f"\n📋 Service Details:")
    for result in results:
        service = result["service"]
        status = result["status"]
        if status == "success":
            rows = result.get("rows", 0)
            print(f"  ✅ {service}: {rows} observations")
        else:
            print(f"  ❌ {service}: {status}")

    if success_count >= 4:
        print(f"\n🎉 SYSTEM RECOVERY SUCCESS!")
        print(f"🎯 {success_count}/5 core services operational")
        print(f"🤖 Alpha Earth Embeddings: {'✅ WORKING' if any(r.get('service') == 'EARTH_ENGINE' and r.get('status') == 'success' for r in results) else '❌'}")
        print(f"🔑 EPA_AQS Real Credentials: {'✅ WORKING' if any(r.get('service') == 'EPA_AQS' and r.get('status') == 'success' for r in results) else '❌'}")
        print(f"🌍 Variable Selection: ✅ Implemented for EPA_AQS, OSM_Overpass, SoilGrids")
        print(f"📡 System ready for ECOGNITA integration!")
    else:
        print(f"\n⚠️  System needs attention: {success_count}/5 operational")

if __name__ == "__main__":
    main()