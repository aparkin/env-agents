# Resolution Strategy: Grid Sampling Design

**Date**: October 20, 2025
**Context**: Designing spatial sampling for bounding box queries

---

## The Core Problem

We have **three scales** that must work together:

1. **Data Scale** (native resolution of service)
   - SRTM: 30m pixels
   - MODIS: 250m pixels
   - SoilGrids: 250m pixels
   - NASA POWER: 0.5° grid (~50km at equator!)

2. **Bbox Size** (user's query extent)
   - Tiny: 10m × 10m (urban block)
   - Small: 1km × 1km (neighborhood)
   - Medium: 10km × 10km (city)
   - Large: 100km × 100km (region)
   - Huge: 1000km × 1000km (country)

3. **Sampling Density** (resolution parameter)
   - Low: 1 sample (fast)
   - Medium: 9 samples (3×3 grid)
   - High: 25 samples (5×5 grid)

**Key Question**: How do these interact? What happens at the extremes?

---

## Scenario Analysis

### **Scenario 1: Tiny Bbox, Fine Data Scale**
**Query**: 10m × 10m bbox, SRTM elevation (30m pixels)

```
Bbox: 10m × 10m
Data scale: 30m
Ratio: 0.33 (bbox smaller than 1 pixel!)

User requests: resolution="medium" (9 samples)
```

**Problem**:
- Bbox is smaller than one SRTM pixel
- Grid sampling returns **same value 9 times** (all points in same pixel)
- Wastes API calls, misleads user

**Solution**:
```python
# Detect undersized bbox
if bbox_width_m < data_scale_m * 2:
    actual_samples = 1
    metadata = {
        "sampling_strategy": "single_point",
        "warning": "Bbox smaller than data resolution, returning 1 sample"
    }
```

**Result**: Return 1 value with clear metadata

---

### **Scenario 2: Medium Bbox, Medium Data Scale**
**Query**: 10km × 10km bbox, MODIS NDVI (250m pixels)

```
Bbox: 10km × 10km = 10,000m × 10,000m
Data scale: 250m
Ratio: 40 pixels per side = 1,600 total pixels in bbox

User requests: resolution="medium" (9 samples)
```

**Analysis**:
- 9 samples from 1,600 available pixels = 0.5% sampling
- Sample spacing: 10,000m / 3 = ~3,333m = 13 pixels apart
- **Good gradient capture without overwhelming detail**

**Grid Layout**:
```
+---+---+---+
| 1 | 2 | 3 |  Each cell spans ~3.3km
+---+---+---+  Captures north-south gradient
| 4 | 5 | 6 |  Captures east-west gradient
+---+---+---+  Captures corners (elevation extremes)
| 7 | 8 | 9 |
+---+---+---+
```

**Solution**: Use requested sampling (9 samples) as-is

---

### **Scenario 3: Huge Bbox, Medium Data Scale**
**Query**: 1000km × 1000km bbox, MODIS NDVI (250m pixels)

```
Bbox: 1,000,000m × 1,000,000m
Data scale: 250m
Ratio: 4,000 pixels per side = 16 MILLION pixels in bbox!

User requests: resolution="medium" (9 samples)
```

**Problem**:
- 9 samples from 16M pixels = 0.00005% sampling
- Sample spacing: 1,000km / 3 = ~333km apart
- **Likely to miss important regional variation**
- Example: Temperature gradient from coast to mountains gets only 3 samples along that axis

**Options**:

**Option A: Respect user's intent** (9 samples)
- Pro: Predictable, fast, gives overview
- Con: Misses important variation in large areas

**Option B: Adaptive scaling** (scale up samples for large bboxes)
- Pro: Better gradient capture
- Con: Unpredictable sample count, possibly slow

**Option C: Warn and suggest alternative**
- Pro: Educational, gives user control
- Con: Extra friction

**Recommended Solution**: **Hybrid approach**

```python
# Calculate adaptive sample count
bbox_area_km2 = calculate_area(bbox)

if bbox_area_km2 < 100:  # < 10km × 10km
    # Small bbox - use requested samples
    multiplier = 1

elif bbox_area_km2 < 10000:  # < 100km × 100km
    # Medium bbox - use requested samples
    multiplier = 1

else:  # > 100km × 100km
    # Large bbox - scale up intelligently
    # But cap at reasonable limit
    multiplier = min(sqrt(bbox_area_km2 / 10000), 5)
    # 1000km × 1000km → multiplier = 3.16
    # So medium (9) → 9 × 3.16 = ~28 samples

# Apply multiplier
if resolution == "low":
    base_samples = 1
elif resolution == "medium":
    base_samples = 9
elif resolution == "high":
    base_samples = 25

actual_samples = base_samples * multiplier
actual_samples = min(actual_samples, max_samples_limit)  # Cap at 100
```

---

### **Scenario 4: Medium Bbox, Coarse Data Scale**
**Query**: 10km × 10km bbox, NASA POWER (0.5° ≈ 50km grid)

```
Bbox: 10km × 10km
Data scale: 50km (!)
Ratio: 0.2 (bbox is 1/5th of one grid cell)

User requests: resolution="medium" (9 samples)
```

**Problem**:
- Entire bbox falls within **single NASA POWER grid cell**
- All 9 samples return **identical value** (same grid cell)
- Like Scenario 1 but due to coarse data, not small bbox

**Detection**:
```python
# Calculate how many data grid cells bbox spans
bbox_width_m = 10000  # 10km
data_scale_m = 50000  # 50km for NASA POWER

cells_spanned = bbox_width_m / data_scale_m  # = 0.2

if cells_spanned < 1.5:
    # Bbox spans less than 2 grid cells
    actual_samples = 1
    metadata = {
        "warning": "Bbox smaller than data grid spacing (50km), returning single grid cell value",
        "recommendation": "For gradients, query bbox > 100km to span multiple grid cells"
    }
```

---

## Design Principles

### **Principle 1: Data-Aware Sampling**
Never sample finer than the data's native resolution

```python
# Calculate minimum meaningful sample spacing
min_spacing_m = data_scale_m * 2  # At least 2 pixels apart

# Calculate bbox-based sample spacing
if resolution == "medium":
    target_spacing_m = bbox_width_m / 3  # 3×3 grid

# Use the larger (coarser) spacing
actual_spacing_m = max(min_spacing_m, target_spacing_m)
```

**Effect**: Automatically reduces samples when data scale limits resolution

---

### **Principle 2: Adaptive Scaling for Large Bboxes**
Scale up sampling for large areas to avoid missing variation

```python
def calculate_sample_count(bbox_area_km2, resolution):
    base = {"low": 1, "medium": 9, "high": 25}[resolution]

    if bbox_area_km2 > 10000:  # > 100km × 100km
        scale_factor = sqrt(bbox_area_km2 / 10000)
        scale_factor = min(scale_factor, 5)  # Cap at 5× scaling
        return int(base * scale_factor)

    return base
```

**Examples**:
- 10km × 10km, medium → 9 samples (no scaling)
- 100km × 100km, medium → 9 samples (boundary case)
- 300km × 300km, medium → 9 × 3 = 27 samples (scaled up)
- 1000km × 1000km, medium → 9 × 5 = 45 samples (capped at 5×)

---

### **Principle 3: Performance Bounds**
Cap maximum samples to avoid overwhelming queries

```python
MAX_SAMPLES = 100  # Hard limit regardless of bbox size

# Also consider per-service limits
SERVICE_LIMITS = {
    "EARTH_ENGINE": 100,  # getInfo() calls are slow
    "NASA_POWER": 50,     # API might rate limit
    "SOILGRIDS": 100      # WCS queries can be slow
}
```

---

### **Principle 4: Transparent Metadata**
Always report actual sampling strategy used

```python
{
    "spatial_sampling": {
        "requested_resolution": "medium",
        "requested_samples": 9,
        "actual_samples": 27,
        "scaling_applied": True,
        "scaling_reason": "Large bbox (300km × 300km) scaled 3×",
        "sample_spacing_km": 100,
        "data_scale_km": 0.25,
        "bbox_area_km2": 90000,
        "sample_coordinates": [
            {"lat": 37.1, "lon": -122.1},
            {"lat": 37.1, "lon": -121.5},
            # ... 25 more
        ]
    }
}
```

---

## Resolution Parameter Design

### **Option A: Fixed Sample Counts** (Simple)

```python
resolution = "medium"  # Fixed 9 samples, period
```

**Pros**: Predictable, simple to understand
**Cons**: Terrible for large bboxes, wasteful for small bboxes

---

### **Option B: Target Spacing** (Distance-based)

```python
resolution = "1km"  # Sample every 1km
# 10km bbox → 10×10 = 100 samples
# 100km bbox → 100×100 = 10,000 samples (!)
```

**Pros**: Scales naturally with bbox size
**Cons**: Can explode for large bboxes, unclear for beginners

---

### **Option C: Adaptive Strategy** (Smart defaults) ⭐ **RECOMMENDED**

```python
resolution = "medium"
# Means: "Give me useful gradients without overwhelming detail"
# Implementation adapts based on bbox size and data scale
```

**Behavior**:
- Small bbox → fewer samples (respects data limits)
- Large bbox → more samples (captures regional variation)
- Always capped at reasonable maximum
- Reports actual strategy in metadata

**With optional overrides**:
```python
spec = RequestSpec(
    geometry=bbox,
    resolution="medium",  # Adaptive strategy
    extra={
        "max_samples": 50,      # User-specified cap
        "min_spacing_km": 10    # Don't sample closer than 10km
    }
)
```

---

## Recommended Implementation

### **Step 1: Calculate Data-Aware Sample Count**

```python
def calculate_sample_count(bbox, data_scale_m, resolution, max_samples=100):
    """
    Calculate appropriate sample count considering bbox size and data scale.

    Args:
        bbox: [minlon, minlat, maxlon, maxlat]
        data_scale_m: Native resolution of data source (meters)
        resolution: "low", "medium", "high", or "adaptive"
        max_samples: Maximum samples to prevent overwhelming queries

    Returns:
        (n_samples, n_side, metadata_dict)
    """
    # Calculate bbox dimensions
    bbox_width_m, bbox_height_m = calculate_bbox_dimensions(bbox)
    bbox_area_km2 = (bbox_width_m * bbox_height_m) / 1e6

    # Base sample counts
    base_counts = {"low": 1, "medium": 9, "high": 25}
    base_samples = base_counts.get(resolution, 9)

    # Check if bbox is smaller than data scale
    if bbox_width_m < data_scale_m * 2 or bbox_height_m < data_scale_m * 2:
        return (1, 1, {
            "strategy": "undersized_bbox",
            "warning": f"Bbox ({bbox_width_m}m) smaller than 2× data scale ({data_scale_m}m)",
            "recommendation": f"Increase bbox to > {data_scale_m * 2}m for meaningful gradients"
        })

    # Adaptive scaling for large bboxes
    if bbox_area_km2 > 10000:  # > 100km × 100km
        scale_factor = (bbox_area_km2 / 10000) ** 0.5  # Square root scaling
        scale_factor = min(scale_factor, 5)  # Cap at 5×
        scaled_samples = int(base_samples * scale_factor)
    else:
        scaled_samples = base_samples
        scale_factor = 1.0

    # Apply maximum cap
    final_samples = min(scaled_samples, max_samples)

    # Calculate grid dimensions (nearest square)
    n_side = int(final_samples ** 0.5)
    if n_side * n_side < final_samples:
        n_side += 1
    actual_samples = n_side * n_side

    # Calculate spacing
    sample_spacing_m = min(bbox_width_m, bbox_height_m) / n_side

    metadata = {
        "strategy": "adaptive" if scale_factor > 1 else "fixed",
        "requested_resolution": resolution,
        "requested_samples": base_samples,
        "actual_samples": actual_samples,
        "grid_size": f"{n_side}×{n_side}",
        "sample_spacing_m": sample_spacing_m,
        "sample_spacing_km": sample_spacing_m / 1000,
        "bbox_area_km2": bbox_area_km2,
        "data_scale_m": data_scale_m,
        "scale_factor": scale_factor,
        "capped": actual_samples < scaled_samples
    }

    return (actual_samples, n_side, metadata)
```

### **Step 2: Generate Sample Grid**

```python
def generate_sample_grid(bbox, n_side):
    """
    Generate regular grid of sample points within bbox.

    Returns: List of (lat, lon) tuples
    """
    minlon, minlat, maxlon, maxlat = bbox

    # Generate linearly spaced coordinates
    lons = np.linspace(minlon, maxlon, n_side)
    lats = np.linspace(minlat, maxlat, n_side)

    # Create grid
    sample_points = []
    for lat in lats:
        for lon in lons:
            sample_points.append((lat, lon))

    return sample_points
```

### **Step 3: Query Each Sample Point**

```python
def sample_raster_bbox(img, bbox, data_scale_m, resolution):
    """Query raster at multiple sample points."""

    # Calculate sampling strategy
    n_samples, n_side, metadata = calculate_sample_count(
        bbox, data_scale_m, resolution
    )

    # Generate sample points
    sample_points = generate_sample_grid(bbox, n_side)

    # Query each point
    rows = []
    for lat, lon in sample_points:
        point = ee.Geometry.Point([lon, lat])
        values = img.reduceRegion(
            reducer=ee.Reducer.first(),  # Get pixel value
            geometry=point,
            scale=data_scale_m,
            maxPixels=1
        ).getInfo()

        # Create row for each variable
        for var, val in values.items():
            if val is not None:
                rows.append({
                    "latitude": lat,
                    "longitude": lon,
                    "variable": var,
                    "value": val,
                    "attributes": {"spatial_sampling": metadata}
                })

    return rows
```

---

## Usage Examples

### **Example 1: Small Urban Area**
```python
# Query 1km × 1km downtown area
bbox = [-122.42, 37.78, -122.41, 37.79]  # San Francisco

spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="medium"
)

# Result: 9 samples (3×3 grid, ~333m spacing)
# Captures elevation gradient from waterfront to hills
```

### **Example 2: Regional Analysis**
```python
# Query 100km × 100km agricultural region
bbox = [-122.0, 37.0, -121.0, 38.0]  # Central Valley

spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="medium"
)

# Result: 9 samples (no scaling, bbox at boundary)
# Spacing: ~33km
# Good for regional overview, might miss local variation
```

### **Example 3: Large State**
```python
# Query 500km × 500km across California
bbox = [-124.0, 36.0, -119.0, 40.0]

spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="medium"
)

# Result: 27-45 samples (3× scaling applied)
# Spacing: ~100km with medium, ~50km with high
# Captures north-south climate gradient, coastal vs inland
```

### **Example 4: Tiny Plot (Sub-resolution)**
```python
# Query 20m × 20m agricultural plot
bbox = [-122.4, 37.78, -122.3999, 37.7801]

spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    resolution="high"  # User wants detail
)

# Result: 1 sample with warning
# Warning: "Bbox (20m) smaller than data resolution (250m for MODIS)"
# Recommendation: "Use higher-resolution data source or larger bbox"
```

---

## Trade-offs Summary

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Fixed samples** | Predictable, simple | Terrible for extremes | Consistent bbox sizes |
| **Distance-based** | Natural scaling | Can explode, complex | Advanced users |
| **Adaptive** ⭐ | Smart defaults, bounded | Less predictable | General use, econita |

**Recommendation**: **Adaptive with user overrides**

---

## Synergies with Resolution Parameter

**Resolution** = User's intent (low/medium/high detail)
**Grid sampling** = Implementation strategy
**Data scale** = Physical constraint

**They work together**:

```python
resolution="high"  # User wants detail
    ↓
base_samples=25  # 5×5 grid
    ↓
[Check data scale and bbox size]
    ↓
actual_samples=16  # Reduced because bbox small
    OR
actual_samples=100  # Scaled up because bbox huge, capped at max
    ↓
[Generate grid and query]
    ↓
[Return results with transparent metadata]
```

---

## API Design Proposal

```python
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),

    # Simple interface
    resolution="medium",  # "low", "medium", "high", "adaptive"

    # Advanced overrides (optional)
    extra={
        "max_samples": 50,           # Cap sample count
        "min_spacing_km": 10,        # Minimum spacing between samples
        "adaptive_scaling": True,    # Enable/disable large bbox scaling
        "return_strategy": "grid"    # "grid", "random", "stratified"
    }
)
```

**Result includes strategy metadata**:
```python
{
    "data": [...],  # Actual observations
    "spatial_sampling": {
        "strategy": "adaptive_grid",
        "requested": "medium",
        "actual_samples": 27,
        "grid_size": "5×5" ,
        "spacing_km": 20,
        "explanation": "Large bbox (300km) scaled from 9 to 25 samples"
    }
}
```

---

## Conclusion

**Resolution and grid sampling are complementary**:

- **Resolution** = What the user wants (detail level)
- **Grid sampling** = How we deliver it (implementation)
- **Data scale** = Physical limit (can't sample finer than pixels)
- **Bbox size** = Context (determines appropriate sampling density)

**Recommended approach**: **Adaptive strategy**
- Respects data limits (no oversampling sub-resolution bboxes)
- Scales intelligently (more samples for large areas)
- Bounded performance (capped at reasonable maximum)
- Transparent (reports actual strategy used)
- User-controllable (can override with max_samples, min_spacing)

**This enables econita to**:
- Query any bbox size without manual tuning
- Get meaningful gradients when they exist
- Avoid wasted API calls on sub-resolution bboxes
- Understand what sampling strategy was actually used
