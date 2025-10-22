"""
Lean Production Earth Engine Adapter

Simple, fast adapter for production data acquisition.
No web scraping, no visualization, no unnecessary metadata.
Just: authenticate once, query EE, return data.

Grid Sampling: Returns multiple spatially-distributed samples within
bounding boxes to capture environmental gradients.
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
from .spatial_sampling import (
    calculate_sample_count,
    generate_sample_grid,
    should_use_grid_sampling
)

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
        'credentials/ecognita-470619-e9e223ea70a7.json',
        'config/ecognita-470619-e9e223ea70a7.json',
        '../credentials/ecognita-470619-e9e223ea70a7.json',
        '../config/ecognita-470619-e9e223ea70a7.json',
        '../../credentials/ecognita-470619-e9e223ea70a7.json',
        '../../config/ecognita-470619-e9e223ea70a7.json',
        Path.cwd() / "credentials",
        Path.cwd().parent / "credentials",
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
                # Check if it's an unsupported type (FeatureCollection/Table)
                try:
                    asset_info = ee.data.getAsset(self.asset_id)
                    actual_type = asset_info.get('type', 'UNKNOWN')

                    if actual_type in ['FeatureCollection', 'TABLE', 'Table']:
                        raise ValueError(
                            f"Asset '{self.asset_id}' is type '{actual_type}', which is not supported. "
                            f"This adapter only supports Image and ImageCollection (raster) assets. "
                            f"Vector/Table assets require different query methods."
                        )
                except ValueError:
                    # Re-raise ValueError (unsupported type)
                    raise
                except:
                    # Other errors, default to Image
                    logger.warning(f"Could not determine asset type for {self.asset_id}, defaulting to Image")

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
            return self._query_image_collection(region, bbox, center_lat, center_lon, start_date, end_date, spec)
        else:
            return self._query_image(region, bbox, center_lat, center_lon, start_date, spec)

    def _query_image(self, region, bbox: list, center_lat: float, center_lon: float, date: str, spec: RequestSpec) -> List[Dict]:
        """
        Query single Image asset with grid sampling support.

        Returns multiple samples within bbox to capture spatial gradients
        instead of single aggregated value.
        """
        img = ee.Image(self.asset_id).clip(region)

        # Determine if we should use grid sampling
        use_grid = should_use_grid_sampling(spec, default_enabled=True)

        if not use_grid:
            # Legacy behavior: single aggregated value
            return self._query_image_aggregated(img, bbox, center_lat, center_lon, date)

        # Grid sampling: multiple samples to capture gradients
        return self._query_image_grid(img, bbox, date, spec)

    def _query_image_aggregated(self, img, bbox: list, center_lat: float, center_lon: float, date: str) -> List[Dict]:
        """Query image with aggregation (legacy behavior for resolution='low')"""
        region = ee.Geometry.Rectangle(bbox)

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

        # Build WKT
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
                        "scale_m": self.scale,
                        "spatial_aggregation": {
                            "method": "mean",
                            "bbox": bbox,
                            "n_samples": 1
                        }
                    }
                })

        return rows

    def _query_image_grid(self, img, bbox: list, date: str, spec: RequestSpec) -> List[Dict]:
        """Query image at multiple grid points to capture spatial gradients"""
        # Calculate appropriate sample count
        max_samples = spec.extra.get("max_samples", 100) if spec.extra else 100
        n_samples, n_side, sampling_metadata = calculate_sample_count(
            bbox, self.scale, spec.resolution, max_samples
        )

        # Generate sample points
        sample_points = generate_sample_grid(bbox, n_side)

        # Query each sample point
        rows = []
        for i, (lat, lon) in enumerate(sample_points):
            point = ee.Geometry.Point([lon, lat])

            # Sample at this point
            def get_sample():
                return img.reduceRegion(
                    reducer=ee.Reducer.first(),  # Get pixel value at point
                    geometry=point,
                    scale=self.scale,
                    bestEffort=True  # Allow EE to use appropriate pixel count
                ).getInfo()

            try:
                values = run_with_timeout(get_sample, timeout_sec=30)
            except TimeoutError:
                logger.warning(f"Timeout sampling point {i+1}/{n_samples} at ({lat:.4f}, {lon:.4f})")
                continue
            except Exception as e:
                logger.warning(f"Error sampling point {i+1}/{n_samples}: {e}")
                continue

            # Create row for each variable at this location
            for variable, value in values.items():
                if value is not None:
                    rows.append({
                        "observation_id": f"ee_{self.asset_id.replace('/', '_')}_{date}_{variable}_{i}",
                        "dataset": self.DATASET,
                        "source_url": self.SOURCE_URL,
                        "source_version": self.SOURCE_VERSION,
                        "license": self.LICENSE,
                        "retrieval_timestamp": datetime.now(),
                        "geometry_type": "point",
                        "latitude": lat,
                        "longitude": lon,
                        "geom_wkt": f"POINT({lon} {lat})",
                        "time": date,
                        "variable": f"ee:{variable}",
                        "value": float(value),
                        "unit": "",
                        "qc_flag": "ok",
                        "attributes": {
                            "asset_id": self.asset_id,
                            "scale_m": self.scale,
                            "spatial_sampling": sampling_metadata,
                            "sample_index": i,
                            "grid_position": f"{i // n_side},{i % n_side}"
                        }
                    })

        return rows

    def _query_image_collection(self, region, bbox: list, center_lat: float, center_lon: float,
                                start_date: str, end_date: str, spec: RequestSpec) -> List[Dict]:
        """
        Query ImageCollection asset with grid sampling support.

        Supports both aggregated (legacy) and grid sampling modes based on spec.resolution.
        Grid sampling captures spatial gradients at each time step.
        """

        # Determine if we should use grid sampling
        use_grid = should_use_grid_sampling(spec, default_enabled=True)

        if not use_grid:
            # Legacy behavior: single aggregated value per time step
            return self._query_image_collection_aggregated(
                region, bbox, center_lat, center_lon, start_date, end_date, spec
            )

        # Grid sampling: multiple spatial samples per time step
        return self._query_image_collection_grid(
            region, bbox, start_date, end_date, spec
        )

    def _query_image_collection_aggregated(self, region, bbox: list, center_lat: float, center_lon: float,
                                          start_date: str, end_date: str, spec: RequestSpec) -> List[Dict]:
        """
        Query ImageCollection with aggregation (legacy behavior for resolution='low').

        Returns single aggregated value at bbox centroid for each time step.
        """

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
                # Efficient approach: get first and last image instead of all timestamps
                first_img = full_collection.sort('system:time_start').first()
                last_img = full_collection.sort('system:time_start', False).first()

                try:
                    first_date = ee.Date(first_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    last_date = ee.Date(last_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    return first_date, last_date
                except Exception:
                    return None, None

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

    def _query_image_collection_grid(self, region, bbox: list, start_date: str, end_date: str,
                                     spec: RequestSpec) -> List[Dict]:
        """
        Query ImageCollection at multiple grid points to capture spatial gradients.

        For each time step, samples at multiple spatial locations within the bbox.
        Returns: N_time_steps × N_spatial_samples rows.
        """

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

        # If no images found, try temporal fallback (same logic as aggregated method)
        if count == 0:
            logger.warning(f"No images found for {self.asset_id} in {start_date} to {end_date}, attempting temporal fallback")
            fallback_applied = True

            # Get collection's actual date range
            full_collection = ee.ImageCollection(self.asset_id).filterBounds(region)

            def get_date_range():
                # Efficient approach: get first and last image instead of all timestamps
                first_img = full_collection.sort('system:time_start').first()
                last_img = full_collection.sort('system:time_start', False).first()

                try:
                    first_date = ee.Date(first_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    last_date = ee.Date(last_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    return first_date, last_date
                except Exception:
                    return None, None

            try:
                available_start, available_end = run_with_timeout(get_date_range, timeout_sec=30)
            except TimeoutError as e:
                raise Exception(f"Earth Engine timeout (getting date range): {e}") from e

            if not available_start or not available_end:
                logger.warning(f"No images found for {self.asset_id} at this location")
                return []

            # Apply temporal fallback logic
            if requested_start > available_end:
                fallback_reason = f"requested_date_{requested_start}_after_dataset_end_{available_end}"
                end_year = available_end[:4]
                start_date = f"{end_year}-01-01"
                end_date = f"{end_year}-12-31"
                logger.info(f"Falling back to most recent year: {start_date} to {end_date}")
            elif requested_end < available_start:
                fallback_reason = f"requested_date_{requested_end}_before_dataset_start_{available_start}"
                start_year = available_start[:4]
                start_date = f"{start_year}-01-01"
                end_date = f"{start_year}-12-31"
                logger.info(f"Falling back to oldest year: {start_date} to {end_date}")
            else:
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

        # Calculate appropriate sample count and generate grid
        max_samples = spec.extra.get("max_samples", 100) if spec.extra else 100

        # Adaptive spatial sampling: reduce grid size for high-frequency collections
        # This prevents memory issues and 5000-element limit
        if count > 100:  # Daily or more frequent data
            # Reduce to 3×3 (9 points) instead of 5×5 (25 points)
            adaptive_max_samples = min(max_samples, 9)
            logger.info(f"High-frequency collection ({count} images): reducing spatial sampling to {adaptive_max_samples} points")
        else:
            adaptive_max_samples = max_samples

        n_samples, n_side, sampling_metadata = calculate_sample_count(
            bbox, self.scale, spec.resolution, adaptive_max_samples
        )

        # Generate sample points
        sample_points = generate_sample_grid(bbox, n_side)

        logger.info(f"Grid sampling ImageCollection (server-side batching): {n_samples} spatial points × {count} time steps = {n_samples * count} total samples")

        # Check if temporal batching is needed for high-frequency collections
        # Earth Engine has limits: ~5000 features in flattened FeatureCollection
        # Conservative threshold: If n_samples * count > 1000, use temporal batching
        needs_batching = (n_samples * count) > 1000

        if needs_batching:
            # Calculate batch size to keep each batch well under 5000-element limit
            # Target ~800 samples per batch (leaves safety margin)
            max_images_per_batch = max(10, 800 // n_samples)  # At least 10 images per batch
            logger.info(f"Using temporal batching: {max_images_per_batch} images per batch (total: {count} images)")

        # Create FeatureCollection from grid points for server-side processing
        features = []
        for spatial_idx, (lat, lon) in enumerate(sample_points):
            features.append(
                ee.Feature(
                    ee.Geometry.Point([lon, lat]),
                    {
                        'lat': lat,
                        'lon': lon,
                        'spatial_idx': spatial_idx,
                        'grid_position': f"{spatial_idx // n_side},{spatial_idx % n_side}"
                    }
                )
            )
        points_fc = ee.FeatureCollection(features)

        # Sample all points across all images using server-side operations
        def sample_image(img):
            """Sample all grid points for a single image"""
            return img.sampleRegions(
                collection=points_fc,
                scale=self.scale,
                geometries=True
            ).map(lambda f: f.set({
                'time': img.date().format('YYYY-MM-dd'),
                'system_time_start': img.get('system:time_start')
            }))

        # Process in batches if needed
        all_samples = {'features': []}

        if needs_batching:
            # Split collection into temporal batches
            num_batches = (count + max_images_per_batch - 1) // max_images_per_batch

            for batch_idx in range(num_batches):
                batch_start = batch_idx * max_images_per_batch
                batch_end = min(batch_start + max_images_per_batch, count)

                logger.info(f"Processing batch {batch_idx + 1}/{num_batches}: images {batch_start} to {batch_end}")

                # Get batch of images
                batch_ic = ee.ImageCollection(ic.toList(batch_end, batch_start))

                # Map and flatten for this batch
                batch_samples_fc = batch_ic.map(sample_image).flatten()

                # Fetch this batch
                def get_batch_samples():
                    return batch_samples_fc.getInfo()

                try:
                    batch_samples = run_with_timeout(get_batch_samples, timeout_sec=120)  # 2 min per batch
                    if 'features' in batch_samples:
                        all_samples['features'].extend(batch_samples['features'])
                except TimeoutError as e:
                    logger.warning(f"Timeout on batch {batch_idx + 1}, skipping: {e}")
                    continue
        else:
            # Process all at once (original behavior for smaller queries)
            all_samples_fc = ic.map(sample_image).flatten()

            # Single API call to fetch all samples
            def get_all_samples():
                return all_samples_fc.getInfo()

            try:
                all_samples = run_with_timeout(get_all_samples, timeout_sec=300)  # 5 min timeout for large queries
            except TimeoutError as e:
                raise Exception(f"Earth Engine timeout (fetching grid samples): {e}") from e

        # Transform FeatureCollection to rows format
        rows = []
        if 'features' in all_samples:
            for feature in all_samples['features']:
                props = feature['properties']

                # Extract coordinates and metadata
                lat = props.get('lat')
                lon = props.get('lon')
                spatial_idx = props.get('spatial_idx')
                grid_pos = props.get('grid_position')
                date = props.get('time')

                # Create row for each variable
                for variable, value in props.items():
                    # Skip metadata fields
                    if variable in ['lat', 'lon', 'spatial_idx', 'grid_position', 'time', 'system_time_start']:
                        continue

                    if value is not None:
                        # Build attributes with both spatial and temporal metadata
                        attributes = {
                            "asset_id": self.asset_id,
                            "scale_m": self.scale,
                            "spatial_sampling": sampling_metadata,
                            "sample_index": spatial_idx,
                            "grid_position": grid_pos,
                            "requested_date_range": f"{requested_start}_to_{requested_end}",
                            "actual_date_range": f"{start_date}_to_{end_date}",
                            "sampling_method": "server_side_batch"
                        }

                        # Add fallback metadata if applicable
                        if fallback_applied:
                            attributes["temporal_fallback_applied"] = True
                            attributes["temporal_fallback_reason"] = fallback_reason
                        else:
                            attributes["temporal_fallback_applied"] = False

                        rows.append({
                            "observation_id": f"ee_{self.asset_id.replace('/', '_')}_{date}_{variable}_{spatial_idx}",
                            "dataset": self.DATASET,
                            "source_url": self.SOURCE_URL,
                            "source_version": self.SOURCE_VERSION,
                            "license": self.LICENSE,
                            "retrieval_timestamp": datetime.now(),
                            "geometry_type": "point",
                            "latitude": lat,
                            "longitude": lon,
                            "geom_wkt": f"POINT({lon} {lat})",
                            "time": date,
                            "variable": f"ee:{variable}",
                            "value": float(value),
                            "unit": "",
                            "qc_flag": "ok",
                            "attributes": attributes
                        })

        logger.info(f"Grid sampling complete (server-side batch): {len(rows)} total observations")
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