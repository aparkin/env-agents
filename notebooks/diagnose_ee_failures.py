#!/usr/bin/env python3
"""
Diagnose Earth Engine asset failures
"""

import ee

# Initialize Earth Engine
try:
    ee.Initialize()
    print("✓ Earth Engine initialized")
except:
    import json
    from pathlib import Path

    # Find service account key
    key_path = Path(__file__).parent.parent / "config" / "ecognita-470619-e9e223ea70a7.json"
    if key_path.exists():
        credentials = ee.ServiceAccountCredentials(
            email='ecognita-service@ecognita-470619.iam.gserviceaccount.com',
            key_file=str(key_path)
        )
        ee.Initialize(credentials)
        print("✓ Earth Engine initialized with service account")
    else:
        raise Exception("Could not find Earth Engine credentials")


def check_asset(asset_id, test_date="2021-01-01"):
    """Check if an asset is available and what dates it covers"""

    print(f"\n{'='*80}")
    print(f"Checking: {asset_id}")
    print(f"{'='*80}")

    try:
        # Try to load as Image
        try:
            img = ee.Image(asset_id)
            print("✓ Asset type: Image")

            # Try to get bands
            bands = img.bandNames().getInfo()
            print(f"✓ Bands: {bands}")

            # Try a simple query
            point = ee.Geometry.Point([-122.4, 37.8])
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            print(f"✓ Sample query successful: {list(stats.keys())[:3]}...")
            return "Image", None, None

        except Exception as e:
            if "not an Image" not in str(e):
                raise

        # Try to load as ImageCollection
        ic = ee.ImageCollection(asset_id)
        print("✓ Asset type: ImageCollection")

        # Get date range
        try:
            dates = ic.aggregate_array('system:time_start').getInfo()
            if dates:
                import datetime
                min_date = datetime.datetime.fromtimestamp(min(dates) / 1000).strftime('%Y-%m-%d')
                max_date = datetime.datetime.fromtimestamp(max(dates) / 1000).strftime('%Y-%m-%d')
                print(f"✓ Date range: {min_date} to {max_date}")
            else:
                print("✗ No dates found")
                min_date, max_date = None, None
        except Exception as e:
            print(f"✗ Could not get date range: {e}")
            min_date, max_date = None, None

        # Try to get first image
        try:
            first = ic.first()
            bands = first.bandNames().getInfo()
            print(f"✓ Bands: {bands}")
        except Exception as e:
            print(f"✗ Could not get bands: {e}")

        # Try with test date
        print(f"\nTesting with date: {test_date}")
        filtered = ic.filterDate(test_date, "2021-12-31")
        count = filtered.size().getInfo()
        print(f"  Images in 2021: {count}")

        if count > 0:
            first = filtered.first()
            bands = first.bandNames().getInfo()
            print(f"  ✓ Can get first image, bands: {bands}")
        else:
            print(f"  ✗ No images found for {test_date}")

            # Try finding actual available dates
            print("\n  Trying to find available dates...")
            for year in [2020, 2019, 2018, 2017, 2016]:
                test_ic = ic.filterDate(f"{year}-01-01", f"{year}-12-31")
                test_count = test_ic.size().getInfo()
                if test_count > 0:
                    print(f"  ✓ Found {test_count} images in {year}")
                    first = test_ic.first()
                    bands = first.bandNames().getInfo()
                    print(f"    Bands: {bands}")
                    break
            else:
                print("  ✗ Could not find any images in recent years")

        return "ImageCollection", min_date, max_date

    except Exception as e:
        print(f"✗ Error: {e}")
        return None, None, None


def check_specific_cluster_locations():
    """Check if specific failing clusters have issues"""

    print(f"\n{'='*80}")
    print("Testing with actual failing cluster locations")
    print(f"{'='*80}")

    # Clusters that failed for MODIS_LANDCOVER: 14, 15, 16
    # Clusters that failed for GOOGLE_EMBEDDINGS: 23, 24, 46, 61, 70

    # From clusters_optimized.csv:
    # Cluster 14: Hawaii (21.289373, -157.91748)
    # Cluster 23: likely international

    test_locations = [
        ("Cluster 14 (Hawaii)", -157.91748, 21.289373),
        ("Cluster 0 (Australia)", 148.25, -35.32),
        ("US mainland", -122.4, 37.8),
    ]

    assets_to_test = [
        "MODIS/006/MCD12Q1",
        "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    ]

    for asset_id in assets_to_test:
        print(f"\n{asset_id}")
        print("-" * 80)

        for name, lon, lat in test_locations:
            print(f"\n  Testing {name}: ({lat:.2f}, {lon:.2f})")

            try:
                ic = ee.ImageCollection(asset_id)
                point = ee.Geometry.Point([lon, lat])

                # Try 2021
                filtered = ic.filterDate("2021-01-01", "2021-12-31").filterBounds(point)
                count = filtered.size().getInfo()

                if count > 0:
                    print(f"    ✓ Found {count} images in 2021")
                    first = filtered.first()
                    bands = first.bandNames().getInfo()
                    print(f"    Bands: {bands}")
                else:
                    print(f"    ✗ No images in 2021")

                    # Try other years
                    for year in [2020, 2019, 2018, 2017]:
                        test_filtered = ic.filterDate(f"{year}-01-01", f"{year}-12-31").filterBounds(point)
                        test_count = test_filtered.size().getInfo()
                        if test_count > 0:
                            print(f"    ✓ Found {test_count} images in {year}")
                            break

            except Exception as e:
                print(f"    ✗ Error: {e}")


if __name__ == "__main__":
    # Check the two failing assets
    assets = [
        "MODIS/006/MCD12Q1",  # MODIS_LANDCOVER
        "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",  # GOOGLE_EMBEDDINGS
    ]

    results = {}
    for asset_id in assets:
        asset_type, min_date, max_date = check_asset(asset_id)
        results[asset_id] = (asset_type, min_date, max_date)

    # Test with actual locations
    check_specific_cluster_locations()

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    for asset_id, (asset_type, min_date, max_date) in results.items():
        print(f"\n{asset_id}")
        print(f"  Type: {asset_type}")
        if min_date and max_date:
            print(f"  Available: {min_date} to {max_date}")
        print(f"  Configured time_range: 2021-01-01 to 2021-12-31")
        if min_date and max_date:
            if "2021" < min_date[:4] or "2021" > max_date[:4]:
                print(f"  ⚠️  WARNING: 2021 is outside available range!")