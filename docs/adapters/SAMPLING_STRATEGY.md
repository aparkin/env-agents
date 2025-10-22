# Earth Engine Sampling Strategy

## Overview

The Earth Engine adapter uses adaptive sampling strategies to balance data quality (capturing spatial/temporal gradients) against performance constraints (API limits, memory, query time).

This document explains how sampling decisions are made and what could be improved with better metadata.

## Current Implementation

### Spatial Sampling Strategy

**Location:** `env_agents/adapters/earth_engine/spatial_sampling.py`

**Decision Factors:**
1. **Bbox dimensions** (calculated from coordinates using Haversine approximation)
2. **Data resolution** (`self.scale` - native resolution in meters)
3. **User preference** (`resolution="low/medium/high"`)
   - `low`: 1 sample (centroid)
   - `medium`: 9 samples (3×3 grid)
   - `high`: 25 samples (5×5 grid)
4. **Adaptive scaling** for large regions:
   - Areas > 10,000 km²: scale up using `sqrt(area/10000)` factor (max 5×)
   - Example: Texas bbox (270×165 km ≈ 44,550 km²) → 25 samples for medium resolution
5. **Max samples cap** (default 100, adaptively reduced for high-frequency data)

**Not Currently Used:**
- ❌ Asset temporal frequency
- ❌ Number of bands/variables
- ❌ Expected data volume

### Temporal Batching Strategy

**Location:** `env_agents/adapters/earth_engine/production_adapter.py:691-718`

**Current Heuristics:**
```python
# 1. Adaptive spatial sampling based on image count
if count > 100:  # Assumes daily or more frequent
    adaptive_max_samples = min(max_samples, 9)  # Reduce to 3×3 grid

# 2. Decide if temporal batching needed
needs_batching = (n_samples * count) > 1000

# 3. Calculate batch size
max_images_per_batch = max(10, 800 // n_samples)
```

**Problems with Current Approach:**

1. **Simple count threshold (100 images)**
   - Doesn't account for actual temporal resolution
   - 100 16-day MODIS images = 4.4 years
   - 100 daily SMAP images = 3.3 months
   - Both treated the same!

2. **No band/variable consideration**
   - SMAP: 46 bands × 365 days × 9 points = ~152,000 values
   - NDSI: 1 band × 365 days × 9 points = ~3,300 values
   - 46× difference ignored!

3. **Fixed thresholds**
   - Product threshold: 1000
   - Batch size target: 800
   - Based on empirical testing, not asset characteristics

4. **No data volume estimation**
   - Could calculate: `spatial_samples × temporal_samples × n_bands`
   - Would give accurate volume prediction

## Earth Engine Metadata Available

### Consistently Available (via `ee.data.getAsset()`)
- ✅ `type`: "IMAGE" or "IMAGE_COLLECTION"
- ✅ Band count: `len(first_image.bands)`
- ✅ Temporal range: `system:time_start`, `system:time_end` from images

### Inconsistently Available
- ⚠️ Temporal cadence/period: **NOT consistently provided**
  - Some datasets have custom properties (e.g., SMAP has daily structure in properties)
  - No standard `period` or `cadence` field
  - Must be inferred from date differences or external documentation

### Example Metadata

**MODIS/061/MOD13Q1** (16-day vegetation):
- Type: IMAGE_COLLECTION
- Bands: 12
- Properties: `system:time_start`, `system:time_end`, `num_tiles`, etc.
- ❌ No `period` field

**NASA/SMAP/SPL4SMGP/008** (daily soil moisture):
- Type: IMAGE_COLLECTION
- Bands: 46 (!!)
- Properties: Many SMAP-specific config fields
- ❌ No `period` field (must infer from `start_hour`/`end_hour`)

**MODIS/MOD09GA_006_NDSI** (daily snow index):
- Type: IMAGE_COLLECTION
- Bands: 1
- Properties: Minimal
- ❌ No `period` field

## Improved Strategy (Future Work)

### Phase 2 Enhancement: Metadata-Driven Batching

**Proposal:** Calculate expected data volume to make smarter decisions

```python
# 1. Get asset metadata at initialization
def __init__(self, asset_id, scale):
    self.asset_id = asset_id
    self.scale = scale
    self.n_bands = self._get_band_count()  # Query once, cache

def _get_band_count(self):
    """Get number of bands from asset"""
    try:
        if self._asset_is_collection():
            ic = ee.ImageCollection(self.asset_id)
            first = ic.first()
            return len(first.bandNames().getInfo())
        else:
            img = ee.Image(self.asset_id)
            return len(img.bandNames().getInfo())
    except:
        return 10  # Conservative fallback

# 2. Estimate temporal cadence from actual dates
def _estimate_cadence_days(self, ic, count):
    """Estimate days between observations from sample"""
    if count < 2:
        return None

    # Sample first and 10th image (or last if fewer)
    sample_size = min(10, count)
    first = ic.sort('system:time_start').first()
    tenth = ic.sort('system:time_start').toList(sample_size).get(sample_size - 1)

    first_date = ee.Date(first.get('system:time_start')).millis().getInfo()
    tenth_date = ee.Date(ee.Image(tenth).get('system:time_start')).millis().getInfo()

    # Calculate average cadence
    days_diff = (tenth_date - first_date) / (1000 * 60 * 60 * 24)
    cadence = days_diff / (sample_size - 1)

    return cadence

# 3. Calculate expected data volume
def _choose_sampling_strategy(self, bbox, count, spec):
    """Choose sampling based on expected data volume"""

    # Estimate data volume
    base_samples = 25 if spec.resolution == 'high' else 9
    estimated_volume = base_samples * count * self.n_bands

    # Adjust spatial sampling based on volume
    if estimated_volume > 100_000:  # Very large query
        adaptive_samples = 9  # Force 3×3
    elif estimated_volume > 50_000:  # Large query
        adaptive_samples = min(base_samples, 16)  # Max 4×4
    else:
        adaptive_samples = base_samples

    # Calculate batch size based on volume per image
    volume_per_image = adaptive_samples * self.n_bands

    if volume_per_image > 500:  # e.g., 25 points × 46 bands = 1,150
        # Very dense data: use small batches
        max_images_per_batch = max(5, 500 // volume_per_image)
    elif volume_per_image > 100:  # e.g., 25 points × 10 bands = 250
        # Moderate density: use medium batches
        max_images_per_batch = max(10, 1000 // volume_per_image)
    else:
        # Sparse data: use large batches
        max_images_per_batch = max(20, 2000 // volume_per_image)

    return adaptive_samples, max_images_per_batch
```

### Benefits of Metadata-Driven Approach

1. **Accurate volume prediction**
   - SMAP: 25 × 365 × 46 = 420,250 → force small batches
   - NDSI: 9 × 365 × 1 = 3,285 → can use large batches

2. **Adaptive thresholds**
   - No fixed "count > 100" rule
   - Based on actual expected data size

3. **Better performance**
   - Fewer unnecessary small batches for sparse data
   - More aggressive batching for dense data

### Limitations

**Cannot fully solve without Earth Engine API changes:**
- No way to query only subset of bands via `sampleRegions()`
- Earth Engine returns all bands or none
- Would need band filtering at API level

**Temporal cadence still requires heuristics:**
- No standard metadata field
- Must infer from actual dates (requires additional API call)
- Could maintain static lookup table for common datasets

## Test Results: Phase 1 Robustness Fixes

**Date:** 2025-10-22

**Changes:**
1. Added asset type validation (detect FeatureCollection/Table)
2. Implemented adaptive spatial sampling (9 pts for count > 100)
3. Tuned batch parameters (threshold=1000, batch=800)

**Results:** 15/17 assets passing (88%)

| Asset | Status | Duration | Samples | Notes |
|-------|--------|----------|---------|-------|
| MOD13Q1 (16d, 12 bands) | ✅ | 4.45s | 25×23 | Perfect |
| MOD15A2H (8d, 6 bands) | ✅ | 3.74s | 24×46 | Perfect |
| NDSI (daily, 1 band) | ✅ | 19.97s | 9×365 | **Fixed!** Was failing |
| SMAP (daily, 46 bands) | ❌ | 209s | Memory exceeded | 9×365×46 = 152k values |
| WorldCereal (Table) | ❌ | 0.45s | Fast fail | Clear error message |

**Key Insight:** Batching strategy successfully fixed NDSI but couldn't handle SMAP's extreme band count (46×).

## Recommendations

**Short term (Current Phase 1):**
- ✅ Use simple heuristics (working well for 88% of assets)
- ✅ Document limitations clearly
- ✅ Provide guidance for problematic assets

**Medium term (Phase 2 - if needed):**
- Query band count at initialization (1 extra API call, cached)
- Use volume-based thresholds instead of count-based
- Maintain lookup table for known asset cadences

**Long term (requires Earth Engine API support):**
- Request band filtering in `sampleRegions()` API
- Request standardized `period`/`cadence` metadata field
- Request progress callbacks for long-running queries

## Usage Guidance

### For High-Frequency, Multi-Band Assets (e.g., SMAP)

**Option 1: Reduce temporal range**
```python
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    time_range=("2020-01-01", "2020-01-31"),  # Single month instead of year
    resolution="medium"
)
```

**Option 2: Use low resolution (single centroid)**
```python
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    time_range=("2020-01-01", "2020-12-31"),
    resolution="low"  # Single aggregated point
)
```

**Option 3: Reduce spatial sampling explicitly**
```python
spec = RequestSpec(
    geometry=Geometry("bbox", bbox),
    time_range=("2020-01-01", "2020-12-31"),
    resolution="medium",
    extra={"max_samples": 4}  # Force 2×2 grid
)
```

### Known Problematic Assets

**High-band, daily datasets** (may exceed memory):
- `NASA/SMAP/SPL4SMGP/008` (46 bands, daily) - use short time ranges or low resolution
- Assets with 20+ bands + daily cadence - similar constraints

**Unsupported asset types:**
- `ESA/WorldCereal/AEZ/v100` (Table) - not supported
- `LARSE/GEDI/GEDI04_A_002` (FeatureCollection) - not supported
- Any FeatureCollection or Table asset - use different query methods

## References

- **Earth Engine Limits:** https://developers.google.com/earth-engine/guides/usage
  - FeatureCollection.flatten(): ~5000 elements
  - User memory limit: varies by account type
  - Computation timeout: 5 minutes (interactive), 30 minutes (batch)

- **Spatial Sampling Implementation:** `env_agents/adapters/earth_engine/spatial_sampling.py`
- **Batching Implementation:** `env_agents/adapters/earth_engine/production_adapter.py:691-780`
- **Comprehensive Test:** `tests/test_comprehensive_assets.py`
