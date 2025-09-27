#!/usr/bin/env python3
"""
Direct WCS functionality test - bypasses full adapter initialization
Tests core WCS requests to verify the fundamental approach works
"""

import sys
import os
import requests
import tempfile
from pathlib import Path

# Add the package to Python path
env_agents_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(env_agents_path))

try:
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False

def test_direct_wcs_requests():
    """Test direct WCS requests to verify core functionality"""
    print("🧪 Direct WCS Functionality Test")
    print("=" * 40)

    if not RIOXARRAY_AVAILABLE:
        print("❌ rioxarray not available - cannot test TIFF processing")
        return False

    # Test scenarios with known working parameters
    test_cases = [
        {
            "name": "Clay 0-5cm Netherlands",
            "params": {
                "map": "/map/clay.map",
                "SERVICE": "WCS",
                "VERSION": "2.0.1",
                "REQUEST": "GetCoverage",
                "coverageid": "clay_0-5cm_Q0.5",
                "format": "image/tiff",
                "subset": ["Long(5.78,5.8)", "Lat(51.98,52.0)"],
                "scaleSize": "Long(50),Lat(50)"
            }
        },
        {
            "name": "Organic Carbon California",
            "params": {
                "map": "/map/soc.map",
                "SERVICE": "WCS",
                "VERSION": "2.0.1",
                "REQUEST": "GetCoverage",
                "coverageid": "soc_0-5cm_Q0.5",
                "format": "image/tiff",
                "subset": ["Long(-122.0,-121.98)", "Lat(37.0,37.02)"],
                "scaleSize": "Long(50),Lat(50)"
            }
        },
        {
            "name": "pH Brazil Amazon",
            "params": {
                "map": "/map/phh2o.map",
                "SERVICE": "WCS",
                "VERSION": "2.0.1",
                "REQUEST": "GetCoverage",
                "coverageid": "phh2o_0-5cm_Q0.5",
                "format": "image/tiff",
                "subset": ["Long(-60.0,-59.98)", "Lat(-3.2,-3.18)"],
                "scaleSize": "Long(50),Lat(50)"
            }
        }
    ]

    base_url = "https://maps.isric.org/mapserv"
    successful_tests = 0
    total_tests = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing {test_case['name']}...")

        try:
            # Make WCS request
            response = requests.get(base_url, params=test_case['params'], timeout=30)

            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"   Content-Length: {len(response.content)} bytes")

            if response.status_code == 200 and "tiff" in response.headers.get('Content-Type', ''):
                # Test TIFF processing
                tmp_file = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                        tmpf.write(response.content)
                        tmp_file = tmpf.name

                    # Read with rioxarray
                    xarr = rioxarray.open_rasterio(tmp_file, masked=True)
                    print(f"   ✅ SUCCESS: TIFF shape {xarr.shape}, valid data points: {(~xarr.isnull()).sum().item()}")

                    # Check for actual data
                    vals = xarr.values[0] if xarr.values.ndim == 3 else xarr.values
                    non_null_vals = vals[~np.isnan(vals)] if hasattr(vals, 'dtype') else vals

                    if len(non_null_vals) > 0:
                        print(f"   Data range: {non_null_vals.min():.2f} to {non_null_vals.max():.2f}")
                        successful_tests += 1
                    else:
                        print(f"   ⚠️  WARNING: No valid data values found")

                except Exception as e:
                    print(f"   ❌ TIFF processing failed: {e}")

                finally:
                    if tmp_file and os.path.exists(tmp_file):
                        os.remove(tmp_file)

            else:
                print(f"   ❌ WCS request failed")
                if response.status_code != 200:
                    print(f"   Error response: {response.text[:200]}")

        except requests.Timeout:
            print(f"   ❌ Request timed out after 30 seconds")
        except Exception as e:
            print(f"   ❌ Request error: {e}")

    # Calculate success rate
    success_rate = successful_tests / total_tests
    print(f"\n{'='*40}")
    print(f"📊 DIRECT WCS SUCCESS RATE")
    print(f"{'='*40}")
    print(f"Successful requests: {successful_tests}/{total_tests}")
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
    print(f"\nCore WCS functionality: {'✅ WORKING' if success_rate > 0 else '❌ BROKEN'}")

    return success_rate > 0

if __name__ == "__main__":
    # Import numpy here to avoid issues if not available
    try:
        import numpy as np
    except ImportError:
        print("❌ numpy not available")
        sys.exit(1)

    success = test_direct_wcs_requests()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: Direct WCS functionality test")
    sys.exit(0 if success else 1)