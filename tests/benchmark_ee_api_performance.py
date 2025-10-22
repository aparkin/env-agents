#!/usr/bin/env python3
"""
Benchmark: Legacy API vs Cloud Project API Performance

Compares performance of earthengine-legacy vs explicit Cloud Project
for various query types.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ee
from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter

# Find credentials
CREDENTIALS_PATH = Path(__file__).parent.parent / "credentials" / "ecognita-470619-e9e223ea70a7.json"

def initialize_ee(use_cloud_project: bool = False):
    """Initialize Earth Engine with or without Cloud Project"""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(f"Credentials not found: {CREDENTIALS_PATH}")

    credentials = ee.ServiceAccountCredentials(email=None, key_file=str(CREDENTIALS_PATH))

    if use_cloud_project:
        with open(CREDENTIALS_PATH, 'r') as f:
            creds_data = json.load(f)
            project_id = creds_data.get('project_id')

        ee.Initialize(credentials, project=project_id)
        return f"Cloud Project: {project_id}"
    else:
        ee.Initialize(credentials)
        return "Legacy API (earthengine-legacy)"


def benchmark_query(adapter, spec, description: str, iterations: int = 3) -> Dict:
    """Benchmark a single query with multiple iterations"""
    times = []

    for i in range(iterations):
        start = time.time()
        try:
            result = adapter.fetch(spec)
            elapsed = time.time() - start
            times.append(elapsed)
            row_count = len(result)
        except Exception as e:
            return {
                "description": description,
                "error": str(e),
                "times": times,
                "failed": True
            }

    return {
        "description": description,
        "times": times,
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "row_count": row_count,
        "failed": False
    }


def run_benchmark_suite(api_name: str) -> List[Dict]:
    """Run full benchmark suite for given API configuration"""

    results = []

    print(f"\n{'='*70}")
    print(f"Benchmarking: {api_name}")
    print(f"{'='*70}")

    # Test 1: Single Image (SRTM) - Small bbox
    print("\n[1/5] Single Image (SRTM) - Small bbox...")
    adapter = ProductionEarthEngineAdapter(asset_id="USGS/SRTMGL1_003", scale=90)
    spec = RequestSpec(
        geometry=Geometry("bbox", [-122.5, 37.5, -122.3, 37.7])  # San Francisco
    )
    result = benchmark_query(adapter, spec, "SRTM Small Bbox (9 samples)", iterations=3)
    results.append(result)
    print(f"  ✓ Mean: {result['mean']:.2f}s, Rows: {result.get('row_count', 'N/A')}")

    # Test 2: Single Image (SRTM) - Large bbox with adaptive scaling
    print("\n[2/5] Single Image (SRTM) - Large bbox...")
    spec_large = RequestSpec(
        geometry=Geometry("bbox", [-96.893, 30.013, -94.501, 31.486])  # Texas
    )
    result = benchmark_query(adapter, spec_large, "SRTM Large Bbox (25 samples)", iterations=3)
    results.append(result)
    print(f"  ✓ Mean: {result['mean']:.2f}s, Rows: {result.get('row_count', 'N/A')}")

    # Test 3: ImageCollection (MODIS) - Single month, medium resolution
    print("\n[3/5] ImageCollection (MODIS) - Single month...")
    adapter_modis = ProductionEarthEngineAdapter(asset_id="MODIS/061/MOD13Q1", scale=250)
    spec_modis = RequestSpec(
        geometry=Geometry("bbox", [-122.5, 37.5, -122.3, 37.7]),
        time_range=("2023-06-01", "2023-06-30"),
        resolution="medium"
    )
    result = benchmark_query(adapter_modis, spec_modis, "MODIS Single Month (9 spatial × ~2 temporal)", iterations=2)
    results.append(result)
    print(f"  ✓ Mean: {result['mean']:.2f}s, Rows: {result.get('row_count', 'N/A')}")

    # Test 4: ImageCollection (MODIS) - Full year, low resolution (legacy behavior)
    print("\n[4/5] ImageCollection (MODIS) - Full year, low resolution...")
    spec_modis_year = RequestSpec(
        geometry=Geometry("bbox", [-122.5, 37.5, -122.3, 37.7]),
        time_range=("2023-01-01", "2023-12-31"),
        resolution="low"  # Single aggregated point
    )
    result = benchmark_query(adapter_modis, spec_modis_year, "MODIS Full Year (1 spatial × 23 temporal)", iterations=2)
    results.append(result)
    print(f"  ✓ Mean: {result['mean']:.2f}s, Rows: {result.get('row_count', 'N/A')}")

    # Test 5: ImageCollection (MODIS) - Large bbox with grid sampling
    print("\n[5/5] ImageCollection (MODIS) - Large bbox grid...")
    spec_modis_grid = RequestSpec(
        geometry=Geometry("bbox", [-96.893, 30.013, -94.501, 31.486]),  # Texas
        time_range=("2023-06-01", "2023-06-30"),
        resolution="medium"
    )
    result = benchmark_query(adapter_modis, spec_modis_grid, "MODIS Large Bbox (25 spatial × ~2 temporal)", iterations=2)
    results.append(result)
    print(f"  ✓ Mean: {result['mean']:.2f}s, Rows: {result.get('row_count', 'N/A')}")

    return results


def compare_results(legacy_results: List[Dict], cloud_results: List[Dict]):
    """Compare and display performance differences"""

    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)

    print(f"\n{'Test':<45} {'Legacy':<12} {'Cloud':<12} {'Speedup':<10}")
    print("-" * 82)

    for legacy, cloud in zip(legacy_results, cloud_results):
        test_name = legacy['description'][:44]

        if legacy['failed'] or cloud['failed']:
            legacy_time = "ERROR" if legacy['failed'] else f"{legacy['mean']:.2f}s"
            cloud_time = "ERROR" if cloud['failed'] else f"{cloud['mean']:.2f}s"
            speedup = "N/A"
        else:
            legacy_time = f"{legacy['mean']:.2f}s"
            cloud_time = f"{cloud['mean']:.2f}s"
            speedup_val = legacy['mean'] / cloud['mean']

            if speedup_val > 1.05:
                speedup = f"🟢 {speedup_val:.2f}x"
            elif speedup_val < 0.95:
                speedup = f"🔴 {1/speedup_val:.2f}x slower"
            else:
                speedup = f"⚪ ~same"

        print(f"{test_name:<45} {legacy_time:<12} {cloud_time:<12} {speedup:<10}")

    # Calculate overall statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    legacy_times = [r['mean'] for r in legacy_results if not r['failed']]
    cloud_times = [r['mean'] for r in cloud_results if not r['failed']]

    if legacy_times and cloud_times:
        print(f"\nLegacy API:")
        print(f"  Total time: {sum(legacy_times):.2f}s")
        print(f"  Average: {statistics.mean(legacy_times):.2f}s")
        print(f"  Range: {min(legacy_times):.2f}s - {max(legacy_times):.2f}s")

        print(f"\nCloud Project API:")
        print(f"  Total time: {sum(cloud_times):.2f}s")
        print(f"  Average: {statistics.mean(cloud_times):.2f}s")
        print(f"  Range: {min(cloud_times):.2f}s - {max(cloud_times):.2f}s")

        overall_speedup = sum(legacy_times) / sum(cloud_times)
        print(f"\nOverall Performance:")
        if overall_speedup > 1.05:
            print(f"  🟢 Cloud API is {overall_speedup:.2f}x FASTER")
        elif overall_speedup < 0.95:
            print(f"  🔴 Cloud API is {1/overall_speedup:.2f}x SLOWER")
        else:
            print(f"  ⚪ APIs have similar performance (~{overall_speedup:.2f}x)")


def main():
    """Run complete benchmark"""

    print("="*70)
    print("Earth Engine API Performance Benchmark")
    print("="*70)
    print("\nThis benchmark compares:")
    print("  • Legacy API (earthengine-legacy)")
    print("  • Cloud Project API (ecognita-470619)")
    print("\nRunning 5 tests with multiple iterations each...")
    print("This may take several minutes...")

    # Benchmark Legacy API
    print("\n" + "="*70)
    print("PHASE 1: Legacy API")
    print("="*70)
    api_name = initialize_ee(use_cloud_project=False)
    legacy_results = run_benchmark_suite(api_name)

    # Force re-initialization for Cloud API
    # (Need to restart ee module state)
    print("\n⚠️  Re-initializing Earth Engine for Cloud API test...")
    import importlib
    importlib.reload(ee)

    # Benchmark Cloud Project API
    print("\n" + "="*70)
    print("PHASE 2: Cloud Project API")
    print("="*70)
    api_name = initialize_ee(use_cloud_project=True)
    cloud_results = run_benchmark_suite(api_name)

    # Compare results
    compare_results(legacy_results, cloud_results)

    print("\n" + "="*70)
    print("✓ BENCHMARK COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
