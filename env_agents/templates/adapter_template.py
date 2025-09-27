"""
Base adapter template for environmental data services

This template provides the structure for implementing new environmental data adapters
following the gold standard pattern established by NWIS, OpenAQ, and NASA POWER.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import logging

from ..base import BaseAdapter
from ...core.models import RequestSpec
from ...core.errors import FetchError


class EnvironmentalServiceAdapter(BaseAdapter):
    """
    Template adapter for environmental data services
    
    Replace 'EnvironmentalService' with your service name and implement the required methods.
    Follow the established patterns from the gold standard services.
    """
    
    # Required service metadata - customize for your service
    DATASET = "ENVIRONMENTAL_SERVICE"          # Unique dataset identifier
    SOURCE_URL = "https://api.example.com"     # Base URL for the service
    SOURCE_VERSION = "v1"                      # Version of the API being used
    LICENSE = "https://example.com/license"    # License or terms of service URL
    REQUIRES_API_KEY = False                   # Whether service requires authentication
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.DATASET}")
        
        # Service-specific configuration
        self._rate_limit_delay = 1.0  # seconds between requests
        self._max_retries = 3
        self._timeout = 60  # seconds
        
        # Cache for parameter catalogs (optional)
        self._parameter_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration_hours = 24  # How long to cache parameter data
    
    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return service capabilities including available variables
        
        This method should:
        1. Discover available parameters (via harvest or hardcoded list)
        2. Return standardized capability information
        3. Handle failures gracefully with fallback data
        """
        try:
            # Try to discover parameters dynamically
            variables = self._discover_variables(extra)
            discovery_method = "dynamic_discovery"
            
        except Exception as e:
            self.logger.warning(f"Dynamic discovery failed: {e}")
            # Fallback to hardcoded variables
            variables = self._get_fallback_variables()
            discovery_method = "fallback_list"
        
        return {
            "dataset": self.DATASET,
            "geometry": ["point", "bbox"],  # Supported geometry types
            "requires_time_range": True,    # Whether time range is required
            "requires_api_key": self.REQUIRES_API_KEY,
            "variables": variables,
            "attributes_schema": self._get_attributes_schema(),
            "rate_limits": {
                "requests_per_minute": 60,  # Adjust based on service
                "notes": "Implement appropriate backoff on 429/5xx"
            },
            "temporal_resolution": "varies",  # e.g., "hourly", "daily", "instantaneous"
            "spatial_coverage": "global",     # or specify regions
            "discovery_method": discovery_method,
            "notes": f"Discovered {len(variables)} variables via {discovery_method}"
        }
    
    def harvest(self) -> List[Dict[str, Any]]:
        """
        Optional: Harvest native parameter catalog for semantic discovery
        
        This method enables automatic parameter discovery and mapping.
        Return format should match ServiceCapability structure.
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                return self._parameter_cache or []
            
            # Harvest fresh parameter data
            parameters = self._harvest_native_parameters()
            
            # Update cache
            self._parameter_cache = parameters
            self._cache_timestamp = datetime.now(timezone.utc)
            
            return parameters
            
        except Exception as e:
            self.logger.error(f"Parameter harvest failed: {e}")
            return []
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """
        Fetch data rows from the service
        
        This is the main implementation method that:
        1. Validates the request specification
        2. Constructs appropriate API calls
        3. Handles pagination, retries, and rate limiting
        4. Returns standardized row data
        """
        # 1. Validate request
        self._validate_request(spec)
        
        # 2. Process geometry
        spatial_params = self._process_geometry(spec.geometry)
        
        # 3. Process time range
        temporal_params = self._process_time_range(spec.time_range)
        
        # 4. Process variables
        variable_params = self._process_variables(spec.variables)
        
        # 5. Build API parameters
        api_params = {
            **spatial_params,
            **temporal_params,
            **variable_params,
            **self._get_extra_params(spec.extra)
        }
        
        # 6. Fetch data with retry logic
        raw_data = self._fetch_with_retry(api_params)
        
        # 7. Parse and normalize data
        rows = self._parse_response_data(raw_data, spec)
        
        # 8. Add service-specific attributes and provenance
        self._enrich_rows(rows, spec, api_params)
        
        return rows
    
    # Helper methods to implement in your adapter
    
    def _discover_variables(self, extra: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover available variables from service API
        
        Return list of variable dictionaries with keys:
        - canonical: suggested canonical variable name
        - platform: native parameter ID
        - unit: unit of measurement
        - description: human-readable description
        """
        # Example implementation:
        # 1. Call service parameter/catalog endpoint
        # 2. Parse response
        # 3. Convert to standardized format
        
        raise NotImplementedError("Implement variable discovery for your service")
    
    def _get_fallback_variables(self) -> List[Dict[str, Any]]:
        """
        Return hardcoded variable list as fallback
        
        This ensures the adapter works even when discovery fails
        """
        # Define a minimal set of key variables for your service
        return [
            {
                "canonical": "example:parameter_1",
                "platform": "param1",
                "unit": "units",
                "description": "Example parameter 1"
            }
            # Add more variables specific to your service
        ]
    
    def _get_attributes_schema(self) -> Dict[str, Dict[str, str]]:
        """
        Define schema for service-specific attributes
        
        These attributes capture service-specific metadata
        that doesn't fit in the core columns
        """
        return {
            "native_parameter": {"type": "string", "description": "Original parameter ID"},
            "measurement_method": {"type": "string", "description": "How measurement was obtained"},
            "quality_flags": {"type": "array", "description": "Data quality indicators"},
            # Add more service-specific attributes
        }
    
    def _harvest_native_parameters(self) -> List[Dict[str, Any]]:
        """
        Harvest native parameter catalog from service API
        
        Return list formatted for ServiceCapability:
        - service: service name
        - native_id: parameter ID  
        - label: parameter name/label
        - unit: unit of measurement
        - description: full description
        - domain: data domain (air, water, etc.)
        """
        # Implementation example:
        # 1. Call service metadata/parameters endpoint
        # 2. Parse parameter catalog
        # 3. Convert to ServiceCapability format
        
        raise NotImplementedError("Implement parameter harvesting for your service")
    
    def _validate_request(self, spec: RequestSpec):
        """Validate request specification against service capabilities"""
        if not spec.geometry:
            raise FetchError(f"{self.DATASET}: geometry is required")
        
        if spec.geometry.type not in ["point", "bbox"]:
            raise FetchError(f"{self.DATASET}: unsupported geometry type {spec.geometry.type}")
        
        if not spec.time_range:
            raise FetchError(f"{self.DATASET}: time_range is required")
        
        # Add service-specific validation
    
    def _process_geometry(self, geometry) -> Dict[str, Any]:
        """Convert geometry to service-specific spatial parameters"""
        if geometry.type == "point":
            lon, lat = geometry.coordinates
            return {
                "longitude": lon,
                "latitude": lat
            }
        elif geometry.type == "bbox":
            minx, miny, maxx, maxy = geometry.coordinates
            return {
                "bbox": f"{minx},{miny},{maxx},{maxy}"
            }
        else:
            raise FetchError(f"Unsupported geometry type: {geometry.type}")
    
    def _process_time_range(self, time_range: Optional[tuple]) -> Dict[str, Any]:
        """Convert time range to service-specific temporal parameters"""
        if not time_range:
            return {}
        
        start, end = time_range
        
        # Convert to service-expected format
        return {
            "start_date": start.replace("T", " ").replace("Z", ""),
            "end_date": end.replace("T", " ").replace("Z", "")
        }
    
    def _process_variables(self, variables: Optional[List[str]]) -> Dict[str, Any]:
        """Convert requested variables to service-specific parameter codes"""
        if not variables or variables == ["*"]:
            return {}  # Request all parameters
        
        # Map canonical variables to native parameter codes
        # This would typically use rule packs or registry mappings
        native_params = []
        for var in variables:
            # Example mapping logic
            if var.startswith("example:"):
                native_params.append(var.split(":", 1)[1])
            else:
                native_params.append(var)  # Pass through if already native
        
        return {
            "parameters": ",".join(native_params)
        }
    
    def _get_extra_params(self, extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Process extra parameters from request spec"""
        if not extra:
            return {}
        
        # Extract service-specific parameters
        service_params = {}
        
        # Example: API key handling
        if self.REQUIRES_API_KEY:
            api_key = extra.get("api_key") or self._get_api_key_from_env()
            if api_key:
                service_params["api_key"] = api_key
        
        # Add other service-specific parameters
        if "quality_level" in extra:
            service_params["quality"] = extra["quality_level"]
        
        return service_params
    
    def _fetch_with_retry(self, params: Dict[str, Any]) -> Any:
        """
        Fetch data from service API with retry logic
        """
        import time
        import requests
        
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                # Add rate limiting
                if attempt > 0:
                    time.sleep(self._rate_limit_delay * (2 ** (attempt - 1)))
                
                # Make API call
                response = self._session.get(
                    self.SOURCE_URL + "/data",  # Adjust endpoint
                    params=params,
                    timeout=self._timeout
                )
                
                # Handle different response types
                if response.status_code == 429:  # Rate limited
                    time.sleep(self._rate_limit_delay * 2)
                    continue
                elif response.status_code >= 500:  # Server error
                    time.sleep(self._rate_limit_delay)
                    continue
                
                response.raise_for_status()
                
                # Return parsed response
                if response.headers.get('content-type', '').startswith('application/json'):
                    return response.json()
                else:
                    return response.text
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise FetchError(f"{self.DATASET} API call failed after {self._max_retries} attempts: {last_exception}")
    
    def _parse_response_data(self, raw_data: Any, spec: RequestSpec) -> List[Dict[str, Any]]:
        """
        Parse raw API response into standardized row format
        
        Each row should contain the core columns or their raw equivalents
        """
        rows = []
        
        # Parse according to your service's response format
        # This is highly service-specific
        
        # Example for JSON response:
        if isinstance(raw_data, dict):
            data_points = raw_data.get('data', [])
            
            for point in data_points:
                row = {
                    "dataset": self.DATASET,
                    "source_url": self.SOURCE_URL,
                    "source_version": self.SOURCE_VERSION,
                    "license": self.LICENSE,
                    "geometry_type": spec.geometry.type,
                    "latitude": point.get('lat'),
                    "longitude": point.get('lon'),
                    "time": point.get('timestamp'),
                    "variable": point.get('parameter'),  # Will be mapped to canonical
                    "value": point.get('value'),
                    "unit": point.get('unit'),
                    "qc_flag": self._map_quality_flag(point.get('quality')),
                    "attributes": {
                        "native_parameter": point.get('parameter'),
                        "measurement_method": point.get('method')
                    },
                    "provenance": self._build_provenance(spec, raw_data)
                }
                rows.append(row)
        
        return rows
    
    def _enrich_rows(self, rows: List[Dict[str, Any]], spec: RequestSpec, api_params: Dict[str, Any]):
        """
        Add final enrichments to row data
        """
        retrieval_time = datetime.now(timezone.utc).isoformat()
        
        for row in rows:
            # Ensure retrieval timestamp
            if not row.get('retrieval_timestamp'):
                row['retrieval_timestamp'] = retrieval_time
            
            # Add trace information for debugging
            if 'attributes' not in row:
                row['attributes'] = {}
            
            row['attributes']['api_params'] = api_params
            row['attributes']['service_dataset'] = self.DATASET
    
    def _map_quality_flag(self, native_quality: Any) -> str:
        """Map service-specific quality indicators to standardized flags"""
        if not native_quality:
            return "unknown"
        
        # Define mappings for your service
        quality_map = {
            "good": "validated",
            "fair": "provisional", 
            "poor": "flagged",
            # Add service-specific mappings
        }
        
        return quality_map.get(str(native_quality).lower(), "unknown")
    
    def _build_provenance(self, spec: RequestSpec, raw_data: Any) -> Dict[str, Any]:
        """Build provenance information for the data"""
        return self._prov(spec, {
            "dataset": self.DATASET,
            "endpoint": self.SOURCE_URL,
            "upstream_version": self.SOURCE_VERSION,
            "license": self.LICENSE,
            "citation": f"{self.DATASET} Environmental Data Service"
        })
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables"""
        import os
        return os.getenv(f"{self.DATASET}_API_KEY")
    
    def _is_cache_valid(self) -> bool:
        """Check if parameter cache is still valid"""
        if not self._cache_timestamp or not self._parameter_cache:
            return False
        
        age_hours = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds() / 3600
        return age_hours < self._cache_duration_hours