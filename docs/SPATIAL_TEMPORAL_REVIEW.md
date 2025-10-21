# Spatial and Temporal Resolution Review

**Date**: October 20, 2025
**Reviewer**: Claude Code
**Context**: Integration with econita agent - bounding box queries returning single center points

---

## Executive Summary

**Problem Identified**: Bounding box queries are being **collapsed to single center points** for raster-based services (Earth Engine, SoilGrids), losing spatial gradients. Point-based services (GBIF, WQP, OpenAQ) work correctly and return multiple points.

**Impact**: When querying a bounding box to understand environmental gradients, users receive only a single aggregated value at the bbox center, not the spatial distribution they expect.

**Root Causes**:
1. **Raster services aggregate to bbox mean** (Earth Engine: `reduceRegion` with `mean()`)
2. **BaseAdapter fills missing lat/lon with bbox centroid** (all rows get same coordinates)
3. **No resolution parameter implementation** (spec.resolution exists but unused)
4. **Inconsistent temporal defaults** (some adapters crash without time_range)

---

## Detailed Findings

### 1. Spatial Resolution Issues

#### **Issue 1.1: Earth Engine Reduces Bbox to Single Mean Value**

**Location**: `env_agents/adapters/earth_engine/production_adapter.py:244-248`

```python
return img.reduceRegion(
    reducer=ee.Reducer.mean(),  # ❌ Aggregates entire bbox to single value
    geometry=region,
    scale=self.scale,
    maxPixels=1e9
).getInfo()
```

**Impact**:
- Query a 10km × 10km bbox → Get 1 value (bbox mean)
- Lose all spatial variation within the bbox
- Cannot detect environmental gradients

**Expected behavior**: Sample multiple points within bbox to capture gradients

---

#### **Issue 1.2: BaseAdapter Fills All Rows with Bbox Centroid**

**Location**: `env_agents/adapters/base.py:474-478`

```python
# Fill lat/lon if missing via centroid
if "latitude" not in df.columns or "longitude" not in df.columns:
    lat, lon = centroid_from_geometry(spec.geometry.type, spec.geometry.coordinates)
    if "latitude"  not in df.columns: df["latitude"]  = lat
    if "longitude" not in df.columns: df["longitude"] = lon
```

**Impact**:
- If adapter doesn't provide lat/lon, **all rows get same centroid coordinates**
- Downstream consumers see identical lat/lon for all variables
- Spatial context is lost

**Why this exists**: Fallback for adapters that don't provide per-observation coordinates

**Problem**: Hides the fact that data is aggregated, makes it appear point-like

---

#### **Issue 1.3: Resolution Parameter Unused**

**Location**: `env_agents/core/models.py:26`

```python
@dataclass
class RequestSpec:
    geometry: Geometry
    time_range: Optional[Tuple[str,str]] = None
    variables: Optional[List[str]] = None
    depth_cm: Optional[Dict[str,int]] = None
    resolution: Optional[str] = None  # ❌ Defined but never used
    filters: Optional[Dict[str,Any]] = None
    extra: Optional[Dict[str,Any]] = None
```

**Impact**: No way to request specific spatial sampling density

**Search result**: `grep "spec.resolution"` → **0 matches** across all adapters

---

### 2. Adapter-Specific Behavior

| Adapter | Type | Bbox Handling | Returns Multiple Points? | Notes |
|---------|------|---------------|--------------------------|-------|
| **Earth Engine** | Raster | Aggregates to mean | ❌ No | Single value per variable |
| **SoilGrids** | Raster | Likely aggregates | ❌ No | Not verified, but probably same issue |
| **NASA POWER** | Gridded | Center point query | ❌ No | API is point-based (0.5° grid) |
| **GBIF** | Point obs | Queries bbox range | ✅ Yes | Returns all occurrences in bbox |
| **WQP** | Point obs | Finds stations in bbox | ✅ Yes | Returns all station measurements |
| **OpenAQ** | Point obs | Radius search from center | ⚠️ Partial | Uses centroid to find nearby stations |
| **SSURGO** | Polygon | Intersects bbox | ⚠️ Unknown | Soil survey polygons |
| **OSM Overpass** | Vector | Queries bbox | ✅ Yes | Returns all features in bbox |

**Summary**:
- ✅ **Point-based services work correctly** (GBIF, WQP, OSM)
- ❌ **Raster services collapse to single point** (Earth Engine, likely SoilGrids)
- ⚠️ **Gridded services query center only** (NASA POWER)

---

### 3. Temporal Handling Issues

#### **Issue 3.1: Inconsistent Time Range Defaults**

**Findings**:

```python
# Earth Engine: Has fallback default
start_date, end_date = spec.time_range or ("2020-01-01", "2020-12-31")

# NASA POWER: No fallback (will crash if None)
start_date, end_date = spec.time_range

# WQP: Gracefully handles None
time_range = spec.time_range  # Can be None
```

**Impact**: Some adapters require time_range, others have defaults, causing inconsistent API behavior

---

#### **Issue 3.2: Temporal Aggregation Strategy Unclear**

When querying a time range (e.g., 2020-2021), adapters handle it differently:

- **Earth Engine ImageCollections**: Composite/mean across all images in range
- **NASA POWER**: Returns daily time series
- **GBIF**: Returns all occurrences in date range
- **WQP**: Returns all measurements in date range

**Problem**: No way to control temporal aggregation (mean vs time series vs climatology)

---

## Recommendations

### **Priority 1: Fix Raster Spatial Sampling (Earth Engine)**

**Goal**: Return multiple spatially distributed samples within bbox to capture gradients

**Strategy**: Sample at regular grid within bbox instead of aggregating

**Proposed Implementation** (`earth_engine/production_adapter.py`):

```python
def _sample_bbox_grid(self, img, bbox, scale, n_samples=9):
    """
    Sample raster at grid of points within bbox to capture spatial gradients.

    Args:
        img: Earth Engine Image
        bbox: [minlon, minlat, maxlon, maxlat]
        scale: Resolution in meters
        n_samples: Number of sample points (default 9 = 3x3 grid)

    Returns:
        List of (lat, lon, values_dict) tuples
    """
    minlon, minlat, maxlon, maxlat = bbox

    # Calculate grid spacing (e.g., 3x3 = 9 points)
    n_side = int(np.sqrt(n_samples))
    lons = np.linspace(minlon, maxlon, n_side)
    lats = np.linspace(minlat, maxlat, n_side)

    samples = []
    for lat in lats:
        for lon in lons:
            point = ee.Geometry.Point([lon, lat])

            # Sample at this point
            values = img.reduceRegion(
                reducer=ee.Reducer.first(),  # Get pixel value, not mean
                geometry=point,
                scale=scale,
                maxPixels=1
            ).getInfo()

            samples.append((lat, lon, values))

    return samples
```

**Then in `_query_image`**: Return one row per sample point instead of bbox centroid

**Benefit**: Captures spatial gradients (e.g., elevation gradient across bbox)

---

### **Priority 2: Implement Resolution Parameter**

**Goal**: Allow users to control spatial sampling density

**Proposed values**:
- `"low"`: 1 sample per bbox (current behavior, fast)
- `"medium"`: 3×3 grid = 9 samples (good balance)
- `"high"`: 5×5 grid = 25 samples (detailed gradients)
- `"adaptive"`: Sample density based on bbox size and data scale
- `None`: Service-specific default

**Implementation**: Each adapter checks `spec.resolution` and adjusts sampling

**Example usage**:
```python
# Low resolution (single point, fast)
spec = RequestSpec(geometry=bbox, resolution="low")

# Medium resolution (capture gradients, balanced)
spec = RequestSpec(geometry=bbox, resolution="medium")

# High resolution (detailed, slower)
spec = RequestSpec(geometry=bbox, resolution="high")
```

---

### **Priority 3: Standardize Temporal Defaults**

**Goal**: Consistent behavior when time_range is None

**Proposed policy**:

1. **Services with temporal data** (Earth Engine, NASA POWER, WQP):
   - Default: Most recent complete year
   - Example: If today is 2025-10-20 → default to ("2024-01-01", "2024-12-31")

2. **Static services** (SoilGrids, SRTM, WorldClim):
   - Ignore time_range (data is atemporal)

3. **Time series services** (NASA POWER):
   - Default to recent year if not specified
   - Add `temporal_aggregation` parameter: "raw", "daily_mean", "monthly_mean", "annual_mean"

**Implementation example**:
```python
def _get_default_time_range(self):
    """Return most recent complete year as default time range"""
    from datetime import datetime
    current_year = datetime.now().year
    last_complete_year = current_year - 1
    return (f"{last_complete_year}-01-01", f"{last_complete_year}-12-31")
```

---

### **Priority 4: Add Metadata About Aggregation**

**Goal**: Make it clear to users when data has been spatially/temporally aggregated

**Proposed**: Add to `attributes` dict:

```python
{
    "spatial_aggregation": {
        "method": "mean",  # or "sample", "none"
        "bbox": [minlon, minlat, maxlon, maxlat],
        "n_samples": 9,  # Number of spatial samples
        "sample_coordinates": [(lat1, lon1), (lat2, lon2), ...]
    },
    "temporal_aggregation": {
        "method": "mean",  # or "first", "time_series", "none"
        "time_range": ("2021-01-01", "2021-12-31"),
        "n_images": 23,  # Number of images composited
        "fallback_applied": False
    }
}
```

**Benefit**: Users know if data is aggregated vs point samples

---

## Implementation Roadmap

### **Phase 1: Quick Wins (1-2 days)**

1. ✅ **Document the issue** (this document)
2. **Add aggregation metadata** to Earth Engine adapter
3. **Standardize time_range defaults** across adapters
4. **Add deprecation warning** when BaseAdapter fills centroid

### **Phase 2: Spatial Sampling (3-5 days)**

1. **Implement grid sampling** for Earth Engine
2. **Add resolution parameter** to Earth Engine adapter
3. **Test with realistic queries** (check performance impact)
4. **Update examples** to show gradient queries

### **Phase 3: Generalize (1 week)**

1. **Apply to SoilGrids** adapter (raster sampling)
2. **Apply to NASA POWER** adapter (request multiple grid points)
3. **Create base class mixin** for raster sampling
4. **Update documentation** with best practices

### **Phase 4: Advanced Features (optional)**

1. **Adaptive resolution** based on bbox size
2. **Temporal compositing control** (mean, median, min, max)
3. **Smart sampling** (avoid water pixels for land-based queries)
4. **Parallel sampling** for large bboxes

---

## Usage Guidance for econita Agent

**Current workaround** until fixes are implemented:

### **For capturing gradients in a bbox**:

**Option A**: Query multiple small bboxes (grid of points)
```python
# Instead of one large bbox:
# bbox = [lon_min, lat_min, lon_max, lat_max]

# Create grid of smaller bboxes:
import numpy as np
lons = np.linspace(lon_min, lon_max, 3)
lats = np.linspace(lat_min, lat_max, 3)

results = []
for lat in lats:
    for lon in lons:
        small_bbox = [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01]
        spec = RequestSpec(geometry=Geometry("bbox", small_bbox), ...)
        result = adapter.fetch(spec)
        results.append(result)

# Combine results to see gradient
all_data = pd.concat(results)
```

**Option B**: Use point queries instead of bbox
```python
# Sample at specific points
points = [
    (lon1, lat1),
    (lon2, lat2),
    (lon3, lat3)
]

results = []
for lon, lat in points:
    spec = RequestSpec(geometry=Geometry("point", [lon, lat]), ...)
    result = adapter.fetch(spec)
    results.append(result)
```

**Option C**: Use point-based services (GBIF, WQP)
These naturally return multiple points within a bbox and are not affected by the aggregation issue.

### **For temporal queries**:

**Always specify time_range explicitly**:
```python
# Good: Explicit time range
spec = RequestSpec(
    geometry=geometry,
    time_range=("2023-01-01", "2023-12-31")
)

# Bad: Relying on defaults (inconsistent)
spec = RequestSpec(geometry=geometry)  # May crash or use arbitrary default
```

---

## Testing Checklist

To verify the issues and validate fixes:

- [ ] **Test 1**: Query 1° × 1° bbox with Earth Engine SRTM (elevation)
  - Expected: Elevation should vary across bbox (mountains have gradients)
  - Current: Single mean elevation value

- [ ] **Test 2**: Query bbox with GBIF occurrences
  - Expected: Multiple occurrence points with different lat/lon
  - Current: ✅ Works correctly (point-based service)

- [ ] **Test 3**: Query bbox without time_range across all adapters
  - Expected: Consistent default behavior (recent year) or error
  - Current: ❌ Inconsistent (some crash, some use arbitrary defaults)

- [ ] **Test 4**: Query large bbox (10° × 10°) with high resolution
  - Expected: Multiple samples showing spatial gradients
  - Current: Single aggregated value

---

## Related Issues

- **GitHub Issue #XX**: "Bbox queries return single point for Earth Engine"
- **Documentation gap**: No guide on spatial resolution best practices
- **Missing examples**: No example showing how to capture gradients

---

## Conclusion

The current system has a **fundamental mismatch** between:
- **What users expect**: Multiple spatially distributed samples within a bbox to understand gradients
- **What's implemented**: Single aggregated value at bbox center for raster services

This is **fixable** with the proposed grid sampling approach. The fix will:
1. ✅ Enable gradient detection within bboxes
2. ✅ Make behavior consistent with point-based services
3. ✅ Give users control via resolution parameter
4. ✅ Preserve performance for users who want single aggregated value (resolution="low")

**Priority**: **HIGH** for econita integration - this is a core use case that's currently broken.
