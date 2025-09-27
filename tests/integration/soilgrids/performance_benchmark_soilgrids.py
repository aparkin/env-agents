#!/usr/bin/env python3
"""
SoilGrids WCS Performance Benchmark Suite
Tests performance across different global locations, request sizes, and resolution strategies.
Based on user requirements for performance analysis of the enhanced WCS adapter.
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import statistics

# Add the package to Python path
env_agents_path = Path(__file__).parent
sys.path.insert(0, str(env_agents_path))

from env_agents.adapters.soil.wcs_adapter import SoilGridsWCSAdapter
from env_agents.core.models import RequestSpec, Geometry

class PerformanceBenchmarkSuite:
    """Comprehensive performance testing for SoilGrids WCS adapter"""

    def __init__(self):
        self.adapter = SoilGridsWCSAdapter()
        self.results = {
            "benchmark_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "adapter_version": "2.0_wcs_enhanced",
                "test_machine": os.uname().nodename if hasattr(os, 'uname') else "unknown",
                "python_version": sys.version
            },
            "location_performance": [],
            "size_performance": [],
            "resolution_strategy_performance": [],
            "catalog_performance": {},
            "summary_statistics": {}
        }

    def benchmark_global_locations(self) -> None:
        """Test performance across diverse global locations"""
        print("\n🌍 === GLOBAL LOCATION PERFORMANCE BENCHMARK ===")

        test_locations = [
            {"name": "Netherlands", "region": "Europe", "bbox": (5.78, 51.98, 5.8, 52.0), "biome": "temperate"},
            {"name": "California_Central_Valley", "region": "North America", "bbox": (-122.0, 37.0, -121.98, 37.02), "biome": "mediterranean"},
            {"name": "Amazon_Basin_Brazil", "region": "South America", "bbox": (-60.0, -3.2, -59.98, -3.18), "biome": "tropical_rainforest"},
            {"name": "Sahel_Mali", "region": "Africa", "bbox": (-4.0, 14.0, -3.98, 14.02), "biome": "semi_arid"},
            {"name": "Indo_Gangetic_Plain", "region": "Asia", "bbox": (77.2, 28.6, 77.22, 28.62), "biome": "subtropical"},
            {"name": "Murray_Darling_Australia", "region": "Oceania", "bbox": (146.0, -36.0, 146.02, -35.98), "biome": "temperate_grassland"},
            {"name": "Siberian_Taiga", "region": "Asia", "bbox": (104.0, 60.0, 104.02, 60.02), "biome": "boreal_forest"},
            {"name": "Pampas_Argentina", "region": "South America", "bbox": (-61.5, -34.0, -61.48, -33.98), "biome": "grassland"},
            {"name": "Great_Plains_USA", "region": "North America", "bbox": (-101.0, 41.0, -100.98, 41.02), "biome": "prairie"},
            {"name": "Scandinavian_Shield", "region": "Europe", "bbox": (15.0, 62.0, 15.02, 62.02), "biome": "boreal"}
        ]

        for i, location in enumerate(test_locations, 1):
            print(f"\n[{i:2d}/10] Testing {location['name']} ({location['region']})...")

            # Test multiple soil properties
            test_properties = ["soil:clay", "soil:organic_carbon", "soil:ph"]
            location_results = {
                "location": location,
                "property_results": [],
                "overall_timing": {},
                "data_quality": {}
            }

            overall_start = time.time()

            for prop in test_properties:
                prop_start = time.time()

                try:
                    geometry = Geometry(type="bbox", coordinates=list(location['bbox']))
                    spec = RequestSpec(
                        geometry=geometry,
                        variables=[prop],
                        extra={"max_pixels": 50000}
                    )

                    rows = self.adapter._fetch_rows(spec)
                    prop_time = time.time() - prop_start

                    result = {
                        "property": prop,
                        "execution_time_seconds": prop_time,
                        "observations_returned": len(rows) if rows else 0,
                        "success": len(rows) > 0 if rows else False,
                        "throughput_obs_per_second": len(rows) / prop_time if rows and prop_time > 0 else 0
                    }

                    # Sample data quality check
                    if rows:
                        sample_values = [r.get('value') for r in rows[:10] if r.get('value') is not None]
                        if sample_values:
                            result["sample_value_range"] = {
                                "min": min(sample_values),
                                "max": max(sample_values),
                                "mean": statistics.mean(sample_values)
                            }

                    location_results["property_results"].append(result)
                    print(f"    {prop}: {len(rows) if rows else 0} obs in {prop_time:.2f}s")

                except Exception as e:
                    error_time = time.time() - prop_start
                    location_results["property_results"].append({
                        "property": prop,
                        "execution_time_seconds": error_time,
                        "observations_returned": 0,
                        "success": False,
                        "error": str(e)[:100]
                    })
                    print(f"    {prop}: FAILED in {error_time:.2f}s - {str(e)[:50]}")

            overall_time = time.time() - overall_start
            location_results["overall_timing"] = {
                "total_time_seconds": overall_time,
                "average_time_per_property": overall_time / len(test_properties)
            }

            self.results["location_performance"].append(location_results)

    def benchmark_request_sizes(self) -> None:
        """Test performance across different bounding box sizes"""
        print("\n📐 === REQUEST SIZE PERFORMANCE BENCHMARK ===")

        # Base location: Netherlands (known to work well)
        base_lat, base_lon = 52.0, 5.8

        test_sizes = [
            {"name": "Micro (0.002°)", "size": 0.002, "description": "Single 250m pixel"},
            {"name": "Tiny (0.01°)", "size": 0.01, "description": "~1km x 1km"},
            {"name": "Small (0.05°)", "size": 0.05, "description": "~5km x 5km"},
            {"name": "Medium (0.1°)", "size": 0.1, "description": "~10km x 10km"},
            {"name": "Large (0.2°)", "size": 0.2, "description": "~20km x 20km"},
            {"name": "XLarge (0.5°)", "size": 0.5, "description": "~50km x 50km"},
            {"name": "XXLarge (1.0°)", "size": 1.0, "description": "~100km x 100km"}
        ]

        for i, test_size in enumerate(test_sizes, 1):
            print(f"\\n[{i}/7] Testing {test_size['name']} - {test_size['description']}...")

            size = test_size['size']
            bbox = (base_lon - size/2, base_lat - size/2, base_lon + size/2, base_lat + size/2)

            start_time = time.time()

            try:
                # Test guard rails calculation
                geometry = Geometry(type="bbox", coordinates=list(bbox))
                spec = RequestSpec(geometry=geometry, variables=["soil:clay"])

                guard_rail_start = time.time()
                limits = self.adapter._get_guard_rail_limits(spec)
                guard_rail_time = time.time() - guard_rail_start

                # Test actual data fetch
                fetch_start = time.time()
                spec_with_limits = RequestSpec(
                    geometry=geometry,
                    variables=["soil:clay"],
                    extra={"max_pixels": 100000}
                )
                rows = self.adapter._fetch_rows(spec_with_limits)
                fetch_time = time.time() - fetch_start

                total_time = time.time() - start_time

                result = {
                    "size_config": test_size,
                    "bbox": bbox,
                    "estimated_pixels": limits.get('estimated_pixels', 0),
                    "strategy": limits.get('strategy', 'unknown'),
                    "guard_rail_time_seconds": guard_rail_time,
                    "fetch_time_seconds": fetch_time,
                    "total_time_seconds": total_time,
                    "observations_returned": len(rows) if rows else 0,
                    "success": len(rows) > 0 if rows else False,
                    "throughput_pixels_per_second": limits.get('estimated_pixels', 0) / total_time if total_time > 0 else 0
                }

                if limits.get('strategy') == 'tiled':
                    result["tile_count"] = limits.get('tile_count', 0)

                print(f"    Strategy: {limits.get('strategy', 'unknown')}, {limits.get('estimated_pixels', 0):,} pixels")
                print(f"    Result: {len(rows) if rows else 0} obs in {total_time:.2f}s")

            except Exception as e:
                error_time = time.time() - start_time
                result = {
                    "size_config": test_size,
                    "bbox": bbox,
                    "total_time_seconds": error_time,
                    "observations_returned": 0,
                    "success": False,
                    "error": str(e)[:100]
                }
                print(f"    FAILED in {error_time:.2f}s - {str(e)[:50]}")

            self.results["size_performance"].append(result)

    def benchmark_resolution_strategies(self) -> None:
        """Test performance of different resolution strategies"""
        print("\\n⚙️ === RESOLUTION STRATEGY PERFORMANCE BENCHMARK ===")

        # Test different strategies with controlled conditions
        test_scenarios = [
            {"name": "Direct (Small)", "bbox": (5.78, 51.98, 5.82, 52.02), "expected_strategy": "direct"},
            {"name": "Resampled (Medium)", "bbox": (5.7, 51.9, 5.9, 52.1), "expected_strategy": "resampled"},
            {"name": "Tiled (Large)", "bbox": (5.5, 51.7, 6.1, 52.3), "expected_strategy": "tiled"}
        ]

        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\\n[{i}/3] Testing {scenario['name']} scenario...")

            start_time = time.time()

            try:
                geometry = Geometry(type="bbox", coordinates=list(scenario['bbox']))
                spec = RequestSpec(
                    geometry=geometry,
                    variables=["soil:clay", "soil:organic_carbon"],
                    extra={"max_pixels": 200000}
                )

                # Get strategy calculation timing
                strategy_start = time.time()
                limits = self.adapter._get_guard_rail_limits(spec)
                strategy_time = time.time() - strategy_start

                # Execute with timing for each stage
                fetch_start = time.time()
                rows = self.adapter._fetch_rows(spec)
                fetch_time = time.time() - fetch_start

                total_time = time.time() - start_time

                result = {
                    "scenario": scenario,
                    "actual_strategy": limits.get('strategy', 'unknown'),
                    "strategy_matches_expected": limits.get('strategy') == scenario['expected_strategy'],
                    "strategy_calculation_time": strategy_time,
                    "fetch_time_seconds": fetch_time,
                    "total_time_seconds": total_time,
                    "estimated_pixels": limits.get('estimated_pixels', 0),
                    "observations_returned": len(rows) if rows else 0,
                    "variables_requested": len(spec.variables),
                    "success": len(rows) > 0 if rows else False,
                    "efficiency_obs_per_second": len(rows) / total_time if rows and total_time > 0 else 0
                }

                if limits.get('strategy') == 'tiled':
                    result["tiles_used"] = limits.get('tile_count', 0)
                elif limits.get('strategy') == 'resampled':
                    result["resampling_factor"] = limits.get('resampling_factor', 1.0)

                print(f"    Strategy: {limits.get('strategy')} ({'✓' if result['strategy_matches_expected'] else '✗'} expected)")
                print(f"    Performance: {len(rows) if rows else 0} obs in {total_time:.2f}s")

            except Exception as e:
                error_time = time.time() - start_time
                result = {
                    "scenario": scenario,
                    "total_time_seconds": error_time,
                    "observations_returned": 0,
                    "success": False,
                    "error": str(e)[:100]
                }
                print(f"    FAILED in {error_time:.2f}s - {str(e)[:50]}")

            self.results["resolution_strategy_performance"].append(result)

    def benchmark_catalog_operations(self) -> None:
        """Benchmark catalog building and caching operations"""
        print("\\n📚 === CATALOG PERFORMANCE BENCHMARK ===")

        # Test cold catalog build (no cache)
        print("\\nTesting catalog build performance...")

        # Clear any existing cache to test cold start
        cache_file = self.adapter.cache_dir / "soilgrids_coverages.json"
        cache_exists = cache_file.exists()

        if cache_exists:
            # Backup existing cache
            backup_file = cache_file.with_suffix('.json.backup')
            cache_file.rename(backup_file)
            print(f"  Backed up existing cache to test cold start")

        try:
            # Cold catalog build
            cold_start = time.time()
            self.adapter.catalog_cache = None
            catalog = self.adapter._build_catalog(force_refresh=True)
            cold_time = time.time() - cold_start

            total_coverages = sum(len(v) for v in catalog.values())

            # Warm catalog load (from cache)
            warm_start = time.time()
            cached_catalog = self.adapter._build_catalog(force_refresh=False)
            warm_time = time.time() - warm_start

            self.results["catalog_performance"] = {
                "cold_build_time_seconds": cold_time,
                "warm_load_time_seconds": warm_time,
                "speedup_factor": cold_time / warm_time if warm_time > 0 else float('inf'),
                "total_services_discovered": len(catalog),
                "total_coverages_discovered": total_coverages,
                "cache_effectiveness": "excellent" if warm_time < 1.0 else "good" if warm_time < 5.0 else "needs_improvement"
            }

            print(f"  Cold build: {cold_time:.1f}s ({total_coverages} coverages)")
            print(f"  Warm load: {warm_time:.3f}s")
            print(f"  Speedup: {cold_time/warm_time:.1f}x faster from cache")

        finally:
            # Restore backup if it exists
            if cache_exists:
                backup_file = cache_file.with_suffix('.json.backup')
                if backup_file.exists():
                    backup_file.rename(cache_file)
                    print(f"  Restored original cache")

    def generate_performance_summary(self) -> None:
        """Generate summary statistics and insights"""
        print("\\n📊 === PERFORMANCE SUMMARY ===")

        # Location performance summary
        location_results = self.results["location_performance"]
        if location_results:
            successful_locations = [r for r in location_results if any(p.get("success", False) for p in r.get("property_results", []))]
            success_rate = len(successful_locations) / len(location_results)

            all_times = []
            all_throughputs = []
            for loc in location_results:
                for prop in loc.get("property_results", []):
                    if prop.get("success", False):
                        all_times.append(prop.get("execution_time_seconds", 0))
                        all_throughputs.append(prop.get("throughput_obs_per_second", 0))

            location_summary = {
                "total_locations_tested": len(location_results),
                "successful_locations": len(successful_locations),
                "global_success_rate": success_rate,
                "average_response_time_seconds": statistics.mean(all_times) if all_times else 0,
                "median_response_time_seconds": statistics.median(all_times) if all_times else 0,
                "average_throughput_obs_per_second": statistics.mean(all_throughputs) if all_throughputs else 0
            }

            print(f"\\n📍 Global Location Performance:")
            print(f"   Success Rate: {success_rate:.1%} ({len(successful_locations)}/{len(location_results)} locations)")
            print(f"   Avg Response Time: {location_summary['average_response_time_seconds']:.2f}s")
            print(f"   Avg Throughput: {location_summary['average_throughput_obs_per_second']:.1f} obs/sec")

        # Size performance summary
        size_results = self.results["size_performance"]
        if size_results:
            successful_sizes = [r for r in size_results if r.get("success", False)]
            size_success_rate = len(successful_sizes) / len(size_results)

            size_summary = {
                "total_sizes_tested": len(size_results),
                "successful_sizes": len(successful_sizes),
                "size_success_rate": size_success_rate,
                "largest_successful_request": max([r.get("estimated_pixels", 0) for r in successful_sizes]) if successful_sizes else 0,
                "strategies_used": list(set([r.get("strategy", "unknown") for r in size_results if r.get("strategy")]))
            }

            print(f"\\n📐 Size Scalability Performance:")
            print(f"   Success Rate: {size_success_rate:.1%} ({len(successful_sizes)}/{len(size_results)} sizes)")
            print(f"   Largest Request: {size_summary['largest_successful_request']:,} pixels")
            print(f"   Strategies Used: {', '.join(size_summary['strategies_used'])}")

        # Overall assessment
        overall_score = 0
        factors = []

        if location_results:
            location_factor = success_rate * 0.4  # 40% weight
            overall_score += location_factor
            factors.append(f"Global Coverage: {success_rate:.1%}")

        if size_results:
            size_factor = size_success_rate * 0.3  # 30% weight
            overall_score += size_factor
            factors.append(f"Size Handling: {size_success_rate:.1%}")

        catalog_perf = self.results.get("catalog_performance", {})
        if catalog_perf:
            cache_factor = min(catalog_perf.get("speedup_factor", 0) / 100, 0.3)  # 30% weight, capped
            overall_score += cache_factor
            factors.append(f"Catalog Cache: {catalog_perf.get('speedup_factor', 0):.1f}x speedup")

        if overall_score >= 0.8:
            assessment = "🎉 EXCELLENT"
        elif overall_score >= 0.6:
            assessment = "👍 GOOD"
        elif overall_score >= 0.4:
            assessment = "⚠️ ADEQUATE"
        else:
            assessment = "❌ NEEDS IMPROVEMENT"

        self.results["summary_statistics"] = {
            "overall_score": overall_score,
            "assessment": assessment,
            "contributing_factors": factors,
            "location_summary": location_summary if location_results else {},
            "size_summary": size_summary if size_results else {},
            "benchmark_completion_time": datetime.now(timezone.utc).isoformat()
        }

        print(f"\\n🏆 OVERALL ASSESSMENT: {assessment} (Score: {overall_score:.2f})")
        for factor in factors:
            print(f"   • {factor}")

    def save_results(self, filename: str = None) -> str:
        """Save benchmark results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"soilgrids_performance_benchmark_{timestamp}.json"

        results_file = Path(__file__).parent / "data" / filename
        results_file.parent.mkdir(exist_ok=True)

        # Add final metadata
        self.results["benchmark_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
        self.results["benchmark_metadata"]["duration_minutes"] = (
            datetime.fromisoformat(self.results["benchmark_metadata"]["end_time"].replace('Z', '+00:00')) -
            datetime.fromisoformat(self.results["benchmark_metadata"]["start_time"].replace('Z', '+00:00'))
        ).total_seconds() / 60

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\\n💾 Benchmark results saved to: {results_file}")
        return str(results_file)

    def run_full_benchmark(self) -> str:
        """Run complete performance benchmark suite"""
        print("🚀 SoilGrids WCS Performance Benchmark Suite")
        print(f"Started: {self.results['benchmark_metadata']['start_time']}")
        print("=" * 60)

        try:
            # Run all benchmark tests
            self.benchmark_catalog_operations()
            self.benchmark_global_locations()
            self.benchmark_request_sizes()
            self.benchmark_resolution_strategies()

            # Generate summary
            self.generate_performance_summary()

            # Save results
            return self.save_results()

        except KeyboardInterrupt:
            print("\\n⚠️ Benchmark interrupted by user")
            return self.save_results("interrupted_benchmark.json")
        except Exception as e:
            print(f"\\n💥 Benchmark failed: {e}")
            self.results["benchmark_error"] = str(e)
            return self.save_results("failed_benchmark.json")

def main():
    """Main benchmark execution"""
    print("SoilGrids WCS Performance Benchmark")
    print("This will test performance across global locations, sizes, and strategies.")
    print("Estimated time: 10-15 minutes")

    response = input("\\nProceed? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("Benchmark cancelled.")
        sys.exit(0)

    benchmark = PerformanceBenchmarkSuite()
    results_file = benchmark.run_full_benchmark()

    print(f"\\n✅ Benchmark Complete!")
    print(f"Results saved to: {results_file}")

    # Quick summary
    summary = benchmark.results.get("summary_statistics", {})
    if summary:
        print(f"\\nFinal Assessment: {summary.get('assessment', 'Unknown')}")
        print(f"Overall Score: {summary.get('overall_score', 0):.2f}")

if __name__ == "__main__":
    main()