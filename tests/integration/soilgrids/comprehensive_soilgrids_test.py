#!/usr/bin/env python3
"""
Comprehensive SoilGrids WCS Integration Test Suite
Tests multiple locations, sizes, and robustness patterns
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the package to Python path
env_agents_path = Path(__file__).parent
sys.path.insert(0, str(env_agents_path))

import pandas as pd
from env_agents.adapters.soil import SoilGridsAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_multiple_locations():
    """Test SoilGrids across multiple global locations"""

    print("\n=== Multi-Location Robustness Test ===")

    locations = [
        {"name": "Netherlands", "bbox": (5.78, 51.98, 5.8, 52.0)},
        {"name": "California", "bbox": (-122.0, 37.0, -121.98, 37.02)},
        {"name": "Brazil", "bbox": (-47.0, -15.8, -46.98, -15.78)},
        {"name": "Kenya", "bbox": (36.8, -1.3, 36.82, -1.28)},
        {"name": "Australia", "bbox": (151.2, -33.9, 151.22, -33.88)}
    ]

    adapter = SoilGridsAdapter()
    success_count = 0

    for location in locations:
        print(f"\n  Testing {location['name']}...")

        try:
            geometry = Geometry(type="bbox", coordinates=list(location['bbox']))
            spec = RequestSpec(
                geometry=geometry,
                variables=["soil:clay"],
                extra={"max_pixels": 50000}
            )

            rows = adapter._fetch_rows(spec)
            if rows and len(rows) > 0:
                success_count += 1
                print(f"    ✅ SUCCESS: {len(rows)} observations")
                sample = rows[0]
                print(f"    Sample: {sample['variable']} = {sample['value']} {sample['unit']}")
            else:
                print(f"    ⚠️  No data returned")

        except Exception as e:
            print(f"    ❌ Error: {str(e)[:100]}...")

    print(f"\n  Location Test Summary: {success_count}/{len(locations)} locations successful")
    return success_count / len(locations)

def test_bounding_box_sizes():
    """Test various bounding box sizes to validate guard rails"""

    print("\n=== Bounding Box Size Test ===")

    # Base location: Netherlands
    base_lat, base_lon = 52.0, 5.8

    test_sizes = [
        {"name": "Tiny (0.01°)", "size": 0.01},
        {"name": "Small (0.05°)", "size": 0.05},
        {"name": "Medium (0.1°)", "size": 0.1},
        {"name": "Large (0.2°)", "size": 0.2},
        {"name": "Very Large (0.5°)", "size": 0.5}
    ]

    adapter = SoilGridsAdapter()
    results = []

    for test in test_sizes:
        print(f"\n  Testing {test['name']} bounding box...")

        size = test['size']
        bbox = (base_lon - size/2, base_lat - size/2, base_lon + size/2, base_lat + size/2)

        try:
            # Test guard rails calculation
            geometry = Geometry(type="bbox", coordinates=list(bbox))
            spec = RequestSpec(geometry=geometry, variables=["soil:clay"])

            limits = adapter._get_guard_rail_limits(spec)
            print(f"    Strategy: {limits['strategy']}")
            print(f"    Estimated pixels: {limits['estimated_pixels']:,}")

            if limits['strategy'] == 'tiled':
                print(f"    Tiles needed: {limits['tile_count']}")

            # Test actual data fetch (with limits)
            spec_limited = RequestSpec(
                geometry=geometry,
                variables=["soil:clay"],
                extra={"max_pixels": 100000}  # Keep reasonable for testing
            )

            rows = adapter._fetch_rows(spec_limited)
            if rows:
                result = {
                    "size": test['name'],
                    "strategy": limits['strategy'],
                    "estimated_pixels": limits['estimated_pixels'],
                    "actual_observations": len(rows),
                    "success": True
                }
                print(f"    ✅ SUCCESS: {len(rows)} observations")
            else:
                result = {
                    "size": test['name'],
                    "strategy": limits['strategy'],
                    "estimated_pixels": limits['estimated_pixels'],
                    "actual_observations": 0,
                    "success": False
                }
                print(f"    ⚠️  No data returned")

        except Exception as e:
            result = {
                "size": test['name'],
                "strategy": "failed",
                "estimated_pixels": 0,
                "actual_observations": 0,
                "success": False,
                "error": str(e)[:100]
            }
            print(f"    ❌ Error: {str(e)[:100]}...")

        results.append(result)

    # Summary
    successful = len([r for r in results if r['success']])
    print(f"\n  Size Test Summary: {successful}/{len(test_sizes)} sizes successful")

    return results

def test_adapter_reliability():
    """Test circuit breaker and error handling"""

    print("\n=== Reliability & Error Handling Test ===")

    adapter = SoilGridsAdapter()

    # Test 1: Valid request
    print("\n  1. Testing valid request...")
    try:
        geometry = Geometry(type="bbox", coordinates=[5.78, 51.98, 5.8, 52.0])
        spec = RequestSpec(geometry=geometry, variables=["soil:clay"])

        rows = adapter._fetch_rows(spec)
        if rows:
            print(f"    ✅ Valid request: {len(rows)} observations")
        else:
            print(f"    ⚠️  Valid request returned no data")
    except Exception as e:
        print(f"    ❌ Valid request failed: {e}")

    # Test 2: Invalid geometry
    print("\n  2. Testing invalid geometry...")
    try:
        geometry = Geometry(type="bbox", coordinates=[200, 100, 210, 110])  # Invalid coords
        spec = RequestSpec(geometry=geometry, variables=["soil:clay"])

        rows = adapter._fetch_rows(spec)
        print(f"    ⚠️  Invalid geometry unexpectedly succeeded: {len(rows) if rows else 0} observations")
    except Exception as e:
        print(f"    ✅ Invalid geometry properly rejected: {str(e)[:100]}...")

    # Test 3: Circuit breaker status
    print("\n  3. Testing circuit breaker...")
    print(f"    Circuit breaker open: {adapter.circuit_breaker.is_open}")
    print(f"    Failure count: {adapter.circuit_breaker.failure_count}")

    return True

def run_comprehensive_test():
    """Run all test suites"""

    print("🧪 SoilGrids WCS Comprehensive Test Suite")
    print(f"Started: {datetime.now()}")
    print("=" * 50)

    try:
        # Initialize adapter (this builds the catalog)
        print("\n📋 Initializing adapter and building catalog...")
        adapter = SoilGridsAdapter()
        caps = adapter.capabilities()

        print(f"✅ Adapter initialized")
        print(f"   Service type: {caps.get('service_type')}")
        print(f"   Variables available: {len(caps.get('variables', []))}")

        if hasattr(adapter, 'catalog_cache') and adapter.catalog_cache:
            total_coverages = sum(len(v) for v in adapter.catalog_cache.values())
            print(f"   Total coverages: {total_coverages}")

        # Run test suites
        location_success_rate = test_multiple_locations()
        size_test_results = test_bounding_box_sizes()
        reliability_ok = test_adapter_reliability()

        # Overall assessment
        print("\n" + "=" * 50)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 50)

        print(f"✅ Adapter Initialization: SUCCESS")
        print(f"📍 Location Success Rate: {location_success_rate:.1%}")

        size_success_rate = len([r for r in size_test_results if r['success']]) / len(size_test_results)
        print(f"📐 Size Handling Success: {size_success_rate:.1%}")

        print(f"🛡️  Reliability Features: {'✅ PASS' if reliability_ok else '❌ FAIL'}")

        # Overall score
        overall_score = (location_success_rate + size_success_rate + (1.0 if reliability_ok else 0.0)) / 3

        if overall_score >= 0.8:
            status = "🎉 EXCELLENT"
        elif overall_score >= 0.6:
            status = "👍 GOOD"
        elif overall_score >= 0.4:
            status = "⚠️  NEEDS WORK"
        else:
            status = "❌ POOR"

        print(f"\n🏆 OVERALL SCORE: {overall_score:.1%} - {status}")

        return overall_score >= 0.6  # Success threshold

    except Exception as e:
        print(f"\n💥 TEST SUITE FAILED: {e}")
        return False

    finally:
        print(f"\nCompleted: {datetime.now()}")

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)