"""
Lean Production Earth Engine Adapter

Simple, fast adapter for production data acquisition.
No web scraping, no visualization, no unnecessary metadata.
Just: authenticate once, query EE, return data.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading

from ..base import BaseAdapter
from ...core.models import RequestSpec
from ...core.config import get_config

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when Earth Engine query times out"""
    pass


def run_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
    """
    Run a function with a timeout using threading.
    Returns (result, exception) tuple.

    Note: This uses daemon threads which will be killed if they timeout.
    Earth Engine queries that timeout will be abandoned.
    """
    if kwargs is None:
        kwargs = {}

    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)

    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Earth Engine query exceeded {timeout_sec}s timeout")

    if exception[0]:
        raise exception[0]

    return result[0]

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    ee = None

# Module-level singleton for authentication (authenticate once per process)
_EE_AUTHENTICATED = False


def _ensure_ee_authenticated():
    """Authenticate Earth Engine once per process (singleton pattern)"""
    global _EE_AUTHENTICATED

    if _EE_AUTHENTICATED:
        return

    if not EE_AVAILABLE:
        raise ImportError("Earth Engine library required: pip install earthengine-api")

    try:
        # Test if already authenticated
        ee.data.getAssetRoots()
        _EE_AUTHENTICATED = True
        logger.debug("Earth Engine already authenticated")  # DEBUG level - only show if verbose
        return
    except:
        pass

    # Search for service account key in standard locations
    credentials_path = None
    search_paths = [
        'config/ecognita-470619-e9e223ea70a7.json',
        '../config/ecognita-470619-e9e223ea70a7.json',
        '../../config/ecognita-470619-e9e223ea70a7.json',
        Path.cwd() / "config",
        Path.cwd().parent / "config"
    ]

    for path_attempt in search_paths:
        if isinstance(path_attempt, str):
            test_path = Path(path_attempt)
        else:
            # It's a Path directory, search for JSON files
            test_path = path_attempt
            if test_path.exists() and test_path.is_dir():
                for json_file in test_path.glob("*.json"):
                    if json_file.exists():
                        credentials_path = str(json_file)
                        break
            continue

        if test_path.exists():
            credentials_path = str(test_path)
            break

    if credentials_path:
        # Service account authentication
        credentials = ee.ServiceAccountCredentials(email=None, key_file=str(credentials_path))
        ee.Initialize(credentials)
        _EE_AUTHENTICATED = True
        logger.debug(f"Earth Engine authenticated from {Path(credentials_path).name}")  # DEBUG: just filename
    else:
        # User authentication fallback
        try:
            ee.Initialize()
            _EE_AUTHENTICATED = True
            logger.debug("Earth Engine authenticated with user credentials")  # DEBUG level
        except Exception as e:
            raise RuntimeError(f"Earth Engine authentication failed: {e}")


class ProductionEarthEngineAdapter(BaseAdapter):
    """
    Lean production Earth Engine adapter

    Designed for high-throughput data acquisition with minimal overhead.
    No web scraping, no visualization, no unnecessary API calls.
    """

    DATASET = "EARTH_ENGINE"
    SOURCE_URL = "https://earthengine.google.com"
    SOURCE_VERSION = "Production v1.0"
    LICENSE = "Various - see individual asset licenses"

    # Class-level metadata cache (shared across all instances)
    _METADATA_CACHE = {}

    def __init__(self, asset_id: Optional[str] = None, scale: int = 500):
        """
        Initialize lean Earth Engine adapter

        Args:
            asset_id: Earth Engine asset ID (e.g., "USGS/SRTMGL1_003") - optional for compatibility
            scale: Scale in meters for analysis (default: 500m)
        """
        super().__init__()

        # Note: asset_id is optional in signature for compatibility with gold_standard adapter,
        # but is required for actual data fetching
        self.asset_id = asset_id
        self.scale = scale

        if not self.asset_id:
            # Allow initialization without asset_id (for compatibility with old notebooks)
            # but _fetch_rows will fail if called without asset_id
            return

        # Authenticate once per process (singleton)
        _ensure_ee_authenticated()

    def _get_asset_type(self) -> str:
        """Get asset type (Image, ImageCollection, etc.) with caching"""
        if self.asset_id in self._METADATA_CACHE:
            return self._METADATA_CACHE[self.asset_id]["type"]

        try:
            # Try as ImageCollection first (most common) - with timeout
            run_with_timeout(
                lambda: ee.ImageCollection(self.asset_id).limit(1).getInfo(),
                timeout_sec=20
            )
            asset_type = "ImageCollection"
        except:
            try:
                # Try as Image - with timeout
                run_with_timeout(
                    lambda: ee.Image(self.asset_id).getInfo(),
                    timeout_sec=20
                )
                asset_type = "Image"
            except:
                # Default to Image if both fail
                asset_type = "Image"

        self._METADATA_CACHE[self.asset_id] = {"type": asset_type}
        return asset_type

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict]:
        """
        Fetch Earth Engine data with minimal overhead

        Returns list of dicts matching env-agents core schema
        """
        # Parse geometry
        if spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
            buffer = 0.005  # Small buffer for point queries (~500m at equator)
            bbox = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]
        elif spec.geometry.type == "bbox":
            bbox = list(spec.geometry.coordinates)
        else:
            raise ValueError(f"Unsupported geometry type: {spec.geometry.type}")

        region = ee.Geometry.Rectangle(bbox)
        center_lat = (bbox[1] + bbox[3]) / 2
        center_lon = (bbox[0] + bbox[2]) / 2

        # Parse time range
        start_date, end_date = spec.time_range or ("2020-01-01", "2020-12-31")

        # Get asset type (cached)
        asset_type = self._get_asset_type()

        # Query based on asset type
        if asset_type == "ImageCollection":
            return self._query_image_collection(region, bbox, center_lat, center_lon, start_date, end_date)
        else:
            return self._query_image(region, bbox, center_lat, center_lon, start_date)

    def _query_image(self, region, bbox: list, center_lat: float, center_lon: float, date: str) -> List[Dict]:
        """Query single Image asset"""
        img = ee.Image(self.asset_id).clip(region)

        # Use modest maxPixels for speed (not 1e13!)
        # Wrap getInfo() with timeout to prevent hanging
        def get_stats():
            return img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=self.scale,
                maxPixels=1e9
            ).getInfo()

        try:
            stats = run_with_timeout(get_stats, timeout_sec=60)
        except TimeoutError as e:
            raise Exception(f"Earth Engine timeout: {e}") from e

        # Build WKT from bbox we already have (no .getInfo() needed!)
        minlon, minlat, maxlon, maxlat = bbox
        wkt = f"POLYGON(({minlon} {minlat}, {maxlon} {minlat}, {maxlon} {maxlat}, {minlon} {maxlat}, {minlon} {minlat}))"

        # Convert to standard schema
        rows = []
        for variable, value in stats.items():
            if value is not None:
                rows.append({
                    "observation_id": f"ee_{self.asset_id.replace('/', '_')}_{date}_{variable}",
                    "dataset": self.DATASET,
                    "source_url": self.SOURCE_URL,
                    "source_version": self.SOURCE_VERSION,
                    "license": self.LICENSE,
                    "retrieval_timestamp": datetime.now(),
                    "geometry_type": "bbox",
                    "latitude": center_lat,
                    "longitude": center_lon,
                    "geom_wkt": wkt,
                    "time": date,
                    "variable": f"ee:{variable}",
                    "value": float(value),
                    "unit": "",
                    "qc_flag": "ok",
                    "attributes": {
                        "asset_id": self.asset_id,
                        "scale_m": self.scale
                    }
                })

        return rows

    def _query_image_collection(self, region, bbox: list, center_lat: float, center_lon: float,
                                start_date: str, end_date: str) -> List[Dict]:
        """Query ImageCollection asset with automatic temporal fallback"""

        # Store original requested dates for metadata
        requested_start = start_date
        requested_end = end_date
        fallback_applied = False
        fallback_reason = None

        # First attempt: try requested date range
        ic = ee.ImageCollection(self.asset_id).filterDate(start_date, end_date).filterBounds(region)

        # Check if we have any images
        def check_size():
            return ic.size().getInfo()

        try:
            count = run_with_timeout(check_size, timeout_sec=30)
        except TimeoutError as e:
            raise Exception(f"Earth Engine timeout (checking image count): {e}") from e

        # If no images found, try temporal fallback
        if count == 0:
            logger.warning(f"No images found for {self.asset_id} in {start_date} to {end_date}, attempting temporal fallback")
            fallback_applied = True

            # Get collection's actual date range
            full_collection = ee.ImageCollection(self.asset_id).filterBounds(region)

            def get_date_range():
                dates = full_collection.aggregate_array('system:time_start').getInfo()
                if not dates:
                    return None, None
                import datetime
                min_ts = min(dates)
                max_ts = max(dates)
                min_date = datetime.datetime.fromtimestamp(min_ts / 1000).strftime('%Y-%m-%d')
                max_date = datetime.datetime.fromtimestamp(max_ts / 1000).strftime('%Y-%m-%d')
                return min_date, max_date

            try:
                available_start, available_end = run_with_timeout(get_date_range, timeout_sec=30)
            except TimeoutError as e:
                raise Exception(f"Earth Engine timeout (getting date range): {e}") from e

            if not available_start or not available_end:
                logger.warning(f"No images found for {self.asset_id} at this location")
                return []

            # Use most recent year available if requested date is too late
            if requested_start > available_end:
                fallback_reason = f"requested_date_{requested_start}_after_dataset_end_{available_end}"
                # Use most recent year
                end_year = available_end[:4]
                start_date = f"{end_year}-01-01"
                end_date = f"{end_year}-12-31"
                logger.info(f"Falling back to most recent year: {start_date} to {end_date}")
            # Use oldest year available if requested date is too early
            elif requested_end < available_start:
                fallback_reason = f"requested_date_{requested_end}_before_dataset_start_{available_start}"
                start_year = available_start[:4]
                start_date = f"{start_year}-01-01"
                end_date = f"{start_year}-12-31"
                logger.info(f"Falling back to oldest year: {start_date} to {end_date}")
            else:
                # Requested range overlaps with available range, use available range
                fallback_reason = f"no_data_in_requested_range_using_available_{available_start}_to_{available_end}"
                start_date = available_start
                end_date = available_end
                logger.info(f"Using full available range: {start_date} to {end_date}")

            # Re-filter with fallback dates
            ic = ee.ImageCollection(self.asset_id).filterDate(start_date, end_date).filterBounds(region)

            # Check again
            try:
                count = run_with_timeout(check_size, timeout_sec=30)
            except TimeoutError as e:
                raise Exception(f"Earth Engine timeout (checking fallback count): {e}") from e

            if count == 0:
                logger.warning(f"No images found even after fallback for {self.asset_id}")
                return []

        # Get band names from first image (with timeout)
        def get_bands():
            first_img = ic.first()
            return first_img.bandNames().getInfo()

        try:
            band_names = run_with_timeout(get_bands, timeout_sec=30)
        except TimeoutError as e:
            raise Exception(f"Earth Engine timeout (metadata fetch): {e}") from e
        except Exception as e:
            # Handle "image is null" errors more gracefully
            if "is required and may not be null" in str(e):
                logger.warning(f"No valid images found for {self.asset_id} after filtering")
                return []
            raise

        if not band_names:
            return []

        # Time series extraction using reduceRegion
        def reduce_img(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=self.scale,
                maxPixels=1e9
            )
            return ee.Feature(None, stats).set("date", img.date().format("YYYY-MM-dd"))

        reduced = ic.map(reduce_img)

        # Filter out images with no data for first band
        reduced = reduced.filter(ee.Filter.notNull([band_names[0]]))

        # Get results (with timeout)
        def get_features():
            return reduced.getInfo()["features"]

        try:
            features = run_with_timeout(get_features, timeout_sec=90)
        except TimeoutError as e:
            raise Exception(f"Earth Engine timeout (data fetch): {e}") from e

        # Convert to standard schema with temporal fallback metadata
        rows = []
        for feat in features:
            props = feat["properties"]
            date = props.pop("date", None)

            if date:
                for variable, value in props.items():
                    if value is not None:
                        # Build attributes with temporal metadata
                        attributes = {
                            "asset_id": self.asset_id,
                            "scale_m": self.scale,
                            "requested_date_range": f"{requested_start}_to_{requested_end}",
                            "actual_date_range": f"{start_date}_to_{end_date}"
                        }

                        # Add fallback metadata if applicable
                        if fallback_applied:
                            attributes["temporal_fallback_applied"] = True
                            attributes["temporal_fallback_reason"] = fallback_reason
                        else:
                            attributes["temporal_fallback_applied"] = False

                        rows.append({
                            "observation_id": f"ee_{self.asset_id.replace('/', '_')}_{date}_{variable}",
                            "dataset": self.DATASET,
                            "source_url": self.SOURCE_URL,
                            "source_version": self.SOURCE_VERSION,
                            "license": self.LICENSE,
                            "retrieval_timestamp": datetime.now(),
                            "geometry_type": "bbox",
                            "latitude": center_lat,
                            "longitude": center_lon,
                            "geom_wkt": f"POINT({center_lon} {center_lat})",  # Simplified for collection
                            "time": date,
                            "variable": f"ee:{variable}",
                            "value": float(value),
                            "unit": "",
                            "qc_flag": "ok",
                            "attributes": attributes
                        })

        return rows

    def capabilities(self) -> Dict[str, Any]:
        """Return basic capabilities"""
        asset_type = self._get_asset_type()

        # Try to get band names
        try:
            if asset_type == "ImageCollection":
                ic = ee.ImageCollection(self.asset_id).limit(1)
                band_names = ic.first().bandNames().getInfo()
            else:
                img = ee.Image(self.asset_id)
                band_names = img.bandNames().getInfo()
        except:
            band_names = []

        variables = [{"name": f"ee:{band}", "description": band} for band in band_names]

        return {
            "dataset": self.DATASET,
            "asset_id": self.asset_id,
            "asset_type": asset_type,
            "variables": variables,
            "spatial_coverage": "Global",
            "requires_auth": True
        }