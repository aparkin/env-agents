# Adapter Review - Best Practices Check

**Date:** 2025-09-29
**Status:** ✅ All adapters following best practices

## Review Criteria

Based on lessons learned from Earth Engine optimization:

1. ✅ **Timeout on blocking API calls**
2. ✅ **Minimize redundant API calls**
3. ✅ **Use correct spatial geometries**
4. ✅ **Graceful error handling with retry**
5. ✅ **Appropriate caching of metadata**

## Adapter Review Summary

### NASA POWER ✅ Good

**Timeout handling:**
```python
response = requests.get(docs_url, timeout=15)
response = requests.get(api_url, timeout=30)
response = requests.get(params_url, timeout=20)
```

**Status:**
- ✅ All HTTP calls have timeout (15-30s)
- ✅ Appropriate timeout values for different operations
- ✅ No blocking operations without timeout

### GBIF ✅ Good

**Timeout handling:**
```python
response = requests.get(docs_url, timeout=10)
response = requests.get(url, params=params, timeout=30)
```

**Status:**
- ✅ All HTTP calls have timeout (10-30s)
- ✅ Higher timeout for data queries vs metadata
- ✅ Clean, straightforward implementation

### OpenAQ ✅ Good

**Timeout handling:**
```python
r = self._rate_limited_get(..., timeout=60)
r = self._rate_limited_get(..., timeout=30)
r = self._rate_limited_get(..., timeout=90)
```

**Status:**
- ✅ All HTTP calls have timeout (30-90s)
- ✅ Rate limiting wrapper for API constraints
- ✅ Higher timeout for complex queries (90s for sensors)

### Earth Engine ✅ Fixed

**Previous issues:**
- ❌ No timeout on `.getInfo()` calls (blocking C extensions)
- ❌ Using uniform 1km buffers instead of actual cluster extents
- ❌ 5 redundant `.getInfo()` calls per query

**Now fixed:**
- ✅ Threading-based timeout (60s) on all `.getInfo()` calls
- ✅ Using actual cluster bounding boxes from DBSCAN
- ✅ Eliminated redundant geometry fetches
- ✅ Only 1 `.getInfo()` call per query (just the data)

## Best Practices Summary

### 1. Timeout Values

**Pattern observed across adapters:**
- **Metadata queries**: 10-20s (fast lookups)
- **Data queries**: 30-60s (computation required)
- **Complex queries**: 60-90s (large result sets)

**Earth Engine:**
- Asset type detection: 20s (metadata)
- Single Image query: 60s (data)
- ImageCollection metadata: 30s (band names)
- ImageCollection data: 90s (time series)

### 2. Rate Limiting

**OpenAQ approach** (good example):
```python
def _rate_limited_get(self, url, **kwargs):
    """Wrapper with rate limiting and retry logic"""
    # Implements exponential backoff
    # Respects API rate limits
    # Returns response or raises exception
```

**Applies to:**
- OpenAQ: Rate-limited public API
- Earth Engine: Quota limits (handled by retry in acquisition script)
- NASA POWER: Generally fast, no rate limits observed
- GBIF: Pagination built-in, no explicit rate limiting needed

### 3. Error Handling Pattern

**All adapters follow similar pattern:**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
except requests.Timeout:
    logger.error(f"Request timed out: {url}")
    raise
except requests.RequestException as e:
    logger.error(f"Request failed: {e}")
    raise
```

**Earth Engine equivalent:**
```python
try:
    stats = run_with_timeout(get_stats, timeout_sec=60)
except TimeoutError as e:
    raise Exception(f"Earth Engine timeout: {e}") from e
```

### 4. Geometry Handling

**Current status:**
- ✅ NASA POWER: Uses bbox from spec
- ✅ GBIF: Uses bbox or point from spec
- ✅ OpenAQ: Uses bbox or point from spec
- ✅ Earth Engine: Now uses actual cluster bboxes (fixed)

**Pattern:**
```python
def _fetch_rows(self, spec: RequestSpec):
    if spec.geometry.type == "bbox":
        minlon, minlat, maxlon, maxlat = spec.geometry.coordinates
        # Use bbox directly
    elif spec.geometry.type == "point":
        lon, lat = spec.geometry.coordinates
        # Add small buffer if needed
```

## Recommendations

### No Changes Needed ✅

All adapters are well-designed with:
- Proper timeout handling on HTTP requests
- Appropriate timeout values for operation types
- Clean error handling and logging
- Correct geometry usage

### Earth Engine Improvements Applied ✅

1. **Threading-based timeout** - Required for C extension blocking calls
2. **Actual cluster bboxes** - Better spatial context
3. **Eliminated redundant API calls** - 5 fewer `.getInfo()` per query

### Future Considerations

1. **Async/await pattern**: Could improve throughput for Earth Engine
   - Current: Sequential queries with timeout
   - Future: Concurrent queries with timeout
   - Benefit: Faster batch processing

2. **Cluster size optimization**: Consider splitting large clusters
   - Current: Some clusters span 44km (could timeout)
   - Future: Split clusters >10km into sub-regions
   - Benefit: More reliable queries for large areas

3. **Caching strategy**: Currently asset type is cached
   - Current: Class-level dict for metadata
   - Future: Could use Redis/memcached for distributed caching
   - Benefit: Faster metadata lookups across processes

## Documentation Updates

### Files Created/Updated

1. ✅ **EARTH_ENGINE_OPTIMIZATION.md** - Comprehensive optimization guide
2. ✅ **DATABASE_MANAGEMENT.md** - Database operations guide
3. ✅ **CLEANUP_SUMMARY.md** - Legacy code cleanup documentation
4. ✅ **CHANGELOG_PRODUCTION_ADAPTER.md** - Production adapter changes
5. ✅ **ADAPTER_REVIEW.md** (this file) - Cross-adapter best practices
6. ⏳ **TIMEOUT_FIX.md** - Needs update with final threading solution

### Archive Created

- `archive/earth_engine_legacy/` - 4 legacy adapters (1,918 lines)
- `archive/debugging_scripts/` - 8 test/debug scripts

## Testing Verification

### Earth Engine Adapter

**Before:**
- Hung indefinitely after 70-90 queries
- Required manual restart
- Used 1km uniform buffers

**After:**
- No hangs reported
- "Much peppier" performance
- Uses actual cluster extents
- Timeout fires after 60s if needed
- Automatic retry with backoff

### Other Adapters

**No changes required** - all following best practices:
- NASA POWER: ✅ Working well
- GBIF: ✅ Working well (3,145 clusters completed)
- OpenAQ: ✅ Working well (252 success, rate limiting active)

## Conclusion

**Status:** Production ready

All adapters now follow consistent best practices:
1. Timeout protection on all blocking operations
2. Appropriate timeout values for operation complexity
3. Clean error handling with retry logic
4. Correct spatial geometry usage
5. Minimal redundant API calls

The Earth Engine adapter improvements serve as a model for handling:
- Blocking C extension calls (threading-based timeout)
- Complex spatial queries (actual cluster extents)
- API efficiency (eliminate redundant calls)

No other adapters require similar changes - they were already well-designed with proper timeout handling on standard HTTP requests.