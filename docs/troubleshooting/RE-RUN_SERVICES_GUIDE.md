# Service Re-Run Guide

**Date**: 2025-10-03
**Status**: Database fixed, ready to re-run services

---

## ✅ Steps 1-3 COMPLETE

### Step 1: Backup Created ✓
- **Backup file**: `notebooks/pangenome_env_data/pangenome_env.db.backup_20251003`
- **Size**: 343 MB
- **Original data preserved**: All current observations safe

### Step 2: Schema Fixed ✓
**Before**:
```sql
PRIMARY KEY (obs_id, service_name)
```

**After**:
```sql
PRIMARY KEY (cluster_id, service_name, variable, time_stamp, obs_id)
```

**Result**: New observations will NOT replace old ones. Each cluster's data is now independent.

### Step 3: --clear Bug Fixed ✓
**Before** (line 411):
```python
DELETE FROM environmental_observations  # ❌ Wrong table!
WHERE dataset = ?
```

**After**:
```python
DELETE FROM env_observations  # ✅ Correct table!
WHERE service_name = ?
```

**Result**: The `--clear` command now properly deletes both processing status AND observations.

---

## Why Use --clear?

The `--clear` flag does two things:

1. **Deletes cluster_processing records** for the service
   - Without this, the script sees "success" status and skips those clusters
   - You MUST clear to force re-processing

2. **Deletes existing observations** for the service (NOW WORKING!)
   - Removes the corrupted/incomplete data
   - Ensures clean slate for new acquisition

**Without --clear**: Script will skip all clusters showing "success", and you won't get any new data.

**With --clear**: Script processes all clusters fresh, replacing bad data with complete data.

---

## Services to Re-Run (Priority Order)

### 🔴 Priority 1: High-Value Climate & Vegetation Services

These provide core environmental variables needed for most analyses.

#### NASA_POWER (Critical - 99.9% loss)
```bash
python scripts/acquire_environmental_data.py --service NASA_POWER --clear
```
- **What**: Temperature, precipitation, solar radiation, humidity, wind
- **Missing**: 10,482,435 observations (only 5,475 of 10.5M present)
- **Clusters**: 4,789
- **Estimated time**: ~4 hours
- **Why first**: Core climate variables, relatively fast

#### MODIS_NDVI (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service MODIS_NDVI --clear
```
- **What**: Normalized Difference Vegetation Index (photosynthetic activity)
- **Missing**: 985,221 observations (only 276 of 985K)
- **Clusters**: 3,674
- **Estimated time**: ~6 hours
- **Why important**: Primary vegetation productivity indicator

#### MODIS_EVI (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service MODIS_EVI --clear
```
- **What**: Enhanced Vegetation Index (improved sensitivity in dense vegetation)
- **Missing**: 985,221 observations (only 276 of 985K)
- **Clusters**: 3,674
- **Estimated time**: ~6 hours
- **Why important**: Complements NDVI, better for high-biomass areas

#### TERRACLIMATE (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service TERRACLIMATE --clear
```
- **What**: Climate water balance (AET, deficit, PDSI, PET, runoff, soil moisture, snow)
- **Missing**: 638,036 observations (only 168 of 638K)
- **Clusters**: 3,799
- **Estimated time**: ~4 hours
- **Why important**: Water availability metrics critical for microbial ecology

---

### 🟡 Priority 2: Soil Properties

Essential for understanding soil microbial habitat.

#### SOILGRIDS_PH (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service SOILGRIDS_PH --clear
```
- **What**: Soil pH at multiple depths
- **Missing**: 21,336 observations (only 6 of 21K)
- **Clusters**: 3,557
- **Estimated time**: ~2 hours
- **Why important**: pH is THE most important factor for microbial community composition

#### SOILGRIDS_OC (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service SOILGRIDS_OC --clear
```
- **What**: Soil organic carbon content
- **Missing**: 21,336 observations
- **Clusters**: 3,557
- **Estimated time**: ~2 hours
- **Why important**: Carbon availability drives microbial metabolism

#### SOILGRIDS_TEXTURE (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service SOILGRIDS_TEXTURE --clear
```
- **What**: Clay, sand, silt percentages
- **Missing**: 21,336 observations
- **Clusters**: 3,557
- **Estimated time**: ~2 hours
- **Why important**: Texture controls water retention, aeration, nutrient availability

---

### 🟢 Priority 3: Topography & Bioclimate

#### SRTM (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service SRTM --clear
```
- **What**: Elevation above sea level
- **Missing**: 4,050 observations (only 1 of 4K)
- **Clusters**: 4,051
- **Estimated time**: ~30 minutes (very fast, single value per cluster)
- **Why important**: Elevation affects temperature, precipitation, UV exposure

#### WORLDCLIM_BIO (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service WORLDCLIM_BIO --clear
```
- **What**: 19 bioclimatic variables (e.g., temperature seasonality, precipitation of driest quarter)
- **Missing**: 68,305 observations (only 19 of 68K)
- **Clusters**: 3,596
- **Estimated time**: ~2 hours
- **Why important**: Summarizes climate extremes and seasonality

#### MODIS_LANDCOVER (Critical - 100% loss)
```bash
python scripts/acquire_environmental_data.py --service MODIS_LANDCOVER --clear
```
- **What**: Land cover classification (forest, grassland, urban, etc.)
- **Missing**: 57,024 observations (only 26 of 57K)
- **Clusters**: 4,512
- **Estimated time**: ~3 hours
- **Why important**: Habitat context

---

### 🟣 Priority 4: High-Dimensional Features (Optional for initial analysis)

#### GOOGLE_EMBEDDINGS (Critical - 99.9% loss)
```bash
python scripts/acquire_environmental_data.py --service GOOGLE_EMBEDDINGS --clear
```
- **What**: 64-dimensional satellite image embeddings from ML model
- **Missing**: 267,328 observations (only 320 of 268K)
- **Clusters**: 4,050
- **Estimated time**: ~24 hours (VERY SLOW - Earth Engine API)
- **Why important**: Captures visual patterns not in other variables
- **Note**: Consider running last or in parallel, can proceed with analysis without it

---

### ⚪ Priority 5: Supplementary Data (Lower Priority)

#### GBIF (Critical - 100% loss, but less essential)
```bash
python scripts/acquire_environmental_data.py --service GBIF --clear
```
- **What**: Occurrence records of nearby plants, animals, fungi
- **Missing**: 1,436,400 observations
- **Clusters**: 4,789
- **Estimated time**: ~8 hours
- **Why lower priority**: Interesting but not directly environmental; presence-only data has biases

#### USGS_NWIS (Warning - 34% loss)
```bash
python scripts/acquire_environmental_data.py --service USGS_NWIS --clear
```
- **What**: Water quality data (temperature, pH, conductivity, discharge)
- **Missing**: 49,314 observations (66% already recovered)
- **Clusters**: 20 (very sparse coverage)
- **Estimated time**: ~1 hour
- **Why lower priority**: Only covers ~0.4% of clusters near water quality stations

---

### 🛑 Skip / Last Priority

#### GPM_PRECIP (Critical loss, but EXTREMELY SLOW)
```bash
# Only run if you have days to spare:
python scripts/acquire_environmental_data.py --service GPM_PRECIP --clear
```
- **What**: Half-hourly precipitation from Global Precipitation Measurement mission
- **Missing**: 125,640 observations
- **Clusters**: 2,095
- **Estimated time**: ~48 hours (!!!)
- **Why skip**: Redundant with NASA_POWER precipitation, much slower
- **Recommendation**: Skip for now, you already have precipitation data from NASA_POWER

---

## Recommended Execution Order

### Phase 1: Essential Climate & Soil (Start Here - ~1 day)
Run these first to enable core analyses:
```bash
python scripts/acquire_environmental_data.py --service NASA_POWER --clear
python scripts/acquire_environmental_data.py --service SOILGRIDS_PH --clear
python scripts/acquire_environmental_data.py --service SOILGRIDS_OC --clear
python scripts/acquire_environmental_data.py --service SOILGRIDS_TEXTURE --clear
python scripts/acquire_environmental_data.py --service SRTM --clear
python scripts/acquire_environmental_data.py --service TERRACLIMATE --clear
```
**Total time**: ~16 hours
**After this**: You can start preliminary analyses!

### Phase 2: Vegetation & Landcover (~12 hours)
```bash
python scripts/acquire_environmental_data.py --service MODIS_NDVI --clear
python scripts/acquire_environmental_data.py --service MODIS_EVI --clear
python scripts/acquire_environmental_data.py --service MODIS_LANDCOVER --clear
python scripts/acquire_environmental_data.py --service WORLDCLIM_BIO --clear
```

### Phase 3: High-Dimensional Features (~24 hours)
```bash
python scripts/acquire_environmental_data.py --service GOOGLE_EMBEDDINGS --clear
```
**Note**: Can run in parallel with other services if you have capacity

### Phase 4: Supplementary (Optional, ~8 hours)
```bash
python scripts/acquire_environmental_data.py --service GBIF --clear
python scripts/acquire_environmental_data.py --service USGS_NWIS --clear
```

---

## Monitoring Progress

After each service completes, run the diagnostic:
```bash
python scripts/diagnose_database_integrity.py
```

This will show:
- Services still needing re-run
- Current recovery rates
- Observation counts

---

## What to Expect

### During Runs:
- Progress messages every ~50 clusters
- Logs written to `notebooks/pangenome_env_data/logs/`
- Some "no_data" results are normal (not all services cover all locations)
- Transient errors with retries are expected for Earth Engine services

### Success Criteria:
After re-running a service, diagnostic should show:
- Recovery rate > 95%
- Clusters with data ≈ clusters marked "success" in cluster_processing

### If Issues:
- Check latest log file in `notebooks/pangenome_env_data/logs/`
- Look for quota errors, network errors, or authentication issues
- Can re-run same command (safe now with fixed schema)

---

## Parallel Execution (Optional)

If you have multiple terminals/screens:
```bash
# Terminal 1: Fast services
python scripts/acquire_environmental_data.py --service SRTM --clear
python scripts/acquire_environmental_data.py --service NASA_POWER --clear

# Terminal 2: MODIS services
python scripts/acquire_environmental_data.py --service MODIS_NDVI --clear
python scripts/acquire_environmental_data.py --service MODIS_EVI --clear

# Terminal 3: SoilGrids batch
python scripts/acquire_environmental_data.py --service SOILGRIDS_PH --clear
python scripts/acquire_environmental_data.py --service SOILGRIDS_OC --clear
```

**Warning**: Watch for rate limits with Earth Engine services (MODIS, GOOGLE_EMBEDDINGS, etc.)

---

## After All Services Complete

1. **Run final diagnostic**:
   ```bash
   python scripts/diagnose_database_integrity.py > data_recovery_report.txt
   ```

2. **Verify database size** (should be ~2-3 GB):
   ```bash
   ls -lh notebooks/pangenome_env_data/pangenome_env.db
   ```

3. **Start analysis** using the new notebooks in `analysis/notebooks/`

4. **Optional**: Remove backup once confirmed:
   ```bash
   # Only after verifying everything works!
   rm notebooks/pangenome_env_data/pangenome_env.db.backup_20251003
   ```
