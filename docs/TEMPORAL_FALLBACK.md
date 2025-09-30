# Temporal Fallback Strategy for Earth Engine Assets

**Date:** 2025-09-30
**Status:** ✅ Implemented and Tested

## Overview

The Earth Engine production adapter automatically handles cases where requested dates are outside a dataset's available temporal range. Instead of failing with "image is null" errors, it falls back to the closest available data and annotates observations with metadata about the fallback.

## Problem Addressed

### Root Cause
Some Earth Engine ImageCollections have finite temporal coverage:
- **MODIS_LANDCOVER (MODIS/006/MCD12Q1)**: Available 2000-2019, ends at 2019
- **GOOGLE_EMBEDDINGS (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL)**: Available 2017-present, but some locations have sparse coverage

When requesting dates outside this range:
```python
ic = ee.ImageCollection(asset_id).filterDate("2021-01-01", "2021-12-31")
count = ic.size().getInfo()  # Returns 0
first = ic.first()  # Returns null
bands = first.bandNames().getInfo()  # ERROR: "Parameter 'image' is required and may not be null"
```

### Previous Behavior
- Requested 2021 data from MODIS_LANDCOVER → Empty collection → Crash with "image is null" error
- 100% failure rate for MODIS_LANDCOVER (all 4,789 clusters)
- Intermittent failures for GOOGLE_EMBEDDINGS at locations with sparse coverage

## Fallback Strategy

### Algorithm

1. **First Attempt**: Try filtering with requested date range
2. **Check Size**: If `ic.size().getInfo() == 0`, trigger fallback
3. **Get Available Range**: Query dataset's actual temporal coverage at this location
4. **Select Fallback**:
   - If requested date **after** dataset end → Use most recent year
   - If requested date **before** dataset start → Use oldest year
   - If requested range **overlaps** but no data → Use full available range
5. **Re-filter**: Apply fallback dates and proceed with data extraction
6. **Annotate**: Add metadata to all observations documenting the fallback

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
        # Get actual available range
        full_collection = ee.ImageCollection(self.asset_id).filterBounds(region)
        dates = full_collection.aggregate_array('system:time_start').getInfo()
        available_start = min(dates)  # Convert to YYYY-MM-DD
        available_end = max(dates)

        # Select fallback strategy
        if requested_start > available_end:
            # Requested date too late → use most recent year
            end_year = available_end[:4]
            start_date = f"{end_year}-01-01"
            end_date = f"{end_year}-12-31"
        elif requested_end < available_start:
            # Requested date too early → use oldest year
            start_year = available_start[:4]
            start_date = f"{start_year}-01-01"
            end_date = f"{start_year}-12-31"
        else:
            # Overlap but no data → use full range
            start_date = available_start
            end_date = available_end
```

## Metadata Annotation

All observations returned after fallback include these attributes:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `requested_date_range` | string | Original requested dates | `"2021-01-01_to_2021-12-31"` |
| `actual_date_range` | string | Dates actually used for query | `"2019-01-01_to_2019-12-31"` |
| `temporal_fallback_applied` | boolean | Whether fallback was triggered | `true` or `false` |
| `temporal_fallback_reason` | string | Explanation of why fallback occurred | `"requested_date_2021-01-01_after_dataset_end_2019-12-31"` |

### Example Observation with Fallback

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

## Test Results

**Test Script**: `notebooks/test_temporal_fallback.py`
**Date Tested**: 2025-09-30
**Status**: All tests passed ✅

### Test 1: MODIS_LANDCOVER (2021 → 2019 Fallback)
- **Requested**: 2021-01-01 to 2021-12-31
- **Actual**: 2019-01-01 to 2019-12-31
- **Fallback**: ✅ Applied
- **Reason**: `requested_date_2021-01-01_after_dataset_end_2019-12-31`
- **Result**: Retrieved 13 observations from 2019 with correct metadata

### Test 2: GOOGLE_EMBEDDINGS (Hong Kong 2021)
- **Requested**: 2021-01-01 to 2021-12-31
- **Actual**: 2021-01-01 to 2021-12-31
- **Fallback**: ❌ Not needed (data exists)
- **Result**: Retrieved 64 observations from 2021

### Test 3: MODIS_NDVI (Future Date 2025)
- **Requested**: 2025-01-01 to 2025-12-31
- **Actual**: 2025-01-01 to 2025-12-31
- **Fallback**: ❌ Not needed (dataset has 2025 data)
- **Result**: Retrieved 192 observations from 2025

## Impact on Production Pipeline

### Before Fallback Implementation
- **MODIS_LANDCOVER**: 100% failure rate (0/4789 clusters)
- **GOOGLE_EMBEDDINGS**: ~5 clusters failing (sparse coverage locations)
- **Error**: "Image.bandNames: Parameter 'image' is required and may not be null"

### After Fallback Implementation
- **MODIS_LANDCOVER**: Expected 0% failure rate (will use 2019 data with annotation)
- **GOOGLE_EMBEDDINGS**: Expected 0% failure rate (will fall back to available years)
- **Data Quality**: All observations include temporal metadata for downstream analysis

### Configuration Updates

**scripts/acquire_environmental_data.py** was updated to use most recent available year for MODIS_LANDCOVER:

```python
"MODIS_LANDCOVER": {
    "asset_id": "MODIS/006/MCD12Q1",
    "time_range": ("2019-01-01", "2019-12-31"),  # Use most recent available year
    # Dataset ends 2019, but adapter will automatically fall back if needed
}
```

## Usage Notes

1. **Transparent Behavior**: Fallback happens automatically, no configuration needed
2. **Metadata Traceability**: All observations include complete temporal metadata
3. **Graceful Degradation**: Returns closest available data rather than failing
4. **Downstream Analysis**: Filter observations by `temporal_fallback_applied` to identify which data used fallback
5. **Logging**: Fallback triggers INFO-level log messages describing the fallback strategy

## Future Considerations

1. **User Override**: Could add configuration to disable fallback and fail instead
2. **Fallback Strategies**: Could add options for different fallback strategies (e.g., nearest year vs. full range)
3. **Validation Rules**: Could add rules to warn if fallback exceeds certain thresholds (e.g., >5 years)
4. **Dataset Metadata**: Could cache known temporal ranges to avoid repeated queries

## Related Documentation

- **EARTH_ENGINE_OPTIMIZATION.md**: Earth Engine quota management and timeouts
- **PANGENOME_SERVICES.md**: Complete service configuration guide
- **diagnose_ee_failures.py**: Diagnostic script that identified this issue
