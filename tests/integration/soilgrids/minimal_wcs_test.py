#!/usr/bin/env python3
"""
Minimal WCS test - just test the core functionality
"""

import requests
import tempfile
import os

try:
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False

def test_minimal_wcs():
    """Test minimal WCS functionality"""
    print("🧪 Minimal WCS Test")
    print("=" * 30)

    if not RIOXARRAY_AVAILABLE:
        print("❌ rioxarray not available - cannot test TIFF processing")
        return False

    # Test parameters from successful debug session
    base_url = "https://maps.isric.org/mapserv"
    params = {
        "map": "/map/clay.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "coverageid": "clay_0-5cm_Q0.5",
        "format": "image/tiff",
        "subset": ["Long(5.78,5.8)", "Lat(51.98,52.0)"],
        "scaleSize": "Long(50),Lat(50)"  # Small size
    }

    print("1. Testing WCS request...")
    try:
        response = requests.get(base_url, params=params, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200 and "tiff" in response.headers.get('Content-Type', ''):
            print(f"   ✅ WCS request successful: {len(response.content)} bytes")

            # Test TIFF processing
            print("2. Testing TIFF processing...")
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                    tmpf.write(response.content)
                    tmp_file = tmpf.name

                # Read with rioxarray
                xarr = rioxarray.open_rasterio(tmp_file, masked=True)
                print(f"   ✅ TIFF processed: shape {xarr.shape}")

                # Extract some values
                vals = xarr.values[0] if xarr.values.ndim == 3 else xarr.values
                print(f"   Data range: {vals.min():.2f} to {vals.max():.2f}")

                return True

            finally:
                if tmp_file and os.path.exists(tmp_file):
                    os.remove(tmp_file)

        else:
            print(f"   ❌ WCS request failed")
            if response.status_code != 200:
                print(f"   Error: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ Request error: {e}")
        return False

if __name__ == "__main__":
    success = test_minimal_wcs()
    print(f"\n{'🎉 SUCCESS' if success else '💥 FAILED'}: Minimal WCS test")
    exit(0 if success else 1)