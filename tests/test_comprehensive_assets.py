#!/usr/bin/env python3
"""
Comprehensive Asset Testing: Grid Sampling Validation

Tests grid sampling across multiple Earth Engine assets with different characteristics:
- PRIORITY_1: Core production assets (MODIS, SoilGrids, SRTM)
- PRIORITY_2: Additional valuable assets (WAPOR, Landsat, SMAP)
- PRIORITY_3: Edge cases and problematic assets

Test Configuration:
- Bounding Box: Texas region (30.013, -96.893 to 31.486, -94.501)
- Time Range: 2020-01-01 to 2020-12-31
- Expected: Multiple coordinates (not single centroid) for spatial queries
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
import pandas as pd

# Test Configuration
TEST_BBOX = [-96.893469, 30.01347, -94.500935, 31.486141]
TEST_TIME_RANGE = ("2020-01-01", "2020-12-31")

# Asset Priority Tiers
PRIORITY_1_ASSETS = [
    ("MODIS/061/MOD13Q1", 250, "ImageCollection"),      # Vegetation indices - 16-day, 250m
    ("MODIS/061/MOD15A2H", 500, "ImageCollection"),     # Leaf Area Index - 8-day, 500m
    ("MODIS/061/MOD17A2H", 500, "ImageCollection"),     # Gross Primary Productivity - 8-day, 500m
    ("MODIS/061/MOD11A2", 1000, "ImageCollection"),     # Land Surface Temperature - 8-day, 1km
    ("MODIS/061/MOD16A2", 500, "ImageCollection"),      # Evapotranspiration - 8-day, 500m
    ("ISRIC/SoilGrids250m/v2_0", 250, "Image"),         # SoilGrids - Static, 250m
    ("USGS/SRTMGL1_003", 90, "Image"),                  # SRTM elevation - Static, 30m
]

PRIORITY_2_ASSETS = [
    ("FAO/WAPOR/3/L1_T_D", 100, "ImageCollection"),     # WAPOR transpiration - Dekadal, 100m
    ("LANDSAT/LC08/C02/T1_L2", 30, "ImageCollection"),  # Landsat 8 - 16-day, 30m
    ("NASA/SMAP/SPL4SMGP/008", 9000, "ImageCollection"), # SMAP soil moisture - Daily, 9km
    ("OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02", 250, "Image"),  # Soil organic carbon
]

PRIORITY_3_ASSETS = [
    ("MODIS/MOD09GA_EVI", 500, "ImageCollection"),      # Deprecated MODIS EVI
    ("UMD/hansen/global_forest_change_2019_v1_7", 30, "Image"),  # Old Hansen version
    ("ESA/WorldCereal/AEZ/v100", 100, "ImageCollection"),  # May cause "not an Image" error
    ("LARSE/GEDI/GEDI04_A_002", 25, "ImageCollection"),    # May cause "not an Image" error
    ("FAO/GHG/1/DROSE_A", 1000, "ImageCollection"),        # Limited temporal coverage
    ("MODIS/MOD09GA_006_NDSI", 500, "ImageCollection"),    # May have temporal gaps
]


@dataclass
class TestResult:
    """Results from testing a single asset"""
    asset_id: str
    scale: int
    asset_type: str
    success: bool
    error_message: Optional[str]
    duration_sec: float
    row_count: int
    unique_coords: int
    unique_times: int
    variables: List[str]
    sample_metadata: Optional[Dict]


def test_asset(asset_id: str, scale: int, asset_type: str,
               use_time_range: bool = True) -> TestResult:
    """Test a single Earth Engine asset"""

    print(f"\n{'='*70}")
    print(f"Testing: {asset_id}")
    print(f"  Scale: {scale}m | Type: {asset_type}")
    print(f"{'='*70}")

    start_time = time.time()

    try:
        # Create adapter
        adapter = ProductionEarthEngineAdapter(
            asset_id=asset_id,
            scale=scale
        )

        # Build request spec
        if use_time_range and asset_type == "ImageCollection":
            spec = RequestSpec(
                geometry=Geometry("bbox", TEST_BBOX),
                time_range=TEST_TIME_RANGE,
                resolution="medium"  # Request 9 samples (3×3 grid)
            )
        else:
            spec = RequestSpec(
                geometry=Geometry("bbox", TEST_BBOX),
                resolution="medium"
            )

        # Fetch data
        result = adapter.fetch(spec)
        duration = time.time() - start_time

        # Analyze results
        row_count = len(result)
        unique_coords = len(result[['latitude', 'longitude']].drop_duplicates())
        unique_times = len(result['time'].unique()) if 'time' in result.columns else 1
        variables = sorted(result['variable'].unique())

        # Extract sampling metadata
        sample_metadata = None
        if 'attributes' in result.columns and len(result) > 0:
            first_attrs = result.iloc[0]['attributes']
            if isinstance(first_attrs, dict) and 'spatial_sampling' in first_attrs:
                sample_metadata = first_attrs['spatial_sampling']

        # Display results
        print(f"\n✅ SUCCESS")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Rows: {row_count:,}")
        print(f"  Unique coordinates: {unique_coords}")
        print(f"  Unique times: {unique_times}")
        print(f"  Variables ({len(variables)}): {', '.join(variables[:5])}")
        if len(variables) > 5:
            print(f"    ... and {len(variables) - 5} more")

        if sample_metadata:
            print(f"  Sampling: {sample_metadata.get('strategy', 'N/A')} "
                  f"({sample_metadata.get('grid_size', 'N/A')})")

        # Show sample data
        if row_count > 0:
            print(f"\n  Sample Data (first 5 rows):")
            display_cols = ['latitude', 'longitude', 'time', 'variable', 'value']
            available_cols = [col for col in display_cols if col in result.columns]
            sample_df = result[available_cols].head(5)
            for line in sample_df.to_string(index=False).split('\n'):
                print(f"    {line}")

        return TestResult(
            asset_id=asset_id,
            scale=scale,
            asset_type=asset_type,
            success=True,
            error_message=None,
            duration_sec=duration,
            row_count=row_count,
            unique_coords=unique_coords,
            unique_times=unique_times,
            variables=variables,
            sample_metadata=sample_metadata
        )

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)

        print(f"\n❌ FAILED")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Error: {error_msg}")

        return TestResult(
            asset_id=asset_id,
            scale=scale,
            asset_type=asset_type,
            success=False,
            error_message=error_msg,
            duration_sec=duration,
            row_count=0,
            unique_coords=0,
            unique_times=0,
            variables=[],
            sample_metadata=None
        )


def test_asset_tier(tier_name: str, assets: List[tuple]) -> List[TestResult]:
    """Test all assets in a priority tier"""

    print(f"\n{'#'*70}")
    print(f"# {tier_name}")
    print(f"# {len(assets)} assets")
    print(f"{'#'*70}")

    results = []
    for asset_id, scale, asset_type in assets:
        result = test_asset(asset_id, scale, asset_type)
        results.append(result)

        # Brief pause between assets to avoid rate limits
        time.sleep(2)

    return results


def print_summary(all_results: Dict[str, List[TestResult]]):
    """Print comprehensive summary of all test results"""

    print(f"\n{'='*70}")
    print(f"COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*70}")

    for tier_name, results in all_results.items():
        print(f"\n{tier_name}:")
        print(f"  Total: {len(results)}")
        print(f"  Success: {sum(1 for r in results if r.success)}")
        print(f"  Failed: {sum(1 for r in results if not r.success)}")

        # Success details
        successful = [r for r in results if r.success]
        if successful:
            total_rows = sum(r.row_count for r in successful)
            avg_coords = sum(r.unique_coords for r in successful) / len(successful)
            print(f"  Total rows: {total_rows:,}")
            print(f"  Avg unique coords: {avg_coords:.1f}")

    # Detailed results table
    print(f"\n{'='*70}")
    print(f"DETAILED RESULTS")
    print(f"{'='*70}")

    print(f"\n{'Asset':<45} {'Status':<10} {'Rows':<10} {'Coords':<8} {'Times':<8}")
    print("-" * 85)

    for tier_name, results in all_results.items():
        print(f"\n{tier_name}:")
        for r in results:
            asset_short = r.asset_id.split('/')[-1][:43]
            status = "✅ OK" if r.success else "❌ FAIL"
            rows = f"{r.row_count:,}" if r.success else "-"
            coords = str(r.unique_coords) if r.success else "-"
            times = str(r.unique_times) if r.success else "-"

            print(f"  {asset_short:<43} {status:<10} {rows:<10} {coords:<8} {times:<8}")

    # Grid sampling validation
    print(f"\n{'='*70}")
    print(f"GRID SAMPLING VALIDATION")
    print(f"{'='*70}")

    multi_coord_count = 0
    single_coord_count = 0

    for tier_name, results in all_results.items():
        for r in results:
            if r.success:
                if r.unique_coords > 1:
                    multi_coord_count += 1
                else:
                    single_coord_count += 1
                    print(f"⚠️  Single coordinate: {r.asset_id}")

    print(f"\n✅ Multiple coordinates: {multi_coord_count}")
    print(f"⚠️  Single coordinate: {single_coord_count}")

    if single_coord_count > 0:
        print(f"\nNote: Some assets returned single coordinates.")
        print(f"This may indicate grid sampling is not yet supported for those asset types.")

    # Failures analysis
    print(f"\n{'='*70}")
    print(f"FAILURE ANALYSIS")
    print(f"{'='*70}")

    failed_results = []
    for tier_name, results in all_results.items():
        failed_results.extend([r for r in results if not r.success])

    if failed_results:
        print(f"\n{len(failed_results)} assets failed:")
        for r in failed_results:
            print(f"\n❌ {r.asset_id}")
            print(f"   Error: {r.error_message[:100]}")
    else:
        print(f"\n✅ All assets succeeded!")


def main():
    """Run comprehensive asset testing"""

    print("="*70)
    print("COMPREHENSIVE EARTH ENGINE ASSET TESTING")
    print("="*70)
    print(f"\nTest Configuration:")
    print(f"  Bounding Box: {TEST_BBOX}")
    print(f"  Time Range: {TEST_TIME_RANGE[0]} to {TEST_TIME_RANGE[1]}")
    print(f"  Resolution: medium (9 samples / 3×3 grid)")
    print(f"\nAsset Counts:")
    print(f"  PRIORITY_1: {len(PRIORITY_1_ASSETS)} assets (core production)")
    print(f"  PRIORITY_2: {len(PRIORITY_2_ASSETS)} assets (additional)")
    print(f"  PRIORITY_3: {len(PRIORITY_3_ASSETS)} assets (edge cases)")
    print(f"  Total: {len(PRIORITY_1_ASSETS) + len(PRIORITY_2_ASSETS) + len(PRIORITY_3_ASSETS)} assets")
    print(f"\nThis may take several minutes...")

    all_results = {}

    # Test each priority tier
    all_results["PRIORITY_1"] = test_asset_tier("PRIORITY 1: CORE ASSETS", PRIORITY_1_ASSETS)
    all_results["PRIORITY_2"] = test_asset_tier("PRIORITY 2: ADDITIONAL ASSETS", PRIORITY_2_ASSETS)
    all_results["PRIORITY_3"] = test_asset_tier("PRIORITY 3: EDGE CASES", PRIORITY_3_ASSETS)

    # Print summary
    print_summary(all_results)

    print(f"\n{'='*70}")
    print(f"✓ COMPREHENSIVE TESTING COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
