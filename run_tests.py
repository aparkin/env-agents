#!/usr/bin/env python3
"""
env-agents test runner - Production test suite for all services
"""

import sys
import os
import argparse
sys.path.append('.')

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters import CANONICAL_SERVICES
import pandas as pd
import time

def run_production_tests():
    """Run production test suite for all canonical services"""
    print("🧪 ENV-AGENTS PRODUCTION TEST SUITE")
    print("=" * 50)

    # Test geometry and time range
    geometry = Geometry(type='bbox', coordinates=[-122.5, 37.6, -122.3, 37.8])
    time_range = ("2021-06-01T00:00:00Z", "2021-08-31T23:59:59Z")

    results = {}
    for service_name, adapter_class in CANONICAL_SERVICES.items():
        print(f"\n🧪 Testing {service_name}...")

        try:
            adapter = adapter_class() if service_name != "EARTH_ENGINE" else adapter_class(asset_id="MODIS/061/MOD13Q1")

            spec = RequestSpec(
                geometry=geometry,
                time_range=time_range,
                variables=None,
                extra={"timeout": 60}
            )

            start_time = time.time()
            result = adapter._fetch_rows(spec)
            elapsed = time.time() - start_time

            if result and len(result) > 0:
                results[service_name] = {"status": "success", "count": len(result), "time": elapsed}
                print(f"  ✅ SUCCESS: {len(result)} observations in {elapsed:.1f}s")
            else:
                results[service_name] = {"status": "no_data", "count": 0, "time": elapsed}
                print(f"  ⚠️  No data returned in {elapsed:.1f}s")

        except Exception as e:
            results[service_name] = {"status": "error", "error": str(e)}
            print(f"  ❌ ERROR: {str(e)[:50]}...")

    # Summary
    print(f"\n📊 TEST SUMMARY:")
    print(f"✅ Services working: {sum(1 for r in results.values() if r['status'] == 'success')}/{len(CANONICAL_SERVICES)}")
    total_obs = sum(r.get('count', 0) for r in results.values())
    print(f"📊 Total observations: {total_obs:,}")

    return results

def run_capabilities_test():
    """Test capabilities for all services"""
    print("🔍 ENV-AGENTS CAPABILITIES TEST")
    print("=" * 50)

    total_variables = 0
    for service_name, adapter_class in CANONICAL_SERVICES.items():
        print(f"\n🔍 {service_name} capabilities:")
        try:
            adapter = adapter_class() if service_name != "EARTH_ENGINE" else adapter_class(asset_id="MODIS/061/MOD13Q1")
            capabilities = adapter.capabilities()

            if "variables" in capabilities:
                count = len(capabilities["variables"])
                total_variables += count
                print(f"  ✅ {count:,} variables available")
            elif "assets" in capabilities and isinstance(capabilities["assets"], dict):
                # Meta-service with categorized assets
                asset_count = sum(info.get('count', 0) for info in capabilities["assets"].values())
                print(f"  ✅ {asset_count:,} assets across {len(capabilities['assets'])} categories")
            else:
                print(f"  ✅ Service available")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:50]}...")

    print(f"\n📊 TOTAL: {total_variables:,} variables across {len(CANONICAL_SERVICES)} services")
    return total_variables

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='env-agents test runner')
    parser.add_argument('--services', action='store_true',
                       help='Run service tests with data fetching')
    parser.add_argument('--capabilities', action='store_true',
                       help='Test service capabilities only')
    args = parser.parse_args()

    if args.services:
        run_production_tests()
    elif args.capabilities:
        run_capabilities_test()
    else:
        # Default: run both
        run_capabilities_test()
        print("\n" + "=" * 50)
        run_production_tests()
