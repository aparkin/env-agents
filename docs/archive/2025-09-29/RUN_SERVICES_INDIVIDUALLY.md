# Running Services Individually

## Quick Reference

You can **already** run services one-by-one using `--service`:

```bash
python acquire_environmental_data.py --service SERVICE_NAME \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

## All Available Services

### Phase 0 Services (Fast, Independent)

```bash
# NASA POWER - Climate data (COMPLETE)
python acquire_environmental_data.py --service NASA_POWER \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# GBIF - Species observations (COMPLETE)
python acquire_environmental_data.py --service GBIF \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# OpenAQ - Air quality (77% done, resume to continue)
python acquire_environmental_data.py --service OpenAQ \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# USGS NWIS - Stream gauge data (FIXED: now gets daily values)
python acquire_environmental_data.py --service USGS_NWIS \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# WQP - Water quality chemistry
python acquire_environmental_data.py --service WQP \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# SSURGO - Soil properties (US only)
python acquire_environmental_data.py --service SSURGO \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# OSM Overpass - Land use features
python acquire_environmental_data.py --service OSM_Overpass \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

---

### Phase 1 Services (Earth Engine - Run Sequentially)

```bash
# SRTM - Elevation (83% done)
python acquire_environmental_data.py --service SRTM \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# MODIS NDVI - Vegetation index time series
python acquire_environmental_data.py --service MODIS_NDVI \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# MODIS LST - Land surface temperature time series
python acquire_environmental_data.py --service MODIS_LST \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# WorldClim - 19 bioclimatic variables
python acquire_environmental_data.py --service WORLDCLIM_BIO \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv

# SoilGrids - Soil texture classification
python acquire_environmental_data.py --service SOILGRIDS_TEXTURE \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

---

### Phase 2 Service (Google Embeddings)

```bash
# Google Embeddings - Satellite image features
python acquire_environmental_data.py --service GOOGLE_EMBEDDINGS \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

---

## USGS_NWIS Fixes Applied

**Problem 1:** Only getting 2 observations per cluster (1 per parameter)

**Root Cause:**
- Adapter was using `/nwis/iv` (instantaneous values = real-time only)
- Not parsing `time_range` from RequestSpec

**Fix 1:**
- Changed to `/nwis/dv` (daily values = historical time series)
- Now correctly reads `spec.time_range` and `spec.geometry`
- Changed `siteStatus` from "active" to "all" for historical data

---

**Problem 2:** 400 errors for non-US locations (e.g., Hong Kong, Europe)

**Root Cause:**
- USGS NWIS only covers US locations
- API returns 400 for locations outside US
- Was treating as error instead of "no_data"

**Fix 2:**
- Handle 400 status gracefully (return empty list, not error)
- Also return empty if no time series data
- Log as DEBUG not ERROR

---

**Problem 3:** Getting 0 observations even from US locations

**Root Cause:**
- Default parameters were `00010, 00095, 00400` (temp, conductivity, pH)
- These are **rarely available** at stream gauges
- Most gauges primarily measure discharge (00060)

**Fix 3:**
- Changed to **comprehensive list of 16 parameter codes** covering:
  - Physical: discharge (00060), gage height (00065), precipitation (00045)
  - Temperature: water temp (00010), air temp (00020)
  - Water quality: conductance (00095), pH (00400), dissolved O2 (00300)
  - Sediment: concentration (80154), discharge (80155)
  - Turbidity: (63680, 00076)
  - Nutrients: phosphorus (00665, 00666), nitrate (00618), NO2+NO3 (00631)

**Verified Results (Northern California test, 31 days):**
- Old parameters (3): 5,896 observations from 3 parameters
- New parameters (16): **8,088 observations** from 10 parameters with data
- **+37% more observations, +67% more time series, 7 more variables!**

**Top parameters retrieved:**
1. Discharge (00060): 3,126 obs
2. Water temp (00010): 2,611 obs
3. Conductance (00095): 642 obs ⭐ NEW!
4. Sediment discharge (80155): 496 obs ⭐ NEW!
5. Sediment conc (80154): 372 obs ⭐ NEW!
6. pH (00400): 279 obs ⭐ NEW!
7. Dissolved O2 (00300): 186 obs ⭐ NEW!
8. Turbidity (63680): 186 obs ⭐ NEW!

**Expected Result:**
- US clusters with gauges: ~100-3000 observations (365 days × 1-10 parameters)
- US clusters without gauges: "no_data" (stream gauges are sparse)
- Non-US clusters: "no_data" (gracefully handled)
- Expected total: **~800K-2M observations** (vs. ~10K with old approach!)
- Expected coverage: ~30-40% of US clusters, ~0% of non-US clusters

**To test the fix:**
```bash
# Clear the bad NWIS data
python acquire_environmental_data.py --clear USGS_NWIS

# Run with fixed adapter
python acquire_environmental_data.py --service USGS_NWIS \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

---

## Status Checking

```bash
# Check overall status
python acquire_environmental_data.py --status

# Check specific service in database
cd notebooks
sqlite3 pangenome_env_data/pangenome_env.db "
SELECT status, COUNT(*) as clusters, SUM(obs_count) as observations
FROM cluster_processing
WHERE service_name = 'USGS_NWIS'
GROUP BY status
"
```

---

## Clearing and Retrying

```bash
# Clear all data for a service (start fresh)
python acquire_environmental_data.py --clear USGS_NWIS

# Clear only failed clusters
python acquire_environmental_data.py --clear USGS_NWIS --clear-status failed

# Clear only no_data clusters (if adapter was fixed)
python acquire_environmental_data.py --clear USGS_NWIS --clear-status no_data
```

---

## Recommended Order

### High Priority (Start These)
1. **USGS_NWIS** (now fixed) - 5-6 hours
2. **WQP** - 5-6 hours
3. **SRTM** (finish remaining 835) - 28 minutes
4. **MODIS_NDVI** - 4 hours

### Medium Priority (Next)
5. **WORLDCLIM_BIO** - 2.7 hours
6. **MODIS_LST** - 4 hours
7. **SOILGRIDS_TEXTURE** - 2.7 hours

### Lower Priority (Later)
8. **SSURGO** (US only) - 4-5 hours
9. **OSM_Overpass** - 6-8 hours
10. **GOOGLE_EMBEDDINGS** - 6.6 hours

---

## Parallel Execution

Phase 0 services can run in parallel (different terminals):

```bash
# Terminal 1
python acquire_environmental_data.py --service WQP ...

# Terminal 2
python acquire_environmental_data.py --service USGS_NWIS ...

# Terminal 3
python acquire_environmental_data.py --service SSURGO ...
```

**Phase 1 (Earth Engine) services MUST run sequentially** (shared quotas)

---

## Expected Results

### USGS_NWIS (After Fix)
- Before: 2 obs/cluster (broken)
- After: ~200-500 obs/cluster (365 days × 1-2 parameters × ~50% sites with data)
- Total expected: ~500K-1M observations

### Other Services
See `CONFIGURED_SERVICES.md` for detailed expectations per service.

---

## Troubleshooting

### Service hangs
- Check if it's Earth Engine (timeout protection should prevent hangs)
- Non-EE services: Check API status at service website

### Too many "no_data"
- **OpenAQ:** Expected (83% no_data) - sparse sensor coverage
- **SSURGO:** Expected (~64% no_data) - US-only coverage
- **NWIS/WQP:** Some no_data expected for remote areas

### Low observation counts
- **USGS_NWIS:** Was broken (only 2 obs/cluster) - now fixed
- **Other services:** Check database to see actual counts vs expected