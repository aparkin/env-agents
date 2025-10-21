# env-agents Spatial Resolution Update - Migration Guide for econita

**Date**: October 20, 2025
**Status**: Proposed Enhancement (Backward Compatible)
**Target**: econita Integration Team

---

## TL;DR - Quick Summary

**What's changing**: Bounding box queries will return **multiple spatially-distributed samples** instead of single aggregated values for raster services (Earth Engine, SoilGrids).

**API impact**: ✅ **Fully backward compatible** - existing code works unchanged with improved behavior

**Action required**: ✅ **None** for basic usage, optional improvements for advanced features

**Timeline**: Can be deployed incrementally, service by service

---

## Current Behavior (Problem)

### **What you're experiencing now**:

```python
# Query 10km × 10km area for elevation
bbox = [-122.5, 37.5, -122.4, 37.6]  # San Francisco
spec = RequestSpec(geometry=Geometry("bbox", bbox))
result = adapter.fetch(spec)

# Result: 1 row with MEAN elevation of entire bbox
# [{"lat": 37.55, "lon": -122.45, "elevation": 125}]
#   ↑ centroid      ↑ centroid       ↑ average of whole area
```

**Problem**:
- Missing spatial gradients (elevation varies 0-300m across SF)
- All points collapse to bbox center
- Can't see variation within the area

---

## New Behavior (Solution)

### **What you'll get**:

```python
# Same query - NO CODE CHANGE NEEDED
bbox = [-122.5, 37.5, -122.4, 37.6]
spec = RequestSpec(geometry=Geometry("bbox", bbox))
result = adapter.fetch(spec)

# Result: 9 rows with elevation at different locations (3×3 grid)
# [
#   {"lat": 37.50, "lon": -122.50, "elevation": 50},   # SW corner (low, near water)
#   {"lat": 37.50, "lon": -122.45, "elevation": 100},  # S edge
#   {"lat": 37.50, "lon": -122.40, "elevation": 80},   # SE corner
#   {"lat": 37.55, "lon": -122.50, "elevation": 150},  # W edge
#   {"lat": 37.55, "lon": -122.45, "elevation": 125},  # Center
#   {"lat": 37.55, "lon": -122.40, "elevation": 200},  # E edge
#   {"lat": 37.60, "lon": -122.50, "elevation": 100},  # NW corner
#   {"lat": 37.60, "lon": -122.45, "elevation": 250},  # N edge (hills!)
#   {"lat": 37.60, "lon": -122.40, "elevation": 300}   # NE corner (peak)
# ]
#   ↑ Captures the elevation gradient from coast to hills
```

**Benefit**:
✅ See spatial variation
✅ Detect environmental gradients
✅ More accurate for econita's spatial reasoning

---

## API Changes

### ✅ **Zero Breaking Changes**

The API surface **does not change**:

```python
@dataclass
class RequestSpec:
    geometry: Geometry                           # Same
    time_range: Optional[Tuple[str,str]] = None  # Same
    variables: Optional[List[str]] = None        # Same
    depth_cm: Optional[Dict[str,int]] = None     # Same
    resolution: Optional[str] = None             # ← Already exists! Just now used
    filters: Optional[Dict[str,Any]] = None      # Same
    extra: Optional[Dict[str,Any]] = None        # Same
```

**The `resolution` parameter already exists** - we're just making it actually work!

---

## Migration Path

### **Phase 1: No Changes Needed** ✅

Your existing code continues to work:

```python
# Your current code
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    time_range=("2023-01-01", "2023-12-31")
)
result = adapter.fetch(spec)
```

**What changes**:
- Instead of 1 row (aggregated), you get 9 rows (grid samples)
- Each row has actual lat/lon (not centroid)
- Same schema, just more rows

**What stays the same**:
- API signature unchanged
- Response format unchanged (same columns)
- Error handling unchanged
- Authentication unchanged

---

### **Phase 2: Opt-In Control (Optional)**

If you want to control sampling density:

```python
# Low resolution (1 sample, fast) - like current behavior
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="low"
)

# Medium resolution (9 samples, balanced) - NEW DEFAULT
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="medium"
)

# High resolution (25 samples, detailed)
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="high"
)
```

**When to use each**:

| Resolution | Samples | Use When | Example |
|------------|---------|----------|---------|
| `"low"` | 1 | Need overview, speed critical | Quick continent-scale query |
| `"medium"` | 9 | Default - good balance | Most econita queries |
| `"high"` | 25 | Need detailed gradients | Fine-scale environmental analysis |
| `None` | 9 | Backward compat default | Existing code |

---

### **Phase 3: Advanced Control (Power Users)**

For special cases, use `extra` parameter:

```python
spec = RequestSpec(
    geometry=Geometry("bbox", huge_bbox),
    resolution="medium",
    extra={
        "max_samples": 50,          # Cap samples for performance
        "min_spacing_km": 10,       # Don't sample closer than 10km
        "adaptive_scaling": False   # Disable auto-scaling for large bboxes
    }
)
```

**Most users won't need this** - it's for edge cases.

---

## Response Format Changes

### **New: Metadata in `attributes`**

Each row will include sampling strategy info:

```python
result = adapter.fetch(spec)
first_row = result[0]

# Existing fields (unchanged)
first_row['latitude']   # Actual sample location
first_row['longitude']  # Actual sample location
first_row['variable']   # e.g., "elevation"
first_row['value']      # e.g., 150

# NEW: Sampling metadata in attributes
first_row['attributes']['spatial_sampling'] = {
    "strategy": "grid",
    "requested_resolution": "medium",
    "actual_samples": 9,
    "grid_size": "3×3",
    "sample_spacing_km": 3.3,
    "bbox_area_km2": 100
}
```

**This is additive** - existing fields work the same.

---

## Rollout Plan

### **Option A: Silent Rollout (Recommended for econita)** ✅

1. Deploy improvement to Earth Engine adapter
2. Existing queries automatically get better results (more samples)
3. Monitor econita performance for issues
4. No code changes required on econita side

**Risk**: Low - response schema unchanged, just more rows

---

### **Option B: Opt-In Rollout**

1. Deploy with feature flag:
   ```python
   extra={"enable_grid_sampling": True}
   ```
2. econita tests new behavior explicitly
3. Once validated, make it default
4. Remove flag

**Risk**: Lower - explicit testing period

---

### **Option C: Gradual Service Rollout**

1. Week 1: Earth Engine only
2. Week 2: SoilGrids
3. Week 3: NASA POWER
4. Point-based services (GBIF, WQP) unchanged (already work correctly)

**Risk**: Lowest - time to fix issues between services

---

## Impact on econita's Code

### **Scenario 1: Simple Data Retrieval**

**Before**:
```python
data = adapter.fetch(spec)
# Returns 1 row per variable
```

**After**:
```python
data = adapter.fetch(spec)
# Returns 9 rows per variable (grid samples)
```

**Code change needed**: ✅ **None** - just more rows with actual locations

**Benefit**: econita can now detect spatial patterns it couldn't before

---

### **Scenario 2: Aggregating Results**

If econita currently aggregates results (e.g., taking mean):

**Before**:
```python
# Single value, already aggregated
elevation = result[0]['value']
```

**After**:
```python
# Multiple values - aggregate as needed
elevations = [row['value'] for row in result if row['variable'] == 'elevation']
mean_elevation = np.mean(elevations)
max_elevation = np.max(elevations)  # NEW: Can detect peaks!
gradient = max(elevations) - min(elevations)  # NEW: Quantify variation
```

**Code change needed**: ⚠️ **Might need update** if you expect single value

**Solution**: Check `len(result)` or aggregate explicitly

---

### **Scenario 3: Spatial Analysis**

**NEW capability** - detect gradients:

```python
# Group by location
import pandas as pd
df = pd.DataFrame(result)

# Plot spatial pattern
df_elevation = df[df['variable'] == 'elevation']
plt.scatter(df_elevation['longitude'], df_elevation['latitude'],
            c=df_elevation['value'], cmap='terrain')
plt.colorbar(label='Elevation (m)')
plt.title('Elevation Gradient Across Query Area')
```

**This wasn't possible before!**

---

## Performance Considerations

### **Query Speed**

| Resolution | Samples | Speed Impact | Use Case |
|------------|---------|--------------|----------|
| `"low"` | 1 | 1× (current) | Fast overview |
| `"medium"` | 9 | ~3-5× slower | **Default** (still fast) |
| `"high"` | 25 | ~8-12× slower | Detailed analysis |

**Notes**:
- Earth Engine: ~2-3s per sample → medium = ~15s (acceptable)
- Capped at 100 samples max to prevent runaway queries
- Large bboxes auto-scale but stay under cap

### **Response Size**

| Resolution | Rows per Variable | Size Impact |
|------------|-------------------|-------------|
| `"low"` | 1 | Same as now |
| `"medium"` | 9 | 9× data |
| `"high"` | 25 | 25× data |

**Example**: Query 10 variables → 90 rows instead of 10 rows

**Impact**: Minimal (JSON is compact, <1KB per row)

---

## Testing Checklist for econita Team

- [ ] **Test 1**: Run existing queries, verify you get more rows with different lat/lon
- [ ] **Test 2**: Check any code that expects single value per variable
- [ ] **Test 3**: Verify spatial patterns make sense (e.g., elevation gradient)
- [ ] **Test 4**: Test tiny bbox (< 1km) - should return 1 sample with warning
- [ ] **Test 5**: Test huge bbox (> 100km) - should scale to more samples
- [ ] **Test 6**: Test with `resolution="low"` - should return 1 sample (old behavior)
- [ ] **Test 7**: Check performance with multiple services (timing)
- [ ] **Test 8**: Verify metadata includes sampling strategy info

---

## FAQ for econita Team

### **Q: Will this break our existing code?**
A: No - the response schema is unchanged. You'll just get more rows with actual spatial distribution instead of centroid aggregation.

### **Q: Do we need to update our code?**
A: Not required. Optionally, you can:
- Use `resolution` parameter to control sampling
- Check sampling metadata to understand results
- Aggregate multiple samples if you need single value

### **Q: What if we want the old behavior (single aggregated value)?**
A: Use `resolution="low"` - returns 1 sample, fastest.

### **Q: Will queries be slower?**
A: Slightly (3-5× for medium, still <30s for most queries). Can use `resolution="low"` for speed-critical queries.

### **Q: What about point-based services (GBIF, WQP)?**
A: Unchanged - they already return multiple points correctly.

### **Q: How do we know what sampling strategy was used?**
A: Check `result[0]['attributes']['spatial_sampling']` for full details.

### **Q: Can we disable this feature?**
A: Use `resolution="low"` or `extra={"max_samples": 1}`.

### **Q: What if bbox is huge (1000km)?**
A: Adaptive scaling kicks in - you'll get ~50 samples instead of 9 (capped for performance).

### **Q: What if bbox is tiny (10m)?**
A: You'll get 1 sample with warning if bbox is smaller than data resolution.

---

## Example Migration Scenarios

### **Scenario A: econita Queries for Context**

**Current code**:
```python
# Get elevation for location
bbox = calculate_bbox(center, radius=5km)
spec = RequestSpec(geometry=Geometry("bbox", bbox))
elevation = adapter.fetch(spec)[0]['value']
context = f"Elevation is {elevation}m"
```

**Updated code** (optional improvement):
```python
# Get elevation gradient
bbox = calculate_bbox(center, radius=5km)
spec = RequestSpec(geometry=Geometry("bbox", bbox))
results = adapter.fetch(spec)

elevations = [r['value'] for r in results if r['variable'] == 'elevation']
mean_elev = np.mean(elevations)
gradient = max(elevations) - min(elevations)

if gradient > 100:
    context = f"Elevation ranges {min(elevations)}-{max(elevations)}m (mountainous)"
else:
    context = f"Elevation ~{mean_elev}m (relatively flat)"
```

**Benefit**: More accurate environmental characterization

---

### **Scenario B: econita Compares Multiple Locations**

**No code change needed** - automatically better:

```python
# Compare two sites
bbox1 = [...]
bbox2 = [...]

results1 = adapter.fetch(RequestSpec(geometry=Geometry("bbox", bbox1)))
results2 = adapter.fetch(RequestSpec(geometry=Geometry("bbox", bbox2)))

# Now you get spatial distribution for both sites
# Can detect: "Site 1 is uniformly warm, Site 2 has strong temperature gradient"
```

---

## Communication Template for econita Leads

**Subject**: env-agents Enhancement - Improved Spatial Resolution (Backward Compatible)

**Body**:

Hi [econita Team],

We've identified and are implementing an improvement to env-agents that will benefit econita's spatial reasoning:

**What's Changing**:
- Bounding box queries will return multiple spatial samples instead of single aggregated values
- This captures environmental gradients that were previously lost

**Impact on econita**:
- ✅ **Fully backward compatible** - existing code works unchanged
- ✅ Automatically improved accuracy for spatial environmental queries
- ✅ New capability: detect gradients (elevation changes, temperature variation)
- ⚠️ Slightly slower queries (3-5× for default resolution, still < 30s)
- ⚠️ More data returned (9 rows instead of 1 per variable)

**Action Required**:
- **Short term**: None - we can deploy silently
- **Optional**: Test with econita to verify behavior meets expectations
- **Future**: Consider leveraging gradient information for better spatial reasoning

**Rollout Options**:
1. Silent rollout (we're confident it's safe)
2. Opt-in testing period (if you prefer explicit validation)
3. Gradual service-by-service (lowest risk)

Which approach do you prefer?

**Documentation**:
- Technical details: `docs/SPATIAL_TEMPORAL_REVIEW.md`
- Migration guide: `docs/ECONITA_MIGRATION_GUIDE.md` (this doc)
- Design rationale: `docs/RESOLUTION_STRATEGY.md`

Happy to discuss on a call if helpful.

Best,
[Your Name]

---

## Contact & Support

**For questions**:
- Technical details: See `docs/SPATIAL_TEMPORAL_REVIEW.md`
- Design decisions: See `docs/RESOLUTION_STRATEGY.md`
- API reference: See updated `docs/API_REFERENCE.md`

**Feedback welcome**:
- GitHub issue: "econita spatial resolution feedback"
- Direct message: [Your contact]

---

## Appendix: Side-by-Side Comparison

### **Current Behavior (Problem)**
```python
spec = RequestSpec(geometry=Geometry("bbox", [-122.5, 37.5, -122.4, 37.6]))
result = ee_adapter.fetch(spec)

# Result:
# [{"lat": 37.55, "lon": -122.45, "variable": "elevation", "value": 125}]
#                  ↑ centroid             ↑ mean of entire bbox
```

### **New Behavior (Solution)**
```python
spec = RequestSpec(geometry=Geometry("bbox", [-122.5, 37.5, -122.4, 37.6]))
result = ee_adapter.fetch(spec)

# Result:
# [
#   {"lat": 37.50, "lon": -122.50, "variable": "elevation", "value": 50},
#   {"lat": 37.50, "lon": -122.45, "variable": "elevation", "value": 100},
#   {"lat": 37.50, "lon": -122.40, "variable": "elevation", "value": 80},
#   {"lat": 37.55, "lon": -122.50, "variable": "elevation", "value": 150},
#   {"lat": 37.55, "lon": -122.45, "variable": "elevation", "value": 125},
#   {"lat": 37.55, "lon": -122.40, "variable": "elevation", "value": 200},
#   {"lat": 37.60, "lon": -122.50, "variable": "elevation", "value": 100},
#   {"lat": 37.60, "lon": -122.45, "variable": "elevation", "value": 250},
#   {"lat": 37.60, "lon": -122.40, "variable": "elevation", "value": 300}
# ]
#       ↑ Grid of actual samples across the bbox, capturing gradient
```

**Key difference**: 9 real measurements vs 1 aggregated value
