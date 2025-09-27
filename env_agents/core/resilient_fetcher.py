"""
Resilient Data Fetcher for Environmental Services

Robust data retrieval with multi-tier fallbacks, error recovery,
intelligent retries, and comprehensive diagnostics.
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .service_registry import ServiceRegistry
from .metadata_schema import ServiceMetadata
from ..adapters.base import BaseAdapter, RequestSpec

logger = logging.getLogger(__name__)


class FetchStatus(Enum):
    """Status of a fetch operation"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"


class FallbackStrategy(Enum):
    """Fallback strategy types"""
    TEMPORAL_EXPANSION = "temporal_expansion"
    SPATIAL_SIMPLIFICATION = "spatial_simplification"
    PARAMETER_REDUCTION = "parameter_reduction"
    ALTERNATIVE_SERVICE = "alternative_service"
    CACHED_RESULT = "cached_result"


@dataclass
class FetchResult:
    """Result of a data fetch operation"""
    status: FetchStatus
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    fallbacks_used: List[FallbackStrategy] = field(default_factory=list)
    response_time: float = 0.0
    error_details: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_success(self) -> bool:
        """Check if fetch was successful"""
        return self.status in [FetchStatus.SUCCESS, FetchStatus.PARTIAL_SUCCESS]
    
    @property  
    def has_data(self) -> bool:
        """Check if result contains data"""
        return self.data is not None and not self.data.empty


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    backoff_max: float = 60.0
    retry_on_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies"""
    enable_temporal_expansion: bool = True
    enable_spatial_simplification: bool = True
    enable_parameter_reduction: bool = True
    enable_alternative_services: bool = True
    enable_cached_results: bool = True
    
    # Thresholds for triggering fallbacks
    temporal_expansion_factor: float = 2.0  # Expand time range by this factor
    max_alternative_services: int = 2
    cache_max_age_hours: int = 24


class ResilientDataFetcher:
    """
    Robust data fetcher with comprehensive error handling and fallback strategies.
    
    Addresses the critical reliability issues identified in testing:
    - 67% government service failure rate
    - Authentication problems
    - Timeout issues
    - Poor error diagnostics
    """
    
    def __init__(self, 
                 registry: ServiceRegistry,
                 adapters: Dict[str, BaseAdapter],
                 retry_config: Optional[RetryConfig] = None,
                 fallback_config: Optional[FallbackConfig] = None):
        self.registry = registry
        self.adapters = adapters
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        
        # Setup session with retry configuration
        self.session = self._create_resilient_session()
        
        # Cache for fallback results
        self._result_cache: Dict[str, Tuple[FetchResult, datetime]] = {}
        
        # Statistics tracking
        self._fetch_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallbacks_used': 0,
            'avg_response_time': 0.0
        }
    
    def fetch(self, service_id: str, spec: RequestSpec) -> FetchResult:
        """
        Fetch data with comprehensive error handling and fallbacks.
        
        Args:
            service_id: ID of the service to fetch from
            spec: Request specification
            
        Returns:
            FetchResult with data, diagnostics, and fallback information
        """
        start_time = time.time()
        self._fetch_stats['total_requests'] += 1
        
        # Get service metadata and adapter
        metadata = self.registry.get_service(service_id)
        adapter = self.adapters.get(service_id)
        
        if not metadata or not adapter:
            return FetchResult(
                status=FetchStatus.FAILED,
                error_details=f"Service not found: {service_id}",
                response_time=time.time() - start_time
            )
        
        # Try primary fetch
        result = self._attempt_primary_fetch(adapter, spec, metadata)
        
        # Apply fallback strategies if primary fetch failed
        if not result.is_success and self.fallback_config:
            result = self._apply_fallback_strategies(adapter, spec, metadata, result)
        
        # Update statistics and service health
        result.response_time = time.time() - start_time
        self._update_statistics(result)
        self.registry.update_service_health(
            service_id, result.is_success, result.response_time, result.error_details
        )
        
        # Cache successful results for potential fallback use
        if result.is_success and self.fallback_config.enable_cached_results:
            cache_key = self._generate_cache_key(service_id, spec)
            self._result_cache[cache_key] = (result, datetime.now())
        
        return result
    
    async def fetch_async(self, service_id: str, spec: RequestSpec) -> FetchResult:
        """Async version of fetch for concurrent operations"""
        # Run in thread pool to avoid blocking
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.fetch, service_id, spec)
            return await asyncio.wrap_future(future)
    
    def fetch_multiple(self, requests: List[Tuple[str, RequestSpec]]) -> List[FetchResult]:
        """
        Fetch from multiple services with intelligent coordination.
        
        Args:
            requests: List of (service_id, spec) tuples
            
        Returns:
            List of FetchResult objects
        """
        results = []
        
        # Sort requests by service reliability (best first)
        sorted_requests = self._sort_by_reliability(requests)
        
        for service_id, spec in sorted_requests:
            result = self.fetch(service_id, spec)
            results.append(result)
            
            # Early termination if we have sufficient successful results
            successful_results = sum(1 for r in results if r.is_success)
            if successful_results >= 3:  # Configurable threshold
                break
        
        return results
    
    async def fetch_multiple_async(self, 
                                  requests: List[Tuple[str, RequestSpec]],
                                  max_concurrent: int = 5) -> List[FetchResult]:
        """Async version of fetch_multiple with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(service_id: str, spec: RequestSpec):
            async with semaphore:
                return await self.fetch_async(service_id, spec)
        
        tasks = [fetch_with_semaphore(service_id, spec) for service_id, spec in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _attempt_primary_fetch(self, adapter: BaseAdapter, spec: RequestSpec, 
                              metadata: ServiceMetadata) -> FetchResult:
        """Attempt primary data fetch with retries"""
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Pre-fetch validation
                validation_issues = self._validate_request(spec, metadata)
                if validation_issues:
                    return FetchResult(
                        status=FetchStatus.FAILED,
                        error_details=f"Request validation failed: {validation_issues}",
                        warnings=validation_issues
                    )
                
                # Apply rate limiting
                self._apply_rate_limiting(metadata)
                
                # Perform fetch
                data = adapter.fetch(spec)
                
                # Validate response
                if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                    if attempt < self.retry_config.max_attempts - 1:
                        self._wait_between_retries(attempt)
                        continue
                    
                    return FetchResult(
                        status=FetchStatus.FAILED,
                        error_details="No data returned from service",
                        warnings=["Service returned empty result"]
                    )
                
                # Success case
                diagnostics = self._generate_diagnostics(spec, data, metadata)
                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=data,
                    diagnostics=diagnostics,
                    metadata={'service': metadata.service_id, 'version': metadata.version}
                )
                
            except requests.exceptions.Timeout as e:
                if attempt < self.retry_config.max_attempts - 1:
                    self._wait_between_retries(attempt)
                    continue
                return FetchResult(
                    status=FetchStatus.TIMEOUT,
                    error_details=f"Request timeout: {str(e)}"
                )
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    return FetchResult(
                        status=FetchStatus.AUTH_ERROR,
                        error_details=f"Authentication failed: {str(e)}"
                    )
                elif e.response.status_code == 429:
                    return FetchResult(
                        status=FetchStatus.RATE_LIMITED,
                        error_details=f"Rate limited: {str(e)}"
                    )
                elif e.response.status_code in self.retry_config.retry_on_status:
                    if attempt < self.retry_config.max_attempts - 1:
                        self._wait_between_retries(attempt)
                        continue
                
                return FetchResult(
                    status=FetchStatus.FAILED,
                    error_details=f"HTTP error: {str(e)}"
                )
                
            except requests.exceptions.ConnectionError as e:
                if attempt < self.retry_config.max_attempts - 1 and self.retry_config.retry_on_connection_error:
                    self._wait_between_retries(attempt)
                    continue
                return FetchResult(
                    status=FetchStatus.SERVICE_UNAVAILABLE,
                    error_details=f"Connection error: {str(e)}"
                )
                
            except Exception as e:
                logger.error(f"Unexpected error fetching from {metadata.service_id}: {e}")
                if attempt < self.retry_config.max_attempts - 1:
                    self._wait_between_retries(attempt)
                    continue
                    
                return FetchResult(
                    status=FetchStatus.FAILED,
                    error_details=f"Unexpected error: {str(e)}"
                )
        
        return FetchResult(
            status=FetchStatus.FAILED,
            error_details=f"All {self.retry_config.max_attempts} attempts failed"
        )
    
    def _apply_fallback_strategies(self, adapter: BaseAdapter, spec: RequestSpec,
                                 metadata: ServiceMetadata, 
                                 primary_result: FetchResult) -> FetchResult:
        """Apply fallback strategies when primary fetch fails"""
        
        fallback_attempts = []
        
        # Strategy 1: Check cache first
        if self.fallback_config.enable_cached_results:
            cached_result = self._try_cached_result(metadata.service_id, spec)
            if cached_result:
                cached_result.fallbacks_used.append(FallbackStrategy.CACHED_RESULT)
                return cached_result
        
        # Strategy 2: Temporal expansion (relax time constraints)
        if (self.fallback_config.enable_temporal_expansion and 
            spec.time_range and primary_result.status != FetchStatus.AUTH_ERROR):
            
            expanded_result = self._try_temporal_expansion(adapter, spec, metadata)
            if expanded_result.is_success:
                expanded_result.fallbacks_used.append(FallbackStrategy.TEMPORAL_EXPANSION)
                return expanded_result
            fallback_attempts.append(expanded_result)
        
        # Strategy 3: Parameter reduction (fewer variables)
        if (self.fallback_config.enable_parameter_reduction and 
            len(spec.variables or []) > 1):
            
            reduced_result = self._try_parameter_reduction(adapter, spec, metadata)
            if reduced_result.is_success:
                reduced_result.fallbacks_used.append(FallbackStrategy.PARAMETER_REDUCTION)
                return reduced_result
            fallback_attempts.append(reduced_result)
        
        # Strategy 4: Spatial simplification (point instead of region)
        if (self.fallback_config.enable_spatial_simplification and 
            spec.geometry and spec.geometry.type != 'point'):
            
            simplified_result = self._try_spatial_simplification(adapter, spec, metadata)
            if simplified_result.is_success:
                simplified_result.fallbacks_used.append(FallbackStrategy.SPATIAL_SIMPLIFICATION)
                return simplified_result
            fallback_attempts.append(simplified_result)
        
        # Strategy 5: Alternative services
        if self.fallback_config.enable_alternative_services:
            alt_result = self._try_alternative_services(spec, metadata)
            if alt_result and alt_result.is_success:
                alt_result.fallbacks_used.append(FallbackStrategy.ALTERNATIVE_SERVICE)
                return alt_result
        
        # All fallbacks failed - return primary result with fallback diagnostics
        primary_result.diagnostics['fallback_attempts'] = len(fallback_attempts)
        primary_result.diagnostics['fallback_errors'] = [
            f.error_details for f in fallback_attempts if f.error_details
        ]
        
        return primary_result
    
    def _try_cached_result(self, service_id: str, spec: RequestSpec) -> Optional[FetchResult]:
        """Try to return a cached result if available and fresh"""
        cache_key = self._generate_cache_key(service_id, spec)
        cached_entry = self._result_cache.get(cache_key)
        
        if cached_entry:
            cached_result, cached_time = cached_entry
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            
            if age_hours <= self.fallback_config.cache_max_age_hours:
                # Return a copy with updated metadata
                cached_copy = FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=cached_result.data.copy() if cached_result.data is not None else None,
                    metadata=cached_result.metadata.copy(),
                    diagnostics=cached_result.diagnostics.copy(),
                    warnings=[f"Using cached result from {age_hours:.1f} hours ago"]
                )
                return cached_copy
        
        return None
    
    def _try_temporal_expansion(self, adapter: BaseAdapter, spec: RequestSpec,
                              metadata: ServiceMetadata) -> FetchResult:
        """Try expanding the temporal range"""
        if not spec.time_range:
            return FetchResult(status=FetchStatus.FAILED, error_details="No time range to expand")
        
        start_date, end_date = spec.time_range
        
        # Expand range by configured factor
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            range_days = (end_dt - start_dt).days
            
            expansion_days = int(range_days * self.fallback_config.temporal_expansion_factor)
            new_start = start_dt - pd.Timedelta(days=expansion_days // 2)
            new_end = end_dt + pd.Timedelta(days=expansion_days // 2)
            
            expanded_spec = RequestSpec(
                geometry=spec.geometry,
                variables=spec.variables,
                time_range=(new_start.strftime('%Y-%m-%d'), new_end.strftime('%Y-%m-%d')),
                filters=spec.filters
            )
            
            return self._attempt_primary_fetch(adapter, expanded_spec, metadata)
            
        except Exception as e:
            return FetchResult(
                status=FetchStatus.FAILED,
                error_details=f"Temporal expansion failed: {str(e)}"
            )
    
    def _try_parameter_reduction(self, adapter: BaseAdapter, spec: RequestSpec,
                               metadata: ServiceMetadata) -> FetchResult:
        """Try reducing the number of parameters requested"""
        if not spec.variables or len(spec.variables) <= 1:
            return FetchResult(status=FetchStatus.FAILED, error_details="Cannot reduce parameters")
        
        # Try with just the first (most important) variable
        reduced_spec = RequestSpec(
            geometry=spec.geometry,
            variables=[spec.variables[0]],
            time_range=spec.time_range,
            filters=spec.filters
        )
        
        return self._attempt_primary_fetch(adapter, reduced_spec, metadata)
    
    def _try_spatial_simplification(self, adapter: BaseAdapter, spec: RequestSpec,
                                  metadata: ServiceMetadata) -> FetchResult:
        """Try simplifying spatial request to a point"""
        if not spec.geometry or spec.geometry.type == 'point':
            return FetchResult(status=FetchStatus.FAILED, error_details="Cannot simplify geometry")
        
        # Convert to centroid point
        try:
            if spec.geometry.type == 'polygon':
                # Use first coordinate as simple approximation
                coords = spec.geometry.coordinates[0]
                center_lon = sum(c[0] for c in coords) / len(coords)
                center_lat = sum(c[1] for c in coords) / len(coords)
            else:
                # Use first coordinate
                center_lon, center_lat = spec.geometry.coordinates[0], spec.geometry.coordinates[1]
            
            from ..core.models import Geometry
            simplified_spec = RequestSpec(
                geometry=Geometry(type='point', coordinates=[center_lon, center_lat]),
                variables=spec.variables,
                time_range=spec.time_range,
                filters=spec.filters
            )
            
            return self._attempt_primary_fetch(adapter, simplified_spec, metadata)
            
        except Exception as e:
            return FetchResult(
                status=FetchStatus.FAILED,
                error_details=f"Spatial simplification failed: {str(e)}"
            )
    
    def _try_alternative_services(self, spec: RequestSpec, 
                                metadata: ServiceMetadata) -> Optional[FetchResult]:
        """Try alternative services that provide similar data"""
        
        # Find services with overlapping capabilities
        alternatives = []
        for service_id, service_meta in self.registry.get_all_metadata().items():
            if service_id == metadata.service_id:
                continue
                
            # Check domain overlap
            domain_overlap = set(metadata.capabilities.domains) & set(service_meta.capabilities.domains)
            if not domain_overlap:
                continue
                
            # Check if alternative service has better reliability
            if service_meta.quality_metrics.reliability_score > metadata.quality_metrics.reliability_score:
                alternatives.append((service_id, service_meta))
        
        # Sort by reliability and try up to max_alternative_services
        alternatives.sort(key=lambda x: x[1].quality_metrics.reliability_score, reverse=True)
        alternatives = alternatives[:self.fallback_config.max_alternative_services]
        
        for alt_service_id, alt_metadata in alternatives:
            alt_adapter = self.adapters.get(alt_service_id)
            if alt_adapter:
                result = self._attempt_primary_fetch(alt_adapter, spec, alt_metadata)
                if result.is_success:
                    result.metadata['alternative_service'] = alt_service_id
                    result.warnings.append(f"Used alternative service: {alt_service_id}")
                    return result
        
        return None
    
    def _validate_request(self, spec: RequestSpec, metadata: ServiceMetadata) -> List[str]:
        """Validate request against service capabilities"""
        issues = []
        
        # Check if requested variables are available
        if spec.variables:
            available_vars = {var.id for var in metadata.capabilities.variables}
            available_vars.update({var.canonical for var in metadata.capabilities.variables if var.canonical})
            
            unavailable = set(spec.variables) - available_vars
            if unavailable:
                issues.append(f"Unavailable variables: {list(unavailable)}")
        
        # Check spatial constraints
        if spec.geometry and metadata.capabilities.spatial_coverage:
            # Basic validation - could be enhanced
            if spec.geometry.type == 'polygon':
                issues.append("Polygon requests may not be supported by all services")
        
        # Check temporal constraints  
        if spec.time_range and metadata.capabilities.temporal_coverage:
            # Could add date range validation against service coverage
            pass
            
        return issues
    
    def _apply_rate_limiting(self, metadata: ServiceMetadata):
        """Apply rate limiting based on service configuration"""
        # Simple rate limiting implementation
        # Could be enhanced with more sophisticated algorithms
        if hasattr(metadata, 'rate_limiting') and metadata.rate_limiting:
            if metadata.rate_limiting.requests_per_second:
                time.sleep(1.0 / metadata.rate_limiting.requests_per_second)
    
    def _wait_between_retries(self, attempt: int):
        """Wait between retry attempts with exponential backoff"""
        wait_time = min(
            self.retry_config.backoff_factor ** attempt,
            self.retry_config.backoff_max
        )
        time.sleep(wait_time)
    
    def _generate_diagnostics(self, spec: RequestSpec, data: pd.DataFrame, 
                            metadata: ServiceMetadata) -> Dict[str, Any]:
        """Generate diagnostic information about the fetch"""
        diagnostics = {
            'request_timestamp': datetime.now().isoformat(),
            'service_id': metadata.service_id,
            'service_version': metadata.version,
            'rows_returned': len(data) if data is not None else 0,
            'columns_returned': list(data.columns) if data is not None else [],
            'requested_variables': spec.variables or [],
            'time_range_requested': spec.time_range,
            'spatial_type': spec.geometry.type if spec.geometry else None
        }
        
        # Add data quality metrics
        if data is not None and not data.empty:
            diagnostics['data_completeness'] = (1 - data.isnull().sum().sum() / data.size) * 100
            
            # Count unique observations, excluding unhashable columns (like dict columns)
            try:
                # First try normal drop_duplicates
                diagnostics['unique_observations'] = len(data.drop_duplicates())
            except TypeError as e:
                # If it fails due to unhashable types, exclude problematic columns
                if 'unhashable' in str(e):
                    # Exclude columns that typically contain dicts
                    hashable_cols = [col for col in data.columns 
                                   if col not in ['attributes', 'provenance'] and 
                                   not data[col].apply(lambda x: isinstance(x, (dict, list))).any()]
                    if hashable_cols:
                        diagnostics['unique_observations'] = len(data[hashable_cols].drop_duplicates())
                    else:
                        diagnostics['unique_observations'] = len(data)  # Fallback to total rows
                else:
                    raise  # Re-raise if it's a different TypeError
            
            # Time range coverage if time column exists
            if 'time' in data.columns:
                diagnostics['temporal_coverage'] = {
                    'start': data['time'].min(),
                    'end': data['time'].max(),
                    'count': len(data['time'].unique())
                }
        
        return diagnostics
    
    def _generate_cache_key(self, service_id: str, spec: RequestSpec) -> str:
        """Generate cache key for request"""
        # Properly serialize geometry to avoid unhashable type errors
        geom_str = "no_geom"
        if spec.geometry:
            try:
                # Convert coordinates to string representation that's hashable
                coords_str = str(tuple(spec.geometry.coordinates)) if isinstance(spec.geometry.coordinates, (list, tuple)) else str(spec.geometry.coordinates)
                geom_str = f"{spec.geometry.type}:{coords_str}"
            except Exception as e:
                # Fallback to basic representation
                geom_str = f"{spec.geometry.type}:coords"
        
        key_parts = [
            service_id,
            geom_str,
            ",".join(spec.variables or []),
            f"{spec.time_range[0]}-{spec.time_range[1]}" if spec.time_range else "no_time"
        ]
        return "|".join(key_parts)
    
    def _sort_by_reliability(self, requests: List[Tuple[str, RequestSpec]]) -> List[Tuple[str, RequestSpec]]:
        """Sort requests by service reliability score"""
        def get_reliability(service_id: str) -> float:
            metadata = self.registry.get_service(service_id)
            return metadata.quality_metrics.reliability_score if metadata else 0.0
        
        return sorted(requests, key=lambda x: get_reliability(x[0]), reverse=True)
    
    def _update_statistics(self, result: FetchResult):
        """Update internal statistics"""
        if result.is_success:
            self._fetch_stats['successful_requests'] += 1
        else:
            self._fetch_stats['failed_requests'] += 1
            
        if result.fallbacks_used:
            self._fetch_stats['fallbacks_used'] += 1
            
        # Update average response time (simple moving average)
        current_avg = self._fetch_stats['avg_response_time']
        total_requests = self._fetch_stats['total_requests']
        self._fetch_stats['avg_response_time'] = (
            (current_avg * (total_requests - 1) + result.response_time) / total_requests
        )
    
    def _create_resilient_session(self) -> requests.Session:
        """Create requests session with retry configuration"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.retry_config.max_attempts,
            status_forcelist=self.retry_config.retry_on_status,
            backoff_factor=self.retry_config.backoff_factor,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get fetcher performance statistics"""
        total = self._fetch_stats['total_requests']
        if total == 0:
            return self._fetch_stats.copy()
            
        stats = self._fetch_stats.copy()
        stats['success_rate'] = (stats['successful_requests'] / total) * 100
        stats['failure_rate'] = (stats['failed_requests'] / total) * 100
        stats['fallback_usage_rate'] = (stats['fallbacks_used'] / total) * 100
        
        return stats
    
    def clear_cache(self):
        """Clear the result cache"""
        self._result_cache.clear()
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        fresh_entries = sum(1 for _, (_, timestamp) in self._result_cache.items() 
                          if (now - timestamp).total_seconds() / 3600 <= self.fallback_config.cache_max_age_hours)
        
        return {
            'total_entries': len(self._result_cache),
            'fresh_entries': fresh_entries,
            'stale_entries': len(self._result_cache) - fresh_entries,
            'cache_max_age_hours': self.fallback_config.cache_max_age_hours
        }