"""
EPA Air Quality System (AQS) Adapter

Enhanced adapter with robust error handling patterns from ECOGNITA agent
Provides access to air quality monitoring data from EPA's AQS database:
- Criteria pollutants (PM2.5, PM10, O3, NO2, SO2, CO, Pb)
- Meteorological data from air quality sites  
- Site information and metadata
- Quality assurance flags

Features:
- Multi-tier geographic search with fallbacks
- Service-specific caching for sites and parameters
- Rich diagnostic reporting
- Earth Engine-style metadata
"""

from __future__ import annotations
import os
import time
import asyncio
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
import logging

from ..base import BaseAdapter
from ...core.models import RequestSpec, Geometry
from ...core.errors import FetchError
from ...core.cache import global_cache
from ...core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)

logger = logging.getLogger(__name__)


@dataclass
class AQSQueryResult:
    """Result from AQS query with diagnostics"""
    success: bool
    data: Optional[pd.DataFrame] = None
    message: str = ""
    filter_diagnostics: List[str] = None
    execution_time: float = 0.0
    api_calls: int = 0
    sites_found: int = 0
    
    def __post_init__(self):
        if self.filter_diagnostics is None:
            self.filter_diagnostics = []


class EPAAQSAdapter(BaseAdapter):
    """EPA Air Quality System API Adapter with robust patterns"""
    
    DATASET = "EPA_AQS"
    SOURCE_URL = "https://aqs.epa.gov/data/api"
    SOURCE_VERSION = "v1.0"
    LICENSE = "Public Domain"
    REQUIRES_API_KEY = True
    
    # Parameter class codes for air quality data
    CRITERIA_POLLUTANTS = {
        'pm25': '88101',     # PM2.5 - Local Conditions
        'pm25_frm': '88502', # PM2.5 - FRM/FEM Mass
        'pm10': '81102',     # PM10 - Local Conditions  
        'o3': '44201',       # Ozone
        'no2': '42602',      # Nitrogen Dioxide
        'so2': '42401',      # Sulfur Dioxide
        'co': '42101',       # Carbon Monoxide
        'lead': '12128'      # Lead (TSP) LC
    }
    
    # State FIPS codes for geographic queries
    STATE_CODES = {
        'CA': '06', 'NY': '36', 'TX': '48', 'FL': '12', 'IL': '17',
        # Add more as needed
    }
    
    def __init__(self, email: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize EPA AQS adapter
        
        Args:
            email: EPA AQS email (defaults to environment variable)
            key: EPA AQS key (defaults to environment variable)
        """
        super().__init__()
        
        # Credential management with graceful fallback for testing
        self.email = email or os.environ.get('EPA_AQS_EMAIL', 'test@example.com')
        self.key = key or os.environ.get('EPA_AQS_KEY', 'test')
        
        # Note: EPA AQS requires valid credentials for production use
        self.test_mode = (self.email == 'test@example.com' or self.key == 'test')
        if self.test_mode:
            logger.info("EPA_AQS running in test mode - some queries may fail due to authentication")
        
        # Request session with authentication
        self.session = requests.Session()
        self.session.params = {'email': self.email, 'key': self.key}
        
        # Rate limiting (AQS allows 1000 requests per hour)
        self.last_request_time = 0
        self.min_request_interval = 3.6  # 1000 requests/hour = 3.6 seconds between requests
        
        # Cache management
        self.cache = global_cache.get_service_cache("EPA_AQS")
        
        # Cached data
        self._parameter_classes = None
        self._criteria_parameters = None
    
    def capabilities(self) -> Dict[str, Any]:
        """Get adapter capabilities with cached parameter discovery"""
        try:
            # Get parameter classes with caching
            parameter_classes = self._get_parameter_classes()
            
            variables = []
            for param_code, param_name in self.CRITERIA_POLLUTANTS.items():
                variables.append({
                    'canonical': f'air:{param_code}',
                    'platform': param_name,
                    'unit': 'µg/m³',  # Most AQS data is in µg/m³
                    'description': f'Air quality {param_code.upper()} from EPA AQS'
                })
            
            return {
                'variables': variables,
                'parameter_classes': len(parameter_classes) if parameter_classes else 0,
                'attributes_schema': {
                    'site_id': 'string',
                    'parameter_code': 'string',
                    'poc': 'integer',  # Parameter Occurrence Code
                    'datum': 'string',
                    'parameter_name': 'string',
                    'sample_duration': 'string',
                    'pollutant_standard': 'string',
                    'method_code': 'string',
                    'method_name': 'string',
                    'state_code': 'string',
                    'county_code': 'string',
                    'site_number': 'string',
                    'aqs_parameter_code': 'string'
                },
                'rate_limits': {
                    'requests_per_hour': 1000,
                    'min_interval_seconds': 3.6
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get AQS capabilities: {e}")
            return {'variables': [], 'error': str(e)}
    
    def harvest(self) -> Dict[str, Any]:
        """Harvest EPA AQS parameter structure for semantic mapping"""
        try:
            harvest_data = {}
            
            # Get parameter classes
            parameter_classes = self._get_parameter_classes()
            if parameter_classes:
                for param_class in parameter_classes:
                    class_code = param_class['code']
                    class_name = param_class['value_represented']
                    
                    # Get parameters for this class
                    parameters = self._get_parameters_by_class(class_code)
                    
                    for param in parameters:
                        param_code = param['code']
                        param_name = param['value_represented']
                        
                        harvest_data[param_code] = {
                            'id': param_code,
                            'label': param_name,
                            'description': f"{param_name} from EPA AQS",
                            'unit': 'µg/m³',  # Default unit for air quality
                            'domain': 'air_quality',
                            'parameter_class': class_name,
                            'class_code': class_code
                        }
            
            # Cache harvest results
            self.cache.set('harvest_data', harvest_data, 'parameters', ttl=604800)  # 7 days
            
            return harvest_data
            
        except Exception as e:
            logger.error(f"Failed to harvest AQS parameters: {e}")
            return {}
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch air quality data with robust multi-tier strategy"""
        try:
            # Handle event loop conflicts in Jupyter notebooks
            try:
                # Check if we're in a running event loop (like Jupyter)
                loop = asyncio.get_running_loop()
                # If we get here, we're in a running loop - use create_task instead
                import concurrent.futures
                import threading
                
                # Run async code in a separate thread to avoid event loop conflict
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._robust_aqs_query(spec))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=120)  # 2 minute timeout
                    
            except RuntimeError:
                # No running event loop, safe to use asyncio.run()
                result = asyncio.run(self._robust_aqs_query(spec))
            
            if not result.success or result.data is None:
                raise FetchError(f"AQS query failed: {result.message}")
            
            # Convert DataFrame to standardized rows
            rows = []
            retrieval_timestamp = datetime.now(timezone.utc)
            
            for _, row in result.data.iterrows():
                standardized_row = {
                    # Identity columns
                    'observation_id': self._generate_observation_id(row),
                    'dataset': self.DATASET,
                    'source_url': self.SOURCE_URL,
                    'source_version': self.SOURCE_VERSION,
                    'license': self.LICENSE,
                    'retrieval_timestamp': retrieval_timestamp,
                    
                    # Spatial columns
                    'geometry_type': 'point',
                    'latitude': row.get('latitude'),
                    'longitude': row.get('longitude'),
                    'geom_wkt': f"POINT({row.get('longitude', 0)} {row.get('latitude', 0)})",
                    'spatial_id': row.get('site_id', ''),
                    'site_name': row.get('local_site_name', ''),
                    'admin': row.get('state_code', ''),
                    'elevation_m': None,
                    
                    # Temporal columns  
                    'time': pd.to_datetime(row.get('date_local', ''), errors='coerce'),
                    'temporal_coverage': row.get('date_local', ''),
                    
                    # Value columns
                    'variable': self._map_parameter_to_canonical(row.get('parameter_code')),
                    'value': pd.to_numeric(row.get('arithmetic_mean', ''), errors='coerce'),
                    'unit': row.get('units_of_measure', ''),
                    'depth_top_cm': None,
                    'depth_bottom_cm': None,
                    'qc_flag': row.get('qualifier', ''),
                    
                    # Metadata columns
                    'attributes': {
                        'terms': [f"{self.DATASET}:parameter:{row.get('parameter_code')}"],
                        'site_id': row.get('site_id'),
                        'parameter_code': row.get('parameter_code'),
                        'parameter_name': row.get('parameter_name'),
                        'poc': row.get('poc'),
                        'method_name': row.get('method_name'),
                        'sample_duration': row.get('sample_duration'),
                        'pollutant_standard': row.get('pollutant_standard'),
                        'state_code': row.get('state_code'),
                        'county_code': row.get('county_code'),
                        'site_number': row.get('site_number'),
                        'native_record': row.to_dict()
                    },
                    'provenance': f"Retrieved from EPA AQS API on {retrieval_timestamp.isoformat()}"
                }
                
                rows.append(standardized_row)
            
            return rows
            
        except Exception as e:
            logger.error(f"Failed to fetch AQS data: {e}")
            raise FetchError(f"AQS data fetch failed: {e}")
    
    async def _robust_aqs_query(self, spec: RequestSpec) -> AQSQueryResult:
        """
        Robust AQS query with multi-tier fallback strategy
        Based on ECOGNITA water quality agent patterns
        """
        start_time = time.time()
        api_calls = 0
        filter_diagnostics = []
        
        try:
            # Check if we should use direct bbox method
            if (spec.geometry.type == "bbox" and 
                spec.extra and 
                spec.extra.get("use_bbox_method")):
                # Use direct bbox daily data API
                bbox_result = await self._get_data_for_bbox(spec)
                return bbox_result
            
            # Step 1: Find monitoring sites in the region (traditional method)
            sites_result = await self._find_sites_robust(spec)
            api_calls += sites_result.api_calls
            
            if not sites_result.success or sites_result.data is None or sites_result.data.empty:
                return AQSQueryResult(
                    success=False,
                    message="No monitoring sites found in specified region",
                    filter_diagnostics=["region"],
                    execution_time=time.time() - start_time,
                    api_calls=api_calls
                )
            
            sites_df = sites_result.data
            logger.info(f"Found {len(sites_df)} monitoring sites")
            
            # Step 2: Get air quality data for these sites
            data_result = await self._get_data_for_sites(sites_df, spec)
            api_calls += data_result.api_calls
            
            execution_time = time.time() - start_time
            
            if data_result.success and data_result.data is not None and not data_result.data.empty:
                return AQSQueryResult(
                    success=True,
                    data=data_result.data,
                    message=f"Retrieved {len(data_result.data)} air quality measurements from {len(sites_df)} sites",
                    filter_diagnostics=filter_diagnostics,
                    execution_time=execution_time,
                    api_calls=api_calls,
                    sites_found=len(sites_df)
                )
            else:
                # Step 3: Fallback - try without date filter
                filter_diagnostics.append("date")
                fallback_spec = RequestSpec(
                    geometry=spec.geometry,
                    variables=spec.variables,
                    time_range=None,  # Remove date filter
                    extra=spec.extra
                )
                
                fallback_result = await self._get_data_for_sites(sites_df, fallback_spec)
                api_calls += fallback_result.api_calls
                
                if fallback_result.success and fallback_result.data is not None:
                    return AQSQueryResult(
                        success=True,
                        data=fallback_result.data,
                        message=f"Retrieved {len(fallback_result.data)} measurements (fallback query without date filter)",
                        filter_diagnostics=filter_diagnostics,
                        execution_time=time.time() - start_time,
                        api_calls=api_calls,
                        sites_found=len(sites_df)
                    )
                
                return AQSQueryResult(
                    success=False,
                    message="No air quality data found for specified parameters",
                    filter_diagnostics=filter_diagnostics,
                    execution_time=time.time() - start_time,
                    api_calls=api_calls,
                    sites_found=len(sites_df)
                )
                
        except Exception as e:
            logger.error(f"Robust AQS query failed: {e}")
            return AQSQueryResult(
                success=False,
                message=f"Query failed with error: {str(e)}",
                filter_diagnostics=filter_diagnostics,
                execution_time=time.time() - start_time,
                api_calls=api_calls
            )
    
    async def _find_sites_robust(self, spec: RequestSpec) -> AQSQueryResult:
        """Find monitoring sites using direct EPA AQS geographic API calls"""
        try:
            if spec.geometry.type == "point":
                # Point-based search - use EPA AQS sites/byBox API directly
                lon, lat = spec.geometry.coordinates
                # Create small bbox around point (±0.5 degrees = ~50km radius)
                buffer = 0.5
                bbox = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]
                
                sites_df = await self._get_sites_by_bbox(bbox)
                
                return AQSQueryResult(
                    success=sites_df is not None and not sites_df.empty,
                    data=sites_df if sites_df is not None else pd.DataFrame(),
                    message="No monitoring sites found in region" if sites_df is None or sites_df.empty else f"Found {len(sites_df)} sites",
                    api_calls=1
                )
                
            elif spec.geometry.type == "bbox":
                # Direct bounding box search using EPA AQS sites/byBox API
                bbox = spec.geometry.coordinates  # [west, south, east, north]
                
                sites_df = await self._get_sites_by_bbox(bbox)
                api_calls = 1
                
                return AQSQueryResult(
                    success=sites_df is not None and not sites_df.empty,
                    data=sites_df if sites_df is not None else pd.DataFrame(),
                    message="No monitoring sites found in bounding box" if sites_df is None or sites_df.empty else f"Found {len(sites_df)} sites",
                    api_calls=api_calls
                )
            
            else:
                return AQSQueryResult(
                    success=False,
                    message=f"Unsupported geometry type: {spec.geometry.type}",
                    api_calls=0
                )
                
        except Exception as e:
            logger.error(f"Site search failed: {e}")
            return AQSQueryResult(
                success=False,
                message=f"Site search error: {str(e)}",
                api_calls=1
            )
    
    async def _get_sites_by_bbox(self, bbox: List[float]) -> Optional[pd.DataFrame]:
        """Get monitoring sites within bounding box using EPA AQS sites/byBox API"""
        try:
            # EPA AQS API format: minlat, maxlat, minlon, maxlon
            west, south, east, north = bbox
            
            # Use sites/byBox endpoint directly
            url = "https://aqs.epa.gov/data/api/list/sites"
            params = {
                'email': self.email,
                'key': self.key,
                'param': '44201',  # Ozone as default parameter for site discovery
                'bdate': '20220101',  # Recent year for active sites
                'edate': '20221231',
                'minlat': south,
                'maxlat': north, 
                'minlon': west,
                'maxlon': east
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('Header', {}).get('status') == 'Success':
                sites = data.get('Data', [])
                if sites:
                    return pd.DataFrame(sites)
                    
            return pd.DataFrame()  # Empty but valid DataFrame for no data
            
        except Exception as e:
            logger.error(f"Failed to fetch sites by bbox {bbox}: {e}")
            return None  # None indicates service error
    
    def _fetch_sites_by_state_sync(self, state_code: str) -> Optional[List[Dict]]:
        """Synchronous site fetching for caching"""
        self._rate_limit()
        
        try:
            url = f"{self.SOURCE_URL}/list/sites"
            params = {'state': state_code}
            
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle authentication errors gracefully
            if response.status_code == 422:
                if self.test_mode:
                    logger.warning(f"EPA AQS authentication failed for state {state_code} (test mode)")
                else:
                    logger.error(f"EPA AQS authentication failed for state {state_code} - check credentials")
                return []
            
            response.raise_for_status()
            
            data = response.json()
            if 'Data' in data:
                return data['Data']
                
        except Exception as e:
            logger.error(f"Failed to fetch sites for state {state_code}: {e}")
        
        return None
    
    async def _get_data_for_bbox(self, spec: RequestSpec) -> AQSQueryResult:
        """Get air quality data using bbox daily data API directly"""
        try:
            if spec.geometry.type != "bbox":
                return AQSQueryResult(success=False, message="Bbox method requires bbox geometry", data=None)
                
            west, south, east, north = spec.geometry.coordinates
            
            # Parameter mapping for AQS
            param_map = {
                "air:pm25": "88101",  # PM2.5
                "air:pm10": "81102",  # PM10  
                "air:o3": "44201",    # Ozone
                "air:no2": "42602",   # NO2
                "air:so2": "42401",   # SO2
                "air:co": "42101"     # CO
            }
            
            all_data = []
            api_calls = 0
            
            # Get parameter codes from requested variables
            parameter_codes = []
            for var in (spec.variables or ["air:pm25"]):
                if var in param_map:
                    parameter_codes.append(param_map[var])
            
            if not parameter_codes:
                parameter_codes = ["88101"]  # Default to PM2.5
            
            # Format dates for AQS API (YYYYMMDD)
            start_date = spec.time_range[0] if spec.time_range else "20230601" 
            end_date = spec.time_range[1] if spec.time_range else "20230603"
            
            # Convert ISO dates to YYYYMMDD if needed
            if len(start_date) > 8:
                start_date = start_date[:10].replace('-', '')
            if len(end_date) > 8:
                end_date = end_date[:10].replace('-', '')
            
            # Fetch data for each parameter using bbox method
            for param_code in parameter_codes:
                try:
                    params = {
                        "param": param_code,
                        "bdate": start_date,
                        "edate": end_date,
                        "minlat": south, 
                        "minlon": west,
                        "maxlat": north, 
                        "maxlon": east,
                        "email": self.email, 
                        "key": self.key
                    }
                    
                    url = f"{self.SOURCE_URL}/dailyData/byBox"
                    response = requests.get(url, params=params, timeout=30)
                    api_calls += 1
                    
                    if response.status_code == 200:
                        data = response.json()
                        records = data.get("Data", [])
                        
                        for record in records:
                            all_data.append({
                                'parameter_code': param_code,
                                'date_local': record.get('date_local'),
                                'arithmetic_mean': record.get('arithmetic_mean'), 
                                'latitude': record.get('latitude'),
                                'longitude': record.get('longitude'),
                                'state_code': record.get('state_code'),
                                'county_code': record.get('county_code'),
                                'site_number': record.get('site_number'),
                                'local_site_name': record.get('local_site_name', ''),
                                'datum': record.get('datum'),
                                'units_of_measure': record.get('units_of_measure')
                            })
                            
                except Exception as param_e:
                    logging.getLogger(__name__).warning(f"Failed to fetch parameter {param_code}: {param_e}")
                    
                # Small delay to be respectful to API
                await asyncio.sleep(0.5)
                
            if all_data:
                df = pd.DataFrame(all_data)
                return AQSQueryResult(
                    success=True, 
                    message=f"Found {len(df)} bbox observations", 
                    data=df, 
                    api_calls=api_calls
                )
            else:
                return AQSQueryResult(
                    success=False, 
                    message="No data found in bbox", 
                    data=None, 
                    api_calls=api_calls
                )
                
        except Exception as e:
            return AQSQueryResult(
                success=False, 
                message=f"Bbox query failed: {e}", 
                data=None, 
                api_calls=1
            )

    async def _get_data_for_sites(self, sites_df: pd.DataFrame, spec: RequestSpec) -> AQSQueryResult:
        """Get air quality data for monitoring sites"""
        try:
            # Limit to reasonable number of sites to avoid API limits
            max_sites = 20
            if len(sites_df) > max_sites:
                sites_df = sites_df.head(max_sites)
                logger.warning(f"Limited to {max_sites} sites to avoid API limits")
            
            all_data = []
            api_calls = 0
            
            # Get parameter codes from variables
            parameter_codes = []
            for variable in spec.variables:
                param_code = self._canonical_to_parameter_code(variable)
                if param_code:
                    parameter_codes.append(param_code)
            
            if not parameter_codes:
                return AQSQueryResult(
                    success=False,
                    message="No valid parameter codes found in variables",
                    api_calls=0
                )
            
            # Query each site
            for _, site in sites_df.iterrows():
                state_code = site['state_code']
                county_code = site['county_code']
                site_number = site['site_number']
                
                for param_code in parameter_codes:
                    data = await self._get_sample_data(
                        state_code, county_code, site_number, param_code, spec.time_range
                    )
                    api_calls += 1
                    
                    if data:
                        all_data.extend(data)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(0.5)
            
            if all_data:
                df = pd.DataFrame(all_data)
                return AQSQueryResult(
                    success=True,
                    data=df,
                    api_calls=api_calls
                )
            else:
                return AQSQueryResult(
                    success=False,
                    message="No measurement data found",
                    api_calls=api_calls
                )
                
        except Exception as e:
            logger.error(f"Data retrieval failed: {e}")
            return AQSQueryResult(
                success=False,
                message=f"Data retrieval error: {str(e)}",
                api_calls=api_calls
            )
    
    async def _get_sample_data(
        self, 
        state_code: str, 
        county_code: str, 
        site_number: str, 
        parameter_code: str,
        time_range: Optional[Tuple[str, str]]
    ) -> Optional[List[Dict]]:
        """Get sample data for specific site and parameter"""
        self._rate_limit()
        
        try:
            url = f"{self.SOURCE_URL}/sampleData/bySite"
            params = {
                'state': state_code,
                'county': county_code,
                'site': site_number,
                'param': parameter_code,
                'bdate': '20230101',  # Default dates
                'edate': '20231231'
            }
            
            # Override with spec time range if provided
            if time_range and time_range[0] and time_range[1]:
                start_date = datetime.fromisoformat(time_range[0]).strftime('%Y%m%d')
                end_date = datetime.fromisoformat(time_range[1]).strftime('%Y%m%d')
                params['bdate'] = start_date
                params['edate'] = end_date
            
            response = self.session.get(url, params=params, timeout=45)
            response.raise_for_status()
            
            data = response.json()
            if 'Data' in data:
                return data['Data']
                
        except Exception as e:
            logger.debug(f"Sample data query failed for {state_code}-{county_code}-{site_number}: {e}")
        
        return None
    
    def _rate_limit(self):
        """Implement rate limiting for EPA AQS API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _get_parameter_classes(self) -> Optional[List[Dict]]:
        """Get parameter classes with caching"""
        cache_key = "parameter_classes"
        
        def fetch_classes():
            return self._fetch_parameter_classes_sync()
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_classes,
            cache_type="parameters",
            ttl=604800  # 7 days
        )
    
    def _fetch_parameter_classes_sync(self) -> Optional[List[Dict]]:
        """Fetch parameter classes synchronously"""
        self._rate_limit()
        
        try:
            url = f"{self.SOURCE_URL}/list/classes"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'Data' in data:
                return data['Data']
                
        except Exception as e:
            logger.error(f"Failed to fetch parameter classes: {e}")
        
        return None
    
    def _get_parameters_by_class(self, class_code: str) -> List[Dict]:
        """Get parameters for a specific class with caching"""
        cache_key = f"parameters_class_{class_code}"
        
        def fetch_params():
            return self._fetch_parameters_by_class_sync(class_code)
        
        return self.cache.get_or_fetch(
            cache_key,
            fetch_params,
            cache_type="parameters",
            ttl=604800  # 7 days
        ) or []
    
    def _fetch_parameters_by_class_sync(self, class_code: str) -> Optional[List[Dict]]:
        """Fetch parameters by class synchronously"""
        self._rate_limit()
        
        try:
            url = f"{self.SOURCE_URL}/list/parametersByClass"
            params = {'pc': class_code}
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'Data' in data:
                return data['Data']
                
        except Exception as e:
            logger.error(f"Failed to fetch parameters for class {class_code}: {e}")
        
        return None
    
    def _canonical_to_parameter_code(self, canonical_var: str) -> Optional[str]:
        """Convert canonical variable to AQS parameter code"""
        if canonical_var.startswith('air:'):
            param_name = canonical_var[4:]  # Remove 'air:' prefix
            return self.CRITERIA_POLLUTANTS.get(param_name)
        
        return None
    
    def _map_parameter_to_canonical(self, parameter_code: str) -> str:
        """Map AQS parameter code to canonical variable"""
        for canonical, code in self.CRITERIA_POLLUTANTS.items():
            if code == parameter_code:
                return f'air:{canonical}'
        
        # If not found, use generic format
        return f'air:parameter_{parameter_code}'
    
    # Hard-coded state mapping functions REMOVED
    # EPA AQS API supports direct bbox queries - no state mapping needed
    
    def _filter_sites_by_distance(
        self, 
        sites_df: pd.DataFrame, 
        target_lat: float, 
        target_lon: float, 
        radius_km: float = 100
    ) -> pd.DataFrame:
        """Filter sites by distance from target point"""
        from geopy.distance import geodesic
        
        def calculate_distance(row):
            return geodesic((target_lat, target_lon), (row['latitude'], row['longitude'])).kilometers
        
        sites_df = sites_df.copy()
        sites_df['distance_km'] = sites_df.apply(calculate_distance, axis=1)
        
        return sites_df[sites_df['distance_km'] <= radius_km].sort_values('distance_km')
    
    def _generate_observation_id(self, row) -> str:
        """Generate unique observation ID"""
        import hashlib
        
        # Use site, parameter, date to create unique ID
        site_id = row.get('site_id', '')
        param_code = row.get('parameter_code', '')
        date_local = row.get('date_local', '')
        poc = row.get('poc', '')
        
        unique_string = f"{site_id}:{param_code}:{date_local}:{poc}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def get_enhanced_metadata(self) -> Optional[AssetMetadata]:
        """Get Earth Engine-style metadata for EPA AQS air quality data"""
        try:
            # Create asset metadata
            asset_id = "EPA_AQS/CRITERIA_POLLUTANTS"
            title = "EPA Air Quality System - Criteria Pollutants"
            description = """
            Air quality monitoring data from EPA's Air Quality System (AQS).
            Includes criteria pollutants (PM2.5, PM10, O3, NO2, SO2, CO, Pb) and meteorological
            data from monitoring stations across the United States.
            """
            
            # Temporal extent (AQS data goes back to 1980s, ongoing)
            temporal_extent = ("1980-01-01", datetime.now().strftime('%Y-%m-%d'))
            
            # Create bands for each criteria pollutant
            bands_dict = {}
            
            # Main pollutant bands
            pollutant_bands = {
                'pm25': {
                    'description': 'Fine Particulate Matter (PM2.5) mass concentration',
                    'data_type': 'float32',
                    'units': 'µg/m³',
                    'valid_range': [0.0, 500.0],
                    'cf_standard_name': 'mass_concentration_of_pm2p5_ambient_aerosol_particles_in_air'
                },
                'pm10': {
                    'description': 'Inhalable Particulate Matter (PM10) mass concentration', 
                    'data_type': 'float32',
                    'units': 'µg/m³',
                    'valid_range': [0.0, 1000.0],
                    'cf_standard_name': 'mass_concentration_of_pm10_ambient_aerosol_particles_in_air'
                },
                'ozone': {
                    'description': 'Ground-level ozone (O3) concentration',
                    'data_type': 'float32', 
                    'units': 'ppb',
                    'valid_range': [0.0, 300.0],
                    'cf_standard_name': 'mole_fraction_of_ozone_in_air'
                },
                'no2': {
                    'description': 'Nitrogen dioxide (NO2) concentration',
                    'data_type': 'float32',
                    'units': 'ppb', 
                    'valid_range': [0.0, 200.0],
                    'cf_standard_name': 'mole_fraction_of_nitrogen_dioxide_in_air'
                },
                'so2': {
                    'description': 'Sulfur dioxide (SO2) concentration',
                    'data_type': 'float32',
                    'units': 'ppb',
                    'valid_range': [0.0, 1000.0],
                    'cf_standard_name': 'mole_fraction_of_sulfur_dioxide_in_air'
                },
                'co': {
                    'description': 'Carbon monoxide (CO) concentration',
                    'data_type': 'float32',
                    'units': 'ppm',
                    'valid_range': [0.0, 50.0],
                    'cf_standard_name': 'mole_fraction_of_carbon_monoxide_in_air'
                },
                'lead': {
                    'description': 'Lead (Pb) concentration in PM10',
                    'data_type': 'float32',
                    'units': 'µg/m³',
                    'valid_range': [0.0, 10.0],
                    'cf_standard_name': 'mass_concentration_of_lead_dry_aerosol_particles_in_air'
                }
            }
            
            bands_dict.update(pollutant_bands)
            
            # Meteorological bands (available at some AQS sites)
            met_bands = {
                'wind_speed': {
                    'description': 'Wind speed at monitoring site',
                    'data_type': 'float32',
                    'units': 'm/s',
                    'valid_range': [0.0, 50.0],
                    'cf_standard_name': 'wind_speed'
                },
                'wind_direction': {
                    'description': 'Wind direction at monitoring site',
                    'data_type': 'float32',
                    'units': 'degrees',
                    'valid_range': [0.0, 360.0],
                    'cf_standard_name': 'wind_from_direction'
                },
                'temperature': {
                    'description': 'Ambient air temperature at monitoring site',
                    'data_type': 'float32',
                    'units': 'degC',
                    'valid_range': [-50.0, 60.0],
                    'cf_standard_name': 'air_temperature'
                },
                'relative_humidity': {
                    'description': 'Relative humidity at monitoring site',
                    'data_type': 'float32',
                    'units': 'percent',
                    'valid_range': [0.0, 100.0],
                    'cf_standard_name': 'relative_humidity'
                },
                'barometric_pressure': {
                    'description': 'Barometric pressure at monitoring site',
                    'data_type': 'float32',
                    'units': 'hPa',
                    'valid_range': [800.0, 1100.0],
                    'cf_standard_name': 'air_pressure'
                }
            }
            
            bands_dict.update(met_bands)
            
            # Data quality bands
            quality_bands = {
                'data_completeness': {
                    'description': 'Data completeness score (0-1)',
                    'data_type': 'float32',
                    'units': 'dimensionless',
                    'valid_range': [0.0, 1.0],
                    'cf_standard_name': None
                },
                'measurement_uncertainty': {
                    'description': 'Measurement uncertainty estimate',
                    'data_type': 'float32', 
                    'units': 'percent',
                    'valid_range': [0.0, 100.0],
                    'cf_standard_name': None
                },
                'site_density': {
                    'description': 'Monitoring site density per 1000 km²',
                    'data_type': 'float32',
                    'units': 'sites/1000km²',
                    'valid_range': [0.0, 100.0],
                    'cf_standard_name': None
                }
            }
            
            bands_dict.update(quality_bands)
            
            # US spatial extent
            spatial_extent = {
                "type": "Polygon",
                "coordinates": [[[-180, 15], [-50, 15], [-50, 72], [-180, 72], [-180, 15]]]
            }
            
            metadata = create_earth_engine_style_metadata(
                asset_id=asset_id,
                title=title,
                description=description.strip(),
                temporal_extent=temporal_extent,
                spatial_extent=spatial_extent,
                bands=bands_dict,
                provider_name="U.S. Environmental Protection Agency",
                provider_url="https://www.epa.gov/aqs"
            )
            
            # Add EPA AQS-specific properties
            if metadata:
                metadata.properties.update({
                    'epa_aqs:criteria_pollutants': list(self.CRITERIA_POLLUTANTS.keys()),
                    'epa_aqs:temporal_resolution': ['hourly', 'daily', 'monthly'],
                    'epa_aqs:site_types': ['urban', 'suburban', 'rural', 'industrial'],
                    'epa_aqs:quality_assurance': 'EPA quality assurance procedures',
                    'epa_aqs:data_availability': 'Real-time and historical',
                    'system:domain': 'air_quality',
                    'system:data_type': 'monitoring_observations',
                    'system:update_frequency': 'hourly'
                })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced metadata for EPA AQS: {e}")
            return None