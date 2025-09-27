#!/usr/bin/env python3
"""
Debug WCS timeout issues with the SoilGrids adapter
"""

import time
import requests
import tempfile
import os
import numpy as np
import rasterio
from pyproj import Transformer

# User's working constants
EQUAL_EARTH_PROJ = "+proj=eqearth +datum=WGS84 +units=m +no_defs"
NATIVE_RES_M = 250.0

def test_single_wcs_request():
    """Test a single WCS request to identify timeout issues"""
    print("🔍 Testing Single WCS Request")
    print("=" * 40)

    # Test the user's known working locations from conversation history
    test_locations = [
        # Amazon Basin (user's tests showed this works)
        {"bbox": (-60.0, -3.0, -59.5, -2.5), "prop": "clay", "cid": "clay_0-5cm_mean", "name": "Amazon Basin"},
        # Iowa farmland (user's tests)
        {"bbox": (-93.8, 42.0, -93.6, 42.2), "prop": "soc", "cid": "soc_0-5cm_mean", "name": "Iowa Corn Belt"},
        # Brazilian Cerrado (user's tests)
        {"bbox": (-47.94, -15.79, -47.90, -15.75), "prop": "phh2o", "cid": "phh2o_0-5cm_mean", "name": "Brazilian Cerrado"}
    ]

    for i, loc in enumerate(test_locations):
        print(f"\n[{i+1}/{len(test_locations)}] Testing {loc['name']}...")
        if test_location(loc["bbox"], loc["prop"], loc["cid"]):
            print(f"✅ SUCCESS with {loc['name']}")
            return True
        else:
            print(f"❌ FAILED with {loc['name']}")

    return False

def test_location(bbox_ll, prop, cid):
    """Test a specific location for WCS data retrieval"""
    nx, ny = 10, 10  # Very small grid

    print(f"   Testing: {prop}:{cid}")
    print(f"   Bbox: {bbox_ll}")
    print(f"   Grid: {nx}x{ny}")

    # Transform to Equal Earth
    transformer = Transformer.from_crs("EPSG:4326", EQUAL_EARTH_PROJ, always_xy=True)
    minx, miny = transformer.transform(bbox_ll[0], bbox_ll[1])
    maxx, maxy = transformer.transform(bbox_ll[2], bbox_ll[3])

    width_m = max(1.0, maxx - minx)
    height_m = max(1.0, maxy - miny)
    resx_m = max(NATIVE_RES_M, width_m / max(1, nx))
    resy_m = max(NATIVE_RES_M, height_m / max(1, ny))

    print(f"   Equal Earth bbox: ({minx:.0f}, {miny:.0f}, {maxx:.0f}, {maxy:.0f})")
    print(f"   Resolution: {resx_m:.1f}m x {resy_m:.1f}m")

    url = f"https://maps.isric.org/mapserv?map=/map/{prop}.map"
    params = {
        "service": "WCS",
        "version": "2.0.1",
        "request": "GetCoverage",
        "coverageid": cid,
        "format": "image/tiff",
        "subset": [f"x({minx},{maxx})", f"y({miny},{maxy})"],
        "resx": f"{resx_m}m",
        "resy": f"{resy_m}m"
    }

    print(f"   📡 Making WCS request...")

    start_time = time.time()

    try:
        # Use shorter timeout to identify issues
        r = requests.get(url, params=params, timeout=30)
        elapsed = time.time() - start_time

        print(f"   ⏱️  Request took: {elapsed:.2f}s")
        print(f"   Status: {r.status_code}")
        print(f"   Content-Length: {len(r.content)} bytes")

        if r.status_code != 200:
            print(f"   ❌ HTTP Error: {r.status_code}")
            return False

        ctype = r.headers.get("Content-Type", "").lower()
        if "tiff" not in ctype and "geotiff" not in ctype:
            print(f"   ❌ Invalid content type: {ctype}")
            return False

        # Process TIFF
        print(f"   📊 Processing TIFF...")
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                tmpf.write(r.content)
                tmp = tmpf.name

            with rasterio.open(tmp) as src:
                print(f"Grid shape: {src.shape}")
                print(f"CRS: {src.crs}")
                print(f"Transform: {src.transform}")

                arr = src.read(1).astype(float)
                print(f"Data shape: {arr.shape}")
                print(f"Data type: {arr.dtype}")

                # Apply user's no-data handling
                original_valid = (~np.isnan(arr)).sum()

                if src.nodata is not None:
                    arr[arr == src.nodata] = np.nan
                    print(f"Applied src.nodata={src.nodata}")

                # Handle sentinel values
                for sentinel in (-32768, -9999):
                    before = (~np.isnan(arr)).sum()
                    arr[arr == sentinel] = np.nan
                    after = (~np.isnan(arr)).sum()
                    if before != after:
                        print(f"Applied sentinel {sentinel}: {before-after} pixels")

                # Handle zeros
                before_zeros = (~np.isnan(arr)).sum()
                arr[arr == 0] = np.nan
                after_zeros = (~np.isnan(arr)).sum()
                if before_zeros != after_zeros:
                    print(f"Applied zero masking: {before_zeros-after_zeros} pixels")

                # Get scaling
                tags_band = src.tags(1)
                scale = float(tags_band.get("scale_factor", tags_band.get("SCALE_FACTOR", "1.0")))
                offset = float(tags_band.get("add_offset", tags_band.get("OFFSET", "0.0")))
                print(f"Scaling: {scale} * value + {offset}")

                # Apply fallback scale if needed
                if scale == 1.0 and prop in ["clay"]:  # Just clay for this test
                    scale = 1.0  # Clay doesn't need scale fallback

                data = arr * scale + offset
                valid_mask = ~np.isnan(data)
                valid_count = valid_mask.sum()

                print(f"Final valid pixels: {valid_count}/{data.size}")

                if valid_count == 0:
                    print("❌ No valid data after processing")
                    return False

                # Check for uniform data
                if np.nanmin(data) == np.nanmax(data):
                    print(f"⚠️  Uniform data (all {np.nanmin(data)})")
                    return False

                # Success!
                values = data[valid_mask]
                print(f"✅ SUCCESS!")
                print(f"Data range: {values.min():.3f} to {values.max():.3f}")
                print(f"Mean: {values.mean():.3f}")
                print(f"Non-zero values: {(values != 0).sum()}")

                return True

        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ TIMEOUT after {elapsed:.2f}s")
        return False

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ ERROR after {elapsed:.2f}s: {e}")
        return False

if __name__ == "__main__":
    success = test_single_wcs_request()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: Single WCS request test")