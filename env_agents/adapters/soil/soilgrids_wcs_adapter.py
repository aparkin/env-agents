"""
Enhanced SoilGrids WCS Adapter - Based on User's Proven Implementation

This adapter follows the user's working approach:
- Direct WCS requests with proper coordinate systems
- Equal Earth projection for numeric layers
- EPSG:4326 for categorical WRB layers
- Uniform grid sampling with max_pixels budget
- Proper scaling and metadata handling
- Long-form DataFrame output with rich metadata

Replaces the previous implementation that had timeout and data issues.
"""

import os
import json
import math
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Iterable

import numpy as np
import pandas as pd
import requests
import rasterio
from pyproj import Transformer

from ..base import BaseAdapter
from ...core.models import RequestSpec

# Constants from user's working code
EQUAL_EARTH_PROJ = "+proj=eqearth +datum=WGS84 +units=m +no_defs"
NATIVE_RES_M = 250.0  # SoilGrids native resolution
WCS_MAX_SIZE = 8192   # Server safety limit

# Scale factors for proper unit conversion
KNOWN_SCALE_FALLBACK = {
    "bdod": 0.01,       # cg/cm³ → g/cm³
    "soc": 0.1,         # g/kg
    "ocd": 0.1,         # g/cm³
    "ocs": 0.1,         # t/ha
    "nitrogen": 0.1     # g/kg
}

SOILGRIDS_SERVICES_NUMERIC = [
    "bdod","cec","cfvo","clay","nitrogen","phh2o",
    "sand","silt","soc","ocs","ocd","wv1500","wv0033","wv0010"
]
SOILGRIDS_SERVICES_CATEGORICAL = ["wrb"]
SOILGRIDS_SERVICES_ALL = SOILGRIDS_SERVICES_NUMERIC + SOILGRIDS_SERVICES_CATEGORICAL

SOILGRIDS_METADATA = {
    "bdod":   {"name":"Bulk density of fine earth fraction","units":"g/cm³","description":"Dry bulk density (<2 mm)."},
    "cec":    {"name":"Cation exchange capacity","units":"cmol(+)/kg","description":"Capacity to retain exchangeable cations."},
    "cfvo":   {"name":"Vol. coarse fragments","units":"cm³/dm³","description":"Volume fraction >2 mm per dm³."},
    "clay":   {"name":"Clay content","units":"%","description":"Mass fraction <2 µm."},
    "nitrogen":{"name":"Total nitrogen","units":"g/kg","description":"Total nitrogen content."},
    "phh2o":  {"name":"Soil pH (H₂O)","units":"pH","description":"pH in water suspension."},
    "sand":   {"name":"Sand content","units":"%","description":"Mass fraction 50–2000 µm."},
    "silt":   {"name":"Silt content","units":"%","description":"Mass fraction 2–50 µm."},
    "soc":    {"name":"Soil organic carbon","units":"g/kg","description":"Organic C mass fraction."},
    "ocs":    {"name":"Soil organic carbon stock","units":"t/ha","description":"Organic C per unit area."},
    "ocd":    {"name":"Soil organic carbon density","units":"g/cm³","description":"Organic C per unit volume."},
    "wv1500": {"name":"Water content @−1500 kPa","units":"cm³/cm³","description":"Permanent wilting point."},
    "wv0033": {"name":"Water content @−33 kPa","units":"cm³/cm³","description":"Field capacity."},
    "wv0010": {"name":"Water content @−10 kPa","units":"cm³/cm³","description":"Near saturation."},
    "wrb":    {"name":"WRB Reference Soil Groups","units":"categorical","description":"World Reference Base soil classes."}
}

# WRB soil class mapping
WRB_CLASSES = {
    1:"Acrisols",2:"Albeluvisols",3:"Alisols",4:"Andosols",5:"Arenosols",
    6:"Calcisols",7:"Cambisols",8:"Chernozems",9:"Cryosols",10:"Durisols",
    11:"Ferralsols",12:"Fluvisols",13:"Gleysols",14:"Gypsisols",15:"Histosols",
    16:"Kastanozems",17:"Leptosols",18:"Luvisols",19:"Nitisols",20:"Phaeozems",
    21:"Planosols",22:"Plinthosols",23:"Podzols",24:"Regosols",25:"Solonchaks",
    26:"Solonetz",27:"Stagnosols",28:"Technosols",29:"Umbrisols",30:"Vertisols",
    31:"Arenic Regosols",32:"Rock outcrop / Misc."
}


class SoilGridsWCSAdapter(BaseAdapter):
    """
    SoilGrids WCS Adapter using user's proven implementation approach

    Features:
    - Direct WCS requests with proper coordinate systems
    - Uniform grid sampling with pixel budget management
    - Proper scaling and unit conversion
    - Long-form DataFrame output with rich metadata
    """

    DATASET = "SoilGrids_WCS"
    SOURCE_URL = "https://maps.isric.org/mapserv"
    SOURCE_VERSION = "v2.0_wcs_proven"
    LICENSE = "https://creativecommons.org/licenses/by/4.0/"
    SERVICE_TYPE = "unitary"

    def __init__(self):
        super().__init__()
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.catalog_cache = None

    def _get_coverages_for_property(self, prop: str) -> List[str]:
        """Query WCS GetCapabilities for a SoilGrids property (user's exact approach)"""
        url = "https://maps.isric.org/mapserv"
        params = {
            "map": f"/map/{prop}.map",
            "SERVICE": "WCS",
            "VERSION": "2.0.1",
            "REQUEST": "GetCapabilities"
        }
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        ns = {"wcs": "http://www.opengis.net/wcs/2.0"}
        return [el.text for el in root.findall(".//wcs:CoverageId", ns)]

    def _build_catalog(self,
                      services: Iterable[str] = SOILGRIDS_SERVICES_ALL,
                      cache_file: str = "soilgrids_coverages.json",
                      refresh: bool = False) -> Dict[str, List[str]]:
        """Build catalog using user's simple, proven approach"""
        full_cache_file = self.cache_dir / cache_file

        if full_cache_file.exists() and not refresh:
            with open(full_cache_file, "r") as f:
                return json.load(f)

        catalog = {}
        for svc in services:
            try:
                cids = self._get_coverages_for_property(svc)
                if svc.lower() == "wrb":
                    # Use the one real categorical coverage
                    catalog[svc] = ["MostProbable"]
                else:
                    catalog[svc] = cids
            except Exception as e:
                print(f"Failed {svc}: {e}")
                catalog[svc] = []

        with open(full_cache_file, "w") as f:
            json.dump(catalog, f, indent=2)

        self.catalog_cache = catalog
        return catalog

    def _parse_depth(self, depth: Optional[str]):
        """Parse '0-5cm' → (0, 5, 'cm')"""
        if not depth:
            return None, None, None
        import re
        m = re.match(r"(\d+)-(\d+)(cm|m)", depth)
        if m:
            top, bottom, unit = m.groups()
            return int(top), int(bottom), unit
        return None, None, None

    def _uniform_grid_from_max_pixels(self, bbox_ll: Tuple[float,float,float,float], max_pixels: int) -> Tuple[int,int]:
        """Choose (nx,ny) for uniform grid so nx*ny ≈ max_pixels, preserving aspect"""
        minlon, minlat, maxlon, maxlat = bbox_ll
        dx, dy = max(0.0, maxlon-minlon), max(0.0, maxlat-minlat)
        if dx <= 0 or dy <= 0:
            return 1, 1
        aspect = dx / dy
        ny = int(round(math.sqrt(max(1, max_pixels) / max(aspect, 1e-9))))
        nx = int(round(aspect * ny))
        nx, ny = max(1, nx), max(1, ny)
        # Respect server safety cap
        nx, ny = min(nx, WCS_MAX_SIZE), min(ny, WCS_MAX_SIZE)
        return nx, ny

    def _to_equal_earth_bbox(self, bbox_ll: Tuple[float,float,float,float]) -> Tuple[float,float,float,float]:
        """Transform lon/lat bbox to Equal Earth meters (user's approach)"""
        transformer = Transformer.from_crs("EPSG:4326", EQUAL_EARTH_PROJ, always_xy=True)
        minx, miny = transformer.transform(bbox_ll[0], bbox_ll[1])
        maxx, maxy = transformer.transform(bbox_ll[2], bbox_ll[3])
        return minx, miny, maxx, maxy

    def _fetch_coverage_to_df_uniform_grid(self,
                                         prop: str,
                                         cid: str,
                                         bbox_ll: Tuple[float,float,float,float],
                                         nx: int,
                                         ny: int) -> Optional[pd.DataFrame]:
        """
        Fetch ONE coverage onto uniform grid (user's exact implementation)

        Numeric layers: Equal Earth meters, subset on x/y
        WRB categorical: EPSG:4326 degrees, subset on long/lat
        """
        minlon, minlat, maxlon, maxlat = bbox_ll
        if not (minlon < maxlon and minlat < maxlat):
            return None

        if prop.lower() == "wrb":
            # WRB categorical: EPSG:4326 with long/lat axes
            coverageid = "MostProbable"  # Ignore stub class names
            width_deg = maxlon - minlon
            height_deg = maxlat - minlat
            resx_deg = max(width_deg / max(1, nx), 1e-6)
            resy_deg = max(height_deg / max(1, ny), 1e-6)

            url = "https://maps.isric.org/mapserv"
            params = {
                "map": "/map/wrb.map",
                "service": "WCS",
                "version": "2.0.1",
                "request": "GetCoverage",
                "coverageid": coverageid,
                "format": "image/tiff",
                "subset": [f"long({minlon},{maxlon})", f"lat({minlat},{maxlat})"],
                "subsettingcrs": "http://www.opengis.net/def/crs/EPSG/0/4326",
                "resx": f"{resx_deg}",
                "resy": f"{resy_deg}",
            }

            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").lower()
            if "tiff" not in ctype and "geotiff" not in ctype:
                print(f"WCS error {prop}:{coverageid} → {r.text[:250].replace(chr(10),' ')}")
                return None

            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                    tmpf.write(r.content)
                    tmp = tmpf.name

                with rasterio.open(tmp) as src:
                    arr = src.read(1).astype(float)
                    # WRB: 0 = no data / water; keep >0
                    arr[arr <= 0] = np.nan

                    valid_mask = ~np.isnan(arr)
                    if valid_mask.sum() == 0:
                        return None

                    rows, cols = np.where(valid_mask)
                    xs, ys = rasterio.transform.xy(src.transform, rows, cols, offset='center')
                    lons, lats = np.asarray(xs), np.asarray(ys)  # already EPSG:4326

                    values = arr[valid_mask].astype(int)
                    class_names = [WRB_CLASSES.get(int(v), "Unknown") for v in values]

                    df = pd.DataFrame({
                        "latitude": lats,
                        "longitude": lons,
                        "parameter": "wrb",
                        "top_depth": None,
                        "bottom_depth": None,
                        "depth_units": None,
                        "statistic": "category",
                        "description": "WRB Reference Soil Group",
                        "unit": "categorical",
                        "value": values,
                        "class_name": class_names,
                        "coverageid": coverageid,
                        "date": "2020-05-18"
                    })
                    return df
            finally:
                if tmp and os.path.exists(tmp):
                    os.remove(tmp)

        # Numeric properties: Equal Earth meters with x/y axes
        minx, miny, maxx, maxy = self._to_equal_earth_bbox(bbox_ll)
        width_m = max(1.0, maxx - minx)
        height_m = max(1.0, maxy - miny)

        resx_m = max(NATIVE_RES_M, width_m / max(1, nx))
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
        ctype = r.headers.get("Content-Type", "").lower()
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

                # Enhanced nodata cleaning (your improvements)
                if src.nodata is not None:
                    arr[arr == src.nodata] = np.nan
                # Handle common sentinel values
                for sentinel in (-32768, -9999):
                    arr[arr == sentinel] = np.nan
                # Many numeric layers encode masked as 0:
                arr[arr == 0] = np.nan

                # Get scaling factors
                tags_band = src.tags(1)
                scale = float(tags_band.get("scale_factor", tags_band.get("SCALE_FACTOR", "1.0")))
                offset = float(tags_band.get("add_offset", tags_band.get("OFFSET", "0.0")))
                if scale == 1.0 and prop in KNOWN_SCALE_FALLBACK:
                    scale = KNOWN_SCALE_FALLBACK[prop]
                data = arr * scale + offset

                valid_mask = ~np.isnan(data)
                # Your additional check for uniform data
                if valid_mask.sum() == 0 or np.nanmin(data) == np.nanmax(data):
                    return None

                rows, cols = np.where(valid_mask)
                xs, ys = rasterio.transform.xy(src.transform, rows, cols, offset='center')
                xs, ys = np.asarray(xs), np.asarray(ys)

                # Back to lon/lat
                to_ll = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
                lons, lats = to_ll.transform(xs, ys)

                # Parse depth/stat from coverage ID
                toks = cid.split("_")
                depth_tok = toks[1] if len(toks) > 1 else None
                stat_tok = "_".join(toks[2:]) if len(toks) > 2 else None
                top, bottom, unit_depth = self._parse_depth(depth_tok)

                meta = SOILGRIDS_METADATA.get(prop, {})
                df = pd.DataFrame({
                    "latitude": lats,
                    "longitude": lons,
                    "parameter": prop,
                    "top_depth": top,
                    "bottom_depth": bottom,
                    "depth_units": unit_depth,
                    "statistic": stat_tok if stat_tok else "mean",
                    "description": meta.get("name", prop),
                    "unit": meta.get("units", "unknown"),
                    "value": data[valid_mask].astype(np.float32),
                    "coverageid": cid,
                    "date": "2020-05-18"
                })
                return df
        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)

    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return adapter capabilities"""
        # Build catalog if not available
        if not self.catalog_cache:
            self._build_catalog()

        variables = []
        for prop, metadata in SOILGRIDS_METADATA.items():
            if prop == "wrb":
                variables.append({
                    "canonical": "soil:wrb_classification",
                    "platform_native": prop,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "unit": "categorical",
                    "data_type": "categorical",
                    "categories": WRB_CLASSES,
                })
            else:
                variables.append({
                    "canonical": f"soil:{prop}",
                    "platform_native": prop,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "unit": metadata["units"],
                    "data_type": "numeric",
                })

        return {
            "dataset": self.DATASET,
            "service_type": self.SERVICE_TYPE,
            "variables": variables,
            "temporal_coverage": {
                "reference_period": "2020-05-18 (model snapshot)",
                "temporal_resolution": "Static global maps",
            },
            "spatial_coverage": {
                "extent": "Global (excluding Antarctica)",
                "spatial_resolution": "250m native",
                "coordinate_system": "WGS84 (EPSG:4326)",
            },
            "data_access_method": "WCS (Web Coverage Service)",
            "proven_approach": True,
        }

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch SoilGrids data using proven uniform grid approach"""
        # Extract bbox from geometry
        if spec.geometry.type == "bbox":
            bbox_ll = tuple(spec.geometry.coordinates)
        elif spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
            # Small buffer around point
            bbox_ll = (lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01)
        else:
            raise ValueError(f"Unsupported geometry type: {spec.geometry.type}")

        # Default parameters
        max_pixels = spec.extra.get("max_pixels", 100_000) if spec.extra else 100_000
        statistics = spec.extra.get("statistics", ["mean"]) if spec.extra else ["mean"]
        include_wrb = spec.extra.get("include_wrb", True) if spec.extra else True

        # Handle variable selection - default to all numeric services
        if spec.variables:
            services = []
            for var in spec.variables:
                if var.startswith("soil:"):
                    prop = var.replace("soil:", "")
                    if prop in SOILGRIDS_SERVICES_ALL:
                        services.append(prop)
                elif var.lower() in [s.lower() for s in SOILGRIDS_SERVICES_ALL]:
                    # Case insensitive matching
                    services.append([s for s in SOILGRIDS_SERVICES_ALL if s.lower() == var.lower()][0])
                elif var in SOILGRIDS_SERVICES_ALL:
                    services.append(var)
                else:
                    self.logger.warning(f"Unknown SoilGrids variable: {var}, available: {SOILGRIDS_SERVICES_ALL}")

            if not services:
                self.logger.warning("No valid SoilGrids variables found, using default numeric services")
                services = SOILGRIDS_SERVICES_NUMERIC.copy()
        else:
            # Default to all numeric services (14 soil properties)
            services = SOILGRIDS_SERVICES_NUMERIC.copy()

        if include_wrb and "wrb" not in services:
            services.append("wrb")

        # Build catalog only if needed
        if not self.catalog_cache:
            self.catalog_cache = self._build_catalog(refresh=False)

        # Check if we need to build catalog for additional services
        missing_services = [s for s in services if s not in self.catalog_cache]
        if missing_services:
            # Only rebuild for missing services
            additional_catalog = self._build_catalog(services=missing_services, refresh=True)
            self.catalog_cache.update(additional_catalog)

        # Use the cached catalog
        catalog = {prop: cids for prop, cids in self.catalog_cache.items() if prop in services}

        # Build (prop, cid) list
        pairs = []
        for prop, cids in catalog.items():
            if prop == "wrb":
                if include_wrb and "MostProbable" in cids:
                    pairs.append(("wrb", "MostProbable"))
                continue

            for cid in cids:
                toks = cid.split("_")
                stat_tok = "_".join(toks[2:]) if len(toks) > 2 else None
                if stat_tok and stat_tok not in statistics:
                    continue
                if (not stat_tok) and ("mean" not in statistics):
                    continue
                pairs.append((prop, cid))

        if not pairs:
            return []

        # Get uniform grid size
        nx, ny = self._uniform_grid_from_max_pixels(bbox_ll, max_pixels=max(1, int(max_pixels)))

        # Fetch all coverages
        dfs = []
        for prop, cid in pairs:
            try:
                df = self._fetch_coverage_to_df_uniform_grid(prop, cid, bbox_ll, nx, ny)
                if df is not None and not df.empty:
                    dfs.append(df)
            except Exception as e:
                print(f"Error for {prop}:{cid}: {e}")

        if not dfs:
            return []

        # Combine and convert to env-agents format
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df.attrs["soilgrids_metadata"] = SOILGRIDS_METADATA
        combined_df.attrs["catalog"] = catalog

        # Transform to core schema
        rows = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        for _, row in combined_df.iterrows():
            # Map to canonical variable
            prop = row["parameter"]
            if prop == "wrb":
                canonical_var = "soil:wrb_classification"
            else:
                canonical_var = f"soil:{prop}"

            core_row = {
                # Identity columns
                "observation_id": f"soilgrids_wcs_{row['latitude']:.6f}_{row['longitude']:.6f}_{prop}_{row.get('statistic', 'value')}",
                "dataset": self.DATASET,
                "source_url": self.SOURCE_URL,
                "source_version": self.SOURCE_VERSION,
                "license": self.LICENSE,
                "retrieval_timestamp": retrieval_timestamp,

                # Spatial columns
                "geometry_type": "point",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "spatial_id": None,
                "site_name": None,
                "admin": None,
                "elevation_m": None,
                "geom_wkt": f"POINT({row['longitude']} {row['latitude']})",

                # Temporal columns
                "time": row.get("date"),
                "temporal_coverage": "2020 model snapshot",

                # Value columns
                "variable": canonical_var,
                "value": float(row["value"]) if pd.notna(row["value"]) else None,
                "unit": row["unit"],
                "depth_top_cm": row.get("top_depth"),
                "depth_bottom_cm": row.get("bottom_depth"),
                "qc_flag": "ok",

                # Metadata columns
                "attributes": {
                    "parameter": prop,
                    "statistic": row.get("statistic"),
                    "coverage_id": row.get("coverageid"),
                    "description": row.get("description"),
                    "class_name": row.get("class_name"),  # For WRB
                    "depth_units": row.get("depth_units"),
                    "wcs_method": "uniform_grid",
                    "processing_metadata": combined_df.attrs,
                    "terms": {
                        "native_id": prop,
                        "canonical_variable": canonical_var,
                        "mapping_confidence": 0.95
                    }
                },
                "provenance": {
                    "data_source": "ISRIC SoilGrids v2.0",
                    "method": "WCS GetCoverage with uniform grid",
                    "api_endpoint": self.SOURCE_URL,
                    "coverage_id": row.get("coverageid"),
                    "retrieval_timestamp": retrieval_timestamp,
                    "coordinate_system": "Equal Earth → WGS84" if prop != "wrb" else "EPSG:4326",
                    "proven_approach": True
                }
            }

            rows.append(core_row)

        return rows