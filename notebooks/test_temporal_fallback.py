#!/usr/bin/env python3
"""
Test temporal fallback logic for Earth Engine adapter
"""

import sys
sys.path.insert(0, '/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents')

from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_modis_landcover_fallback():
    """Test MODIS_LANDCOVER with 2021 request (should fall back to 2019)"""

    print("="*80)
    print("TEST 1: MODIS_LANDCOVER with 2021 request (should fall back to 2019)")
    print("="*80)

    adapter = ProductionEarthEngineAdapter(
        asset_id="MODIS/006/MCD12Q1",
        scale=500
    )

    # Request 2021 data (doesn't exist - should fall back to 2019)
    spec = RequestSpec(
        geometry=Geometry(
            type="point",
            coordinates=[-122.4, 37.8]  # San Francisco
        ),
        time_range=("2021-01-01", "2021-12-31")  # Doesn't exist!
    )

    print(f"\nRequesting: {spec.time_range}")
    print(f"Location: San Francisco ({spec.geometry.coordinates})")

    try:
        rows = adapter._fetch_rows(spec)

        if rows:
            print(f"\n✓ Success! Retrieved {len(rows)} observations")

            # Check metadata
            first_row = rows[0]
            attrs = first_row.get('attributes', {})

            print(f"\nMetadata from first observation:")
            print(f"  Requested range: {attrs.get('requested_date_range')}")
            print(f"  Actual range: {attrs.get('actual_date_range')}")
            print(f"  Fallback applied: {attrs.get('temporal_fallback_applied')}")
            if attrs.get('temporal_fallback_applied'):
                print(f"  Fallback reason: {attrs.get('temporal_fallback_reason')}")

            # Show first observation
            print(f"\nFirst observation:")
            print(f"  Time: {first_row['time']}")
            print(f"  Variable: {first_row['variable']}")
            print(f"  Value: {first_row['value']}")

            # Check that we got 2019 data
            year = first_row['time'][:4]
            if year == "2019":
                print(f"\n✓ Correctly fell back to 2019 data")
            else:
                print(f"\n⚠️  WARNING: Expected 2019 data, got {year}")

        else:
            print(f"\n✗ No data returned")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_google_embeddings_with_sparse_coverage():
    """Test GOOGLE_EMBEDDINGS with location that might not have 2021 data"""

    print("\n" + "="*80)
    print("TEST 2: GOOGLE_EMBEDDINGS with 2021 request")
    print("="*80)

    adapter = ProductionEarthEngineAdapter(
        asset_id="GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
        scale=10
    )

    # Test with cluster 23 (one that failed before)
    # From clusters_optimized.csv this is likely an international location
    spec = RequestSpec(
        geometry=Geometry(
            type="point",
            coordinates=[113.8762, 22.4932]  # Hong Kong area
        ),
        time_range=("2021-01-01", "2021-12-31")
    )

    print(f"\nRequesting: {spec.time_range}")
    print(f"Location: Hong Kong area ({spec.geometry.coordinates})")

    try:
        rows = adapter._fetch_rows(spec)

        if rows:
            print(f"\n✓ Success! Retrieved {len(rows)} observations")

            # Check metadata
            first_row = rows[0]
            attrs = first_row.get('attributes', {})

            print(f"\nMetadata from first observation:")
            print(f"  Requested range: {attrs.get('requested_date_range')}")
            print(f"  Actual range: {attrs.get('actual_date_range')}")
            print(f"  Fallback applied: {attrs.get('temporal_fallback_applied')}")
            if attrs.get('temporal_fallback_applied'):
                print(f"  Fallback reason: {attrs.get('temporal_fallback_reason')}")

            print(f"\nFirst few observations:")
            for i, row in enumerate(rows[:5]):
                print(f"  {i+1}. Time: {row['time']}, Variable: {row['variable']}, Value: {row['value']:.4f}")

        else:
            print(f"\n✗ No data returned (this location may have no coverage at all)")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_future_date_fallback():
    """Test requesting future date (should fall back to most recent)"""

    print("\n" + "="*80)
    print("TEST 3: Request future date (2025) for MODIS_NDVI")
    print("="*80)

    adapter = ProductionEarthEngineAdapter(
        asset_id="MODIS/061/MOD13Q1",
        scale=250
    )

    # Request future data
    spec = RequestSpec(
        geometry=Geometry(
            type="point",
            coordinates=[-122.4, 37.8]
        ),
        time_range=("2025-01-01", "2025-12-31")  # Future!
    )

    print(f"\nRequesting: {spec.time_range} (future date)")
    print(f"Location: San Francisco")

    try:
        rows = adapter._fetch_rows(spec)

        if rows:
            print(f"\n✓ Success! Retrieved {len(rows)} observations")

            # Check metadata
            first_row = rows[0]
            attrs = first_row.get('attributes', {})

            print(f"\nMetadata:")
            print(f"  Requested range: {attrs.get('requested_date_range')}")
            print(f"  Actual range: {attrs.get('actual_date_range')}")
            print(f"  Fallback applied: {attrs.get('temporal_fallback_applied')}")
            if attrs.get('temporal_fallback_applied'):
                print(f"  Fallback reason: {attrs.get('temporal_fallback_reason')}")

            # Check year
            year = first_row['time'][:4]
            print(f"\n✓ Fell back to year: {year}")

        else:
            print(f"\n✗ No data returned")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_modis_landcover_fallback()
    test_google_embeddings_with_sparse_coverage()
    test_future_date_fallback()

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)