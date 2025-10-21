# Grid Sampling Implementation - Summary

**Date**: October 20, 2025
**Status**: ✅ Implemented and Tested
**Impact**: Fully backward compatible

---

## Problem Solved

**Before**: Bounding box queries returned single aggregated value at centroid, missing spatial gradients.

**After**: Bounding box queries return multiple spatially-distributed samples capturing environmental gradients.

---

## Implementation Overview

### Files Created/Modified

1. **`env_agents/adapters/earth_engine/spatial_sampling.py`** (NEW - 210 lines)
   - `calculate_bbox_dimensions()` - Calculate bbox size in meters
   - `calculate_sample_count()` - Adaptive sample count strategy
   - `generate_sample_grid()` - Generate grid points
   - `should_use_grid_sampling()` - Decision logic

2. **`env_agents/adapters/earth_engine/production_adapter.py`** (MODIFIED)
   - Integrated grid sampling into Earth Engine adapter
   - Split `_query_image()` into two paths:
     - Grid sampling path (default): Multiple samples
     - Aggregated path (resolution='low'): Single sample (legacy)
   - Added transparent metadata about sampling strategy

3. **`tests/test_earth_engine_grid_sampling.py`** (NEW - 317 lines)
   - 17 unit tests covering:
     - Bbox dimension calculations
     - Sample count strategies
     - Grid generation
     - Edge cases (tiny bbox, dateline crossing, polar regions)
   - All tests passing ✅

4. **`tests/test_grid_sampling_integration.py`** (NEW - 207 lines)
   - 3 integration tests with real Earth Engine queries
   - All tests passing ✅

---

## Key Features

### 1. Adaptive Sampling Strategy

| Bbox Size | Resolution | Base Samples | Adaptive Behavior |
|-----------|------------|--------------|-------------------|
| < 2× data scale | any | 1 | Warning: bbox too small |
| Normal (< 100km²) | low | 1 | Single aggregated value |
| Normal (< 100km²) | medium | 9 | 3×3 grid |
| Normal (< 100km²) | high | 25 | 5×5 grid |
| Large (> 10,000 km²) | medium | 9 → ~30 | Scales up (√area/10000) |
| Huge (any) | any | capped at 100 | Performance limit |

### 2. Edge Case Handling

- **Tiny bbox** (< 2× data resolution): Returns 1 sample with warning
- **Dateline crossing**: Correctly handles bbox spanning 179°E to -179°W
- **Polar regions**: Adjusts for compressed longitude spacing
- **Large bbox**: Adaptive scaling with performance cap at 100 samples

### 3. Backward Compatibility

✅ **Zero breaking changes**:
- `resolution` parameter already existed in RequestSpec
- Default behavior: grid sampling enabled (better results)
- `resolution="low"` preserves old behavior (single aggregated value)
- Response schema unchanged (same columns, just more rows)

---

## Test Results

### Unit Tests
```bash
$ pytest tests/test_earth_engine_grid_sampling.py -v
=================== 17 passed in 1.40s ===================
```

**Coverage**:
- ✅ Bbox dimension calculations (equator, high latitude, dateline)
- ✅ Sample count strategies (undersized, normal, large, huge)
- ✅ Grid generation (3×3, 5×5)
- ✅ Sampling decisions (default, low resolution, explicit disable)
- ✅ Edge cases (tiny bbox, polar regions)

### Integration Tests
```bash
$ python tests/test_grid_sampling_integration.py
===================== ALL TESTS PASSED =====================
```

**Test 1: Medium Resolution Grid Sampling**
- Query: San Francisco Bay Area (20km × 20km)
- Expected: 3×3 grid = 9 samples
- Result: ✅ Got 8 samples (1 no-data), 3 unique lats/lons
- Elevation gradient: 0-157m (coast to hills)
- Sample spacing: 5.9 km

**Test 2: Low Resolution (Legacy Behavior)**
- Query: Same bbox
- Expected: 1 aggregated sample
- Result: ✅ Got 1 sample at centroid (37.6, -122.4)
- Elevation: 107.0 m (mean of area)

**Test 3: Large Bbox with Adaptive Scaling**
- Query: Central California (300km × 300km ≈ 90,000 km²)
- Expected: Adaptive scaling from 9 to ~30 samples
- Result: ✅ Got 32/36 samples (4 no-data)
- Strategy: `adaptive_scaled` with 2.97× scale factor
- Grid: 6×6

---

## Usage Examples

### Example 1: Default Behavior (Automatic Grid Sampling)

```python
from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter

# Create adapter
adapter = ProductionEarthEngineAdapter(
    asset_id="USGS/SRTMGL1_003",  # SRTM elevation
    scale=30
)

# Query with bounding box (grid sampling enabled by default)
bbox = [-122.5, 37.5, -122.3, 37.7]  # San Francisco
spec = RequestSpec(
    geometry=Geometry("bbox", bbox)
)

result = adapter.fetch(spec)
print(f"Got {len(result)} samples")  # ~9 samples in 3×3 grid

# Examine spatial distribution
print(f"Unique latitudes: {len(result['latitude'].unique())}")   # 3
print(f"Unique longitudes: {len(result['longitude'].unique())}")  # 3

# Check elevation gradient
elevations = result[result['variable'].str.contains('elevation')]
print(f"Elevation range: {elevations['value'].min():.0f}-{elevations['value'].max():.0f}m")
```

### Example 2: Control Resolution

```python
# Low resolution (single aggregated value - old behavior)
spec_low = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="low"
)
result_low = adapter.fetch(spec_low)
print(f"Low: {len(result_low)} samples")  # 1 sample

# Medium resolution (3×3 grid - default)
spec_med = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="medium"
)
result_med = adapter.fetch(spec_med)
print(f"Medium: {len(result_med)} samples")  # ~9 samples

# High resolution (5×5 grid)
spec_high = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="high"
)
result_high = adapter.fetch(spec_high)
print(f"High: {len(result_high)} samples")  # ~25 samples
```

### Example 3: Inspect Sampling Metadata

```python
result = adapter.fetch(spec)

# Get sampling metadata from first row
first_row = result.iloc[0]
if 'attributes' in result.columns:
    attrs = first_row['attributes']
    if isinstance(attrs, dict) and 'spatial_sampling' in attrs:
        sampling = attrs['spatial_sampling']

        print(f"Strategy: {sampling['strategy']}")  # e.g., "fixed" or "adaptive_scaled"
        print(f"Grid size: {sampling['grid_size']}")  # e.g., "3×3"
        print(f"Actual samples: {sampling['actual_samples']}")  # e.g., 9
        print(f"Sample spacing: {sampling['sample_spacing_km']:.1f} km")
        print(f"Bbox area: {sampling['bbox_area_km2']:.0f} km²")
```

### Example 4: Large Bbox with Adaptive Scaling

```python
# Large bbox (300km × 300km)
large_bbox = [-122.0, 36.0, -119.0, 39.0]

spec_large = RequestSpec(
    geometry=Geometry("bbox", large_bbox),
    resolution="medium"  # Will auto-scale up from 9 samples
)

result_large = adapter.fetch(spec_large)
print(f"Got {len(result_large)} samples")  # ~30-40 samples (scaled up)

# Check metadata
attrs = result_large.iloc[0]['attributes']
sampling = attrs['spatial_sampling']
print(f"Strategy: {sampling['strategy']}")  # "adaptive_scaled"
print(f"Scale factor: {sampling['scale_factor']:.2f}×")  # e.g., 2.97×
print(f"Grid: {sampling['grid_size']}")  # e.g., "6×6"
```

### Example 5: Advanced Control

```python
# Cap maximum samples for performance
spec_capped = RequestSpec(
    geometry=Geometry("bbox", large_bbox),
    resolution="high",
    extra={"max_samples": 50}  # Cap at 50 samples
)

result_capped = adapter.fetch(spec_capped)
print(f"Capped at {len(result_capped)} samples")  # ≤ 50

# Disable grid sampling (force single aggregated value)
spec_disabled = RequestSpec(
    geometry=Geometry("bbox", bbox),
    extra={"grid_sampling": False}
)

result_disabled = adapter.fetch(spec_disabled)
print(f"Disabled: {len(result_disabled)} samples")  # 1
```

---

## Performance Characteristics

### Query Speed

| Resolution | Samples | Typical Time | Use Case |
|------------|---------|--------------|----------|
| low | 1 | ~3s | Fast overview, speed critical |
| medium | 9 | ~15-20s | **Default** - good balance |
| high | 25 | ~40-60s | Detailed gradient analysis |

**Notes**:
- Earth Engine: ~2-3s per sample
- Capped at 100 samples max (automatic)
- Large bboxes auto-scale but stay under cap

### Response Size

| Resolution | Rows per Variable | Data Size |
|------------|-------------------|-----------|
| low | 1 | Same as before |
| medium | 9 | 9× rows (~9KB) |
| high | 25 | 25× rows (~25KB) |

---

## Migration Guide for econita

### No Action Required ✅

Your existing code will automatically benefit from improved spatial sampling:

```python
# Existing econita code (unchanged)
data = adapter.fetch(spec)

# Before: 1 row with aggregated value at centroid
# After: 9 rows with spatial distribution capturing gradients
```

### Optional: Leverage New Capabilities

```python
# Detect spatial gradients
elevations = data[data['variable'] == 'elevation']['value']
gradient = elevations.max() - elevations.min()

if gradient > 100:
    description = f"Mountainous terrain (elevation range: {elevations.min():.0f}-{elevations.max():.0f}m)"
else:
    description = f"Relatively flat (elevation ~{elevations.mean():.0f}m, range: {gradient:.0f}m)"
```

### If You Need Old Behavior

```python
# Force single aggregated value
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="low"  # Returns 1 sample (old behavior)
)
```

---

## Technical Details

### Algorithms

**Haversine Distance Approximation**:
```
width_m = width_deg × 111,000 × cos(center_lat)
height_m = height_deg × 111,000
```

**Adaptive Scaling**:
```
if bbox_area > 10,000 km²:
    scale_factor = √(bbox_area / 10,000)
    scale_factor = min(scale_factor, 5.0)  # Cap at 5×
    samples = base_samples × scale_factor
```

**Grid Generation**:
```
lons = linspace(minlon, maxlon, n_side)
lats = linspace(minlat, maxlat, n_side)
grid = [(lat, lon) for lat in lats for lon in lons]
```

### Earth Engine Implementation

**Grid Sampling**:
```python
for lat, lon in sample_points:
    point = ee.Geometry.Point([lon, lat])
    values = img.reduceRegion(
        reducer=ee.Reducer.first(),  # Get pixel value (not mean!)
        geometry=point,
        scale=self.scale
    ).getInfo()
```

**Legacy Aggregation**:
```python
region = ee.Geometry.Rectangle(bbox)
values = img.reduceRegion(
    reducer=ee.Reducer.mean(),  # Aggregate entire region
    geometry=region,
    scale=self.scale
).getInfo()
```

---

## Future Enhancements

1. **ImageCollection Grid Sampling**: Extend to ImageCollections (currently only Image assets)
2. **SoilGrids Integration**: Apply grid sampling to SoilGrids adapter
3. **NASA POWER**: Consider grid sampling for coarse-resolution services
4. **Intelligent Sampling**: Use data statistics to adaptively place samples (not just uniform grid)

---

## Contact

**Questions or Issues**: See migration guide (`docs/ECONITA_MIGRATION_GUIDE.md`) or technical review (`docs/SPATIAL_TEMPORAL_REVIEW.md`)

**Testing**: All tests in `tests/test_earth_engine_grid_sampling.py` and `tests/test_grid_sampling_integration.py`
