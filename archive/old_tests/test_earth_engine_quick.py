#!/usr/bin/env python3
"""
Earth Engine Quick Test - Two-Stage Architecture
==============================================
"""

import sys
import time
from pathlib import Path

project_root = Path().absolute()
sys.path.insert(0, str(project_root))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters import EARTH_ENGINE

def test_earth_engine_quick():
    """Test Earth Engine with established two-stage pattern"""
    print("🛰️  EARTH ENGINE - QUICK TWO-STAGE TEST")
    print("=" * 50)

    # Stage 1: Capabilities Testing
    print("📋 Stage 1: Asset Capabilities...")

    test_assets = [
        "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",  # Alpha embeddings
        "MODIS/006/MOD13Q1",  # MODIS vegetation
    ]

    working_assets = []
    for asset_id in test_assets:
        try:
            adapter = EARTH_ENGINE(asset_id=asset_id)
            caps = adapter.capabilities()
            if caps and "variables" in caps:
                var_count = len(caps.get("variables", []))
                print(f"  ✅ {asset_id}: {var_count} variables")
                working_assets.append(asset_id)
            else:
                print(f"  ❌ {asset_id}: No capabilities")
        except Exception as e:
            print(f"  🚨 {asset_id}: {str(e)[:50]}")

    if not working_assets:
        print("❌ No assets working in Stage 1")
        return

    # Stage 2: Data Fetching (Unified pattern)
    print(f"\n📊 Stage 2: Data Fetching...")

    # Test alpha embeddings specifically
    asset_to_test = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    if asset_to_test in working_assets:
        try:
            # Use established pattern - Asset-specific adapter instance
            adapter = EARTH_ENGINE(asset_id=asset_to_test)  # Asset ID in constructor

            # Very small area for quick test
            geometry = Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.40, 37.78])
            spec = RequestSpec(
                geometry=geometry,
                time_range=("2020-01-01T00:00:00Z", "2020-12-31T23:59:59Z"),
                variables=None  # No variables needed - asset in constructor
            )

            print(f"  🎯 Testing: {asset_to_test}")
            print(f"  📍 Location: SF Point {geometry.coordinates}")

            start_time = time.time()
            result = adapter._fetch_rows(spec)
            duration = time.time() - start_time

            if result and len(result) > 0:
                print(f"  ✅ SUCCESS: {len(result)} observations in {duration:.1f}s")

                # Sample data
                sample = result[0]
                print(f"  📊 Variable: {sample.get('variable', 'N/A')}")
                print(f"  📊 Value: {sample.get('value', 'N/A')}")
                print(f"  🎯 Alpha Earth Embeddings: WORKING")

                return {"status": "success", "asset": asset_to_test, "rows": len(result)}
            else:
                print(f"  ❌ No data returned")
                return {"status": "no_data", "asset": asset_to_test}

        except Exception as e:
            print(f"  🚨 Data fetch error: {str(e)[:100]}")
            return {"status": "error", "asset": asset_to_test, "error": str(e)[:200]}
    else:
        print(f"  ⚠️  {asset_to_test} not available in capabilities")
        return {"status": "not_available", "asset": asset_to_test}

if __name__ == "__main__":
    result = test_earth_engine_quick()

    print(f"\n{'='*50}")
    print("🛰️  EARTH ENGINE RESULTS")
    print(f"{'='*50}")

    if result and result.get("status") == "success":
        print(f"✅ Earth Engine: OPERATIONAL")
        print(f"🤖 Alpha Earth Embeddings: WORKING")
        print(f"📊 Observations: {result.get('rows', 0)}")
        print(f"🎯 Two-stage pattern: SUCCESS")
    else:
        print(f"⚠️  Earth Engine status: {result.get('status', 'unknown') if result else 'failed'}")