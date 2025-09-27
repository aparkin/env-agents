#!/usr/bin/env python3
"""
SERVICE RECOVERY VALIDATION
===========================
🎯 Restore all previously working services to operational status
📊 Focus on working patterns from complete_system_validation_final.py

RECOVERY TARGETS:
- NASA_POWER: 552 rows ✅
- SoilGrids: 488 rows ✅
- OpenAQ: 1,000 rows ✅
- GBIF: 300 rows ✅
- SSURGO: 36 rows ✅
- EPA_AQS: 1 row (real API) ✅
- Earth Engine: 148 rows (generic adapter) ✅
"""

import os
import sys
import time
import warnings
warnings.filterwarnings('ignore')

print("🛠️  SERVICE RECOVERY VALIDATION")
print("=" * 50)
print("🎯 Goal: Restore all previously working services")
print("📊 Target: 6/9 services operational (2,377 observations)")
print()

# Set working directory
os.chdir("/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")
sys.path.insert(0, "/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents")

# Import using WORKING PATTERNS from complete_system_validation_final.py
try:
    from env_agents.core.router import EnvRouter
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters import (NASA_POWER, SoilGrids, OpenAQ, GBIF, WQP,
                                    OSM_Overpass, EPA_AQS, USGS_NWIS, SSURGO, EARTH_ENGINE)
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_working_service(service_name, adapter_instance, geometry, variables, time_range, target_rows):
    """Test service using EXACT patterns from working validation"""
    try:
        print(f"  🧪 Testing {service_name}...")

        spec = RequestSpec(
            geometry=geometry,
            variables=variables,
            time_range=time_range
        )

        start_time = time.time()
        result = adapter_instance._fetch_rows(spec)  # Direct adapter call like working version
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"    ✅ SUCCESS: {len(result)} rows (target: {target_rows}), {duration:.2f}s")
            return {"status": "success", "rows": len(result), "duration": duration}
        else:
            print(f"    ❌ FAILED: No data returned")
            return {"status": "failure", "rows": 0, "duration": duration}

    except Exception as e:
        print(f"    ❌ ERROR: {str(e)[:80]}...")
        return {"status": "error", "error": str(e), "rows": 0}

def main():
    print("\n🔧 PHASE 1: SERVICE RECOVERY TESTING")
    print("=" * 45)

    # Initialize router
    router = EnvRouter(base_dir=".")

    # Test services using WORKING PATTERNS from complete_system_validation_final.py
    recovery_results = {}

    # 1. NASA_POWER (Previously: 552 rows)
    geometry = Geometry(type="bbox", coordinates=[-60.0, -3.0, -59.0, -2.0])  # Amazon Basin
    recovery_results["NASA_POWER"] = test_working_service(
        "NASA_POWER", NASA_POWER(), geometry, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 552
    )

    # 2. SoilGrids (Previously: 488 rows)
    recovery_results["SoilGrids"] = test_working_service(
        "SoilGrids", SoilGrids(), geometry, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 488
    )

    # 3. OpenAQ (Previously: 1,000 rows)
    geometry_nl = Geometry(type="bbox", coordinates=[4.0, 52.0, 5.0, 53.0])  # Netherlands
    recovery_results["OpenAQ"] = test_working_service(
        "OpenAQ", OpenAQ(), geometry_nl, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 1000
    )

    # 4. GBIF (Previously: 300 rows)
    recovery_results["GBIF"] = test_working_service(
        "GBIF", GBIF(), geometry, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 300
    )

    # 5. SSURGO (Previously: 36 rows)
    geometry_iowa = Geometry(type="bbox", coordinates=[-94.0, 42.0, -93.0, 43.0])  # Iowa
    recovery_results["SSURGO"] = test_working_service(
        "SSURGO", SSURGO(), geometry_iowa, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 36
    )

    # 6. EPA_AQS (Previously: 1 row - REAL API)
    geometry_sf = Geometry(type="bbox", coordinates=[-122.3, 37.7, -122.2, 37.8])  # SF Bay
    recovery_results["EPA_AQS"] = test_working_service(
        "EPA_AQS", EPA_AQS(), geometry_sf, None,
        ("2020-01-01T00:00:00Z", "2020-01-31T23:59:59Z"), 1
    )

    print("\n📊 RECOVERY RESULTS SUMMARY")
    print("=" * 30)

    successful = [name for name, result in recovery_results.items() if result.get("status") == "success"]
    total_observations = sum([result.get("rows", 0) for result in recovery_results.values()])

    print(f"✅ Services recovered: {len(successful)}/6")
    print(f"📊 Total observations: {total_observations}")
    print(f"🎯 Target observations: 2,377")

    for service, result in recovery_results.items():
        status_icon = "✅" if result.get("status") == "success" else "❌"
        rows = result.get("rows", 0)
        print(f"  {status_icon} {service}: {rows} rows")

    recovery_rate = len(successful) / 6 * 100
    if recovery_rate >= 83:  # 5/6 services
        print(f"\n🏆 RECOVERY STATUS: EXCELLENT ({recovery_rate:.0f}%)")
    elif recovery_rate >= 67:  # 4/6 services
        print(f"\n🟡 RECOVERY STATUS: GOOD ({recovery_rate:.0f}%)")
    else:
        print(f"\n🔴 RECOVERY STATUS: NEEDS WORK ({recovery_rate:.0f}%)")

    return recovery_results

if __name__ == "__main__":
    main()