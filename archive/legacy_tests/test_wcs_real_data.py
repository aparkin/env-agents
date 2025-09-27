#!/usr/bin/env python3
"""
Test WCS requests for real data using discovered coverages
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

def test_wcs_real_data():
    """Test WCS with discovered coverages to get real data"""
    print("🧪 WCS Real Data Test")
    print("=" * 30)

    if not RIOXARRAY_AVAILABLE:
        print("❌ rioxarray not available")
        return False

    # Load the catalog we just built
    with open("test_soilgrids_coverages.json", "r") as f:
        catalog = json.load(f)

    base_url = "https://maps.isric.org/mapserv"

    # Test locations with known good soil (terrestrial, agricultural areas)
    test_cases = [
        {
            "name": "Netherlands Farmland",
            "bbox": (5.79, 51.99, 5.81, 52.01),
            "prop": "clay",
            "coverage": catalog["clay"][0],  # clay_0-5cm_Q0.05
        },
        {
            "name": "Iowa Corn Belt",
            "bbox": (-93.67, 42.01, -93.63, 42.05),
            "prop": "soc",
            "coverage": catalog["soc"][1],  # soc_0-5cm_Q0.5
        },
        {
            "name": "Brazilian Cerrado",
            "bbox": (-47.94, -15.79, -47.90, -15.75),
            "prop": "phh2o",
            "coverage": catalog["phh2o"][1],  # phh2o_0-5cm_Q0.5
        }
    ]

    successful_tests = 0
    total_tests = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing {test_case['name']} - {test_case['coverage']}...")

        try:
            minx, miny, maxx, maxy = test_case["bbox"]

            params = {
                "map": f"/map/{test_case['prop']}.map",
                "SERVICE": "WCS",
                "VERSION": "2.0.1",
                "REQUEST": "GetCoverage",
                "coverageid": test_case['coverage'],
                "format": "image/tiff",
                "subset": [f"Long({minx},{maxx})", f"Lat({miny},{maxy})"],
                "scaleSize": "Long(20),Lat(20)"  # Small but not tiny
            }

            response = requests.get(base_url, params=params, timeout=30)

            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            print(f"   Size: {len(response.content)} bytes")

            if response.status_code == 200 and "tiff" in response.headers.get('Content-Type', ''):
                # Process TIFF
                tmp_file = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                        tmpf.write(response.content)
                        tmp_file = tmpf.name

                    # Read with rioxarray
                    xarr = rioxarray.open_rasterio(tmp_file, masked=True)
                    vals = xarr.values[0] if xarr.values.ndim == 3 else xarr.values

                    # Check for real data
                    valid_mask = ~np.isnan(vals)
                    valid_vals = vals[valid_mask]

                    print(f"   Grid shape: {vals.shape}")
                    print(f"   Valid pixels: {valid_mask.sum()}/{vals.size}")

                    if len(valid_vals) > 0:
                        min_val, max_val = valid_vals.min(), valid_vals.max()
                        mean_val = valid_vals.mean()

                        print(f"   Data range: {min_val:.3f} to {max_val:.3f}")
                        print(f"   Mean: {mean_val:.3f}")

                        # Check if we got real varied data (not all same value)
                        if min_val != max_val and max_val > 0:
                            print(f"   ✅ SUCCESS: Real varied soil data!")
                            successful_tests += 1
                        elif max_val > 0:
                            print(f"   ⚠️  Uniform data (all {max_val:.3f})")
                        else:
                            print(f"   ⚠️  All zero values")
                    else:
                        print(f"   ❌ No valid data pixels")

                except Exception as e:
                    print(f"   ❌ TIFF processing error: {e}")

                finally:
                    if tmp_file and os.path.exists(tmp_file):
                        os.remove(tmp_file)

            else:
                print(f"   ❌ WCS request failed")
                if response.status_code != 200:
                    print(f"   Error: {response.text[:100]}")

        except Exception as e:
            print(f"   ❌ Request error: {e}")

    # Results
    success_rate = successful_tests / total_tests
    print(f"\n{'='*30}")
    print(f"📊 REAL DATA SUCCESS RATE")
    print(f"{'='*30}")
    print(f"Real data retrievals: {successful_tests}/{total_tests}")
    print(f"Success rate: {success_rate:.1%}")

    if success_rate >= 0.75:
        status = "🎉 EXCELLENT"
    elif success_rate >= 0.50:
        status = "👍 GOOD"
    elif success_rate >= 0.25:
        status = "⚠️ POOR"
    else:
        status = "💥 CRITICAL"

    print(f"Assessment: {status}")

    return success_rate > 0

if __name__ == "__main__":
    success = test_wcs_real_data()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: WCS real data test")