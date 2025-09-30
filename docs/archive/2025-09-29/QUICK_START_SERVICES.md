# Quick Start - Adding New Services

## Currently Running

✅ **Complete:**
- NASA_POWER (4,789 clusters, 10.5M obs)
- GBIF (4,789 clusters, 1.4M obs)

🔄 **In Progress:**
- SRTM (83% complete, 835 remaining)
- OpenAQ (77% complete, 1,115 remaining + 11 errors)

🟡 **Testing:**
- MODIS_NDVI (18 / 4,789)
- GOOGLE_EMBEDDINGS (20 / 4,789)

## Ready to Add - Copy/Paste Configs

### 1. Water Quality Portal (WQP) - High Priority

Add to `PHASE0_SERVICES` in `scripts/acquire_environmental_data.py`:

```python
"WQP": {
    "rate_limit": 2.0,
    "timeout": 60,
    "time_range": ("2020-01-01", "2023-12-31"),
    "retry_on_quota": False,
    "max_retries": 2,
    "backoff_seconds": 10
}
```

Run:
```bash
python acquire_environmental_data.py --phase 0 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

**Estimated:** 5-6 hours, ~500K-1M observations

---

### 2. USGS Stream Gauge (NWIS) - High Priority

Add to `PHASE0_SERVICES`:

```python
"USGS_NWIS": {
    "rate_limit": 2.0,
    "timeout": 60,
    "time_range": ("2020-01-01", "2023-12-31"),
    "retry_on_quota": False,
    "max_retries": 2,
    "backoff_seconds": 10
}
```

**Estimated:** 5-6 hours, ~200K-500K observations

---

### 3. SSURGO Soil Data - Medium Priority

Add to `PHASE0_SERVICES`:

```python
"SSURGO": {
    "rate_limit": 3.0,  # Slower queries (spatial lookups)
    "timeout": 90,
    "time_range": None,  # Static data
    "retry_on_quota": False,
    "max_retries": 2,
    "backoff_seconds": 10
}
```

**Note:** US-only coverage, expect many "no_data" for non-US clusters

**Estimated:** 4-5 hours, ~100K-200K observations

---

### 4. OSM Overpass (Land Use) - Medium Priority

Add to `PHASE0_SERVICES`:

```python
"OSM_Overpass": {
    "rate_limit": 5.0,  # Slower, complex queries
    "timeout": 120,
    "time_range": None,  # Static data
    "retry_on_quota": True,  # Overpass has rate limits
    "max_retries": 3,
    "backoff_seconds": 30
}
```

**Note:** May be slow for large bboxes, queries OpenStreetMap

**Estimated:** 6-8 hours, ~1M-2M observations

---

### 5. EPA AQS (US Air Quality) - Lower Priority

Add to `PHASE0_SERVICES`:

```python
"EPA_AQS": {
    "rate_limit": 2.0,
    "timeout": 60,
    "time_range": ("2020-01-01", "2023-12-31"),
    "retry_on_quota": False,
    "max_retries": 2,
    "backoff_seconds": 10
}
```

**Note:** US-only, redundant with OpenAQ for most locations

**Estimated:** 3-4 hours, ~200K-300K observations

---

## Additional Earth Engine Assets

The Earth Engine adapter can query any asset. Add to `PHASE1_SERVICES` or `PHASE2_SERVICES`:

### Climate Data

```python
"WORLDCLIM_TEMP": {
    "asset_id": "WORLDCLIM/V1/BIO",  # Bioclimatic variables
    "rate_limit": 2.0,
    "timeout": 60,
    "time_range": None,  # Static data
    "is_earth_engine": True,
    "retry_on_quota": True,
    "max_retries": 3,
    "backoff_seconds": 60
}
```

### Soil Properties

```python
"SOILGRIDS": {
    "asset_id": "OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02",
    "rate_limit": 2.0,
    "timeout": 60,
    "time_range": None,
    "is_earth_engine": True,
    "retry_on_quota": True,
    "max_retries": 3,
    "backoff_seconds": 60
}
```

### Land Cover

```python
"MODIS_LANDCOVER": {
    "asset_id": "MODIS/006/MCD12Q1",
    "rate_limit": 3.0,
    "timeout": 90,
    "time_range": ("2021-01-01", "2021-12-31"),
    "is_earth_engine": True,
    "retry_on_quota": True,
    "max_retries": 3,
    "backoff_seconds": 60
}
```

---

## Complete Configuration Template

```python
# In scripts/acquire_environmental_data.py

PHASE0_SERVICES = {
    "NASA_POWER": { ... },  # Already configured
    "GBIF": { ... },        # Already configured
    "OpenAQ": { ... },      # Already configured

    # ADD NEW SERVICES HERE:
    "WQP": {
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": ("2020-01-01", "2023-12-31"),
        "retry_on_quota": False,
        "max_retries": 2,
        "backoff_seconds": 10
    },
    "USGS_NWIS": {
        "rate_limit": 2.0,
        "timeout": 60,
        "time_range": ("2020-01-01", "2023-12-31"),
        "retry_on_quota": False,
        "max_retries": 2,
        "backoff_seconds": 10
    }
}
```

---

## Adapter Mapping

The acquisition script automatically maps service names to adapters:

```python
# In get_or_create_adapter():
service_map = {
    "NASA_POWER": "NASA_POWER",
    "GBIF": "GBIF",
    "OpenAQ": "OpenAQ",
    "USGS_NWIS": "USGS_NWIS",
    "OSM_Overpass": "OSM_Overpass",
    "WQP": "WQP",
    "SSURGO": "SSURGO",
    "EPA_AQS": "EPA_AQS"
}
```

Service name in config must match key in `service_map`.

---

## Run Commands

### Run specific service:
```bash
python acquire_environmental_data.py --service WQP \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Run all Phase 0 services:
```bash
python acquire_environmental_data.py --phase 0 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Check status:
```bash
python acquire_environmental_data.py --status
```

### Clear service data:
```bash
# Clear all data for service
python acquire_environmental_data.py --clear WQP

# Clear only failed clusters
python acquire_environmental_data.py --clear WQP --clear-status failed

# Clear only no_data clusters (if adapter was fixed)
python acquire_environmental_data.py --clear WQP --clear-status no_data
```

---

## OpenAQ 500 Errors

**Issue:** 11 clusters returning `500 Internal Server Error` from OpenAQ API

**Examples:**
- Location 921132, 10542, 3616712, etc.

**Diagnosis:** OpenAQ server issues, not our code

**Fix:** Retry later when their API is stable:
```bash
python acquire_environmental_data.py --clear OpenAQ --clear-status failed
python acquire_environmental_data.py --service OpenAQ \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

**Note:** 3,053 "no_data" clusters are expected - most locations don't have air quality sensors

---

## Priority Recommendations

### Today/Tomorrow (Complete Phase 1):
1. ✅ SRTM (28 min remaining)
2. ✅ MODIS_NDVI (4 hours)
3. ✅ GOOGLE_EMBEDDINGS (6.6 hours)

### This Week (Add High-Priority Services):
4. 🔧 WQP - Water chemistry (5-6 hours)
5. 🔧 USGS_NWIS - Stream data (5-6 hours)

### Next Week (Add Medium-Priority):
6. 🔧 SSURGO - Soil properties (4-5 hours)
7. 🔧 OSM_Overpass - Land use (6-8 hours)

### Future (Additional EE Assets):
8. 🔧 WorldClim - Climate variables
9. 🔧 MODIS Land Cover
10. 🔧 Additional soil/terrain layers

---

## Expected Timeline

**If running serially:**
- Phase 1 complete: ~11 hours
- High-priority services: ~11 hours
- Medium-priority services: ~11 hours
- **Total:** ~33 hours compute time

**If running in parallel** (multiple terminals):
- Can run Phase 0 services concurrently (different APIs)
- Earth Engine services must run sequentially (shared quotas)
- **Total:** ~15-20 hours wall-clock time

---

## Database Growth

- Current: ~31 MB
- After Phase 1/2: ~2-3 GB
- After all services: ~5-7 GB
- Final (with all EE assets): ~10-15 GB

Monitor with:
```bash
du -h notebooks/pangenome_env_data/pangenome_env.db
```