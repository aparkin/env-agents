# Earth Engine Operations Guide

**Last Updated:** 2025-09-30
**Status:** Production-Ready

## Overview

The Earth Engine adapter provides access to 100+ Google Earth Engine assets through the env-agents framework. This guide covers operational best practices, common challenges, and proven solutions for running production workloads.

**Key Operational Challenges:**
- Hanging queries due to slow API responses
- Out-of-range temporal queries causing null errors
- Quota management and rate limiting
- Optimizing query efficiency for large-scale pipelines

**Production Performance:**
- 4,789 clusters processed in ~2.7 hours
- 60-second timeout protection prevents indefinite hangs
- Automatic temporal fallback for out-of-range dates
- 83% reduction in API calls through geometry optimization

---

## Timeout Handling

### Problem: Hanging Queries

Earth Engine's `.getInfo()` makes blocking HTTP requests through C extension code that can hang indefinitely when servers are slow or experiencing issues.

**Symptoms:**
```
SRTM: 2%|▍ | 72/4789 [04:22<∞, ???] (hangs forever - no progress, no error)
```

**Root Cause:**
- Not quota-related (can restart immediately)
- Blocking C extension HTTP calls cannot be interrupted by signal-based timeouts
- 21-minute gaps observed between successful queries
- Consistent hangs after 70-90 queries

### Solution: Threading-Based Timeout

**Why signal.alarm() fails:**
```python
# DOES NOT WORK - signal can't interrupt C extension code
signal.alarm(60)
img.reduceRegion(...).getInfo()  # Will still hang
```

**Working solution using threading:**
```python
def run_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
    """Run a function with timeout using threading."""
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
        raise TimeoutError(f"Earth Engine query exceeded {timeout_sec}s timeout")

    if exception[0]:
        raise exception[0]

    return result[0]
```

**Usage:**
```python
# Wrap the blocking call
def get_stats():
    return img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=scale,
        bestEffort=True
    ).getInfo()

stats = run_with_timeout(get_stats, timeout_sec=60)
```

**Why this works:**
- Daemon threads allow process to abandon hung HTTP calls
- `thread.join(timeout)` returns control after timeout
- Hung threads don't block process exit
- Can retry after timeout with backoff

### Retry Configuration

When timeout occurs, implement exponential backoff:

```python
# In acquire_environmental_data.py
max_retries = 3
backoff_seconds = 60

if any(keyword in error_msg for keyword in ['quota', 'rate limit',
                                              'too many requests',
                                              'user rate limit exceeded',
                                              'timeout']):
    logger.warning(f"Transient error for {service_name} cluster {cluster_id}, "
                   f"attempt {attempt+1}/{max_retries}. "
                   f"Retrying after {backoff}s...")
    time.sleep(backoff)
    continue  # Retry
```

**Behavior:**
1. Query times out after 60s
2. Wait 60s (backoff)
3. Retry (usually succeeds)
4. After 3 failures, mark as "error" and move on
5. Can retry later with `--clear SRTM --clear-status failed`

### Implementation Location

**File:** `env_agents/adapters/earth_engine/production_adapter.py`

All `.getInfo()` calls are wrapped with timeout protection:
- Data queries: `reduceRegion(...).getInfo()`
- Asset type detection: Cached, one-time check
- ImageCollection metadata: Band names and time series data

---

## Optimization Best Practices

### Minimize .getInfo() Calls

Each `.getInfo()` is a round-trip HTTP request. Eliminate unnecessary calls.

**Before (6 calls per query):**
```python
# 1 call for data
stats = img.reduceRegion(...).getInfo()

# 5 calls for geometry WKT!
geom_wkt = f"POLYGON(({region.coordinates().getInfo()[0][0][0]} " +
           f"{region.coordinates().getInfo()[0][0][1]}, " +
           f"{region.coordinates().getInfo()[0][1][0]} " +
           f"{region.coordinates().getInfo()[0][1][1]}, ..."
```

**After (1 call per query):**
```python
# Pass bbox through from _fetch_rows to _query_image
minlon, minlat, maxlon, maxlat = bbox

# 1 call for data
stats = img.reduceRegion(...).getInfo()

# Zero additional calls - construct WKT from bbox we already have
wkt = f"POLYGON(({minlon} {minlat}, {maxlon} {minlat}, " +
      f"{maxlon} {maxlat}, {minlon} {maxlat}, {minlon} {minlat}))"
```

**Impact:** 83% reduction in API calls

### Use Correct Geometries

Don't impose artificial buffers that lose spatial information.

**Before (wrong):**
```python
# Always use 1km buffer, regardless of actual cluster extent
tight_minlat = center_lat - 0.005  # ~500m at equator
tight_maxlat = center_lat + 0.005
tight_minlon = center_lon - 0.005
tight_maxlon = center_lon + 0.005
```

**After (correct):**
```python
# Use actual cluster bbox from DBSCAN clustering
if minlat == maxlat and minlon == maxlon:
    # Single point - add small buffer for environmental context (~500m)
    minlat = center_lat - 0.005
    maxlat = center_lat + 0.005
    minlon = center_lon - 0.005
    maxlon = center_lon + 0.005
else:
    # Multi-point - use actual extent
    return Geometry(type="bbox", coordinates=[minlon, minlat, maxlon, maxlat])
```

**Cluster Distribution:**
- 4,240 (89%): Single points → get 500m buffer
- 290 (6%): <1km multi-point clusters
- 233 (5%): 1-5km clusters
- 24 (<1%): 5-11km clusters
- 2 (<1%): >11km clusters (up to 44km extent)

### Efficient Querying Patterns

**Best Practices:**
1. **Cache metadata that doesn't change**
   - Asset types (Image vs ImageCollection)
   - Band names
   - Units and scale factors

2. **Pass computed values through method chains**
   ```python
   # Don't recompute bbox in every method
   def _fetch_rows(self, spec):
       bbox = self._compute_bbox(spec)
       return self._query_image(bbox)  # Pass it through
   ```

3. **Use bestEffort=True for reduceRegion**
   ```python
   stats = img.reduceRegion(
       reducer=ee.Reducer.mean(),
       geometry=region,
       scale=scale,
       bestEffort=True  # Allows automatic scale adjustment
   ).getInfo()
   ```

4. **Filter before processing**
   ```python
   # Filter ImageCollection early
   ic = ee.ImageCollection(asset_id) \
       .filterDate(start_date, end_date) \
       .filterBounds(region)

   # Check size before processing
   if ic.size().getInfo() == 0:
       # Handle empty collection
   ```

### Review Checklist

When reviewing Earth Engine adapter code:

- [ ] Are all blocking `.getInfo()` calls wrapped with timeouts?
- [ ] Can we reduce the number of API calls per query?
- [ ] Are we using correct spatial geometries (not artificial buffers)?
- [ ] Do we have retry logic for transient failures?
- [ ] Is there proper error handling and logging?
- [ ] Are we caching expensive metadata lookups?
- [ ] Is bestEffort=True used for reduceRegion?

---

## Temporal Fallback Strategy

### Problem: Out-of-Range Dates

Some Earth Engine ImageCollections have finite temporal coverage:
- **MODIS_LANDCOVER (MODIS/006/MCD12Q1)**: 2000-2019 (ends at 2019)
- **GOOGLE_EMBEDDINGS (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL)**: 2017-present (sparse coverage)

**Error when requesting out-of-range dates:**
```python
ic = ee.ImageCollection(asset_id).filterDate("2021-01-01", "2021-12-31")
count = ic.size().getInfo()  # Returns 0
first = ic.first()  # Returns null
bands = first.bandNames().getInfo()  # ERROR: "Parameter 'image' is required and may not be null"
```

**Previous Behavior:**
- 100% failure rate for MODIS_LANDCOVER (all 4,789 clusters)
- Intermittent failures for GOOGLE_EMBEDDINGS at sparse locations

### Solution: Automatic Fallback with Metadata

The adapter automatically falls back to closest available data and annotates observations with complete metadata.

**Algorithm:**
1. Try filtering with requested date range
2. If `ic.size().getInfo() == 0`, trigger fallback
3. Get available temporal range at this location
4. Select fallback strategy:
   - Requested date **after** dataset end → Use most recent year
   - Requested date **before** dataset start → Use oldest year
   - Requested range **overlaps** but no data → Use full available range
5. Re-filter with fallback dates
6. Annotate all observations with fallback metadata

### Implementation

Located in `env_agents/adapters/earth_engine/production_adapter.py:283-454`:

```python
def _query_image_collection(self, region, bbox, center_lat, center_lon,
                            start_date: str, end_date: str) -> List[Dict]:
    """Query ImageCollection asset with automatic temporal fallback"""

    # Store original requested dates
    requested_start = start_date
    requested_end = end_date
    fallback_applied = False
    fallback_reason = None

    # Try requested range
    ic = ee.ImageCollection(self.asset_id).filterDate(start_date, end_date).filterBounds(region)
    count = ic.size().getInfo()

    # Fallback if empty
    if count == 0:
        logger.info(f"No data in requested range {start_date} to {end_date}, checking available range...")

        # Get actual available range
        full_collection = ee.ImageCollection(self.asset_id).filterBounds(region)
        dates = full_collection.aggregate_array('system:time_start').getInfo()

        if not dates:
            return []  # No data at this location at all

        # Convert timestamps to dates
        from datetime import datetime
        available_dates = [datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d')
                          for ts in dates]
        available_start = min(available_dates)
        available_end = max(available_dates)

        # Select fallback strategy
        if requested_start > available_end:
            # Requested date too late → use most recent year
            end_year = available_end[:4]
            start_date = f"{end_year}-01-01"
            end_date = f"{end_year}-12-31"
            fallback_reason = f"requested_date_{requested_start}_after_dataset_end_{available_end}"
        elif requested_end < available_start:
            # Requested date too early → use oldest year
            start_year = available_start[:4]
            start_date = f"{start_year}-01-01"
            end_date = f"{start_year}-12-31"
            fallback_reason = f"requested_date_{requested_end}_before_dataset_start_{available_start}"
        else:
            # Overlap but no data → use full range
            start_date = available_start
            end_date = available_end
            fallback_reason = f"no_data_in_overlap_using_full_range_{available_start}_to_{available_end}"

        fallback_applied = True
        logger.info(f"Temporal fallback applied: {fallback_reason}")
        logger.info(f"Using date range: {start_date} to {end_date}")

        # Re-filter with fallback dates
        ic = ee.ImageCollection(self.asset_id).filterDate(start_date, end_date).filterBounds(region)
```

### Metadata Annotation

All observations returned after fallback include these attributes:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `requested_date_range` | string | Original requested dates | `"2021-01-01_to_2021-12-31"` |
| `actual_date_range` | string | Dates actually used for query | `"2019-01-01_to_2019-12-31"` |
| `temporal_fallback_applied` | boolean | Whether fallback was triggered | `true` or `false` |
| `temporal_fallback_reason` | string | Explanation of why fallback occurred | `"requested_date_2021-01-01_after_dataset_end_2019-12-31"` |

**Example observation with fallback:**
```json
{
  "observation_id": "ee_MODIS_006_MCD12Q1_2019-01-01_LC_Prop1",
  "dataset": "EARTH_ENGINE",
  "time": "2019-01-01",
  "variable": "ee:LC_Prop1",
  "value": 7.583912611717975,
  "latitude": 37.8,
  "longitude": -122.4,
  "attributes": {
    "asset_id": "MODIS/006/MCD12Q1",
    "scale_m": 500,
    "requested_date_range": "2021-01-01_to_2021-12-31",
    "actual_date_range": "2019-01-01_to_2019-12-31",
    "temporal_fallback_applied": true,
    "temporal_fallback_reason": "requested_date_2021-01-01_after_dataset_end_2019-12-31"
  }
}
```

### Configuration Updates

**For datasets with known temporal limits:**

```python
# scripts/acquire_environmental_data.py
"MODIS_LANDCOVER": {
    "asset_id": "MODIS/006/MCD12Q1",
    "time_range": ("2019-01-01", "2019-12-31"),  # Use most recent available year
    # Adapter will automatically fall back if needed
}
```

### Downstream Analysis

Filter observations by fallback status:

```python
import pandas as pd

# Load observations
df = pd.read_parquet("observations.parquet")

# Identify fallback observations
df['fallback'] = df['attributes'].apply(
    lambda x: x.get('temporal_fallback_applied', False)
)

# Filter to only requested dates
df_requested = df[~df['fallback']]

# Analyze fallback observations separately
df_fallback = df[df['fallback']]
print(f"Fallback rate: {len(df_fallback) / len(df) * 100:.1f}%")
```

### Test Results

**Test Script:** `notebooks/test_temporal_fallback.py`

| Test | Requested | Actual | Fallback | Result |
|------|-----------|--------|----------|--------|
| MODIS_LANDCOVER | 2021 | 2019 | ✅ Applied | 13 obs from 2019 |
| GOOGLE_EMBEDDINGS | 2021 | 2021 | ❌ Not needed | 64 obs from 2021 |
| MODIS_NDVI | 2025 | 2025 | ❌ Not needed | 192 obs from 2025 |

**Production Impact:**
- **Before:** 100% failure rate for MODIS_LANDCOVER
- **After:** 0% failure rate with automatic 2019 fallback

---

## Quota Management

### Rate Limiting

Earth Engine has per-user quotas for:
- Concurrent requests
- Requests per second
- Total daily computation

**Implemented Strategy:**
```python
# Sequential processing with rate limiting
for cluster in clusters:
    try:
        result = adapter.fetch(spec)
        time.sleep(2.0)  # 2-second delay between queries
    except QuotaError:
        time.sleep(60)  # 60-second backoff on quota
        continue
```

**Configuration:**
- **Base delay:** 2 seconds between queries
- **Quota backoff:** 60 seconds after quota error
- **Max retries:** 3 attempts per cluster
- **Timeout:** 60 seconds per attempt

### Retry Strategies

**Sequential vs Parallel Execution:**

```python
# Sequential (Recommended for Earth Engine)
for spec in specs:
    try:
        result = router.fetch(dataset="EARTH_ENGINE", spec=spec)
    except TimeoutError:
        time.sleep(60)
        result = router.fetch(dataset="EARTH_ENGINE", spec=spec)

# Parallel (Use with caution)
from concurrent.futures import ThreadPoolExecutor

# Limit workers to avoid quota
with ThreadPoolExecutor(max_workers=2) as executor:
    results = executor.map(fetch_with_retry, specs)
```

**Recommendation:** Use sequential processing for large workloads (>100 queries) to avoid quota issues.

### Error Keywords for Retry

```python
TRANSIENT_ERRORS = [
    'quota',
    'rate limit',
    'too many requests',
    'user rate limit exceeded',
    'timeout',
    'server error',
    '503',
    '429'
]

if any(keyword in error_msg.lower() for keyword in TRANSIENT_ERRORS):
    # Retry with backoff
    time.sleep(backoff_seconds)
    continue
```

---

## Troubleshooting

### Issue: Query Hangs Indefinitely

**Symptoms:**
- No progress for >5 minutes
- No error messages
- Can restart immediately (not quota)

**Solution:**
- Ensure timeout protection is enabled (see Timeout Handling section)
- Check timeout is set appropriately (60s recommended)
- Verify threading-based timeout is used (not signal-based)

**Diagnosis:**
```python
# Add logging around .getInfo() calls
logger.info(f"Starting Earth Engine query at {time.time()}")
result = run_with_timeout(get_stats, timeout_sec=60)
logger.info(f"Completed Earth Engine query at {time.time()}")
```

---

### Issue: "Parameter 'image' is required" Error

**Symptoms:**
```
Error: Image.bandNames: Parameter 'image' is required and may not be null
```

**Root Cause:**
- Requested date range outside dataset's temporal coverage
- ImageCollection filter returns empty collection

**Solution:**
- Enable temporal fallback (see Temporal Fallback Strategy section)
- Verify date ranges align with dataset availability
- Check Earth Engine Data Catalog for temporal coverage

**Diagnosis:**
```python
# Check if collection is empty before processing
ic = ee.ImageCollection(asset_id).filterDate(start, end).filterBounds(region)
count = ic.size().getInfo()

if count == 0:
    logger.warning(f"Empty collection for {asset_id} at {start} to {end}")
    # Apply fallback
```

---

### Issue: Quota Exceeded

**Symptoms:**
```
EEException: User memory limit exceeded
EEException: Too many concurrent requests
```

**Solution:**
1. Increase delay between queries
2. Reduce concurrent requests (use sequential processing)
3. Reduce spatial extent (smaller bboxes)
4. Use `bestEffort=True` for reduceRegion

**Configuration:**
```python
# Increase delay
time.sleep(5.0)  # 5 seconds instead of 2

# Reduce scale for faster queries
stats = img.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=region,
    scale=1000,  # 1km instead of 500m
    bestEffort=True
).getInfo()
```

---

### Issue: Wrong Spatial Context

**Symptoms:**
- Single-point clusters appear correct
- Multi-point clusters only return data for single point
- Missing spatial variability

**Root Cause:**
- Using uniform 1km buffer for all clusters
- Ignoring actual cluster extents from DBSCAN

**Solution:**
- Use actual cluster bounding boxes (see Optimization Best Practices)
- Add buffer only for single-point clusters
- Verify bbox computation in `get_cluster_geometry()`

**Diagnosis:**
```python
# Check cluster extent
print(f"Cluster {cluster_id}:")
print(f"  Points: {num_points}")
print(f"  Extent: {minlon:.4f},{minlat:.4f} to {maxlon:.4f},{maxlat:.4f}")
print(f"  Width: {(maxlon - minlon) * 111:.1f} km")
print(f"  Height: {(maxlat - minlat) * 111:.1f} km")
```

---

### Issue: Excessive API Calls

**Symptoms:**
- Slow query performance (>5s per cluster)
- High quota usage
- Many `.getInfo()` calls in logs

**Root Cause:**
- Redundant geometry fetches
- Recomputing metadata on every query
- Not caching asset information

**Solution:**
- Pass bbox through method chain (see Optimization Best Practices)
- Cache asset type, band names, and metadata
- Minimize calls to `.getInfo()`

**Diagnosis:**
```python
# Count .getInfo() calls
import functools

original_getInfo = ee.ComputedObject.getInfo
call_count = [0]

def counted_getInfo(self, *args, **kwargs):
    call_count[0] += 1
    return original_getInfo(self, *args, **kwargs)

ee.ComputedObject.getInfo = counted_getInfo

# Run query
result = adapter.fetch(spec)
print(f"Total .getInfo() calls: {call_count[0]}")
```

---

## Performance Metrics

### Production Workload

**Scale:**
- 4,789 clusters
- 100+ Earth Engine assets
- Multiple temporal ranges

**Performance:**
- **Total time:** ~2.7 hours
- **Average query time:** ~2 seconds
- **Timeout rate:** <1% (timeouts recover on retry)
- **Fallback rate (MODIS_LANDCOVER):** 100% (expected, uses 2019 data)

### Before vs After Optimization

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Hangs | Infinite (after 70-90 queries) | 0 (60s timeout) | ✅ Eliminated |
| API calls per query | 6 (1 data + 5 geometry) | 1 (data only) | 83% reduction |
| Spatial accuracy | Wrong (1km uniform) | Correct (actual extent) | ✅ Fixed |
| Temporal coverage | Fails on out-of-range | Auto-fallback with metadata | ✅ Fixed |
| User experience | Manual intervention | Fully automated | ✅ Production-ready |

---

## Best Practices Summary

### For Operators

1. **Always enable timeout protection** - Use threading-based timeouts for all `.getInfo()` calls
2. **Monitor fallback rates** - Check `temporal_fallback_applied` in observations
3. **Use sequential processing** - Avoid parallel execution for large workloads
4. **Configure appropriate delays** - 2s between queries is optimal for most workloads
5. **Implement retry logic** - 3 retries with 60s backoff for transient errors

### For Developers

1. **Minimize .getInfo() calls** - Pass computed values through method chains
2. **Use correct geometries** - Don't impose artificial buffers
3. **Cache metadata** - Store asset types, band names, and temporal ranges
4. **Enable fallback** - Handle out-of-range dates gracefully
5. **Log extensively** - Track timing, fallbacks, and errors for debugging

### Review Checklist

Before deploying Earth Engine adapter changes:

- [ ] All `.getInfo()` calls wrapped with 60s timeout
- [ ] Geometry computed once and passed through
- [ ] Temporal fallback enabled with metadata annotation
- [ ] Retry logic includes 'timeout' keyword
- [ ] Logging covers timing, fallbacks, and errors
- [ ] Test with out-of-range dates (e.g., MODIS_LANDCOVER 2021)
- [ ] Test with hanging query (timeout fires and recovers)
- [ ] Verify spatial context (multi-point clusters use actual extent)

---

## Related Documentation

- **EARTH_ENGINE_OPTIMIZATION.md** - Original optimization analysis (archived)
- **TIMEOUT_FIX.md** - Threading timeout implementation (archived)
- **TEMPORAL_FALLBACK.md** - Temporal fallback strategy (superseded by this guide)
- **PANGENOME_PIPELINE.md** - Production pipeline configuration
- **DATABASE_MANAGEMENT.md** - Database operations and retry strategies

---

## Change History

| Date | Change | Status |
|------|--------|--------|
| 2025-09-29 | Threading-based timeout implemented | ✅ Deployed |
| 2025-09-29 | Geometry optimization (1 API call instead of 6) | ✅ Deployed |
| 2025-09-29 | Actual cluster bboxes (not uniform 1km) | ✅ Deployed |
| 2025-09-30 | Temporal fallback with metadata annotation | ✅ Deployed |
| 2025-09-30 | Consolidated operations guide created | ✅ Current |