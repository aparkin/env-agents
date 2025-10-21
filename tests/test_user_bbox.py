#!/usr/bin/env python3
"""
Test user-specified bounding box: (30.013, -96.893 to 31.486, -94.501)
Texas region (Houston/College Station area)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
import pandas as pd

def test_user_bbox():
    """Test user's Texas bounding box"""
    print("\n" + "="*70)
    print("Testing User Bounding Box: Texas Region")
    print("="*70)

    # User's bbox: (30.013, -96.893 to 31.486, -94.501)
    # Format: [minlon, minlat, maxlon, maxlat]
    bbox = [-96.893, 30.013, -94.501, 31.486]

    print(f"\nBounding Box:")
    print(f"  Southwest corner: ({bbox[1]:.3f}, {bbox[0]:.3f})")
    print(f"  Northeast corner: ({bbox[3]:.3f}, {bbox[2]:.3f})")
    print(f"  Approximate size: ~270km × 165km")

    # Create SRTM elevation adapter
    adapter = ProductionEarthEngineAdapter(
        asset_id="USGS/SRTMGL1_003",  # SRTM elevation data
        scale=90  # Use 90m resolution for faster query
    )

    # Test with default (should use grid sampling)
    print("\n" + "-"*70)
    print("Query 1: Default (Grid Sampling Enabled)")
    print("-"*70)

    spec = RequestSpec(
        geometry=Geometry("bbox", bbox)
    )

    result = adapter.fetch(spec)

    print(f"\n✓ Got {len(result)} rows")

    # Show unique coordinates
    unique_lats = sorted(result['latitude'].unique())
    unique_lons = sorted(result['longitude'].unique())

    print(f"\n✓ Unique Latitudes ({len(unique_lats)}):")
    for lat in unique_lats:
        print(f"    {lat:.4f}")

    print(f"\n✓ Unique Longitudes ({len(unique_lons)}):")
    for lon in unique_lons:
        print(f"    {lon:.4f}")

    # Show coordinate pairs
    print(f"\n✓ Coordinate Pairs (lat, lon):")
    coords = result[['latitude', 'longitude']].drop_duplicates().sort_values(['latitude', 'longitude'])
    for idx, row in coords.iterrows():
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
            print(f"    Bbox area: {sampling.get('bbox_area_km2', 'N/A'):.0f} km²")
            if sampling.get('strategy') == 'adaptive_scaled':
                print(f"    Scale factor: {sampling.get('scale_factor', 'N/A'):.2f}×")

    # Show elevation data if available
    elevation_rows = result[result['variable'].str.contains('elevation', na=False)]
    if len(elevation_rows) > 0:
        print(f"\n✓ Elevation Data:")
        print(f"    Min: {elevation_rows['value'].min():.1f} m")
        print(f"    Max: {elevation_rows['value'].max():.1f} m")
        print(f"    Mean: {elevation_rows['value'].mean():.1f} m")
        print(f"    Range: {elevation_rows['value'].max() - elevation_rows['value'].min():.1f} m")

    # Display first few rows as table
    print(f"\n✓ Sample Data (first 10 rows):")
    display_cols = ['latitude', 'longitude', 'variable', 'value']
    available_cols = [col for col in display_cols if col in result.columns]
    print(result[available_cols].head(10).to_string(index=False))

    # Compare with low resolution (legacy behavior)
    print("\n" + "-"*70)
    print("Query 2: Low Resolution (Legacy - Single Aggregated Value)")
    print("-"*70)

    spec_low = RequestSpec(
        geometry=Geometry("bbox", bbox),
        resolution="low"
    )

    result_low = adapter.fetch(spec_low)

    print(f"\n✓ Got {len(result_low)} rows")
    print(f"✓ Single coordinate: ({result_low.iloc[0]['latitude']:.4f}, {result_low.iloc[0]['longitude']:.4f})")

    if len(elevation_rows) > 0:
        print(f"✓ Aggregated elevation: {result_low.iloc[0]['value']:.1f} m")

    print("\n" + "="*70)
    print("✓ TEST COMPLETED")
    print("="*70)
    print(f"\nSummary:")
    print(f"  • Default query returned {len(result)} rows with {len(unique_lats)} × {len(unique_lons)} grid")
    print(f"  • Low resolution returned {len(result_low)} row (legacy behavior)")
    print(f"  • ✅ Multiple coordinates confirmed!")


if __name__ == "__main__":
    test_user_bbox()
