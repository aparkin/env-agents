# Environmental Data Acquisition - Service Plan

**Date:** 2025-09-29
**Total Clusters:** 4,789

## Current Status

### ✅ Phase 0: Complete (100%)

| Service | Status | Clusters | Observations | Notes |
|---------|--------|----------|--------------|-------|
| **NASA_POWER** | ✅ Complete | 4,789 / 4,789 | 10,487,910 | All clusters processed |
| **GBIF** | ✅ Complete | 4,789 / 4,789 | 1,436,700 | All clusters processed |

**Total observations:** 11,924,610

### 🔄 Phase 1: Earth Engine Services (In Progress)

#### SRTM Elevation ✅ Complete
- **Status:** 3,954 / 4,789 (83% complete)
- **Success:** 3,392 clusters → 3,392 observations
- **No data:** 562 clusters (outside coverage -56°S to 60°N)
- **Remaining:** 835 clusters
- **Estimated time:** 835 × 2s = ~28 minutes

#### MODIS NDVI 🟡 Testing Phase
- **Status:** 18 / 4,789 (<1% complete)
- **Success:** 12 clusters → 3,312 observations
- **No data:** 6 clusters
- **Remaining:** 4,771 clusters
- **Estimated time:** 4,771 × 3s = ~4 hours

### 🔄 Phase 2: Google Embeddings (Testing)

#### GOOGLE_EMBEDDINGS 🟡 Testing Phase
- **Status:** 20 / 4,789 (<1% complete)
- **Success:** 16 clusters → 1,024 observations
- **No data:** 4 clusters
- **Remaining:** 4,769 clusters
- **Estimated time:** 4,769 × 5s = ~6.6 hours

### ⚠️ Phase 0 (Additional): OpenAQ Issues

#### OpenAQ Air Quality 🟡 Mostly Complete with Errors
- **Status:** 3,674 / 4,789 (77% complete)
- **Success:** 610 clusters → 1,254,549 observations
- **No data:** 3,053 clusters (no sensors in area)
- **Error:** 11 clusters (OpenAQ API 500 errors)
- **Remaining:** 1,115 clusters
- **Issue:** API returning `500 Internal Server Error` intermittently

**Error analysis:**
```
All 11 errors: "500 Server Error: Internal Server Error"
Examples:
- https://api.openaq.org/v3/locations/921132/sensors
- https://api.openaq.org/v3/locations/10542/sensors
```

**Recommendation:** These are OpenAQ server issues, not our code. Can retry later with:
```bash
python acquire_environmental_data.py --clear OpenAQ --clear-status failed
```

## Services Available but Not Yet Configured

### High Priority (Should Add)

1. **USGS Water Quality Portal (WQP)**
   - Adapter exists: `env_agents/adapters/wqp/adapter.py`
   - Data: Stream water chemistry (pH, nutrients, metals, etc.)
   - Coverage: US focus but some international
   - **Why important:** Water chemistry crucial for microbial ecology
   - **Estimated time:** ~5-6 hours (similar to GBIF)

2. **USGS NWIS (Stream Gauge)**
   - Adapter exists: `env_agents/adapters/nwis/adapter.py`
   - Data: Stream discharge, water level, temperature
   - Coverage: US + some international
   - **Why important:** Hydrology affects microbial communities
   - **Estimated time:** ~5-6 hours

3. **SSURGO Soil Data**
   - Adapter exists: `env_agents/adapters/ssurgo/adapter.py`
   - Data: Soil properties (texture, pH, organic matter)
   - Coverage: US only
   - **Why important:** Many samples are soil microbes
   - **Estimated time:** ~4-5 hours

4. **OSM Overpass (Land Use)**
   - Adapter exists: `env_agents/adapters/overpass/adapter.py`
   - Data: Land use, buildings, roads, water bodies
   - Coverage: Global
   - **Why important:** Land use context for samples
   - **Estimated time:** ~6-8 hours (complex queries)

### Medium Priority (Consider Adding)

5. **Additional Earth Engine Assets**

   Available in `CANONICAL_SERVICES["EARTH_ENGINE"]`:
   - Climate datasets (WorldClim, CHELSA)
   - Soil datasets (SoilGrids, Polaris)
   - Land cover (MODIS, Copernicus)
   - Terrain (slope, aspect from SRTM)

   **How to add:** Configure like SRTM/MODIS in `acquire_environmental_data.py`

### Lower Priority (Future Consideration)

6. **AIRNow (US Air Quality)**
   - Adapter exists: `env_agents/adapters/air/adapter.py`
   - Data: US EPA air quality (PM2.5, ozone, etc.)
   - Coverage: US only
   - **Why lower:** OpenAQ already covers most locations

## Recommended Next Steps

### Immediate (Today/Tomorrow)

1. **Complete SRTM** (28 minutes)
   ```bash
   python acquire_environmental_data.py --service SRTM \
       --clusters clusters_optimized.csv \
       --samples df_gtdb_tagged_cleaneed.tsv
   ```

2. **Run MODIS NDVI** (4 hours)
   ```bash
   python acquire_environmental_data.py --service MODIS_NDVI \
       --clusters clusters_optimized.csv \
       --samples df_gtdb_tagged_cleaneed.tsv
   ```

3. **Run Google Embeddings** (6.6 hours)
   ```bash
   python acquire_environmental_data.py --service GOOGLE_EMBEDDINGS \
       --clusters clusters_optimized.csv \
       --samples df_gtdb_tagged_cleaneed.tsv
   ```

### Short Term (This Week)

4. **Add and run high-priority services:**

   a. **WQP (Water Quality)** - Add to `PHASE0_SERVICES`:
   ```python
   "WQP": {
       "rate_limit": 2.0,
       "timeout": 60,
       "time_range": ("2020-01-01", "2023-12-31")
   }
   ```

   b. **NWIS (Stream Gauge)** - Add to `PHASE0_SERVICES`:
   ```python
   "NWIS": {
       "rate_limit": 2.0,
       "timeout": 60,
       "time_range": ("2020-01-01", "2023-12-31")
   }
   ```

   c. **SSURGO (Soil)** - US-only, so will have many no_data:
   ```python
   "SSURGO": {
       "rate_limit": 3.0,
       "timeout": 90,
       "time_range": None  # Static data
   }
   ```

5. **Retry OpenAQ errors** (when their API is stable):
   ```bash
   python acquire_environmental_data.py --clear OpenAQ --clear-status failed
   ```

## Configuration Template

To add a new service to `acquire_environmental_data.py`:

```python
PHASE0_SERVICES = {
    # ... existing services ...

    "SERVICE_NAME": {
        "rate_limit": 2.0,          # Seconds between queries
        "timeout": 60,              # Query timeout
        "time_range": ("2020-01-01", "2023-12-31"),  # Or None
        "retry_on_quota": False,    # True for rate-limited APIs
        "max_retries": 1,           # Number of retries on error
        "backoff_seconds": 10       # Wait between retries
    }
}
```

Then run:
```bash
python acquire_environmental_data.py --phase 0 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

## Expected Data Volume

### Current (after Phase 1 complete)
- NASA_POWER: 10.5M observations
- GBIF: 1.4M observations
- SRTM: 3.4K observations
- OpenAQ: 1.3M observations
- **Total:** ~13.2M observations

### After Earth Engine complete
- MODIS_NDVI: ~12-15K observations (16 dates × 4,789 clusters × ~20% success)
- Google Embeddings: ~3-4K observations (1 per cluster × ~80% success)
- **Total:** ~13.2M observations

### After high-priority services added
- WQP: ~500K-1M observations
- NWIS: ~200K-500K observations
- SSURGO: ~100K-200K observations (US only)
- **Total:** ~14-15M observations

### Database size estimates
- Current: ~31 MB
- After Phase 1/2: ~2-3 GB
- After all services: ~5-7 GB

## OpenAQ Analysis

### Issue: High no_data and error rate

**Statistics:**
- Success rate: 610 / 3,674 = 16.6%
- No data rate: 3,053 / 3,674 = 83.1%
- Error rate: 11 / 3,674 = 0.3%

**Reasons for "no_data":**
1. Most clusters have no air quality sensors nearby
2. OpenAQ coverage is sparse (concentrated in urban areas)
3. Rural/remote areas where many samples are from have no sensors

**500 errors:**
- All are `500 Internal Server Error` from OpenAQ API
- Specific location IDs that trigger server errors
- Not our code issue - their API is having problems
- Can retry later when their API is stable

**Recommendation:** This is expected behavior. OpenAQ has good data where it exists (1.3M observations from 610 clusters), but coverage is limited to areas with sensors.

## Summary

**Ready to run:**
- ✅ SRTM: 28 minutes remaining
- ✅ MODIS_NDVI: 4 hours
- ✅ Google Embeddings: 6.6 hours

**Need to configure:**
- 🔧 WQP (Water Quality Portal)
- 🔧 NWIS (Stream Gauge)
- 🔧 SSURGO (Soil Data)
- 🔧 OSM Overpass (Land Use)

**Retry when stable:**
- ⏳ OpenAQ failed clusters (11 clusters, API issues)

**Total estimated time:** ~11-12 hours of compute time for currently configured services.