#!/usr/bin/env python3
"""
Compare WCS vs REST API approaches for same locations
This will help identify why we're getting zeros in WCS but should get real data from REST
"""

import requests
import tempfile
import os
import json
import numpy as np

try:
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False

def test_rest_api(location):
    """Test REST API for a location"""
    print(f"  🌐 REST API test...")

    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    # Use center of bbox for point query
    minx, miny, maxx, maxy = location["bbox"]
    center_lon = (minx + maxx) / 2
    center_lat = (miny + maxy) / 2

    params = {
        "lon": center_lon,
        "lat": center_lat,
        "property": location["prop"],
        "depth": "0-5cm",
        "value": "Q0.5"
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        properties = data.get("properties", {})
        prop_data = properties.get(location["prop"], {})
        values = prop_data.get("values", {})
        depth_data = values.get("0-5cm", {})
        value = depth_data.get("Q0.5")

        if value is not None:
            print(f"     ✅ REST value: {value}")
            return value
        else:
            print(f"     ❌ REST returned None")
            return None

    except Exception as e:
        print(f"     ❌ REST error: {e}")
        return None

def test_wcs_api(location, coverage):
    """Test WCS API for a location"""
    print(f"  🗺️  WCS API test with coverage: {coverage}...")

    url = "https://maps.isric.org/mapserv"
    minx, miny, maxx, maxy = location["bbox"]

    params = {
        "map": f"/map/{location['prop']}.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "coverageid": coverage,
        "format": "image/tiff",
        "subset": [f"Long({minx},{maxx})", f"Lat({miny},{maxy})"],
        "scaleSize": "Long(10),Lat(10)"  # Very small grid
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        if "tiff" in response.headers.get('Content-Type', ''):
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                    tmpf.write(response.content)
                    tmp_file = tmpf.name

                xarr = rioxarray.open_rasterio(tmp_file, masked=True)
                vals = xarr.values[0] if xarr.values.ndim == 3 else xarr.values

                valid_mask = ~np.isnan(vals)
                valid_vals = vals[valid_mask]

                if len(valid_vals) > 0:
                    mean_val = valid_vals.mean()
                    min_val, max_val = valid_vals.min(), valid_vals.max()
                    print(f"     WCS grid: {vals.shape}, mean: {mean_val:.3f}, range: {min_val:.3f}-{max_val:.3f}")
                    return mean_val
                else:
                    print(f"     ❌ WCS: No valid pixels")
                    return None

            finally:
                if tmp_file and os.path.exists(tmp_file):
                    os.remove(tmp_file)
        else:
            print(f"     ❌ WCS: Invalid response")
            return None

    except Exception as e:
        print(f"     ❌ WCS error: {e}")
        return None

def compare_approaches():
    """Compare WCS vs REST API approaches"""
    print("🧪 WCS vs REST API Comparison")
    print("=" * 40)

    if not RIOXARRAY_AVAILABLE:
        print("❌ rioxarray not available")
        return

    # Load catalog
    with open("test_soilgrids_coverages.json", "r") as f:
        catalog = json.load(f)

    # Test locations - use very specific agricultural areas
    test_locations = [
        {
            "name": "Netherlands Polder",
            "bbox": (4.35, 52.05, 4.37, 52.07),  # Specific polder area
            "prop": "clay",
        },
        {
            "name": "Kansas Wheat Belt",
            "bbox": (-98.5, 38.5, -98.48, 38.52),  # Kansas agricultural area
            "prop": "soc",
        },
        {
            "name": "UK Farmland",
            "bbox": (-1.25, 52.48, -1.23, 52.50),  # Leicestershire farmland
            "prop": "clay",
        }
    ]

    results = []

    for i, location in enumerate(test_locations, 1):
        print(f"\n[{i}/{len(test_locations)}] Testing {location['name']}...")

        # Test REST API
        rest_value = test_rest_api(location)

        # Test WCS with different coverages
        prop_coverages = catalog.get(location["prop"], [])

        # Try mean coverage first (most likely to have data)
        mean_coverages = [c for c in prop_coverages if "mean" in c and "0-5cm" in c]
        wcs_values = []

        if mean_coverages:
            coverage = mean_coverages[0]
            wcs_val = test_wcs_api(location, coverage)
            if wcs_val is not None:
                wcs_values.append(("mean", wcs_val))

        # Try Q0.5 coverage
        q05_coverages = [c for c in prop_coverages if "Q0.5" in c and "0-5cm" in c]
        if q05_coverages:
            coverage = q05_coverages[0]
            wcs_val = test_wcs_api(location, coverage)
            if wcs_val is not None:
                wcs_values.append(("Q0.5", wcs_val))

        result = {
            "location": location["name"],
            "rest_value": rest_value,
            "wcs_values": wcs_values,
            "rest_works": rest_value is not None and rest_value != 0,
            "wcs_works": any(val != 0 for _, val in wcs_values)
        }
        results.append(result)

        # Summary for this location
        if result["rest_works"] and result["wcs_works"]:
            print(f"  ✅ Both REST and WCS working!")
        elif result["rest_works"]:
            print(f"  ⚠️  REST works, WCS returns zeros")
        elif result["wcs_works"]:
            print(f"  ⚠️  WCS works, REST failed")
        else:
            print(f"  ❌ Both approaches failed")

    # Overall comparison
    print(f"\n{'='*40}")
    print(f"📊 COMPARISON RESULTS")
    print(f"{'='*40}")

    rest_working = sum(1 for r in results if r["rest_works"])
    wcs_working = sum(1 for r in results if r["wcs_works"])

    print(f"REST API success: {rest_working}/{len(results)} locations")
    print(f"WCS API success: {wcs_working}/{len(results)} locations")

    if rest_working > wcs_working:
        print(f"🎯 KEY FINDING: REST API approach is more reliable")
        print(f"   Recommendation: Use your proven REST API method")
    elif wcs_working > rest_working:
        print(f"🎯 KEY FINDING: WCS approach working better")
    else:
        print(f"🎯 KEY FINDING: Both approaches need investigation")

    return results

if __name__ == "__main__":
    results = compare_approaches()
    print(f"\n🏁 Comparison complete!")