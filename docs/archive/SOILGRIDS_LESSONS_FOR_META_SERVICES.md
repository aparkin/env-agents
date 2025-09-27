# SoilGrids WCS Implementation: Lessons Learned for Environmental Data Services

**Document Version:** 1.0
**Date:** September 21, 2025
**Context:** Extracted from SoilGrids WCS adapter implementation (unitary service)

## Executive Summary

The SoilGrids WCS adapter implementation provides critical lessons for building robust environmental data services in env-agents, both unitary and meta-services. This document extracts architectural patterns, performance strategies, and reliability approaches that can be applied to other complex environmental data adapters.

## Key Architectural Lessons

### 1. **Service Protocol Selection is Critical**

**Lesson:** The choice of underlying protocol can make or break a service adapter.

- **Failed Approach:** REST API with custom parameter handling
- **Successful Approach:** WCS (Web Coverage Service) standard protocol
- **Why WCS Won:** Built-in spatial processing, server-side scaling, standardized error handling

**Meta-Service Application:**
```python
# Prioritize standardized protocols over custom APIs
PROTOCOL_PRIORITY = [
    "WCS",      # Spatial raster data
    "WFS",      # Vector features
    "OGC API",  # Modern RESTful standards
    "Custom API"  # Last resort
]
```

### 2. **Server Auto-Scaling > Client Calculations**

**Lesson:** Let the server handle complexity when possible.

**Working Pattern:**
```python
# Let server scale automatically with pixel limits
params = {
    "scaleSize": f"Long({target_width}),Lat({target_height})",
    # Server automatically determines best resolution
}
```

**Failed Pattern:**
```python
# Manual resolution calculations are fragile
resolution = self._calculate_optimal_resolution(bbox, target_pixels)
# Often fails due to server-side constraints we can't predict
```

**Meta-Service Application:** Design APIs to leverage server-side processing capabilities rather than implementing complex client-side logic.

### 3. **Comprehensive Catalog Caching Strategy**

**Implementation Pattern:**
```python
def _build_catalog(self, force_refresh: bool = False) -> Dict[str, List[str]]:
    cache_file = self.cache_dir / f"{self.service_name}_catalog.json"

    # 7-day cache with metadata
    if not force_refresh and cache_file.exists():
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age < timedelta(days=7):
            # Load cached catalog with metadata
            return self._load_cached_catalog(cache_file)

    # Build fresh catalog with timing metrics
    catalog = self._discover_assets()
    self._save_catalog_with_metadata(catalog, cache_file)
    return catalog
```

**Key Benefits:**
- Reduces 2-3 minute discovery to milliseconds
- Preserves metadata about discovery process
- Handles cache invalidation gracefully
- Consistent with other env-agents services

### 4. **Guard Rails with Progressive Fallback**

**Architecture Pattern:**
```python
class GuardRailSystem:
    def _get_strategy(self, request_size):
        if request_size <= self.max_direct:
            return "direct"           # Native resolution
        elif request_size <= self.max_resampled:
            return "resampled"        # Server-side scaling
        else:
            return "tiled"            # Break into chunks

    def _fetch_with_backoff(self, strategy, properties):
        backoff_levels = [1.0, 0.75, 0.5, 0.25, 0.1]  # Progressive resolution reduction

        for level in backoff_levels:
            try:
                return self._execute_strategy(strategy, properties, resolution_factor=level)
            except MemoryError:
                continue  # Try lower resolution
            except NetworkError:
                raise     # Don't retry network issues
```

**Meta-Service Application:** Any service dealing with large datasets should implement tiered strategies with automatic fallback.

### 5. **Circuit Breaker for Service Reliability**

**Implementation:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None

    def __enter__(self):
        if self.is_open:
            raise CircuitBreakerOpen("Service temporarily unavailable")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.failure_count += 1
            self.last_failure_time = time.time()
```

**Benefits for Meta-Services:**
- Prevents cascade failures
- Automatic recovery after timeout
- Graceful degradation to cached data

## Performance and Scalability Insights

### 1. **Pixel-Based Resource Management**

**Key Insight:** For raster services, pixels are the primary resource constraint.

```python
# Effective resource management
def _estimate_resource_requirements(self, bbox, resolution):
    width = abs(bbox[2] - bbox[0]) / resolution
    height = abs(bbox[3] - bbox[1]) / resolution
    estimated_pixels = int(width * height)

    # Memory estimation (rough)
    memory_mb = estimated_pixels * 4 * 1.5 / (1024**2)  # 4 bytes * 1.5 overhead
    return {"pixels": estimated_pixels, "memory_mb": memory_mb}
```

### 2. **Metadata Preservation Across Processing Stages**

**Pattern:**
```python
def _attach_comprehensive_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
    """Attach metadata following user's working code pattern"""
    df.attrs.update({
        "service_metadata": self.SERVICE_METADATA,
        "catalog": self.catalog_cache,
        "endpoint": self.SOURCE_URL,
        "retrieval_method": self.protocol_name,
        "processing_timestamp": datetime.now().isoformat(),
        "guard_rails_applied": True,
        "resolution_strategy": self.last_strategy_used
    })
    return df
```

**Meta-Service Application:** All processing stages should preserve and enhance metadata rather than discarding it.

### 3. **Discovery Optimization Patterns**

**Lesson:** Batch discovery operations and cache aggressively.

```python
def _batch_discovery(self, services: List[str]) -> Dict[str, List[str]]:
    """Discover multiple services in parallel"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(self._discover_single_service, service): service
            for service in services
        }

        results = {}
        for future in as_completed(futures):
            service = futures[future]
            try:
                results[service] = future.result(timeout=60)
            except Exception as e:
                logger.warning(f"Discovery failed for {service}: {e}")
                results[service] = []

        return results
```

## Error Handling and Recovery Strategies

### 1. **Error Classification System**

```python
class ErrorClassifier:
    RECOVERABLE_ERRORS = [
        "memory", "allocate", "too large", "timeout", "temporary"
    ]

    NETWORK_ERRORS = [
        "connection", "network", "unreachable", "dns"
    ]

    AUTHENTICATION_ERRORS = [
        "unauthorized", "forbidden", "authentication", "api key"
    ]

    def classify_error(self, error_msg: str) -> str:
        error_lower = error_msg.lower()

        if any(term in error_lower for term in self.RECOVERABLE_ERRORS):
            return "recoverable"
        elif any(term in error_lower for term in self.NETWORK_ERRORS):
            return "network"
        elif any(term in error_lower for term in self.AUTHENTICATION_ERRORS):
            return "auth"
        else:
            return "unknown"
```

### 2. **Fallback Strategies by Error Type**

```python
def _handle_error_with_strategy(self, error: Exception, context: Dict) -> Any:
    error_type = self.error_classifier.classify_error(str(error))

    if error_type == "recoverable":
        return self._retry_with_reduced_scope(context)
    elif error_type == "network":
        return self._use_cached_fallback(context)
    elif error_type == "auth":
        return self._refresh_credentials_and_retry(context)
    else:
        raise error  # No recovery strategy available
```

## Recommendations for New Environmental Data Services

### 1. **Adopt the WCS Pattern for Spatial Services**

For any service dealing with raster/gridded data (both unitary and meta-services):
- Investigate WCS capabilities first
- Use server-side scaling with pixel limits
- Implement progressive resolution backoff

### 2. **Implement Standard Caching Architecture**

```python
class StandardCachingMixin:
    def __init__(self):
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_max_age = timedelta(days=7)

    def _get_cached_or_fetch(self, cache_key: str, fetch_func: Callable):
        cache_file = self.cache_dir / f"{cache_key}.json"

        if self._is_cache_fresh(cache_file):
            return self._load_cache(cache_file)

        result = fetch_func()
        self._save_cache(result, cache_file)
        return result
```

### 3. **Design for Degraded Service**

Every meta-service should have:
- Circuit breaker implementation
- Cached fallback data
- Progressive capability reduction
- Clear error messaging to users

### 4. **Performance Instrumentation**

```python
class PerformanceTracker:
    def __init__(self):
        self.metrics = {}

    def track_operation(self, operation_name: str, func: Callable, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self.metrics[operation_name] = {
                "duration": time.time() - start_time,
                "status": "success",
                "result_size": len(result) if hasattr(result, '__len__') else None
            }
            return result
        except Exception as e:
            self.metrics[operation_name] = {
                "duration": time.time() - start_time,
                "status": "error",
                "error": str(e)
            }
            raise
```

## Conclusion

The SoilGrids WCS implementation demonstrates that robust environmental data services require:

1. **Protocol-First Design**: Choose standards-based protocols over custom APIs
2. **Server-Side Intelligence**: Leverage server capabilities for scaling and processing
3. **Comprehensive Caching**: 7-day catalog caching with metadata preservation
4. **Progressive Fallback**: Multi-tier strategies with automatic resolution backoff
5. **Circuit Breaking**: Reliability patterns that prevent cascade failures
6. **Metadata Preservation**: Rich metadata attachment throughout the processing pipeline

These patterns should be applied to all future meta-services to ensure reliability, performance, and maintainability in production ECOGNITA deployments.