# Earth Engine Timeout Fix - Final Solution

**Date:** 2025-09-29
**Issue:** Earth Engine queries hanging after ~70 calls
**Status:** ✅ Fixed with threading-based timeout
**Result:** "Much peppier" - no more hangs

## Problem

After ~70 Earth Engine queries, the script would hang indefinitely.

**Symptoms:**
```
SRTM: 2%|▍ | 72/4789 [04:22<4:13:24, 3.22s/it, success=61, no_data=11]
(hangs forever - no progress, no error)
```

**Root Causes:**
1. Earth Engine's `.getInfo()` makes blocking C extension HTTP calls
2. When servers are slow, `.getInfo()` hangs indefinitely
3. No timeout protection
4. **Not quota** - could restart immediately (21-min gap between clusters)

## Solution: Threading-Based Timeout

### Why Signal-Based Timeout Failed ❌

```python
# Attempt 1 - DOESN'T WORK
signal.alarm(60)  # Can't interrupt C extension HTTP calls
```

### Threading-Based Timeout Works ✅

```python
def run_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
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
        raise TimeoutError(f"Query exceeded {timeout_sec}s timeout")

    if exception[0]:
        raise exception[0]

    return result[0]
```

**Usage:**
```python
def get_stats():
    return img.reduceRegion(...).getInfo()

stats = run_with_timeout(get_stats, timeout_sec=60)
```

## Additional Optimizations

### 1. Eliminated 5 Redundant `.getInfo()` Calls

**Before:** 6 calls per query (1 data + 5 geometry)
```python
geom_wkt = f"POLYGON(({region.coordinates().getInfo()[0][0][0]} ..."  # 5 calls!
```

**After:** 1 call per query (just data)
```python
minlon, minlat, maxlon, maxlat = bbox  # Already have it
wkt = f"POLYGON(({minlon} {minlat}, ..."
```

**Impact:** 83% reduction in API calls

### 2. Fixed Bounding Boxes

**Before:** Artificial 1km buffer for ALL clusters
```python
tight_minlat = center_lat - 0.005  # Always 1km
```

**After:** Actual cluster extents from DBSCAN
```python
if minlat == maxlat:  # Single point
    minlat = center_lat - 0.005  # 500m buffer
else:  # Multi-point
    # Use actual extent (can be 1-44km!)
    return Geometry(type="bbox", coordinates=[minlon, minlat, maxlon, maxlat])
```

**Cluster distribution:**
- 4,240 (89%): Single points → 500m buffer
- 549 (11%): Multi-point → 1-44km actual extent

## Performance Impact

**Before:**
- Hung after 70-90 queries (infinite wait)
- Wrong spatial context (1km uniform)
- 6 API calls per query

**After:**
- No hangs (60s timeout → retry)
- Correct spatial context
- 1 API call per query
- **"Much peppier"**

## Files Modified

1. `env_agents/adapters/earth_engine/production_adapter.py`
   - Added `run_with_timeout()` function
   - Wrapped all `.getInfo()` calls
   - Eliminated redundant geometry fetches

2. `scripts/acquire_environmental_data.py`
   - Fixed bbox handling (actual cluster extents)
   - Added 'timeout' to error keywords

## Testing

**Test 1:** Signal timeout (failed)
```
SRTM: 2%|▍ | 90/4789 [05:19<...] (still hung)
```

**Test 2:** Threading timeout (success)
```
(No more hangs - "much peppier")
```

## See Also

- **EARTH_ENGINE_OPTIMIZATION.md** - Comprehensive guide
- **ADAPTER_REVIEW.md** - Cross-adapter best practices
- **DATABASE_MANAGEMENT.md** - Database operations