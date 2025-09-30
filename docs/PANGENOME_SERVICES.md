# Pangenome Environmental Data Services

**Complete guide to all configured services for pangenome environmental data acquisition**

---

## Quick Reference

**Total Services:** 16 configured
**Total Clusters:** 4,789
**Expected Total Observations:** 16-20M

| Phase | Services | Status | Time | Coverage |
|-------|----------|--------|------|----------|
| **Phase 0** | 7 unitary services | 2 complete | ~18-25 hours | Global + US-only |
| **Phase 1** | 12 Earth Engine assets | Testing | ~30-35 hours | Global (sequential) |
| **Phase 2** | 1 embedding service | Testing | ~6.6 hours | Global |

---

## Phase 0: Unitary Services (7 services)

Can run in parallel (independent rate limits).

### ✅ NASA_POWER - Climate Data
- **Status:** Complete
- **Coverage:** Global (0.5° resolution)
- **Data:** Temperature, precipitation, radiation, humidity
- **Temporal:** Daily aggregates
- **Observations:** 10,487,910 (COMPLETE)

### ✅ GBIF - Species Observations
- **Status:** Complete
- **Coverage:** Global
- **Data:** Species occurrences
- **Temporal:** Historical through present
- **Observations:** 1,436,700 (COMPLETE)

### 🔄 OpenAQ - Air Quality
- **Status:** 77% complete
- **Coverage:** Urban areas with sensors (sparse)
- **Data:** PM2.5, PM10, ozone, NO2, SO2, CO
- **Temporal:** Hourly/daily measurements
- **Expected:** ~1.3M observations
- **Note:** 11 clusters with API 500 errors (retry later)

### ⏳ USGS_NWIS - Stream Gauges
- **Status:** Not started
- **Coverage:** US only (~13% of clusters, ~3-5% with data)
- **Data:** Discharge, gage height, water temp, water quality, sediment, turbidity
- **Temporal:** Daily values
- **Expected:** ~126,000 observations from ~126 clusters
- **Parameters:** 16 comprehensive codes (see docs/USGS_NWIS_ADAPTER.md)
- **Time:** ~5-6 hours

### ⏳ WQP - Water Quality Portal
- **Status:** Not started
- **Coverage:** US + some international
- **Data:** Water chemistry (pH, nutrients, metals, turbidity)
- **Temporal:** Discrete samples
- **Expected:** ~1M observations
- **Time:** ~5-6 hours

### ⏳ SSURGO - US Soil Survey
- **Status:** Not started
- **Coverage:** US only (~64% will be no_data)
- **Data:** Soil texture, pH, organic matter, bulk density
- **Temporal:** Static (survey data)
- **Expected:** ~200K observations
- **Time:** ~4-5 hours

### ⏳ OSM_Overpass - OpenStreetMap Features
- **Status:** Not started
- **Coverage:** Global
- **Data:** Buildings, roads, water bodies, land use features
- **Temporal:** Current snapshot
- **Expected:** ~2M observations
- **Time:** ~6-8 hours

---

## Phase 1: Earth Engine Services (12 services)

**MUST run sequentially** due to shared Earth Engine quotas.

**⚙️ Temporal Fallback Enabled**: All Earth Engine services automatically handle out-of-range dates by falling back to closest available data with metadata annotation. See `docs/TEMPORAL_FALLBACK.md` for details.

### Terrain & Elevation

#### 🔄 SRTM - Shuttle Radar Topography Mission
- **Status:** 83% complete (3,392/4,789)
- **Asset:** `USGS/SRTMGL1_003`
- **Data:** Elevation (meters above sea level)
- **Resolution:** 30m
- **Coverage:** -56°S to 60°N (96% of clusters)
- **Time remaining:** ~28 minutes

### Vegetation Indices

#### 🟡 MODIS_NDVI - Vegetation Index
- **Status:** Testing
- **Asset:** `MODIS/061/MOD13Q1`
- **Data:** NDVI time series (vegetation greenness)
- **Temporal:** 16-day composites (23 per year)
- **Resolution:** 250m
- **Variables:** NDVI, EVI, SummaryQA
- **Expected:** ~15K observations
- **Time:** ~4 hours

#### ⏳ MODIS_EVI - Enhanced Vegetation Index
- **Asset:** `MODIS/061/MOD13Q1` (same as NDVI, different band)
- **Data:** EVI time series (better in high biomass areas)
- **Why separate:** EVI performs better in tropics/forests
- **Time:** ~4 hours

#### ⏳ MODIS_LANDCOVER - Land Cover Classification
- **Status:** Ready to run (temporal fallback implemented)
- **Asset:** `MODIS/006/MCD12Q1`
- **Data:** Land cover types (17 IGBP classes)
- **Temporal:** Annual (dataset ends 2019)
- **Resolution:** 500m
- **Classes:** Forest, grassland, cropland, urban, water, etc.
- **Time:** ~2.7 hours
- **Note:** Configured to use 2019 data (most recent available). Temporal fallback will handle any edge cases.

### Temperature

#### ⏳ MODIS_LST - Land Surface Temperature
- **Asset:** `MODIS/061/MOD11A1`
- **Data:** Day/night land surface temperature
- **Temporal:** Daily
- **Resolution:** 1km
- **Variables:** LST_Day_1km, LST_Night_1km, QC_Day, QC_Night
- **Time:** ~4 hours

### Climate Variables

#### ⏳ WORLDCLIM_BIO - Bioclimatic Variables
- **Asset:** `WORLDCLIM/V1/BIO`
- **Data:** 19 bioclimatic variables (static, 1970-2000 average)
- **Resolution:** 1km
- **Variables:** BIO1-BIO19 (annual mean temp, precip seasonality, etc.)
- **Expected:** ~20K observations
- **Time:** ~2.7 hours

#### ⏳ TERRACLIMATE - Climate Water Balance
- **Asset:** `IDAHO_EPSCOR/TERRACLIMATE`
- **Data:** Monthly climate and water balance
- **Temporal:** Monthly (12 per year)
- **Resolution:** 4km
- **Variables:** aet, def, pdsi, pet, pr, ro, soil, swe, tmmn, tmmx, vpd
- **Time:** ~4 hours

#### ⏳ GPM_PRECIP - High-Resolution Precipitation
- **Asset:** `NASA/GPM_L3/IMERG_V06`
- **Data:** Half-hourly global precipitation
- **Temporal:** 30-minute intervals (aggregate to daily/monthly)
- **Resolution:** 0.1° (~10km)
- **Variables:** precipitationCal, randomError, precipitationQualityIndex
- **Time:** ~4 hours

### Soil Properties

#### ⏳ SOILGRIDS_TEXTURE - Soil Texture Class
- **Asset:** `OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02`
- **Data:** USDA soil texture classification (0-5cm depth)
- **Resolution:** 250m
- **Classes:** 12 USDA texture classes
- **Time:** ~2.7 hours

#### ⏳ SOILGRIDS_PH - Soil pH
- **Asset:** `OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02`
- **Data:** Soil pH in H2O (0-5cm depth)
- **Resolution:** 250m
- **Range:** pH 4-9
- **Time:** ~2.7 hours

#### ⏳ SOILGRIDS_OC - Organic Carbon
- **Asset:** `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- **Data:** Soil organic carbon (g/kg, 0-5cm depth)
- **Resolution:** 250m
- **Time:** ~2.7 hours

---

## Phase 2: Embeddings (1 service)

#### 🟡 GOOGLE_EMBEDDINGS - Satellite Image Features
- **Status:** Ready to run (temporal fallback implemented)
- **Asset:** `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`
- **Data:** 64-dimensional feature vectors from deep learning
- **Source:** Sentinel-2 imagery
- **Temporal:** Annual composites (2017-present)
- **Resolution:** 10m
- **Use:** Image similarity, unsupervised clustering, transfer learning
- **Expected:** ~4K observations
- **Time:** ~6.6 hours
- **Note:** Some locations may have sparse coverage. Temporal fallback will use closest available year if 2021 data missing.

---

## Execution Strategy

### Option 1: Complete Each Phase Sequentially
```bash
# Day 1: Phase 0 (18-25 hours)
python scripts/acquire_environmental_data.py --phase 0 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# Day 2: Phase 1 (30-35 hours, must be sequential)
python scripts/acquire_environmental_data.py --phase 1 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# Day 3: Phase 2 (6.6 hours)
python scripts/acquire_environmental_data.py --phase 2 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### Option 2: Run Individual Services
```bash
# Run specific high-priority services
python scripts/acquire_environmental_data.py --service USGS_NWIS \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

python scripts/acquire_environmental_data.py --service WORLDCLIM_BIO \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

See `docs/EXTENDING_SERVICES.md` for full list of available services.

---

## Priority Recommendations

### Tier 1: Critical Environmental Context (Run First)
1. **SRTM** - Elevation (finish remaining 835 clusters, ~28 min)
2. **WORLDCLIM_BIO** - Climate niche (19 variables, ~2.7 hours)
3. **SOILGRIDS_PH** - Soil pH (major microbial driver, ~2.7 hours)
4. **SOILGRIDS_OC** - Organic carbon (substrate availability, ~2.7 hours)

**Subtotal:** ~8 hours

### Tier 2: Hydrology & Water (Next)
5. **USGS_NWIS** - Stream gauge data (~5-6 hours)
6. **WQP** - Water quality chemistry (~5-6 hours)

**Subtotal:** ~11 hours

### Tier 3: Vegetation & Land Use (Then)
7. **MODIS_NDVI** - Vegetation productivity (~4 hours)
8. **MODIS_LANDCOVER** - Habitat classification (~2.7 hours)

**Subtotal:** ~7 hours

### Tier 4: Temporal Dynamics & Advanced (Later)
9. **MODIS_LST** - Temperature time series (~4 hours)
10. **TERRACLIMATE** - Water balance (~4 hours)
11. **GPM_PRECIP** - Precipitation patterns (~4 hours)
12. **GOOGLE_EMBEDDINGS** - Deep learning features (~6.6 hours)

**Subtotal:** ~19 hours

---

## Monitoring Progress

### Check Overall Status
```bash
python scripts/acquire_environmental_data.py --status
```

### Check Database Directly
```bash
cd notebooks
sqlite3 pangenome_env_data/pangenome_env.db "
SELECT
    service_name,
    status,
    COUNT(*) as clusters,
    SUM(obs_count) as observations
FROM cluster_processing
GROUP BY service_name, status
ORDER BY service_name, status
"
```

### Clear and Retry Failed Clusters
```bash
# Clear all data for a service
python scripts/acquire_environmental_data.py --clear SERVICE_NAME

# Clear only specific status (e.g., failed)
python scripts/acquire_environmental_data.py --clear SERVICE_NAME --clear-status failed
```

---

## Expected Final Dataset

### Size
- **Database size:** ~5-7 GB
- **Total observations:** 16-20M
- **Services complete:** 16

### By Category
- **Climate:** ~10.5M (NASA_POWER, WORLDCLIM, TERRACLIMATE)
- **Species:** ~1.4M (GBIF)
- **Air Quality:** ~1.3M (OpenAQ)
- **Water:** ~1-2M (NWIS, WQP)
- **Soil:** ~200K-300K (SSURGO, SoilGrids)
- **Land Use:** ~2M (OSM)
- **Remote Sensing:** ~50K (SRTM, MODIS, Embeddings)

---

## Documentation Links

- **Adapter Details:** `docs/USGS_NWIS_ADAPTER.md` (example for one service)
- **Earth Engine Assets:** `docs/EARTH_ENGINE_ASSETS.md` (archived, see PANGENOME_SERVICES.md)
- **Database Schema:** `docs/DATABASE_MANAGEMENT.md`
- **Extending Services:** `docs/EXTENDING_SERVICES.md`
- **Script Usage:** `scripts/README.md`