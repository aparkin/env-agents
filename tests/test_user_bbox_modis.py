#!/usr/bin/env python3
"""
Test user-specified bounding box with MODIS NDVI data
Asset: MODIS/061/MOD13Q1 (MODIS Terra Vegetation Indices 16-Day Global 250m)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
import pandas as pd

def test_modis_ndvi():
    """Test MODIS NDVI with user's Texas bounding box"""
    print("\n" + "="*70)
    print("Testing MODIS/061/MOD13Q1 with Texas Bounding Box")
    print("="*70)

    # User's bbox: (30.013, -96.893 to 31.486, -94.501)
    bbox = [-96.893, 30.013, -94.501, 31.486]

    print(f"\nBounding Box:")
    print(f"  Southwest corner: ({bbox[1]:.3f}, {bbox[0]:.3f})")
    print(f"  Northeast corner: ({bbox[3]:.3f}, {bbox[2]:.3f})")
    print(f"  Approximate size: ~270km × 165km")

    # Create MODIS adapter
    adapter = ProductionEarthEngineAdapter(
        asset_id="MODIS/061/MOD13Q1",  # MODIS NDVI
        scale=250  # Native MODIS resolution
    )

    print("\n" + "-"*70)
    print("Query 1: Default Resolution (Recent NDVI Data)")
    print("-"*70)

    # Query recent year of data
    spec = RequestSpec(
        geometry=Geometry("bbox", bbox),
        time_range=("2023-01-01", "2023-12-31")
    )

    print("\nQuerying MODIS NDVI for 2023...")
    result = adapter.fetch(spec)

    print(f"\n✓ Got {len(result)} rows")

    # Show unique coordinates
    unique_lats = sorted(result['latitude'].unique())
    unique_lons = sorted(result['longitude'].unique())

    print(f"\n✓ Unique Latitudes ({len(unique_lats)}):")
    if len(unique_lats) <= 10:
        for lat in unique_lats:
            print(f"    {lat:.4f}")
    else:
        print(f"    {unique_lats[0]:.4f} ... {unique_lats[-1]:.4f}")

    print(f"\n✓ Unique Longitudes ({len(unique_lons)}):")
    if len(unique_lons) <= 10:
        for lon in unique_lons:
            print(f"    {lon:.4f}")
    else:
        print(f"    {unique_lons[0]:.4f} ... {unique_lons[-1]:.4f}")

    # Count unique coordinate pairs
    coords = result[['latitude', 'longitude']].drop_duplicates()
    print(f"\n✓ Total unique coordinate pairs: {len(coords)}")

    if len(coords) <= 25:
        print("\nCoordinate Pairs (lat, lon):")
        for idx, row in coords.sort_values(['latitude', 'longitude']).iterrows():
            print(f"    ({row['latitude']:.4f}, {row['longitude']:.4f})")

    # Show sampling metadata
    if 'attributes' in result.columns and len(result) > 0:
        first_attrs = result.iloc[0]['attributes']
        if isinstance(first_attrs, dict) and 'spatial_sampling' in first_attrs:
            sampling = first_attrs['spatial_sampling']
            print(f"\n✓ Sampling Metadata:")
            print(f"    Strategy: {sampling.get('strategy', 'N/A')}")
            print(f"    Grid size: {sampling.get('grid_size', 'N/A')}")
            print(f"    Actual samples: {sampling.get('actual_samples', 'N/A')}")
            print(f"    Sample spacing: {sampling.get('sample_spacing_km', 'N/A'):.1f} km")
        else:
            print(f"\n⚠️  No spatial_sampling metadata found")
            print(f"    (ImageCollections may not yet support grid sampling)")

    # Show variables
    variables = result['variable'].unique()
    print(f"\n✓ Variables returned ({len(variables)}):")
    for var in sorted(variables):
        count = len(result[result['variable'] == var])
        print(f"    {var}: {count} values")

    # Show NDVI statistics if available
    ndvi_rows = result[result['variable'].str.contains('NDVI', na=False)]
    if len(ndvi_rows) > 0:
        print(f"\n✓ NDVI Statistics:")
        print(f"    Count: {len(ndvi_rows)}")
        print(f"    Min: {ndvi_rows['value'].min():.4f}")
        print(f"    Max: {ndvi_rows['value'].max():.4f}")
        print(f"    Mean: {ndvi_rows['value'].mean():.4f}")
        print(f"    Std: {ndvi_rows['value'].std():.4f}")

    # Check temporal coverage
    if 'time' in result.columns:
        unique_times = result['time'].unique()
        print(f"\n✓ Temporal Coverage:")
        print(f"    Unique dates: {len(unique_times)}")
        if len(unique_times) <= 10:
            for t in sorted(unique_times):
                print(f"    {t}")
        else:
            sorted_times = sorted(unique_times)
            print(f"    {sorted_times[0]} to {sorted_times[-1]}")
            print(f"    ({len(unique_times)} time steps)")

    # Display first few rows as table
    print(f"\n✓ Sample Data (first 10 rows):")
    display_cols = ['latitude', 'longitude', 'time', 'variable', 'value']
    available_cols = [col for col in display_cols if col in result.columns]
    print(result[available_cols].head(10).to_string(index=False))

    # Test with explicit resolution control
    print("\n" + "-"*70)
    print("Query 2: Medium Resolution Explicitly Set")
    print("-"*70)

    spec_med = RequestSpec(
        geometry=Geometry("bbox", bbox),
        time_range=("2023-06-01", "2023-06-30"),  # Single month
        resolution="medium"
    )

    print("\nQuerying MODIS NDVI for June 2023 with resolution='medium'...")
    result_med = adapter.fetch(spec_med)

    print(f"\n✓ Got {len(result_med)} rows")
    unique_coords_med = result_med[['latitude', 'longitude']].drop_duplicates()
    print(f"✓ Unique coordinate pairs: {len(unique_coords_med)}")

    if 'attributes' in result_med.columns and len(result_med) > 0:
        first_attrs_med = result_med.iloc[0]['attributes']
        if isinstance(first_attrs_med, dict) and 'spatial_sampling' in first_attrs_med:
            sampling_med = first_attrs_med['spatial_sampling']
            print(f"✓ Grid size: {sampling_med.get('grid_size', 'N/A')}")
        else:
            print("⚠️  No spatial_sampling metadata (ImageCollection not using grid sampling)")

    print("\n" + "="*70)
    print("✓ TEST COMPLETED")
    print("="*70)

    # Summary
    print(f"\nSummary:")
    print(f"  • Asset: MODIS/061/MOD13Q1 (250m resolution)")
    print(f"  • Query 1: {len(result)} rows, {len(coords)} unique locations")
    print(f"  • Query 2: {len(result_med)} rows, {len(unique_coords_med)} unique locations")

    if len(coords) > 1:
        print(f"  • ✅ Multiple coordinates returned!")
    else:
        print(f"  • ⚠️  Single coordinate (ImageCollection may not yet support grid sampling)")


if __name__ == "__main__":
    test_modis_ndvi()
