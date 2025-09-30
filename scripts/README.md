# Scripts Directory

Production scripts for environmental data acquisition and framework maintenance.

---

## `acquire_environmental_data.py` 🚀

**Main production script for pangenome environmental data acquisition pipeline.**

### Purpose
Orchestrates fetching environmental data from 16 different services for spatial clusters derived from microbial genome samples. Manages database persistence, rate limiting, error handling, and resume capabilities.

### Quick Start
```bash
# Run all Phase 0 services (unitary, can parallelize)
python acquire_environmental_data.py --phase 0 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv

# Run specific service
python acquire_environmental_data.py --service USGS_NWIS \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv

# Check progress
python acquire_environmental_data.py --status
```

### Features
- **16 configured services:** NASA_POWER, GBIF, OpenAQ, USGS_NWIS, WQP, SSURGO, OSM_Overpass, SRTM, MODIS (NDVI/LST/EVI/LANDCOVER), WorldClim, SoilGrids (3 types), TerraClimate, GPM, Google Embeddings
- **Resume capability:** Automatically skips completed clusters
- **Phased execution:** Organize services into phases (0=unitary, 1=Earth Engine, 2=embeddings)
- **Rate limiting:** Respects API limits with configurable delays
- **Earth Engine optimization:** Timeout protection, sequential execution for shared quotas
- **Error handling:** Graceful handling of failures, retries, no_data responses

### Available Services

**Phase 0 (7 services, can run in parallel):**
- NASA_POWER - Climate data (COMPLETE - 10.5M obs)
- GBIF - Species observations (COMPLETE - 1.4M obs)
- OpenAQ - Air quality (77% done)
- USGS_NWIS - Stream gauges (US only, ~126K expected)
- WQP - Water quality (US + international)
- SSURGO - Soil survey (US only)
- OSM_Overpass - Land use features

**Phase 1 (12 services, must run sequentially):**
- SRTM - Elevation (83% done)
- MODIS_NDVI, MODIS_LST, MODIS_EVI, MODIS_LANDCOVER - Remote sensing
- WORLDCLIM_BIO - 19 bioclimatic variables
- SOILGRIDS_TEXTURE, SOILGRIDS_PH, SOILGRIDS_OC - Global soil properties
- TERRACLIMATE - Climate water balance
- GPM_PRECIP - High-resolution precipitation

**Phase 2 (1 service):**
- GOOGLE_EMBEDDINGS - 64-dim satellite image features

### Usage Examples

#### Run by Phase
```bash
# Phase 0: Unitary services (~18-25 hours)
python acquire_environmental_data.py --phase 0 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv

# Phase 1: Earth Engine (~30-35 hours, sequential)
python acquire_environmental_data.py --phase 1 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv

# Phase 2: Embeddings (~6.6 hours)
python acquire_environmental_data.py --phase 2 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv
```

#### Run Individual Services
```bash
# Run specific high-priority services
python acquire_environmental_data.py --service WORLDCLIM_BIO \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv

python acquire_environmental_data.py --service SOILGRIDS_PH \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv
```

#### Test with Limited Clusters
```bash
# Process only first 10 clusters (for testing)
python acquire_environmental_data.py --phase 1 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv \
    --max-clusters 10
```

#### Check Status and Clear Data
```bash
# View overall progress
python acquire_environmental_data.py --status

# Clear all data for a service
python acquire_environmental_data.py --clear USGS_NWIS

# Clear only failed clusters
python acquire_environmental_data.py --clear USGS_NWIS --clear-status failed

# Clear no_data (useful after adapter fixes)
python acquire_environmental_data.py --clear USGS_NWIS --clear-status no_data
```

### Related Documentation
- **Service overview:** `../docs/PANGENOME_SERVICES.md`
- **USGS NWIS details:** `../docs/USGS_NWIS_ADAPTER.md`
- **Database schema:** `../docs/DATABASE_MANAGEMENT.md`
- **Earth Engine optimization:** `../EARTH_ENGINE_OPTIMIZATION.md`

---

## `refresh_metadata.py` 🔧

**Updates and maintains Earth Engine catalog and metadata system.**

### Usage
```bash
python scripts/refresh_metadata.py
```

### Function
- Downloads latest Earth Engine catalog from Google
- Updates asset metadata and discovery information (997 assets)
- Refreshes local catalog cache
- Essential for keeping Earth Engine service current

**Recommendation:** Run monthly to keep catalog up-to-date.

---

## `setup_credentials.py` 🔐

**Interactive setup for service credentials and authentication.**

### Usage
```bash
python scripts/setup_credentials.py
```

### Function
- Guides through credential setup for all services
- Creates `config/credentials.yaml` with proper structure
- Sets up Earth Engine service account authentication
- Configures API keys for government and research services

### Required Credentials (for full functionality)
- **EPA AQS**: Email + API key (free registration)
- **Earth Engine**: Google Cloud service account (requires GCP project)

### No Authentication Required
- NASA POWER, USGS NWIS, SSURGO, SoilGrids, GBIF, WQP, OpenAQ, Overpass

---

## Operational Workflow

### Initial Setup
```bash
# 1. Set up credentials (if needed)
python scripts/setup_credentials.py

# 2. Refresh Earth Engine catalog (optional - already populated)
python scripts/refresh_metadata.py

# 3. Start data acquisition
python scripts/acquire_environmental_data.py --phase 0 \
    --clusters ../notebooks/clusters_optimized.csv \
    --samples ../notebooks/df_gtdb_tagged_cleaneed.tsv
```

### Maintenance
```bash
# Update Earth Engine catalog (monthly)
python scripts/refresh_metadata.py

# Reconfigure credentials (when adding new API keys)
python scripts/setup_credentials.py
```

---

## Version History

**v2.0.3** (2025-09-30)
- Added support for 16 services (expanded from 8)
- Dynamic service list for --service argument
- Comprehensive USGS_NWIS with 16 parameter codes

**v2.0.2** (2025-09-29)
- Earth Engine timeout protection
- Fixed USGS_NWIS endpoint and parameters
- Added WQP, SSURGO, OSM_Overpass services

**v2.0.1** (2025-09-28)
- Initial production version