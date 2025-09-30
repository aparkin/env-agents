# Earth Engine Assets - Complete Guide

**Total Phase 1 Services:** 12 assets (all global coverage)

## Currently Configured Assets

### Terrain & Topography

#### SRTM - Elevation
- **Asset:** `USGS/SRTMGL1_003`
- **Data:** Elevation (meters above sea level)
- **Resolution:** 30m
- **Coverage:** -56°S to 60°N (96% of your clusters)
- **Variables:** `elevation`
- **Status:** 83% complete
- **Use cases:** Altitude effects on microbes, drainage patterns

---

### Vegetation Indices

#### MODIS_NDVI - Normalized Difference Vegetation Index
- **Asset:** `MODIS/061/MOD13Q1`
- **Data:** NDVI time series (vegetation greenness)
- **Temporal:** 16-day composites (23 per year)
- **Resolution:** 250m
- **Variables:** `NDVI`, `EVI`, `SummaryQA`
- **Status:** Testing
- **Use cases:** Vegetation productivity, seasonality, plant-microbe interactions

#### MODIS_EVI - Enhanced Vegetation Index
- **Asset:** `MODIS/061/MOD13Q1` (same as NDVI, different band)
- **Data:** EVI time series (less sensitive to atmospheric conditions)
- **Temporal:** 16-day composites
- **Resolution:** 250m
- **Why separate:** EVI better in high biomass areas (tropics, forests)

#### MODIS_LANDCOVER - Land Cover Classification
- **Asset:** `MODIS/006/MCD12Q1`
- **Data:** Land cover types (17 IGBP classes)
- **Temporal:** Annual
- **Resolution:** 500m
- **Classes:** Forest, grassland, cropland, urban, water, etc.
- **Use cases:** Habitat classification, land use impacts

---

### Temperature

#### MODIS_LST - Land Surface Temperature
- **Asset:** `MODIS/061/MOD11A1`
- **Data:** Day/night land surface temperature
- **Temporal:** Daily
- **Resolution:** 1km
- **Variables:** `LST_Day_1km`, `LST_Night_1km`, `QC_Day`, `QC_Night`
- **Use cases:** Temperature stress, diurnal cycles, thermal niches

---

### Climate Variables

#### WORLDCLIM_BIO - Bioclimatic Variables
- **Asset:** `WORLDCLIM/V1/BIO`
- **Data:** 19 bioclimatic variables (static, 1970-2000 average)
- **Resolution:** 1km
- **Variables:**
  - BIO1: Annual mean temperature
  - BIO2: Mean diurnal range
  - BIO3: Isothermality
  - BIO4: Temperature seasonality
  - BIO5: Max temperature of warmest month
  - BIO6: Min temperature of coldest month
  - BIO7: Temperature annual range
  - BIO8-11: Quarterly temperatures
  - BIO12: Annual precipitation
  - BIO13: Precipitation of wettest month
  - BIO14: Precipitation of driest month
  - BIO15: Precipitation seasonality
  - BIO16-19: Quarterly precipitation
- **Use cases:** Climate niche modeling, biogeography, climate gradients

#### TERRACLIMATE - Climate Water Balance
- **Asset:** `IDAHO_EPSCOR/TERRACLIMATE`
- **Data:** Monthly climate and water balance
- **Temporal:** Monthly (12 per year)
- **Resolution:** 4km
- **Variables:**
  - `aet`: Actual evapotranspiration
  - `def`: Climate water deficit
  - `pdsi`: Palmer Drought Severity Index
  - `pet`: Potential evapotranspiration
  - `pr`: Precipitation
  - `ro`: Runoff
  - `soil`: Soil moisture
  - `swe`: Snow water equivalent
  - `tmmn`, `tmmx`: Min/max temperature
  - `vpd`: Vapor pressure deficit
- **Use cases:** Drought stress, water availability, aridity

#### GPM_PRECIP - High-Resolution Precipitation
- **Asset:** `NASA/GPM_L3/IMERG_V06`
- **Data:** Half-hourly global precipitation
- **Temporal:** 30-minute intervals (can aggregate to daily/monthly)
- **Resolution:** 0.1° (~10km)
- **Variables:** `precipitationCal`, `randomError`, `precipitationQualityIndex`
- **Use cases:** Rainfall patterns, extreme events, moisture pulses

---

### Soil Properties (Global)

#### SOILGRIDS_TEXTURE - Soil Texture Class
- **Asset:** `OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02`
- **Data:** USDA soil texture classification
- **Depth:** 0-5cm (surface layer)
- **Resolution:** 250m
- **Classes:** Clay, silty clay, sandy clay, clay loam, silty clay loam, sandy clay loam, loam, silt loam, sandy loam, silt, loamy sand, sand
- **Use cases:** Soil physical properties, water retention, microbial habitat

#### SOILGRIDS_PH - Soil pH
- **Asset:** `OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02`
- **Data:** Soil pH in H2O (0-5cm depth)
- **Resolution:** 250m
- **Range:** pH 4-9
- **Use cases:** Nutrient availability, microbial community composition, biogeochemistry

#### SOILGRIDS_OC - Organic Carbon
- **Asset:** `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- **Data:** Soil organic carbon (g/kg, 0-5cm depth)
- **Resolution:** 250m
- **Use cases:** Carbon cycling, soil fertility, microbial substrate

---

### Satellite Embeddings

#### GOOGLE_EMBEDDINGS - Satellite Image Features
- **Asset:** `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`
- **Data:** 64-dimensional feature vectors from deep learning
- **Source:** Sentinel-2 imagery
- **Temporal:** Annual composites
- **Resolution:** 10m
- **Use cases:** Image similarity, unsupervised clustering, transfer learning

---

## Summary Statistics

### Phase 1 Assets (12 total)

| Category | Count | Coverage | Temporal |
|----------|-------|----------|----------|
| Terrain | 1 | 96% | Static |
| Vegetation | 3 | Global | Time series |
| Temperature | 1 | Global | Daily |
| Climate | 3 | Global | Static/Monthly |
| Soil | 3 | Global | Static |
| Embeddings | 1 | Global | Annual |

### Expected Observations

**Static assets (6):**
- SRTM, WORLDCLIM_BIO, SOILGRIDS × 3, MODIS_LANDCOVER
- ~1-20 variables per asset
- ~50K total observations

**Time series assets (5):**
- MODIS_NDVI, MODIS_EVI, MODIS_LST, TERRACLIMATE, GPM_PRECIP
- ~12-365 time points per year
- ~200K-500K total observations

**Embeddings (1):**
- GOOGLE_EMBEDDINGS
- 64 dimensions
- ~4K total observations

**Phase 1 Total:** ~250K-550K observations from Earth Engine

---

## Running Earth Engine Assets

### Individual Service
```bash
python acquire_environmental_data.py --service SOILGRIDS_PH \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

### All Phase 1 (Sequential - Required)
```bash
python acquire_environmental_data.py --phase 1 \
    --clusters clusters_optimized.csv \
    --samples df_gtdb_tagged_cleaneed.tsv
```

**Estimated time for all Phase 1:** ~30-35 hours (must run sequentially due to shared quotas)

---

## Priority Recommendations

### Tier 1: Critical Environmental Context (Run First)
1. **SRTM** - Elevation (finish remaining 835 clusters, ~28 min)
2. **WORLDCLIM_BIO** - Climate niche (19 variables, ~2.7 hours)
3. **SOILGRIDS_PH** - Soil pH (major microbial driver, ~2.7 hours)
4. **SOILGRIDS_OC** - Organic carbon (substrate availability, ~2.7 hours)

**Subtotal:** ~8 hours

### Tier 2: Vegetation & Land Use (Next)
5. **MODIS_NDVI** - Vegetation productivity (~4 hours)
6. **MODIS_LANDCOVER** - Habitat classification (~2.7 hours)

**Subtotal:** ~7 hours

### Tier 3: Temporal Dynamics (Then)
7. **MODIS_LST** - Temperature time series (~4 hours)
8. **TERRACLIMATE** - Water balance (~4 hours)
9. **GPM_PRECIP** - Precipitation patterns (~4 hours)

**Subtotal:** ~12 hours

### Tier 4: Additional Features (Later)
10. **MODIS_EVI** - Alternative vegetation index (~4 hours)
11. **SOILGRIDS_TEXTURE** - Soil physical properties (~2.7 hours)
12. **GOOGLE_EMBEDDINGS** - Deep learning features (~6.6 hours)

**Subtotal:** ~13 hours

---

## Variable Interpretation Guide

### Most Important for Microbial Ecology

**Soil:**
- **pH**: Strong driver of community composition (acidophiles vs alkaliphiles)
- **Organic carbon**: Energy/substrate availability
- **Texture**: Water retention, oxygen availability, habitat structure

**Climate:**
- **BIO1** (annual mean temp): Temperature optima
- **BIO4** (temperature seasonality): Environmental variability
- **BIO12** (annual precip): Water availability
- **BIO15** (precip seasonality): Drought/flood cycles

**Water Balance:**
- **Soil moisture**: Direct microbial activity control
- **Water deficit**: Stress indicator
- **PDSI**: Drought severity

**Vegetation:**
- **NDVI/EVI**: Primary productivity (carbon inputs)
- **Land cover**: Habitat type (forest vs grassland vs urban)

**Temperature:**
- **LST day/night**: Thermal stress, diurnal variation
- **Temperature range**: Thermal niche breadth

---

## Data Integration Strategy

### Recommended Analysis Workflow

1. **Static environmental characterization:**
   - SRTM elevation
   - WORLDCLIM_BIO climate niche
   - SOILGRIDS pH, OC, texture
   - MODIS_LANDCOVER habitat type

2. **Temporal dynamics:**
   - MODIS_NDVI vegetation seasonality
   - MODIS_LST temperature variation
   - TERRACLIMATE water balance
   - GPM_PRECIP rainfall patterns

3. **Advanced features:**
   - GOOGLE_EMBEDDINGS for image-based clustering
   - Integration with species observations (GBIF)
   - Cross-reference with measured variables (NASA_POWER)

### Example Use Cases

**Biogeography:**
- Cluster genomes by WORLDCLIM_BIO variables
- Identify climate niche specialization
- Map species-environment relationships

**Temporal ecology:**
- Correlate community composition with NDVI seasonality
- Link to precipitation pulses (GPM)
- Temperature stress responses (LST)

**Soil-microbe interactions:**
- pH effects on community structure
- Organic carbon and functional guilds
- Texture and spatial distribution

---

## Additional Assets to Consider (Not Yet Configured)

### Human Impact
- **ESA WorldCover** - High-res land cover (10m)
- **GHSL** - Global Human Settlement Layer
- **Roads/Infrastructure** - Already have OSM_Overpass

### Additional Soil
- **SoilGrids Nitrogen** - `OpenLandMap/SOL/SOL_NITROGEN_M/v02`
- **SoilGrids Clay Content** - `OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02`
- **SoilGrids Bulk Density** - `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02`

### Additional Climate
- **CHELSA** - High-resolution climate (1km)
- **ERA5** - Hourly climate reanalysis

Add these if needed - follow same pattern as current assets!