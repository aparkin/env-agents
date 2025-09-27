#!/usr/bin/env python3
"""
Test user's core SoilGrids function directly to verify it works
"""

import os
import json
import math
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple, Iterable

import numpy as np
import pandas as pd
import requests
import rasterio
from pyproj import Transformer

# User's exact constants and functions
EQUAL_EARTH_PROJ = "+proj=eqearth +datum=WGS84 +units=m +no_defs"
NATIVE_RES_M = 250.0
WCS_MAX_SIZE = 8192

KNOWN_SCALE_FALLBACK = {
    "bdod": 0.01,
    "soc": 0.1,
    "ocd": 0.1,
    "ocs": 0.1,
    "nitrogen": 0.1
}

def _parse_depth(depth: Optional[str]):
    """Parse '0-5cm' → (0, 5, 'cm')."""
    if not depth:
        return None, None, None
    import re
    m = re.match(r"(\d+)-(\d+)(cm|m)", depth)
    if m:
        top, bottom, unit = m.groups()
        return int(top), int(bottom), unit
    return None, None, None

def _to_equal_earth_bbox(bbox_ll: Tuple[float,float,float,float]) -> Tuple[float,float,float,float]:
    """Transform lon/lat bbox (EPSG:4326) to Equal Earth meters (WCS native for numeric)."""
    transformer = Transformer.from_crs("EPSG:4326", EQUAL_EARTH_PROJ, always_xy=True)
    minx,miny = transformer.transform(bbox_ll[0], bbox_ll[1])
    maxx,maxy = transformer.transform(bbox_ll[2], bbox_ll[3])
    return minx,miny,maxx,maxy

def _fetch_coverage_to_df_uniform_grid(
    prop: str,
    cid: str,
    bbox_ll: Tuple[float,float,float,float],
    nx: int,
    ny: int
) -> Optional[pd.DataFrame]:
    """User's exact function"""
    # Common checks
    minlon,minlat,maxlon,maxlat = bbox_ll
    if not (minlon < maxlon and minlat < maxlat):
        return None

    # ----- Numeric properties: Equal Earth meters with x/y axes -----
    minx, miny, maxx, maxy = _to_equal_earth_bbox(bbox_ll)
    width_m  = max(1.0, maxx - minx)
    height_m = max(1.0, maxy - miny)

    resx_m = max(NATIVE_RES_M, width_m  / max(1, nx))
    resy_m = max(NATIVE_RES_M, height_m / max(1, ny))

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

    r = requests.get(url, params=params, timeout=180)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type","").lower()
    if "tiff" not in ctype and "geotiff" not in ctype:
        print(f"WCS error {prop}:{cid} → {r.text[:250].replace(chr(10),' ')}")
        return None

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
            tmpf.write(r.content)
            tmp = tmpf.name

        with rasterio.open(tmp) as src:
            arr = src.read(1).astype(float)
            if src.nodata is not None:
                arr[arr == src.nodata] = np.nan
            # Many numeric layers encode masked as 0:
            arr[arr == 0] = np.nan

            tags_band = src.tags(1)
            scale = float(tags_band.get("scale_factor", tags_band.get("SCALE_FACTOR", "1.0")))
            offset = float(tags_band.get("add_offset",   tags_band.get("OFFSET",       "0.0")))
            if scale == 1.0 and prop in KNOWN_SCALE_FALLBACK:
                scale = KNOWN_SCALE_FALLBACK[prop]
            data = arr * scale + offset

            valid_mask = ~np.isnan(data)
            if valid_mask.sum() == 0:
                return None

            rows, cols = np.where(valid_mask)
            xs, ys = rasterio.transform.xy(src.transform, rows, cols, offset='center')
            xs, ys = np.asarray(xs), np.asarray(ys)

            # back to lon/lat
            to_ll = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            lons, lats = to_ll.transform(xs, ys)

            # parse depth/stat from cid
            toks = cid.split("_")
            depth_tok = toks[1] if len(toks) > 1 else None
            stat_tok  = "_".join(toks[2:]) if len(toks) > 2 else None
            top, bottom, unit_depth = _parse_depth(depth_tok)

            df = pd.DataFrame({
                "latitude": lats,
                "longitude": lons,
                "parameter": prop,
                "top_depth": top,
                "bottom_depth": bottom,
                "depth_units": unit_depth,
                "statistic": stat_tok if stat_tok else "mean",
                "value": data[valid_mask].astype(np.float32),
                "coverageid": cid,
            })
            return df
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

def test_user_core_function():
    """Test user's core function directly"""
    print("🧪 Testing User's Core SoilGrids Function")
    print("=" * 40)

    # Use cached catalog from earlier
    with open("test_soilgrids_coverages.json", "r") as f:
        catalog = json.load(f)

    # Test cases - smaller areas in known agricultural regions
    test_cases = [
        {
            "name": "Netherlands Clay Soils",
            "bbox": (4.5, 52.0, 4.7, 52.2),
            "prop": "clay",
            "coverage": "clay_0-5cm_mean"
        },
        {
            "name": "Iowa Corn Belt",
            "bbox": (-93.8, 42.0, -93.6, 42.2),
            "prop": "soc",
            "coverage": "soc_0-5cm_mean"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing {test_case['name']}...")

        try:
            df = _fetch_coverage_to_df_uniform_grid(
                test_case["prop"],
                test_case["coverage"],
                test_case["bbox"],
                nx=20,
                ny=20
            )

            if df is not None and not df.empty:
                values = df["value"].values
                valid_vals = values[~pd.isna(values)]
                non_zero_vals = valid_vals[valid_vals != 0]

                print(f"   ✅ SUCCESS: {len(df)} points retrieved")
                print(f"   Valid values: {len(valid_vals)}")
                print(f"   Non-zero values: {len(non_zero_vals)}")

                if len(non_zero_vals) > 0:
                    print(f"   Data range: {non_zero_vals.min():.3f} to {non_zero_vals.max():.3f}")
                    print(f"   Mean: {non_zero_vals.mean():.3f}")
                    print(f"   🎉 REAL DATA FOUND!")
                else:
                    print(f"   ⚠️  Only zeros/nulls")
            else:
                print(f"   ❌ No data returned")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n🏁 User's core function test complete")

if __name__ == "__main__":
    test_user_core_function()