from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import time
import requests
import logging
from datetime import datetime, timezone
try:
    from shapely import wkt
except Exception:
    wkt = None

from ..base import BaseAdapter
from ...core.models import RequestSpec
from ...core.cache import global_cache
from ...core.adapter_mixins import StandardAdapterMixin
from ...core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)

class OpenAQAdapter(BaseAdapter, StandardAdapterMixin):
    DATASET = "OpenAQ"
    SOURCE_URL = "https://api.openaq.org/v3"
    SOURCE_VERSION = "v3"
    LICENSE = "https://docs.openaq.org/about/about#terms-of-use"
    REQUIRES_API_KEY = True

    _PARAM_CACHE: Optional[List[Dict[str, Any]]] = None
    
    def __init__(self):
        """Initialize OpenAQ adapter with standard components"""
        super().__init__()

        # Initialize standard components (auth, config, logging)
        self.initialize_adapter()

        # OpenAQ-specific initialization
        self.cache = global_cache.get_service_cache(self.DATASET)

        # Rate limiting: Add delay between requests to prevent 429 errors
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests (increased from 500ms)

    def _rate_limited_get(self, url, **kwargs):
        """Make GET request with rate limiting to prevent 429 errors"""
        import time

        # Ensure minimum time between requests
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)

        self._last_request_time = time.time()
        return self._session.get(url, **kwargs)

    def _get_api_key(self, extra: Optional[Dict[str, Any]]) -> str:
        import os
        from ...core.config import get_config
        
        # Try extra parameters first
        key = (extra or {}).get("openaq_api_key")
        if key and key != "demo_missing":
            return key
        
        # Try unified configuration system
        try:
            config = get_config()
            credentials = config.get_service_credentials("OpenAQ")
            if "api_key" in credentials:
                return credentials["api_key"]
        except Exception:
            pass
        
        # Fallback to environment variable
        key = os.getenv("OPENAQ_API_KEY")
        if key:
            return key
            
        raise RuntimeError("OpenAQ v3 requires X-API-Key. Configure in config/credentials.yaml, provide extra={'openaq_api_key':'...'} or set OPENAQ_API_KEY.")
        

    def _openaq_parameter_catalog(self, headers: dict) -> List[Dict[str, Any]]:
        """Get parameter catalog with caching support"""
        # Try cache first
        try:
            cached_params = self.cache.get_or_fetch(
                "parameter_catalog",
                lambda: self._fetch_parameter_catalog(headers),
                "metadata",
                ttl=3600  # 1 hour TTL for parameter catalog
            )
            if cached_params:
                return cached_params
        except Exception:
            pass
            
        # Fall back to class-level cache
        if OpenAQAdapter._PARAM_CACHE is not None:
            return OpenAQAdapter._PARAM_CACHE
            
        # Fetch fresh data
        return self._fetch_parameter_catalog(headers)
    
    def _fetch_parameter_catalog(self, headers: dict) -> List[Dict[str, Any]]:
        """Fetch parameter catalog from OpenAQ API"""

        try:
            out: List[Dict[str, Any]] = []
            page = 1
            while True:
                r = self._rate_limited_get(f"{self.SOURCE_URL}/parameters", params={"page": page, "limit": 200}, headers=headers, timeout=60)
                if r.status_code >= 500:
                    self.logger.warning(f"Server error {r.status_code}, retrying...")
                    time.sleep(0.8)
                    r = self._rate_limited_get(f"{self.SOURCE_URL}/parameters", params={"page": page, "limit": 200}, headers=headers, timeout=60)
                if r.status_code == 401:
                    self.logger.debug(f"OpenAQ API key required for parameter catalog")
                    # Return fallback parameters
                    return self._get_fallback_parameters()
                r.raise_for_status()
                js = r.json()
                out.extend(js.get("results", []))
                meta = js.get("meta", {})
                p, limit, found = meta.get("page", page), meta.get("limit", 200), meta.get("found", 0)
                if isinstance(found, str) and found.startswith(">"):
                    found = int(found[1:])
                if p * limit >= (found or 0):
                    break
                page += 1

            norm = []
            for it in out:
                name = it.get("name")
                units = it.get("units") or it.get("unit") or ""
                display_name = it.get("displayName") or name
                description = it.get("description") or f"{name} air quality parameter"
                if not name:
                    continue
                norm.append({
                    "name": name, 
                    "units": units,
                    "displayName": display_name,
                    "description": description
                })
            OpenAQAdapter._PARAM_CACHE = norm
            return norm
            
        except Exception as e:
            self.logger.error(f"Failed to fetch OpenAQ parameter catalog: {e}")
            return self._get_fallback_parameters()
    
    def _get_fallback_parameters(self) -> List[Dict[str, Any]]:
        """Return fallback parameters when API is unavailable"""
        return [
            {"name": "pm25", "units": "µg/m³", "displayName": "PM2.5"},
            {"name": "pm10", "units": "µg/m³", "displayName": "PM10"},
            {"name": "o3", "units": "µg/m³", "displayName": "Ozone"},
            {"name": "no2", "units": "µg/m³", "displayName": "Nitrogen Dioxide"},
            {"name": "so2", "units": "µg/m³", "displayName": "Sulfur Dioxide"},
            {"name": "co", "units": "mg/m³", "displayName": "Carbon Monoxide"},
            {"name": "bc", "units": "µg/m³", "displayName": "Black Carbon"}
        ]

    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> dict:
        # Discover live parameter catalog
        try:
            headers = {"X-API-Key": self._get_api_key(extra)}
            catalog = self._openaq_parameter_catalog(headers)  # returns [{'name','units','displayName'}, ...]
            vars_list = [
                {
                    "canonical": f"air:{p['name']}",
                    "platform": p["name"],
                    "unit": p.get("units") or "",
                    "description": p.get("displayName") or p["name"],
                }
                for p in catalog
            ]
            notes = "Live discovery from /v3/parameters."
        except Exception as e:
            # Minimal fallback when key missing/offline
            base = ["pm25","pm10","no2","o3","so2","co","bc"]
            vars_list = [{"canonical": f"air:{n}", "platform": n, "unit": ""} for n in base]
            notes = f"Fallback list; discovery failed: {e}"
    
        return {
            "dataset": self.DATASET,
            "geometry": ["point","bbox","polygon"],
            "requires_time_range": False,
            "requires_api_key": True,
            "variables": vars_list,
            "attributes_schema": {
                "method": {"type":"string"}, "sourceName": {"type":"string"},
                "city": {"type":"string"}, "aggregation": {"type":"string"}, "interval": {"type":"string"},
            },
            "rate_limits": {"notes": "Backoff on 429/5xx; moderate pagination."},
            "notes": notes,
        }

    def _discover_locations_with_fallback(
        self,
        lon: float,
        lat: float,
        headers: dict,
        *,
        initial_radius_m: int = 2000,
        max_attempts: int = 2,
    ) -> tuple[list[dict], str]:
        """
        Try /locations by coordinates+radius first (with brief retries).
        If that 5xx's or yields nothing, try /locations with bbox and widen radius.
        Returns (locations, strategy_string).
        strategy_string examples: "coordinates+radius", "bbox(2000m)", "bbox(5000m)", "none"
        """
        BASE = self.SOURCE_URL

        def _get(path: str, **params):
            for i in range(max_attempts):
                r = self._rate_limited_get(f"{BASE}{path}", params=params, headers=headers, timeout=30)
                # auth failures should surface immediately
                if r.status_code in (401, 403):
                    r.raise_for_status()
                # brief backoff on 5xx / 408 / 429
                if r.status_code in (408, 429) or r.status_code >= 500:
                    if i + 1 < max_attempts:
                        time.sleep(0.5 * (2 ** i))
                        continue
                r.raise_for_status()
                return r

        def _bbox_for_radius(lon: float, lat: float, r_m: int) -> str:
            d = (r_m / 1000.0) / 111.0
            return f"{lon - d},{lat - d},{lon + d},{lat + d}"

        # A) coordinates+radius path
        try:
            r = _get("/locations", coordinates=f"{lon},{lat}", radius=int(initial_radius_m), limit=100, sort="desc", page=1)
            locs = r.json().get("results", []) or []
            if locs:
                return locs, "coordinates+radius"
        except requests.HTTPError:
            # fall through to bbox
            pass

        # B) bbox with widening radii
        for rad in (initial_radius_m, 5000, 10000):
            try:
                bbox = _bbox_for_radius(lon, lat, int(rad))
                r = _get("/locations", bbox=bbox, limit=100, sort="desc", page=1)
                locs = r.json().get("results", []) or []
                if locs:
                    return locs, f"bbox({rad}m)"
            except requests.HTTPError:
                continue

        return [], "none"

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        api_key = self._get_api_key(spec.extra)
        headers = {"X-API-Key": api_key, "User-Agent": "env-agents/OpenAQ_v3"}

        catalog = self._openaq_parameter_catalog(headers)
        name_to_unit = {p["name"]: (p.get("units") or "") for p in catalog}

        # Variables wanted
        if spec.variables == ["*"]:
            params_wanted = {p["name"] for p in catalog}
        else:
            variables = spec.variables or ["air:pm25","air:o3","air:no2"]
            params_wanted = set()
            for v in variables:
                params_wanted.add(v.split(":",1)[1] if ":" in v else v)

        date_from, date_to = (spec.time_range or (None, None))

        # 1) Discover locations in AOI
        if spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
        elif spec.geometry.type == "bbox":
            minx, miny, maxx, maxy = spec.geometry.coordinates
            # centroid for discovery
            lon = (minx + maxx) / 2.0
            lat = (miny + maxy) / 2.0
        else:
            if wkt is None:
                raise RuntimeError("OpenAQ polygon requires shapely to compute centroid/bbox.")
            poly = wkt.loads(spec.geometry.coordinates)
            c = poly.centroid
            lon, lat = float(c.x), float(c.y)

        initial_radius = int((spec.extra or {}).get("radius_m", 2000))
        locations, discovery_strategy = self._discover_locations_with_fallback(lon, lat, headers, initial_radius_m=initial_radius)
        if not locations:
            return []

        # 2) From locations → sensors, filtered by wanted parameters
        sensor_ids: List[int] = []
        for loc in locations:
            lid = loc.get("id")
            if lid is None:
                continue
            # Use proven exponential backoff pattern for rate limiting
            max_attempts = 3
            for attempt in range(max_attempts):
                r = self._rate_limited_get(f"{self.SOURCE_URL}/locations/{lid}/sensors", headers=headers, timeout=60)

                # Auth failures surface immediately
                if r.status_code in (401, 403):
                    r.raise_for_status()

                # Skip missing locations
                if r.status_code in (422, 404):
                    break

                # Exponential backoff on rate limits and server errors
                if r.status_code in (408, 429) or r.status_code >= 500:
                    if attempt + 1 < max_attempts:
                        sleep_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                        time.sleep(sleep_time)
                        continue

                # Success or final attempt - break and handle
                break
            r.raise_for_status()
            sjs = r.json()
            for s in sjs.get("results", []):
                p = (s.get("parameter") or {}).get("name")
                if p in params_wanted and s.get("id"):
                    sensor_ids.append(s.get("id"))

        if not sensor_ids:
            return []

        retrieval_ts = datetime.now(timezone.utc).isoformat()
        upstream = {"dataset": self.DATASET, "endpoint": self.SOURCE_URL, "upstream_version": self.SOURCE_VERSION, "license": self.LICENSE, "citation": "OpenAQ v3"}
        rows: List[Dict[str, Any]] = []
        per_page = min(1000, int((spec.extra or {}).get("per_page", 500)))
        max_sensors = int((spec.extra or {}).get("max_sensors", 50))
        sensor_ids = sensor_ids[:max_sensors]

        for sid in sensor_ids:
            q = {"limit": per_page, "page": 1}
            if date_from: q["date_from"] = date_from
            if date_to:   q["date_to"] = date_to

            while True:
                url = f"{self.SOURCE_URL}/sensors/{sid}/measurements"

                # Use proven exponential backoff pattern for rate limiting
                max_attempts = 3
                for attempt in range(max_attempts):
                    r = self._rate_limited_get(url, params=q, headers=headers, timeout=90)

                    # Exponential backoff on rate limits and server errors
                    if r.status_code in (408, 429) or r.status_code >= 500:
                        if attempt + 1 < max_attempts:
                            sleep_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                            time.sleep(sleep_time)
                            continue
                    break

                r.raise_for_status()
                js = r.json()
                results = js.get("results", [])
                if not results:
                    break

                for item in results:
                    param_obj = item.get("parameter") or {}
                    pname = param_obj.get("name")
                    if pname not in params_wanted:
                        continue
                    val = item.get("value")
                    period = (item.get("period") or {})
                    dt_to = ((period.get("datetimeTo") or {}).get("utc")) or None
                    coords = item.get("coordinates") or {}
                    lat = coords.get("latitude"); lon = coords.get("longitude")
                    
                    # Try alternative coordinate locations if not found
                    if lat is None or lon is None:
                        # Try from parent location or other nested structures
                        location = item.get("location", {})
                        if "coordinates" in location:
                            alt_coords = location["coordinates"]
                            if lat is None:
                                lat = alt_coords.get("latitude")
                            if lon is None:
                                lon = alt_coords.get("longitude")
                    
                    # Final fallback: use the original geometry from the request
                    if lat is None or lon is None:
                        if spec.geometry.type == "point" and len(spec.geometry.coordinates) == 2:
                            if lon is None:
                                lon = spec.geometry.coordinates[0]
                            if lat is None:
                                lat = spec.geometry.coordinates[1]
                    unit = param_obj.get("units") or name_to_unit.get(pname) or ""

                    # Generate deterministic observation ID
                    obs_id = f"openaq_{sid}_{pname}_{dt_to.replace(':', '').replace('-', '') if dt_to else 'unknown'}"
                    
                    # Get location metadata from item
                    location_info = item.get("location", {})
                    site_name = location_info.get("name") or location_info.get("label")
                    admin_info = location_info.get("country") or location_info.get("admin")
                    elevation = location_info.get("elevation")
                    
                    # Create WKT geometry
                    geom_wkt = f"POINT({lon} {lat})" if lon is not None and lat is not None else None
                    
                    # Determine temporal coverage
                    period_start = (period.get("datetimeFrom") or {}).get("utc")
                    temporal_coverage = f"{period_start}/{dt_to}" if period_start and dt_to else dt_to
                    
                    rows.append({
                        "observation_id": obs_id,
                        "dataset": self.DATASET,
                        "source_url": self.SOURCE_URL,
                        "source_version": self.SOURCE_VERSION,
                        "license": self.LICENSE,
                        "retrieval_timestamp": retrieval_ts,
                        "geometry_type": "point",
                        "latitude": float(lat) if lat is not None else None,
                        "longitude": float(lon) if lon is not None else None,
                        "geom_wkt": geom_wkt,
                        "spatial_id": str(sid),
                        "site_name": site_name,
                        "admin": admin_info,
                        "elevation_m": float(elevation) if elevation is not None else None,
                        "time": dt_to,
                        "temporal_coverage": temporal_coverage,
                        "variable": f"air:{pname}",
                        "value": None if val is None else float(val),
                        "unit": unit,
                        "depth_top_cm": None,  # Not applicable for air quality
                        "depth_bottom_cm": None,  # Not applicable for air quality
                        "qc_flag": "ok",
                        "attributes": {"aggregation": period.get("label") or "raw", "interval": period.get("interval"),"discovery_strategy": discovery_strategy,"native_parameter": pname},
                        "provenance": self._prov(spec, upstream),
                    })

                meta = js.get("meta", {})
                page = meta.get("page", q["page"]); limit = meta.get("limit", per_page); found = meta.get("found", 0)
                if isinstance(found, str) and found.startswith(">"): found = int(found[1:])
                if page * limit >= (found or 0): break
                q["page"] = page + 1

        return rows

    def harvest(self) -> List[Dict[str, Any]]:
        """
        Harvest OpenAQ parameter catalog for semantic discovery
        Returns ServiceCapability-compatible objects
        """
        try:
            # Get API key (required for catalog access)
            headers = {"X-API-Key": self._get_api_key({})}
            
            # Use existing _openaq_parameter_catalog method
            catalog = self._openaq_parameter_catalog(headers)
            
            # Convert to ServiceCapability format
            capabilities = []
            for param in catalog:
                param_name = param.get('name', '')
                capabilities.append({
                    'service': self.DATASET,
                    'native_id': param_name,
                    'label': param.get('displayName', param_name),
                    'unit': param.get('units', ''),
                    'description': param.get('description', param_name),
                    'domain': 'air',
                    'frequency': 'varies',
                    'spatial_coverage': 'global',
                    'temporal_coverage': 'realtime_and_historical',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': f"air:{param_name}",
                        'parameter_group': 'air_quality',
                        'openaq_parameter': param_name,
                        'data_types': ['measurements']
                    }
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"Failed to harvest OpenAQ parameters: {e}")
            # Return fallback minimal list
            fallback_params = ["pm25", "pm10", "no2", "o3", "so2", "co"]
            return [
                {
                    'service': self.DATASET,
                    'native_id': param,
                    'label': f"{param.upper()} concentration",
                    'unit': 'µg/m³' if param.startswith('pm') else 'ppb',
                    'description': f"{param.upper()} air quality parameter",
                    'domain': 'air',
                    'frequency': 'varies',
                    'spatial_coverage': 'global',
                    'temporal_coverage': 'realtime_and_historical',
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'canonical': f"air:{param}",
                        'parameter_group': 'air_quality_fallback',
                        'openaq_parameter': param,
                        'data_types': ['measurements']
                    }
                }
                for param in fallback_params
            ]
    
    def get_enhanced_metadata(self) -> Optional[AssetMetadata]:
        """Get Google Earth Engine-style metadata for OpenAQ data"""
        try:
            # Get parameter catalog for metadata
            try:
                # Try to get API key from environment 
                import os
                api_key = os.environ.get('OPENAQ_API_KEY')
                if api_key:
                    headers = {"X-API-Key": api_key}
                    parameters = self._openaq_parameter_catalog(headers)
                else:
                    raise RuntimeError("No API key available")
            except Exception:
                # Use fallback parameters if API unavailable
                parameters = [
                    {"name": "pm25", "units": "µg/m³", "displayName": "PM2.5", "description": "Fine particulate matter"},
                    {"name": "pm10", "units": "µg/m³", "displayName": "PM10", "description": "Coarse particulate matter"},
                    {"name": "no2", "units": "ppb", "displayName": "NO₂", "description": "Nitrogen dioxide"},
                    {"name": "o3", "units": "ppb", "displayName": "O₃", "description": "Ground-level ozone"},
                    {"name": "so2", "units": "ppb", "displayName": "SO₂", "description": "Sulfur dioxide"},
                    {"name": "co", "units": "ppm", "displayName": "CO", "description": "Carbon monoxide"}
                ]
            
            # Create asset metadata
            asset_id = "OPENAQ/MEASUREMENTS_V3"
            title = "OpenAQ Global Air Quality Measurements v3"
            description = "Real-time and historical air quality measurements from government agencies and research organizations worldwide"
            
            # Temporal extent (OpenAQ has historical to present data)
            temporal_extent = ("2013-11-01", datetime.now().strftime('%Y-%m-%d'))
            
            # Create bands for each parameter
            bands_dict = {}
            for param in parameters:
                param_name = param['name']
                param_units = param.get('units', '')
                param_desc = param.get('description', f"{param_name} air quality parameter")
                
                bands_dict[param_name] = {
                    'description': param_desc,
                    'data_type': 'float32',
                    'units': param_units,
                    'valid_range': self._get_parameter_range(param_name),
                    'cf_standard_name': self._get_cf_standard_name(param_name)
                }
                
                # Add quality/metadata bands
                bands_dict[f"{param_name}_uncertainty"] = {
                    'description': f"Measurement uncertainty for {param_name}",
                    'data_type': 'float32',
                    'units': param_units,
                    'valid_range': [0.0, 1000.0],
                    'cf_standard_name': None
                }
            
            # Data quality and metadata bands
            bands_dict['data_completeness'] = {
                'description': 'Temporal data completeness fraction',
                'data_type': 'float32',
                'units': 'fraction',
                'valid_range': [0.0, 1.0],
                'cf_standard_name': None
            }
            
            bands_dict['measurement_method'] = {
                'description': 'Measurement method classification',
                'data_type': 'string',
                'units': 'categorical',
                'valid_range': [],
                'cf_standard_name': None
            }
            
            # Global spatial extent
            spatial_extent = {
                "type": "Polygon",
                "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]
            }
            
            metadata = create_earth_engine_style_metadata(
                asset_id=asset_id,
                title=title,
                description=description,
                temporal_extent=temporal_extent,
                spatial_extent=spatial_extent,
                bands=bands_dict,
                provider_name="OpenAQ Foundation",
                provider_url="https://openaq.org/"
            )
            
            # Add OpenAQ-specific properties
            metadata.properties.update({
                'openaq:api_version': self.SOURCE_VERSION,
                'openaq:parameters_count': len(parameters),
                'openaq:data_types': ['measurements', 'real_time', 'historical'],
                'openaq:measurement_methods': ['reference', 'low_cost_sensor', 'government'],
                'openaq:temporal_resolution': ['hourly', 'daily', 'raw'],
                'system:domain': 'air_quality',
                'system:data_type': 'time_series_measurements',
                'system:bbox': [-180, -90, 180, 90],
                'system:requires_auth': True
            })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced metadata for OpenAQ: {e}")
            return None
    
    def _get_parameter_range(self, param: str) -> List[float]:
        """Get realistic parameter ranges for validation"""
        ranges = {
            'pm25': [0.0, 1000.0],
            'pm10': [0.0, 2000.0], 
            'no2': [0.0, 200.0],
            'o3': [0.0, 500.0],
            'so2': [0.0, 100.0],
            'co': [0.0, 50.0],
            'bc': [0.0, 100.0],
            'nh3': [0.0, 100.0],
            'nox': [0.0, 200.0],
            'ch4': [1.8, 2.2]  # ppm
        }
        return ranges.get(param, [0.0, 10000.0])
    
    def _get_cf_standard_name(self, param: str) -> Optional[str]:
        """Get CF standard names where available"""
        cf_names = {
            'pm25': 'mass_concentration_of_pm2p5_ambient_aerosol_particles_in_air',
            'pm10': 'mass_concentration_of_pm10_ambient_aerosol_particles_in_air',
            'no2': 'mole_fraction_of_nitrogen_dioxide_in_air',
            'o3': 'mole_fraction_of_ozone_in_air',
            'so2': 'mole_fraction_of_sulfur_dioxide_in_air',
            'co': 'mole_fraction_of_carbon_monoxide_in_air'
        }
        return cf_names.get(param)
