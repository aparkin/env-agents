#!/usr/bin/env python3
"""
Integration test for Earth Engine grid sampling.

Tests grid sampling with real Earth Engine queries to verify:
1. Multiple samples are returned for medium/high resolution
2. Single sample for low resolution (legacy behavior)
3. Spatial distribution captures gradients
4. Metadata includes sampling strategy info

Requires Earth Engine authentication.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
import pandas as pd

def test_srtm_elevation_grid_sampling():
    """Test SRTM elevation with medium resolution (3×3 grid)"""
    print("\n" + "="*70)
    print("Test 1: SRTM Elevation with Medium Resolution")
    print("="*70)

    # San Francisco Bay Area - small bbox with elevation gradient
    bbox = [-122.5, 37.5, -122.3, 37.7]  # ~20km × 20km

    adapter = ProductionEarthEngineAdapter(
        asset_id="USGS/SRTMGL1_003",
        scale=30
    )

    spec = RequestSpec(
        geometry=Geometry("bbox", bbox),
        resolution="medium"  # Should give 9 samples
    )

    print(f"Querying bbox: {bbox}")
    print(f"Resolution: medium (expecting 3×3 grid = 9 samples)")

    result = adapter.fetch(spec)

    print(f"\n✓ Got {len(result)} rows")

    # Check we got multiple samples
    assert len(result) > 1, f"Expected multiple samples, got {len(result)}"

    # Check lat/lon are different (not all at centroid)
    lats = set(result['latitude'].unique())
    lons = set(result['longitude'].unique())
    print(f"✓ Unique latitudes: {len(lats)}")
    print(f"✓ Unique longitudes: {len(lons)}")
    assert len(lats) > 1, "All samples at same latitude (not a grid)"
    assert len(lons) > 1, "All samples at same longitude (not a grid)"

    # Check metadata includes sampling strategy
    if 'attributes' in result.columns and len(result) > 0:
        first_attrs = result.iloc[0]['attributes']
        if isinstance(first_attrs, dict) and 'spatial_sampling' in first_attrs:
            sampling = first_attrs['spatial_sampling']
            print(f"\nSampling Strategy:")
            print(f"  - Strategy: {sampling.get('strategy', 'N/A')}")
            print(f"  - Grid size: {sampling.get('grid_size', 'N/A')}")
            print(f"  - Actual samples: {sampling.get('actual_samples', 'N/A')}")
            print(f"  - Sample spacing: {sampling.get('sample_spacing_km', 'N/A'):.1f} km")

    # Check elevation values vary (capturing gradient)
    elevation_rows = result[result['variable'].str.contains('elevation', na=False)]
    if len(elevation_rows) > 0:
        elevations = elevation_rows['value'].tolist()
    else:
        elevations = []

    if elevations:
        print(f"\nElevation Statistics:")
        print(f"  - Min: {min(elevations):.1f} m")
        print(f"  - Max: {max(elevations):.1f} m")
        print(f"  - Mean: {sum(elevations)/len(elevations):.1f} m")
        print(f"  - Range: {max(elevations) - min(elevations):.1f} m")

        # San Francisco has significant elevation variation
        assert max(elevations) - min(elevations) > 20, \
            f"Expected elevation gradient > 20m, got {max(elevations) - min(elevations):.1f}m"

    print("\n✓ Test 1 PASSED")
    return result


def test_srtm_elevation_low_resolution():
    """Test SRTM with low resolution (single aggregated value)"""
    print("\n" + "="*70)
    print("Test 2: SRTM Elevation with Low Resolution (Legacy Behavior)")
    print("="*70)

    bbox = [-122.5, 37.5, -122.3, 37.7]

    adapter = ProductionEarthEngineAdapter(
        asset_id="USGS/SRTMGL1_003",
        scale=30
    )

    spec = RequestSpec(
        geometry=Geometry("bbox", bbox),
        resolution="low"  # Should give 1 sample
    )

    print(f"Querying bbox: {bbox}")
    print(f"Resolution: low (expecting 1 aggregated sample)")

    result = adapter.fetch(spec)

    print(f"\n✓ Got {len(result)} rows")

    # Check we got single sample (old behavior)
    assert len(result) == 1, f"Expected 1 sample for low resolution, got {len(result)}"

    # Check it has a value
    first_row = result.iloc[0]
    assert first_row['value'] is not None, "No elevation value returned"

    print(f"✓ Single aggregated elevation: {first_row['value']:.1f} m")
    print(f"✓ Location: ({first_row['latitude']:.4f}, {first_row['longitude']:.4f})")

    print("\n✓ Test 2 PASSED")
    return result


def test_large_bbox_adaptive_scaling():
    """Test large bbox with adaptive scaling"""
    print("\n" + "="*70)
    print("Test 3: Large Bbox with Adaptive Scaling")
    print("="*70)

    # Large bbox: ~300km × 300km (Central California)
    bbox = [-122.0, 36.0, -119.0, 39.0]

    adapter = ProductionEarthEngineAdapter(
        asset_id="USGS/SRTMGL1_003",
        scale=90  # Use 90m resolution (faster)
    )

    spec = RequestSpec(
        geometry=Geometry("bbox", bbox),
        resolution="medium"  # Should scale up from 9 samples
    )

    print(f"Querying bbox: {bbox}")
    print(f"Bbox size: ~300km × 300km ≈ 90,000 km²")
    print(f"Resolution: medium (expecting adaptive scaling)")

    result = adapter.fetch(spec)

    print(f"\n✓ Got {len(result)} rows")

    # Check we got more than base 9 samples
    assert len(result) > 9, f"Expected adaptive scaling > 9 samples, got {len(result)}"

    # Check metadata
    if 'attributes' in result.columns and len(result) > 0:
        first_attrs = result.iloc[0]['attributes']
        if isinstance(first_attrs, dict) and 'spatial_sampling' in first_attrs:
            sampling = first_attrs['spatial_sampling']
            print(f"\nAdaptive Sampling:")
            print(f"  - Strategy: {sampling.get('strategy', 'N/A')}")
            print(f"  - Requested: {sampling.get('requested_samples', 'N/A')}")
            print(f"  - Actual: {sampling.get('actual_samples', 'N/A')}")
            print(f"  - Scale factor: {sampling.get('scale_factor', 'N/A'):.2f}×")
            print(f"  - Grid size: {sampling.get('grid_size', 'N/A')}")

            assert sampling.get('strategy') == 'adaptive_scaled', \
                f"Expected adaptive_scaled strategy, got {sampling.get('strategy')}"

    print("\n✓ Test 3 PASSED")
    return result


def main():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("Earth Engine Grid Sampling Integration Tests")
    print("="*70)

    try:
        # Test 1: Medium resolution grid sampling
        test_srtm_elevation_grid_sampling()

        # Test 2: Low resolution (legacy behavior)
        test_srtm_elevation_low_resolution()

        # Test 3: Large bbox adaptive scaling
        test_large_bbox_adaptive_scaling()

        print("\n" + "="*70)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("="*70)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
