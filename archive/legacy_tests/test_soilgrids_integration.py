#!/usr/bin/env python3
"""
Quick integration test for the new WCS-based SoilGrids adapter
Tests basic functionality and validates the integration works correctly.
"""

import sys
import os
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent
sys.path.insert(0, str(env_agents_path))

import pandas as pd
from datetime import datetime
from env_agents.adapters.soil import SoilGridsAdapter
from env_agents.core.models import RequestSpec, Geometry

def test_soilgrids_wcs_integration():
    """Test basic SoilGrids WCS adapter functionality"""

    print("=== SoilGrids WCS Integration Test ===")
    print(f"Test started at: {datetime.now()}")

    # Initialize adapter
    print("\n1. Initializing SoilGrids adapter...")
    try:
        adapter = SoilGridsAdapter()
        print(f"✅ Adapter initialized: {adapter.__class__.__name__}")
        print(f"   Dataset: {adapter.DATASET}")
        print(f"   Source URL: {adapter.SOURCE_URL}")
        print(f"   Service Type: {adapter.SERVICE_TYPE}")
    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return False

    # Test capabilities
    print("\n2. Testing capabilities discovery...")
    try:
        # Note: This may take a while on first run as it builds the catalog
        caps = adapter.capabilities()
        print(f"✅ Capabilities retrieved successfully")
        print(f"   Service type: {caps.get('service_type', 'unknown')}")
        print(f"   Variables available: {len(caps.get('variables', []))}")

        # Show sample variables
        variables = caps.get('variables', [])
        if variables:
            print("   Sample variables:")
            for var in variables[:3]:
                print(f"     - {var.get('canonical', 'unknown')}: {var.get('name', 'unknown')}")

        # Debug: Check what coverage IDs were actually discovered
        if hasattr(adapter, 'catalog_cache') and adapter.catalog_cache:
            print("\n   Coverage discovery debug:")
            for prop, coverages in adapter.catalog_cache.items():
                if coverages:
                    print(f"     {prop}: {len(coverages)} coverages")
                    if coverages:
                        print(f"       Sample IDs: {coverages[:3]}")

    except Exception as e:
        print(f"❌ Capabilities test failed: {e}")
        return False

    # Test small data fetch
    print("\n3. Testing small data fetch...")
    try:
        # Small bbox around a known location (Netherlands)
        geometry = Geometry(type="bbox", coordinates=[5.78, 51.98, 5.8, 52.0])

        # First try a single coverage manually to debug
        print("   Debug: Testing single coverage fetch...")
        if hasattr(adapter, 'catalog_cache') and adapter.catalog_cache:
            # Get the first available coverage
            for prop, coverages in adapter.catalog_cache.items():
                if coverages and prop == 'clay':  # Start with clay
                    first_coverage = coverages[0]
                    print(f"   Testing single coverage: {prop}:{first_coverage}")

                    try:
                        test_df = adapter._fetch_coverage_to_df(prop, first_coverage, geometry.coordinates)
                        if test_df is not None and not test_df.empty:
                            print(f"   ✅ Single coverage test successful: {len(test_df)} points")
                            break
                        else:
                            print(f"   ⚠️  Single coverage returned no data")
                    except Exception as e:
                        print(f"   ❌ Single coverage test failed: {e}")

        # Now try the full fetch
        print("   Testing full fetch...")
        spec = RequestSpec(
            geometry=geometry,
            variables=["soil:clay"],  # Start with just clay
            extra={"max_pixels": 10000}  # Keep it small for testing
        )

        print(f"   Requesting data for bbox: {geometry.coordinates}")
        print(f"   Variables: {spec.variables}")

        # This tests the actual WCS functionality
        rows = adapter._fetch_rows(spec)

        if rows:
            print(f"✅ Data fetch successful: {len(rows)} observations")

            # Validate core schema compliance
            sample_row = rows[0]
            required_columns = [
                'observation_id', 'dataset', 'latitude', 'longitude',
                'variable', 'value', 'unit', 'retrieval_timestamp'
            ]

            missing_columns = [col for col in required_columns if col not in sample_row]
            if missing_columns:
                print(f"⚠️  Missing required columns: {missing_columns}")
            else:
                print("✅ Core schema compliance validated")

            # Show sample data
            print("   Sample observation:")
            for key in ['variable', 'value', 'unit', 'latitude', 'longitude']:
                if key in sample_row:
                    print(f"     {key}: {sample_row[key]}")
        else:
            print("⚠️  No data returned (may be expected for test location)")

    except Exception as e:
        print(f"❌ Data fetch test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

    # Test guard rails
    print("\n4. Testing guard rails...")
    try:
        # Test large request that should trigger guard rails
        large_geometry = Geometry(type="bbox", coordinates=[5.0, 51.0, 6.0, 52.0])
        large_spec = RequestSpec(geometry=large_geometry)

        limits = adapter._get_guard_rail_limits(large_spec)
        print(f"✅ Guard rails calculated successfully")
        print(f"   Strategy: {limits['strategy']}")
        print(f"   Estimated pixels: {limits['estimated_pixels']:,}")

        if limits['strategy'] == 'tiled':
            print(f"   Tile count: {limits['tile_count']}")
        elif limits['strategy'] == 'resampled':
            print(f"   Target pixels: {limits['target_pixels']:,}")

    except Exception as e:
        print(f"❌ Guard rails test failed: {e}")
        return False

    print(f"\n=== Integration Test Complete ===")
    print(f"Test completed at: {datetime.now()}")
    return True

if __name__ == "__main__":
    success = test_soilgrids_wcs_integration()
    if success:
        print("\n🎉 SoilGrids WCS integration test PASSED!")
        sys.exit(0)
    else:
        print("\n💥 SoilGrids WCS integration test FAILED!")
        sys.exit(1)