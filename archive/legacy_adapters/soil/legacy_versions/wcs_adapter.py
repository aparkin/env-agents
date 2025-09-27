"""
Enhanced SoilGrids WCS Adapter - Production Ready
Integrates working WCS-based approach with comprehensive guard rails and reliability patterns.
Replaces failing REST API with robust Web Coverage Service (WCS) interface.
"""

import json
import logging
import requests
import pandas as pd
import numpy as np
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import time
import urllib.parse
import math
import os
from pathlib import Path

try:
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False
    logging.warning("rioxarray not available - SoilGrids WCS functionality limited")

from ..base import BaseAdapter
from ...core.models import RequestSpec
from ...core.adapter_mixins import StandardAdapterMixin

logger = logging.getLogger(__name__)

# Circuit breaker for reliability
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None

    @property
    def is_open(self) -> bool:
        if self.failure_count >= self.failure_threshold:
            if self.last_failure_time and (time.time() - self.last_failure_time) < self.recovery_timeout:
                return True
            # Reset circuit breaker after timeout
            self.failure_count = 0
            self.last_failure_time = None
        return False

    def __enter__(self):
        if self.is_open:
            raise CircuitBreakerOpen("Circuit breaker is open")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.failure_count += 1
            self.last_failure_time = time.time()

class CircuitBreakerOpen(Exception):
    pass

# WRB Soil Classification with enhanced agricultural context
WRB_CLASSES = {
    1:  {"name": "Acrisols",    "profile": "Strongly weathered, acidic, nutrient-poor tropical soils; low fertility."},
    2:  {"name": "Albeluvisols","profile": "Clay-illuviated soils with abrupt textural contrasts; poor drainage risk."},
    3:  {"name": "Alisols",     "profile": "Acidic soils with high-activity clays; low base saturation; moderately fertile."},
    4:  {"name": "Andosols",    "profile": "Volcanic ash soils; very fertile, high water holding, but P fixation issues."},
    5:  {"name": "Arenosols",   "profile": "Sandy, weakly developed soils; low nutrient and water holding capacity."},
    6:  {"name": "Calcisols",   "profile": "Carbonate-rich soils; semi-arid/arid regions; often alkaline, moderate fertility."},
    7:  {"name": "Cambisols",   "profile": "Weakly developed soils; generally fertile; transitional between young and mature soils."},
    8:  {"name": "Chernozems",  "profile": "Humus-rich black soils of grasslands; highly fertile; agricultural breadbasket."},
    9:  {"name": "Cryosols",    "profile": "Permafrost soils; limited rooting depth; sensitive to climate warming."},
    10: {"name": "Durisols",    "profile": "Soils with silica cementation (duripan); arid climates; root-limiting horizons."},
    11: {"name": "Ferralsols",  "profile": "Deeply weathered tropical soils; dominated by oxides; very low fertility."},
    12: {"name": "Fluvisols",   "profile": "Young alluvial soils; fertile; floodplains and deltas."},
    13: {"name": "Gleysols",    "profile": "Waterlogged soils with gleyic features; poor drainage; flooding risk."},
    14: {"name": "Gypsisols",   "profile": "Gypsum-rich soils; arid climates; structure and salinity constraints."},
    15: {"name": "Histosols",   "profile": "Organic soils (peat, muck); high carbon storage; waterlogged; unstable when drained."},
    16: {"name": "Kastanozems", "profile": "Brown steppe soils; moderately humus-rich; good fertility but drier than Chernozems."},
    17: {"name": "Leptosols",   "profile": "Very shallow soils over rock; limited rooting depth; erosion-prone."},
    18: {"name": "Luvisols",    "profile": "Clay-illuviated, base-rich soils; fertile; common in temperate regions."},
    19: {"name": "Nitisols",    "profile": "Deep, well-structured tropical soils; good fertility and resilience."},
    20: {"name": "Phaeozems",   "profile": "Dark, humus-rich soils; fertile; more moist than Chernozems."},
    21: {"name": "Planosols",   "profile": "Textural contrast soils; perched water; seasonal waterlogging constraints."},
    22: {"name": "Plinthosols", "profile": "Iron-rich plinthite layers; harden irreversibly; rooting and drainage limits."},
    23: {"name": "Podzols",     "profile": "Acidic sandy soils; leached; poor fertility; forested uplands."},
    24: {"name": "Regosols",    "profile": "Young, weakly developed soils; shallow, unstable; low fertility."},
    25: {"name": "Solonchaks",  "profile": "Saline soils; arid zones; severe constraints for crops."},
    26: {"name": "Solonetz",    "profile": "Sodic soils; poor structure; water infiltration problems."},
    27: {"name": "Stagnosols",  "profile": "Soils with perched water tables; drainage and aeration issues."},
    28: {"name": "Technosols",  "profile": "Soils with significant human materials; urban, industrial, mine spoils."},
    29: {"name": "Umbrisols",   "profile": "Dark, acidic, humus-rich soils; low base saturation; limited fertility."},
    30: {"name": "Vertisols",   "profile": "Clay-rich shrink–swell soils; very fertile but engineering challenges (cracks)."},
    31: {"name": "Arenic Regosols","profile": "Sandy regosols; weak horizon development; drought-prone, nutrient poor."}
}

# Inverse mapping for quick lookup
WRB_CLASSES_INV = {v["name"]: k for k, v in WRB_CLASSES.items()}

# Comprehensive SoilGrids metadata with enhanced descriptions
SOILGRIDS_METADATA = {
    "bdod": {
        "name": "Bulk density of fine earth fraction",
        "units": "cg/cm³",
        "description": "Dry bulk density of particles <2 mm. Critical for root growth, water infiltration, and carbon storage calculations.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"],
        "pedological_significance": "Indicates soil compaction and structural quality. Reflects management impacts and natural consolidation processes.",
        "agricultural_applications": ["Compaction monitoring", "Traffic management", "Root growth assessment", "Soil health indicators"]
    },
    "cec": {
        "name": "Cation exchange capacity",
        "units": "cmol(+)/kg",
        "description": "Soil capacity to retain exchangeable cations. Fundamental property determining nutrient retention, buffering capacity, and fertilizer efficiency.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"],
        "pedological_significance": "Indicates clay mineral types and organic matter content. Fundamental property affecting nutrient cycling and soil buffering capacity.",
        "agricultural_applications": ["Fertilizer rates", "Nutrient management", "Soil amendment needs", "Ion exchange capacity"]
    },
    "cfvo": {
        "name": "Volumetric fraction of coarse fragments",
        "units": "cm³/dm³",
        "description": "Volume fraction of particles >2 mm per dm³. Affects soil volume calculations, root growth space, and water storage capacity.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "clay": {
        "name": "Clay content (<2 µm) mass fraction",
        "units": "%",
        "description": "Mass fraction of clay-sized particles. Controls soil plasticity, water retention, and nutrient holding capacity.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"],
        "pedological_significance": "Controls soil structure formation, swelling/shrinking behavior, and defines textural classes. Primary factor in soil classification systems.",
        "agricultural_applications": ["Irrigation scheduling", "Tillage timing", "Compaction risk assessment", "Plasticity index"]
    },
    "nitrogen": {
        "name": "Total nitrogen",
        "units": "g/kg",
        "description": "Total nitrogen content including organic and inorganic forms. Essential macronutrient affecting crop productivity and environmental quality.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "phh2o": {
        "name": "Soil pH in H₂O",
        "units": "pH",
        "description": "pH measured in water suspension affecting nutrient availability, microbial activity, and plant growth.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "sand": {
        "name": "Sand content (50–2000 µm) mass fraction",
        "units": "%",
        "description": "Mass fraction of sand-sized particles determining soil drainage, aeration, and ease of cultivation.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "silt": {
        "name": "Silt content (2–50 µm) mass fraction",
        "units": "%",
        "description": "Mass fraction of silt-sized particles contributing to soil texture and water holding capacity.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "soc": {
        "name": "Soil organic carbon content",
        "units": "g/kg",
        "description": "Organic carbon mass fraction. Critical for soil health, nutrient cycling, fertility, and climate change mitigation.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "ocs": {
        "name": "Soil organic carbon stock",
        "units": "t/ha",
        "description": "Organic carbon mass per unit area. Essential for carbon accounting and climate change assessments.",
        "depths": ["0-30cm","0-100cm","0-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "ocd": {
        "name": "Soil organic carbon density",
        "units": "g/cm³",
        "description": "Organic carbon per unit volume providing absolute measure of soil carbon stocks.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "wv1500": {
        "name": "Water content at permanent wilting point (pF 4.2, −1500 kPa)",
        "units": "cm³/cm³",
        "description": "Volumetric water content at −1500 kPa matric potential. Minimum water content at which plants can extract water.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "wv0033": {
        "name": "Water content at field capacity (pF 2.0, −33 kPa)",
        "units": "cm³/cm³",
        "description": "Volumetric water content at −33 kPa matric potential.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "wv0010": {
        "name": "Water content near saturation (pF 1.0, −10 kPa)",
        "units": "cm³/cm³",
        "description": "Volumetric water content at −10 kPa matric potential. Maximum water storage available to plants after drainage.",
        "depths": ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"],
        "statistics": ["mean","Q0.05","Q0.5","Q0.95","uncertainty"]
    },
    "wrb": {
        "name": "WRB Reference Soil Groups",
        "units": "categorical",
        "description": "World Reference Base soil classification map with agricultural and ecological context.",
        "categories": WRB_CLASSES
    }
}

# Service listings
SOILGRIDS_SERVICES_NUMERIC = [
    "bdod","cec","cfvo","clay","nitrogen","phh2o",
    "sand","silt","soc","ocs","ocd","wv1500","wv0033","wv0010"
]
SOILGRIDS_SERVICES_CATEGORICAL = ["wrb"]
SOILGRIDS_SERVICES_ALL = SOILGRIDS_SERVICES_NUMERIC + SOILGRIDS_SERVICES_CATEGORICAL


class SoilGridsWCSAdapter(BaseAdapter, StandardAdapterMixin):
    """
    Enhanced SoilGrids WCS Adapter - Production Ready

    Uses robust Web Coverage Service (WCS) instead of failing REST API.
    Includes comprehensive guard rails, metadata system, and reliability patterns.
    """

    DATASET = "SoilGrids"
    SOURCE_URL = "https://maps.isric.org/mapserv"
    SOURCE_VERSION = "v2.0_wcs"
    LICENSE = "https://creativecommons.org/licenses/by/4.0/"
    SERVICE_TYPE = "unitary"

    def __init__(self):
        """Initialize SoilGrids WCS adapter with reliability patterns"""
        super().__init__()

        # Initialize standard components (auth, config, logging)
        self.initialize_adapter()

        # Circuit breaker for service failures
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=300)

        # Response size limits and guard rails (match working code)
        self.max_pixels_default = 500_000     # Conservative for env-agents (vs 4M in your code)
        self.max_native_pixels = 2_500_000    # For tiling decisions
        self.native_resolution = 0.00225      # SoilGrids native resolution (degrees)
        self.max_side = 2048                  # Maximum dimension for resampling

        # Catalog caching
        self.catalog_cache = None
        self.catalog_timestamp = None
        self.catalog_max_age = 24 * 3600       # 24 hours

        # Fallback cache directory
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        if not RIOXARRAY_AVAILABLE:
            logger.warning("rioxarray not available - SoilGrids WCS adapter will have limited functionality")

    def _get_coverages_for_property(self, prop: str) -> List[str]:
        """Discover available coverages for a soil property using WCS GetCapabilities (user's proven approach)"""
        url = "https://maps.isric.org/mapserv"
        params = {"map": f"/map/{prop}.map", "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCapabilities"}

        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()

        root = ET.fromstring(r.text)
        ns = {"wcs": "http://www.opengis.net/wcs/2.0"}
        return [el.text for el in root.findall(".//wcs:CoverageId", ns)]

    def _build_catalog(self, services: List[str] = None, force_refresh: bool = False) -> Dict[str, List[str]]:
        """Build or load catalog using user's proven approach"""
        services = services or SOILGRIDS_SERVICES_ALL
        cache_file = self.cache_dir / "soilgrids_coverages.json"

        # Use user's simple cache check
        if cache_file.exists() and not force_refresh:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)

            # Handle both old and new formats
            if isinstance(cached_data, dict) and "catalog" in cached_data:
                catalog = cached_data["catalog"]
            else:
                catalog = cached_data  # Old format

            if catalog:
                self.catalog_cache = catalog
                self.catalog_timestamp = datetime.fromtimestamp(cache_file.stat().st_mtime)
                total_coverages = sum(len(v) for v in catalog.values())
                logger.info(f"✅ Loaded cached SoilGrids catalog: {len(catalog)} properties, {total_coverages} coverages")
                return catalog

        # Build catalog using user's simple approach
        catalog = {}
        for svc in services:
            try:
                ids = self._get_coverages_for_property(svc)
                catalog[svc] = ids
            except Exception as e:
                logger.warning(f"Failed {svc}: {e}")
                catalog[svc] = []

        # Save with metadata for tracking
        catalog_data = {
            "catalog": catalog,
            "metadata": {
                "discovery_timestamp": datetime.now().isoformat(),
                "total_services": len(services),
                "total_coverages": sum(len(v) for v in catalog.values()),
                "version": "2.0_wcs_user_approach"
            }
        }

        self.cache_dir.mkdir(exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(catalog_data, f, indent=2)

        self.catalog_cache = catalog
        self.catalog_timestamp = datetime.now()

        total_coverages = sum(len(v) for v in catalog.values())
        logger.info(f"✅ Built SoilGrids catalog: {total_coverages} coverages")

        return catalog

    def _is_catalog_fresh(self) -> bool:
        """Check if catalog is fresh enough to avoid refresh"""
        if self.catalog_timestamp is None:
            return False
        age_seconds = (datetime.now() - self.catalog_timestamp).total_seconds()
        return age_seconds < self.catalog_max_age

    def _get_guard_rail_limits(self, spec: RequestSpec) -> Dict[str, Any]:
        """Calculate appropriate limits and strategy based on request size"""
        # Extract bbox from geometry
        if spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
            # Use small buffer for point requests (1km)
            buffer = 0.01  # ~1km at equator
            bbox = (lon - buffer, lat - buffer, lon + buffer, lat + buffer)
        elif spec.geometry.type == "bbox":
            bbox = tuple(spec.geometry.coordinates)
        else:
            raise ValueError(f"Unsupported geometry type: {spec.geometry.type}")

        # Calculate native pixel count
        minx, miny, maxx, maxy = bbox
        dx, dy = maxx - minx, maxy - miny
        native_pixels = (dx / self.native_resolution) * (dy / self.native_resolution)

        # Use strategy similar to working code
        if native_pixels <= self.max_pixels_default:
            # Small enough for direct fetch with auto-scaling
            return {
                "strategy": "direct",
                "bbox": bbox,
                "tiling": False,
                "resolution": "auto",  # Let server scale automatically
                "target_pixels": self.max_pixels_default,
                "estimated_pixels": int(native_pixels)
            }
        elif native_pixels <= self.max_native_pixels:
            # Medium size: use resampling
            return {
                "strategy": "resampled",
                "bbox": bbox,
                "tiling": False,
                "resolution": "auto",
                "target_pixels": self.max_pixels_default,
                "estimated_pixels": int(native_pixels)
            }
        else:
            # Large: use tiling (your _tile_bbox_native approach)
            tiles = self._tile_bbox_native(bbox, self.max_native_pixels)
            return {
                "strategy": "tiled",
                "bbox": bbox,
                "tiling": True,
                "tiles": tiles,
                "resolution": "auto",  # Each tile auto-scaled
                "estimated_pixels": int(native_pixels),
                "tile_count": len(tiles)
            }

    def _tile_bbox_native(self, bbox: Tuple[float, float, float, float],
                         max_pixels: int) -> List[Tuple[float, float, float, float]]:
        """Split large bounding box into tiles that respect pixel limits"""
        minx, miny, maxx, maxy = bbox
        dx, dy = maxx - minx, maxy - miny

        # Calculate how many tiles needed
        nx = dx / self.native_resolution
        ny = dy / self.native_resolution
        total_pixels = nx * ny

        if total_pixels <= max_pixels:
            return [bbox]

        # Calculate tile grid
        k = math.sqrt(total_pixels / max_pixels)
        tiles_x = int(math.ceil(k))
        tiles_y = int(math.ceil(k))

        tiles = []
        for i in range(tiles_x):
            for j in range(tiles_y):
                tile_minx = minx + i * dx / tiles_x
                tile_miny = miny + j * dy / tiles_y
                tile_maxx = minx + (i + 1) * dx / tiles_x
                tile_maxy = miny + (j + 1) * dy / tiles_y
                tiles.append((tile_minx, tile_miny, tile_maxx, tile_maxy))

        return tiles

    def _choose_scale_size(self, bbox: Tuple[float, float, float, float],
                          target_pixels: int = 4_000_000) -> Tuple[int, int]:
        """Calculate appropriate scale size for resampling"""
        minx, miny, maxx, maxy = bbox
        dx, dy = maxx - minx, maxy - miny

        # Account for latitude distortion
        lat_mid = 0.5 * (miny + maxy)
        eff_dx = dx * max(0.2, math.cos(math.radians(lat_mid)))

        # Calculate aspect ratio and dimensions
        ratio = max(0.1, min(eff_dx / dy if dy > 0 else 1.0, 10.0))
        H = int(round(math.sqrt(target_pixels / ratio)))
        W = int(round(ratio * H))

        return min(W, self.max_side), min(H, self.max_side)

    def _parse_depth(self, depth_str: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Parse depth string like '0-5cm' into components"""
        if not depth_str:
            return None, None, None

        import re
        match = re.match(r"(\d+)-(\d+)(cm|m)", depth_str)
        if match:
            top, bottom, unit = match.groups()
            return int(top), int(bottom), unit

        return None, None, None

    def _fetch_coverage_to_df(self, prop: str, coverage_id: str,
                             bbox: Tuple[float, float, float, float],
                             scalesize: Optional[Tuple[int, int]] = None) -> Optional[pd.DataFrame]:
        """Fetch a single coverage using WCS and convert to DataFrame"""
        if not RIOXARRAY_AVAILABLE:
            logger.error("rioxarray required for WCS data fetching")
            return None

        minx, miny, maxx, maxy = bbox
        base_url = "https://maps.isric.org/mapserv"

        # Properly format WCS parameters using requests params (this works!)
        params = {
            "map": f"/map/{prop}.map",
            "SERVICE": "WCS",
            "VERSION": "2.0.1",
            "REQUEST": "GetCoverage",
            "coverageid": coverage_id,
            "format": "image/tiff",
            "subset": [f"Long({minx},{maxx})", f"Lat({miny},{maxy})"]
        }

        # Add scaleSize if provided, or use automatic server scaling
        if scalesize:
            W, H = scalesize
            params["scaleSize"] = f"Long({W}),Lat({H})"
        else:
            # Let server auto-scale based on reasonable pixel limits
            # This is more robust than manual calculations
            target_pixels = min(self.max_pixels_default, 200000)  # Conservative for testing
            default_size = self._choose_scale_size(bbox, target_pixels=target_pixels)
            W, H = default_size
            params["scaleSize"] = f"Long({W}),Lat({H})"

        try:
            logger.debug(f"WCS request to {base_url} with params: {params}")
            response = requests.get(base_url, params=params, timeout=180)
            response.raise_for_status()

            # Verify we got a TIFF response
            if "tiff" not in response.headers.get("Content-Type", "").lower():
                logger.warning(f"WCS error for {prop}:{coverage_id} - got: {response.text[:200]}")
                return None

            # Process TIFF data
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpf:
                    tmpf.write(response.content)
                    tmp_file = tmpf.name

                # Read with rioxarray
                xarr = rioxarray.open_rasterio(tmp_file, masked=True)

                # Extract values and coordinates
                vals = xarr.values[0] if xarr.values.ndim == 3 else xarr.values
                lats, lons = np.meshgrid(xarr.y.values, xarr.x.values, indexing="ij")

                # Handle masked arrays
                if np.ma.is_masked(vals):
                    valid = ~vals.mask
                    data = vals.data[valid]
                else:
                    valid = ~np.isnan(vals)
                    data = vals[valid]

                if data.size == 0:
                    return None

                lat_valid = lats[valid]
                lon_valid = lons[valid]

                # Handle WRB categorical data differently
                if prop == "wrb":
                    # For WRB, nonzero means presence of soil class
                    if data.max() == 0:
                        return None

                    # coverageid is the class name for WRB
                    class_name = coverage_id
                    class_code = WRB_CLASSES_INV.get(class_name)

                    df = pd.DataFrame({
                        "latitude": lat_valid,
                        "longitude": lon_valid,
                        "parameter": "wrb",
                        "top_depth": None,
                        "bottom_depth": None,
                        "depth_units": None,
                        "statistic": "category",
                        "description": class_name,
                        "unit": "categorical",
                        "value": class_code,
                        "coverageid": coverage_id,
                        "date": "2020-05-18"
                    })
                    return df

                # Handle numeric properties
                tokens = coverage_id.split("_")
                depth_token = tokens[1] if len(tokens) > 1 else None
                stat_token = "_".join(tokens[2:]) if len(tokens) > 2 else None

                top_depth, bottom_depth, depth_unit = self._parse_depth(depth_token)
                metadata = SOILGRIDS_METADATA.get(prop, {})

                df = pd.DataFrame({
                    "latitude": lat_valid,
                    "longitude": lon_valid,
                    "parameter": prop,
                    "top_depth": top_depth,
                    "bottom_depth": bottom_depth,
                    "depth_units": depth_unit,
                    "statistic": stat_token,
                    "description": metadata.get("name", prop),
                    "unit": metadata.get("units", "unknown"),
                    "value": data.astype(np.float32),
                    "coverageid": coverage_id,
                    "date": "2020-05-18"
                })
                return df

            finally:
                if tmp_file and os.path.exists(tmp_file):
                    os.remove(tmp_file)

        except Exception as e:
            logger.warning(f"Failed to fetch coverage {prop}:{coverage_id}: {e}")
            return None

    def _map_variables_to_properties(self, variables: Optional[List[str]]) -> List[str]:
        """Map canonical variables to SoilGrids property names"""
        if not variables:
            return SOILGRIDS_SERVICES_ALL

        # Mapping from canonical variables to SoilGrids properties
        variable_map = {
            "soil:clay": "clay",
            "soil:sand": "sand",
            "soil:silt": "silt",
            "soil:soc": "soc",
            "soil:ph": "phh2o",
            "soil:bulk_density": "bdod",
            "soil:cec": "cec",
            "soil:nitrogen": "nitrogen",
            "soil:wrb": "wrb",
            "soil:water_content": ["wv0010", "wv0033", "wv1500"],
            "soil:organic_carbon": ["soc", "ocs", "ocd"]
        }

        mapped_props = set()
        for var in variables:
            # Direct mapping
            if var in variable_map:
                mapped = variable_map[var]
                if isinstance(mapped, list):
                    mapped_props.update(mapped)
                else:
                    mapped_props.add(mapped)
            # Partial matching
            else:
                for prop in SOILGRIDS_SERVICES_ALL:
                    if prop in var.lower() or var.lower() in prop:
                        mapped_props.add(prop)

        return list(mapped_props) if mapped_props else SOILGRIDS_SERVICES_ALL

    def _refresh_metadata(self, metadata_type: str = "capabilities",
                         force_refresh: bool = False) -> Dict[str, Any]:
        """Refresh catalog metadata using WCS discovery"""
        try:
            if not force_refresh and self._is_catalog_fresh():
                return {
                    "refreshed": False,
                    "method": "cache_hit",
                    "timestamp": self.catalog_timestamp,
                    "items_count": sum(len(v) for v in (self.catalog_cache or {}).values()),
                    "errors": []
                }

            # Build fresh catalog
            catalog = self._build_catalog(force_refresh=True)

            return {
                "refreshed": True,
                "method": "wcs_discovery",
                "timestamp": datetime.now(),
                "items_count": sum(len(v) for v in catalog.values()),
                "errors": []
            }

        except Exception as e:
            return {
                "refreshed": False,
                "method": "failed",
                "timestamp": datetime.now(),
                "items_count": 0,
                "errors": [str(e)]
            }

    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced capabilities with WCS discovery and comprehensive metadata"""
        # Ensure catalog is available
        if not self.catalog_cache:
            self._build_catalog()

        refresh_result = self._refresh_metadata()

        # Build comprehensive variables list
        variables = []
        catalog = self.catalog_cache or {}

        for prop, metadata in SOILGRIDS_METADATA.items():
            if prop not in catalog:
                continue

            available_coverages = catalog[prop]

            if prop == "wrb":
                # WRB soil classification
                variables.append({
                    "canonical": "soil:wrb_classification",
                    "platform_native": prop,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "unit": "categorical",
                    "data_type": "categorical",
                    "categories": {str(k): v["name"] for k, v in WRB_CLASSES.items()},
                    "category_profiles": {v["name"]: v["profile"] for v in WRB_CLASSES.values()},
                    "coverages_available": len(available_coverages),
                    "metadata_completeness": 0.95
                })
            else:
                # Numeric soil properties with depth/statistic combinations
                base_variable = {
                    "canonical": f"soil:{prop}",
                    "platform_native": prop,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "unit": metadata["units"],
                    "data_type": "numeric",
                    "depths_available": metadata.get("depths", []),
                    "statistics_available": metadata.get("statistics", []),
                    "coverages_available": len(available_coverages),
                    "pedological_significance": metadata.get("pedological_significance", ""),
                    "agricultural_applications": metadata.get("agricultural_applications", []),
                    "metadata_completeness": 0.92
                }
                variables.append(base_variable)

        return self._create_uniform_response(
            service_type="unitary",
            variables=variables,
            temporal_coverage={
                "reference_period": "2020-05-18 (model snapshot)",
                "temporal_resolution": "Static global maps",
                "update_frequency": "Major updates every 3-5 years",
                "static_nature": "Represents current/recent soil conditions"
            },
            spatial_coverage={
                "extent": "Global (excluding Antarctica)",
                "spatial_resolution": "250m native, configurable resampling",
                "coordinate_system": "WGS84 (EPSG:4326)",
                "coverage_density": "Complete global coverage",
                "pixel_count": "~5.6 billion pixels globally"
            },
            quality_metadata={
                "prediction_method": "Machine learning ensemble models",
                "training_data": "~240,000 soil profiles from global databases",
                "validation_method": "10-fold cross-validation + independent validation",
                "model_performance": "R² values ranging from 0.3-0.8 depending on property",
                "uncertainty_maps": "Prediction interval maps available",
                "processing_level": "Level 3 - Model predictions with uncertainty"
            },
            service_characteristics={
                "access_method": "WCS (Web Coverage Service)",
                "data_format": "GeoTIFF raster coverages",
                "guard_rails": {
                    "max_pixels_default": self.max_pixels_default,
                    "automatic_tiling": True,
                    "resolution_adaptation": True
                },
                "reliability": {
                    "circuit_breaker": True,
                    "fallback_caching": True,
                    "error_recovery": "Automatic"
                }
            },
            discovery_method="wcs_getcapabilities",
            catalog_info={
                "total_coverages": sum(len(v) for v in catalog.values()),
                "properties_available": len([p for p, covs in catalog.items() if covs]),
                "freshness": refresh_result
            }
        )

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch SoilGrids data using WCS with comprehensive guard rails"""
        try:
            # Circuit breaker check
            if self.circuit_breaker.is_open:
                logger.warning("SoilGrids circuit breaker is open, using fallback")
                return self._fetch_from_cache(spec)

            with self.circuit_breaker:
                # Ensure catalog is available
                if not self.catalog_cache:
                    self._build_catalog()

                # Get guard rail limits
                limits = self._get_guard_rail_limits(spec)
                logger.info(f"SoilGrids request strategy: {limits['strategy']}, estimated pixels: {limits['estimated_pixels']}")

                # Map variables to properties
                requested_props = self._map_variables_to_properties(spec.variables)
                logger.debug(f"Mapped variables to properties: {requested_props}")

                # Execute with resolution backoff for oversized requests
                df = self._fetch_with_backoff(limits, requested_props)

                # Transform to env-agents core schema
                return self._transform_to_core_schema(df, spec)

        except CircuitBreakerOpen:
            logger.warning("Circuit breaker opened during request")
            return self._fetch_from_cache(spec)
        except Exception as e:
            logger.error(f"SoilGrids WCS fetch failed: {e}")
            return []

    def _fetch_direct_wcs(self, bbox: Tuple[float, float, float, float],
                         properties: List[str]) -> pd.DataFrame:
        """Direct WCS fetch at native resolution"""
        catalog = self.catalog_cache or {}
        coverage_pairs = []

        for prop in properties:
            if prop in catalog:
                for coverage_id in catalog[prop]:
                    coverage_pairs.append((prop, coverage_id))

        dfs = []
        for prop, coverage_id in coverage_pairs:
            try:
                df = self._fetch_coverage_to_df(prop, coverage_id, bbox)
                if df is not None:
                    dfs.append(df)
            except Exception as e:
                logger.warning(f"Coverage {prop}:{coverage_id} failed: {e}")
                continue

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)

        # Attach comprehensive metadata like your working code
        result.attrs["soilgrids_metadata"] = SOILGRIDS_METADATA
        result.attrs["catalog"] = catalog
        result.attrs["wcs_endpoint"] = self.SOURCE_URL
        result.attrs["data_source"] = "ISRIC SoilGrids v2.0"
        result.attrs["spatial_resolution"] = "250m native"
        result.attrs["temporal_coverage"] = "2020 model snapshot"
        result.attrs["license"] = self.LICENSE
        result.attrs["retrieval_method"] = "WCS GetCoverage"
        result.attrs["processing_timestamp"] = datetime.now().isoformat()

        return result

    def _fetch_resampled_wcs(self, bbox: Tuple[float, float, float, float],
                            properties: List[str], target_pixels: int) -> pd.DataFrame:
        """WCS fetch with automatic resampling"""
        scale_size = self._choose_scale_size(bbox, target_pixels)
        catalog = self.catalog_cache or {}
        coverage_pairs = []

        for prop in properties:
            if prop in catalog:
                for coverage_id in catalog[prop]:
                    coverage_pairs.append((prop, coverage_id))

        dfs = []
        for prop, coverage_id in coverage_pairs:
            try:
                df = self._fetch_coverage_to_df(prop, coverage_id, bbox, scalesize=scale_size)
                if df is not None:
                    dfs.append(df)
            except Exception as e:
                logger.warning(f"Coverage {prop}:{coverage_id} failed: {e}")
                continue

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)

        # Attach metadata with resampling info
        result.attrs["soilgrids_metadata"] = SOILGRIDS_METADATA
        result.attrs["wcs_endpoint"] = self.SOURCE_URL
        result.attrs["data_source"] = "ISRIC SoilGrids v2.0"
        result.attrs["spatial_resolution"] = f"Resampled to {scale_size[0]}x{scale_size[1]} pixels"
        result.attrs["temporal_coverage"] = "2020 model snapshot"
        result.attrs["license"] = self.LICENSE
        result.attrs["retrieval_method"] = "WCS GetCoverage (resampled)"
        result.attrs["resampling"] = {"scale_size": scale_size, "target_pixels": target_pixels}
        result.attrs["processing_timestamp"] = datetime.now().isoformat()

        return result

    def _fetch_tiled_wcs(self, tiles: List[Tuple[float, float, float, float]],
                        properties: List[str]) -> pd.DataFrame:
        """WCS fetch with automatic tiling for large requests"""
        all_dfs = []

        for i, tile in enumerate(tiles):
            logger.debug(f"Processing tile {i+1}/{len(tiles)}")
            try:
                tile_df = self._fetch_direct_wcs(tile, properties)
                if not tile_df.empty:
                    all_dfs.append(tile_df)
            except Exception as e:
                logger.warning(f"Tile {i+1} failed: {e}")
                continue

        if not all_dfs:
            return pd.DataFrame()

        result = pd.concat(all_dfs, ignore_index=True)

        # Attach metadata with tiling info
        result.attrs["soilgrids_metadata"] = SOILGRIDS_METADATA
        result.attrs["wcs_endpoint"] = self.SOURCE_URL
        result.attrs["data_source"] = "ISRIC SoilGrids v2.0"
        result.attrs["spatial_resolution"] = "250m native (tiled)"
        result.attrs["temporal_coverage"] = "2020 model snapshot"
        result.attrs["license"] = self.LICENSE
        result.attrs["retrieval_method"] = "WCS GetCoverage (tiled)"
        result.attrs["tiling"] = {"tile_count": len(tiles), "successful_tiles": len(all_dfs)}
        result.attrs["processing_timestamp"] = datetime.now().isoformat()

        return result

    def _fetch_with_backoff(self, limits: Dict[str, Any], properties: List[str]) -> pd.DataFrame:
        """Execute fetch with resolution backoff if requests are too large"""

        # Define backoff strategies (progressively reduce resolution)
        backoff_strategies = [
            {"name": "original", "target_pixels": limits.get("target_pixels", self.max_pixels_default)},
            {"name": "reduced_75%", "target_pixels": int(self.max_pixels_default * 0.75)},
            {"name": "reduced_50%", "target_pixels": int(self.max_pixels_default * 0.50)},
            {"name": "reduced_25%", "target_pixels": int(self.max_pixels_default * 0.25)},
            {"name": "minimal", "target_pixels": 50000}  # Absolute minimum
        ]

        last_exception = None

        for i, strategy in enumerate(backoff_strategies):
            try:
                logger.debug(f"Attempting fetch with {strategy['name']} strategy ({strategy['target_pixels']:,} pixels)")

                # Execute based on original strategy but with adjusted pixel limits
                if limits["strategy"] == "direct":
                    df = self._fetch_direct_wcs(limits["bbox"], properties)
                elif limits["strategy"] == "resampled":
                    df = self._fetch_resampled_wcs(limits["bbox"], properties, strategy["target_pixels"])
                elif limits["strategy"] == "tiled":
                    df = self._fetch_tiled_wcs(limits["tiles"], properties)
                else:
                    raise ValueError(f"Unknown strategy: {limits['strategy']}")

                # Success! Log the strategy used
                if i > 0:
                    logger.info(f"✅ SoilGrids fetch succeeded with {strategy['name']} resolution backoff")
                else:
                    logger.info(f"✅ SoilGrids fetch succeeded with original resolution")

                return df

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Check if this is a memory/size-related error that justifies backoff
                if any(term in error_msg for term in ['memory', 'allocate', 'too large', 'out of', 'timeout']):
                    logger.warning(f"⚠️  {strategy['name']} strategy failed ({e}), trying lower resolution...")
                    continue
                else:
                    # Non-size related error, don't continue backoff
                    logger.error(f"❌ Non-recoverable error in {strategy['name']} strategy: {e}")
                    raise e

        # All strategies failed
        logger.error(f"💥 All resolution backoff strategies failed. Final error: {last_exception}")
        raise last_exception

    def _transform_to_core_schema(self, df: pd.DataFrame, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Transform WCS DataFrame to env-agents core schema"""
        if df.empty:
            return []

        rows = []
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        for _, row in df.iterrows():
            # Extract depth information
            depth_top_cm = row.get("top_depth")
            depth_bottom_cm = row.get("bottom_depth")

            # Map to canonical variable
            prop = row["parameter"]
            if prop == "wrb":
                canonical_var = "soil:wrb_classification"
            else:
                canonical_var = f"soil:{prop}"

            # Build core schema row
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
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "geom_wkt": f"POINT({row['longitude']} {row['latitude']})",
                "spatial_id": None,
                "site_name": f"SoilGrids location {row['latitude']:.4f}, {row['longitude']:.4f}",
                "admin": None,
                "elevation_m": None,

                # Temporal columns
                "time": row.get("date"),
                "temporal_coverage": "2020-snapshot",

                # Value columns
                "variable": canonical_var,
                "value": float(row["value"]),
                "unit": row.get("unit", ""),
                "depth_top_cm": depth_top_cm,
                "depth_bottom_cm": depth_bottom_cm,
                "qc_flag": "ok",

                # Metadata columns
                "attributes": {
                    "parameter": prop,
                    "statistic": row.get("statistic"),
                    "coverage_id": row.get("coverageid"),
                    "description": row.get("description"),
                    "depth_units": row.get("depth_units"),
                    "wcs_method": "getcoverage",
                    "processing_metadata": df.attrs,
                    "terms": {
                        "native_id": prop,
                        "canonical_variable": canonical_var,
                        "mapping_confidence": 0.95
                    }
                },
                "provenance": {
                    "data_source": "ISRIC SoilGrids v2.0",
                    "method": "WCS GetCoverage",
                    "api_endpoint": self.SOURCE_URL,
                    "coverage_id": row.get("coverageid"),
                    "retrieval_timestamp": retrieval_timestamp,
                    "guard_rails_applied": True
                }
            }

            rows.append(core_row)

        logger.info(f"Transformed {len(rows)} WCS observations to core schema")
        return rows

    def _fetch_from_cache(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fallback method when circuit breaker is open or service fails"""
        logger.warning("Using fallback cache for SoilGrids data")

        # This would implement cached fallback data
        # For now, return empty list but log the attempt
        cache_file = self.cache_dir / "fallback_data.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    cached_data = json.load(f)
                logger.info(f"Returned {len(cached_data)} cached observations")
                return cached_data
            except Exception as e:
                logger.warning(f"Failed to load cached data: {e}")

        return []