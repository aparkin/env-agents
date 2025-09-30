# Configured Services - Complete List

**Date:** 2025-09-29
**Total Clusters:** 4,789

## Phase 0: Fast Unitary Services (8 services)

Run with: `python acquire_environmental_data.py --phase 0`

| Service | Status | Est. Time | Data Type | Coverage |
|---------|--------|-----------|-----------|----------|
| **NASA_POWER** | ✅ Complete | - | Climate (temp, precip, radiation) | Global |
| **GBIF** | ✅ Complete | - | Species observations | Global |
| **OpenAQ** | 🔄 77% done | ~2 hours | Air quality (PM2.5, ozone, NO2) | Urban areas |
| **USGS_NWIS** | ⏳ Not started | ~5-6 hours | Stream gauge (discharge, temp) | US + some international |
| **WQP** | ⏳ Not started | ~5-6 hours | Water chemistry (pH, nutrients) | US + some international |
| **SSURGO** | ⏳ Not started | ~4-5 hours | Soil properties (texture, pH) | US only |
| **OSM_Overpass** | ⏳ Not started | ~6-8 hours | Land use (buildings, roads, water) | Global |

**Phase 0 Total:** ~18-25 hours remaining (if run serially)

---

## Phase 1: Earth Engine Services (7 services)

Run with: `python acquire_environmental_data.py --phase 1`

**Note:** These share Earth Engine quotas - must run sequentially

### Terrain & Elevation

| Service | Asset ID | Status | Est. Time | Data Type |
|---------|----------|--------|-----------|-----------|
| **SRTM** | USGS/SRTMGL1_003 | 🔄 83% done | ~28 min | Elevation (m) |

### Vegetation & Land Surface

| Service | Asset ID | Status | Est. Time | Data Type |
|---------|----------|--------|-----------|-----------|
| **MODIS_NDVI** | MODIS/061/MOD13Q1 | 🟡 Testing | ~4 hours | NDVI time series (vegetation) |
| **MODIS_LST** | MODIS/061/MOD11A1 | ⏳ Not started | ~4 hours | Land surface temp time series |

### Climate (Static)

| Service | Asset ID | Status | Est. Time | Data Type |
|---------|----------|--------|-----------|-----------|
| **WORLDCLIM_BIO** | WORLDCLIM/V1/BIO | ⏳ Not started | ~2.7 hours | 19 bioclimatic variables |

### Soil (Static)

| Service | Asset ID | Status | Est. Time | Data Type |
|---------|----------|--------|-----------|-----------|
| **SOILGRIDS_TEXTURE** | OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02 | ⏳ Not started | ~2.7 hours | Soil texture class |

**Phase 1 Total:** ~14 hours remaining (must run sequentially)

---

## Phase 2: Google Embeddings (1 service)

Run with: `python acquire_environmental_data.py --phase 2`

| Service | Asset ID | Status | Est. Time | Data Type |
|---------|----------|--------|-----------|-----------|
| **GOOGLE_EMBEDDINGS** | GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL | 🟡 Testing | ~6.6 hours | Satellite embedding vectors |

---

## Summary Statistics

### Already Complete (2 services)
- NASA_POWER: 4,789 clusters → **10,487,910 observations**
- GBIF: 4,789 clusters → **1,436,700 observations**
- **Total: 11,924,610 observations**

### In Progress (2 services)
- SRTM: 3,392 success, 835 remaining
- OpenAQ: 610 success, 1,115 remaining, 11 API errors
- **Current: ~1.3M additional observations**

### Not Yet Started (12 services)

**Phase 0 (5 services):**
1. USGS_NWIS (~500K obs)
2. WQP (~1M obs)
3. SSURGO (~200K obs, US only)
4. OSM_Overpass (~2M obs)

**Phase 1 (4 services):**
5. MODIS_NDVI (~15K obs)
6. MODIS_LST (~15K obs)
7. WORLDCLIM_BIO (~20K obs)
8. SOILGRIDS_TEXTURE (~4K obs)

**Phase 2 (1 service):**
9. GOOGLE_EMBEDDINGS (~4K obs)

**Estimated additional:** ~4-5M observations

---

## Run Commands

### Run all services (full pipeline)
```bash
# Complete Phase 0
python acquire_environmental_data.py --phase 0 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# Complete Phase 1 (Earth Engine)
python acquire_environmental_data.py --phase 1 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# Complete Phase 2 (Embeddings)
python acquire_environmental_data.py --phase 2 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Run specific service
```bash
python acquire_environmental_data.py --service WQP \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Check progress
```bash
python acquire_environmental_data.py --status
```

---

## Service Details

### Phase 0 Services (Can run in parallel)

#### NASA_POWER ✅
- **Data:** Temperature, precipitation, solar radiation, humidity
- **Temporal:** Daily aggregates
- **Coverage:** Global, 0.5° resolution
- **Rate:** 0.5s between queries

#### GBIF ✅
- **Data:** Species occurrences
- **Temporal:** Historical through present
- **Coverage:** Global
- **Rate:** 1.0s between queries

#### OpenAQ 🔄
- **Data:** PM2.5, PM10, ozone, NO2, SO2, CO
- **Temporal:** Hourly/daily measurements
- **Coverage:** Urban areas with sensors (sparse)
- **Rate:** 1.0s between queries
- **Note:** 11 clusters with API 500 errors (retry later)

#### USGS_NWIS ⏳
- **Data:** Stream discharge, water level, temperature
- **Temporal:** Daily measurements
- **Coverage:** US + some international
- **Rate:** 0.5s between queries

#### WQP ⏳
- **Data:** Water chemistry (pH, nutrients, metals, turbidity)
- **Temporal:** Discrete samples
- **Coverage:** US + some international
- **Rate:** 2.0s between queries

#### SSURGO ⏳
- **Data:** Soil texture, pH, organic matter, bulk density
- **Temporal:** Static (survey data)
- **Coverage:** US only (expect ~64% no_data for non-US)
- **Rate:** 3.0s between queries

#### OSM_Overpass ⏳
- **Data:** Buildings, roads, water bodies, land use features
- **Temporal:** Current snapshot
- **Coverage:** Global (OpenStreetMap)
- **Rate:** 3.0s between queries
- **Note:** Has rate limits, retry enabled

---

### Phase 1 Services (Must run sequentially)

#### SRTM 🔄
- **Data:** Elevation (meters above sea level)
- **Resolution:** 30m
- **Coverage:** -56°S to 60°N (96% of clusters)
- **Rate:** 2.0s between queries
- **Current:** 3,392 / 4,789 (83% complete)

#### MODIS_NDVI 🟡
- **Data:** Normalized Difference Vegetation Index
- **Temporal:** 16-day composites
- **Resolution:** 250m
- **Rate:** 3.0s between queries (queries take ~8s themselves)

#### MODIS_LST ⏳
- **Data:** Land surface temperature (day/night)
- **Temporal:** Daily
- **Resolution:** 1km
- **Rate:** 3.0s between queries

#### WORLDCLIM_BIO ⏳
- **Data:** 19 bioclimatic variables (BIO1-BIO19)
  - Annual mean temp, precip seasonality, etc.
- **Temporal:** Static (1970-2000 average)
- **Resolution:** 1km
- **Rate:** 2.0s between queries

#### SOILGRIDS_TEXTURE ⏳
- **Data:** Soil texture class (USDA system)
- **Temporal:** Static
- **Resolution:** 250m
- **Rate:** 2.0s between queries

---

### Phase 2 Services

#### GOOGLE_EMBEDDINGS 🟡
- **Data:** 64-dimensional satellite image embeddings
- **Temporal:** Annual composites
- **Resolution:** 10m (Sentinel-2)
- **Rate:** 5.0s between queries (queries take ~44s themselves)
- **Use:** Deep learning features for image similarity

---

## Expected Data Volume

### Current Database
- **Size:** ~31 MB
- **Observations:** ~13.2M
- **Services:** 4 complete, 2 in progress

### After All Services Complete
- **Size:** ~5-7 GB
- **Observations:** ~16-20M
- **Services:** 16 complete

### By Category
- **Climate:** ~10.5M (NASA_POWER, WORLDCLIM)
- **Species:** ~1.4M (GBIF)
- **Air Quality:** ~1.3M (OpenAQ)
- **Water:** ~1-2M (NWIS, WQP)
- **Soil:** ~200K-300K (SSURGO, SoilGrids)
- **Land Use:** ~2M (OSM)
- **Remote Sensing:** ~50K (SRTM, MODIS, Embeddings)

---

## Recommended Execution Order

### Option 1: Complete Each Phase (Recommended)

```bash
# Day 1: Finish Phase 0 (18-25 hours)
python acquire_environmental_data.py --phase 0 ...

# Day 2: Run Phase 1 (14 hours, sequential)
python acquire_environmental_data.py --phase 1 ...

# Day 3: Run Phase 2 (6.6 hours)
python acquire_environmental_data.py --phase 2 ...
```

**Total:** ~40 hours compute time, ~3 days wall-clock

### Option 2: Parallel Execution (Faster)

```bash
# Terminal 1: Phase 0 services (can run concurrently within phase)
python acquire_environmental_data.py --phase 0 ...

# Terminal 2: Phase 1 services (after Phase 0 settles)
python acquire_environmental_data.py --phase 1 ...

# Terminal 3: Phase 2 (can start anytime)
python acquire_environmental_data.py --phase 2 ...
```

**Total:** ~25-30 hours wall-clock

### Option 3: High Priority First

```bash
# 1. Complete critical Phase 1 services first (7 hours)
python acquire_environmental_data.py --service SRTM ...
python acquire_environmental_data.py --service MODIS_NDVI ...
python acquire_environmental_data.py --service WORLDCLIM_BIO ...

# 2. Then high-value Phase 0 (11 hours)
python acquire_environmental_data.py --service WQP ...
python acquire_environmental_data.py --service USGS_NWIS ...

# 3. Then everything else (22 hours)
python acquire_environmental_data.py --phase 0 ...  # Remaining
python acquire_environmental_data.py --phase 1 ...  # Remaining
python acquire_environmental_data.py --phase 2 ...
```

---

## Notes

- **Earth Engine quotas:** Phase 1 services share quotas - run sequentially
- **API rate limits:** Phase 0 services have independent rate limits - can run in parallel
- **Resume capability:** All services support interruption and resume
- **OpenAQ errors:** 11 clusters with 500 errors - retry when API is stable
- **SSURGO coverage:** US-only, expect ~64% "no_data" for international clusters
- **Database size:** Monitor with `du -h pangenome_env_data/pangenome_env.db`