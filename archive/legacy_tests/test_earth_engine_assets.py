#!/usr/bin/env python3
"""
Test Earth Engine Assets - Two-Stage Discovery + Data Fetching
==============================================================
"""

import os
import sys
import time
from pathlib import Path

# Setup
project_root = Path().absolute()
sys.path.insert(0, str(project_root))

try:
    from env_agents.core.models import RequestSpec, Geometry
    from env_agents.adapters import EARTH_ENGINE
    print("✅ Earth Engine imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_earth_engine_capabilities():
    """Test Earth Engine capabilities (asset information)"""
    print("\n🔍 TESTING EARTH ENGINE - CAPABILITIES")
    print("=" * 50)

    try:
        # Test different assets by creating adapter instances
        test_assets = [
            "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",  # Alpha embeddings
            "MODIS/006/MOD13Q1",  # MODIS vegetation
            "LANDSAT/LC08/C02/T1_L2"  # Landsat 8
        ]

        capabilities_results = []
        for asset_id in test_assets:
            print(f"  🛰️  Testing capabilities for {asset_id}...")
            try:
                adapter = EARTH_ENGINE(asset_id=asset_id)
                start_time = time.time()
                caps = adapter.capabilities()
                duration = time.time() - start_time

                if caps and "variables" in caps:
                    var_count = len(caps.get("variables", []))
                    print(f"    ✅ SUCCESS: {var_count} variables in {duration:.2f}s")
                    capabilities_results.append({"asset": asset_id, "status": "success", "variables": var_count})
                else:
                    print(f"    ❌ FAILED: No capabilities returned")
                    capabilities_results.append({"asset": asset_id, "status": "failure"})

            except Exception as e:
                print(f"    🚨 ERROR: {str(e)}")
                capabilities_results.append({"asset": asset_id, "status": "error", "error": str(e)})

        success_count = sum(1 for r in capabilities_results if r.get("status") == "success")
        return {"status": "success" if success_count > 0 else "failure", "results": capabilities_results, "success_count": success_count}

    except Exception as e:
        print(f"  🚨 ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}

def test_earth_engine_data_fetching(asset_id):
    """Test Earth Engine data fetching (unitary service pattern)"""
    print(f"\n📊 TESTING EARTH ENGINE - DATA FETCHING")
    print(f"Asset: {asset_id}")
    print("=" * 50)

    try:
        adapter = EARTH_ENGINE()

        # Small area for quick test
        geometry = Geometry(type="bbox", coordinates=[-122.5, 37.7, -122.4, 37.8])  # SF Bay
        spec = RequestSpec(
            geometry=geometry,
            time_range=("2020-01-01T00:00:00Z", "2020-12-31T23:59:59Z"),
            variables=[asset_id]  # Asset ID passed via variables (key design)
        )

        print(f"  📍 Location: SF Bay {geometry.coordinates}")
        print(f"  📅 Time: 2020 (1 year)")
        print(f"  🛰️  Asset: {asset_id}")

        start_time = time.time()
        result = adapter._fetch_rows(spec)
        duration = time.time() - start_time

        if result and len(result) > 0:
            print(f"  ✅ SUCCESS: {len(result)} observations in {duration:.2f}s")

            # Sample data
            sample = result[0]
            print(f"  📊 Sample variable: {sample.get('variable', 'N/A')}")
            print(f"  📊 Sample value: {sample.get('value', 'N/A')}")
            print(f"  📊 Sample unit: {sample.get('unit', 'N/A')}")

            # Show asset metadata
            attrs = sample.get('attributes', {})
            print(f"  🛰️  Asset metadata: {list(attrs.keys())[:3]}")

            return {"status": "success", "rows": len(result), "duration": duration, "asset": asset_id}
        else:
            print(f"  ❌ FAILED: No data returned for {asset_id}")
            return {"status": "failure", "rows": 0, "asset": asset_id}

    except Exception as e:
        print(f"  🚨 ERROR: {str(e)}")
        return {"status": "error", "error": str(e), "asset": asset_id}

def main():
    print("🛰️  EARTH ENGINE COMPREHENSIVE TEST")
    print("Asset-Specific Testing: Capabilities → Data Fetching")
    print("=" * 60)

    # Stage 1: Asset Capabilities Testing
    capabilities_result = test_earth_engine_capabilities()

    if capabilities_result.get("status") != "success":
        print("\n❌ Asset capabilities failed, cannot proceed to data fetching")
        return

    # Stage 2: Data Fetching (Unitary service pattern)
    # Test key assets including user's alpha embeddings
    test_assets = [
        "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",  # User requested alpha embeddings
        "MODIS/006/MOD13Q1",  # MODIS vegetation indices
        "LANDSAT/LC08/C02/T1_L2"  # Landsat 8 surface reflectance
    ]

    fetch_results = []
    for asset_id in test_assets:
        result = test_earth_engine_data_fetching(asset_id)
        fetch_results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("🛰️  EARTH ENGINE TEST RESULTS")
    print(f"{'='*60}")

    capabilities_success = capabilities_result.get("status") == "success"
    capabilities_count = capabilities_result.get("success_count", 0)
    fetch_success_count = sum(1 for r in fetch_results if r.get("status") == "success")
    total_observations = sum(r.get("rows", 0) for r in fetch_results)

    print(f"✅ Asset Capabilities: {capabilities_count}/3 assets working")
    print(f"✅ Data Fetching: {fetch_success_count}/{len(test_assets)} assets working")
    if total_observations > 0:
        print(f"   📊 Total Observations: {total_observations}")

    print(f"\n📋 Asset Details:")
    for result in fetch_results:
        asset = result.get("asset", "unknown")
        status = result.get("status", "unknown")
        if status == "success":
            rows = result.get("rows", 0)
            duration = result.get("duration", 0)
            print(f"  ✅ {asset}: {rows} observations ({duration:.1f}s)")
        else:
            print(f"  ❌ {asset}: {status}")

    # Overall assessment
    if capabilities_success and fetch_success_count > 0:
        print(f"\n🎉 EARTH ENGINE: OPERATIONAL")
        print(f"🎯 Asset-specific pattern working: Capabilities + Data fetching")
        if "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL" in [r.get("asset") for r in fetch_results if r.get("status") == "success"]:
            print(f"🤖 Alpha Earth Embeddings: WORKING")
    else:
        print(f"\n⚠️  Earth Engine needs attention")

if __name__ == "__main__":
    main()