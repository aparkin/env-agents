# Environmental Data Services

This document lists all available environmental data services in env-agents. Services are organized by domain and ready for production use.

## Summary

- **Total Services**: 16
- **No Authentication Required**: 9 services
- **API Key Required**: 2 services (OpenAQ, EPA_AQS)
- **Service Account Required**: 5 services (Earth Engine assets)

---

## Climate & Weather

### NASA POWER
- **Domain**: Climate & Weather
- **Coverage**: Global
- **Authentication**: No
- **Key Variables**: Solar radiation, temperature, precipitation, humidity, wind speed
- **Description**: NASA POWER (Prediction of Worldwide Energy Resources) provides meteorological and solar energy data from satellite observations and climate models. High temporal resolution with global coverage.

### TerraClimate
- **Domain**: Climate & Water Balance
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Precipitation, evapotranspiration, soil moisture, temperature, vapor pressure deficit
- **Description**: Monthly climate and water balance data with 4km resolution. Ideal for understanding climate water balance and drought conditions.

### WorldClim Bioclimatic
- **Domain**: Climate
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: 19 bioclimatic variables (annual mean temperature, temperature seasonality, precipitation patterns, etc.)
- **Description**: Static bioclimatic variables derived from temperature and precipitation. Widely used for species distribution modeling and ecological analysis.

### GPM Precipitation
- **Domain**: Weather
- **Coverage**: Global (60°N-60°S)
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Precipitation rates, accumulation
- **Description**: NASA Global Precipitation Measurement (GPM) IMERG provides high-resolution (0.1°) half-hourly precipitation estimates from satellite observations.

---

## Satellite & Remote Sensing

### SRTM Elevation
- **Domain**: Terrain
- **Coverage**: Global (60°N-56°S)
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Elevation (meters above sea level)
- **Description**: Shuttle Radar Topography Mission (SRTM) provides 30m resolution digital elevation data. Essential for terrain analysis and topographic context.

### MODIS NDVI
- **Domain**: Vegetation
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: NDVI (Normalized Difference Vegetation Index), vegetation health
- **Description**: 16-day composite vegetation indices at 250m resolution from MODIS MOD13Q1. Tracks vegetation greenness and productivity.

### MODIS EVI
- **Domain**: Vegetation
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: EVI (Enhanced Vegetation Index)
- **Description**: Enhanced vegetation index from MODIS MOD13Q1, less sensitive to atmospheric conditions than NDVI. Useful in high biomass regions.

### MODIS Land Surface Temperature
- **Domain**: Temperature
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Day/night land surface temperature
- **Description**: Daily land surface temperature from MODIS MOD11A1 at 1km resolution. Provides thermal conditions at Earth's surface.

### MODIS Land Cover
- **Domain**: Land Use
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Land cover classification (17 IGBP classes)
- **Description**: Annual land cover classification from MODIS MCD12Q1. Identifies vegetation types, urban areas, water bodies, and barren land.

### Google Satellite Embeddings
- **Domain**: Multi-spectral Remote Sensing
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: 64-dimensional learned embeddings from Sentinel-2 imagery
- **Description**: Machine learning embeddings capturing multi-spectral patterns from annual Sentinel-2 composites (2017-present). Useful for site similarity analysis.

---

## Water Quality & Hydrology

### USGS NWIS
- **Domain**: Water Hydrology
- **Coverage**: United States
- **Authentication**: No
- **Key Variables**: Stream flow, gage height, water temperature, dissolved oxygen
- **Description**: USGS National Water Information System provides real-time and historical data from thousands of monitoring stations across the US.

### WQP (Water Quality Portal)
- **Domain**: Water Quality
- **Coverage**: United States (primary), some international
- **Authentication**: No
- **Key Variables**: pH, turbidity, nutrients, dissolved oxygen, temperature, specific conductance
- **Description**: Aggregates water quality data from EPA, USGS, and state agencies. Comprehensive water chemistry and physical parameters.

---

## Soil Properties

### SoilGrids Texture
- **Domain**: Soil Physical Properties
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Soil texture class (USDA classification)
- **Description**: Global soil texture classification at 250m resolution. Provides USDA soil texture classes (clay, sandy loam, etc.) at multiple depth intervals.

### SoilGrids pH
- **Domain**: Soil Chemistry
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Soil pH (H2O)
- **Description**: Global soil pH at 250m resolution at multiple depth intervals (0-5cm, 5-15cm, etc.). Critical for understanding nutrient availability.

### SoilGrids Organic Carbon
- **Domain**: Soil Chemistry
- **Coverage**: Global
- **Authentication**: Service Account (Earth Engine)
- **Key Variables**: Soil organic carbon content
- **Description**: Global soil organic carbon at 250m resolution. Important for soil fertility and carbon cycle analysis.

### SSURGO
- **Domain**: Soil Properties
- **Coverage**: United States
- **Authentication**: No
- **Key Variables**: Soil taxonomy, drainage class, pH, organic matter, texture, water capacity
- **Description**: USDA NRCS Soil Survey Geographic Database (SSURGO) provides detailed soil property data for the US with high spatial resolution (~1:24,000 scale).

---

## Air Quality

### OpenAQ
- **Domain**: Air Quality
- **Coverage**: Global (urban areas)
- **Authentication**: API Key required
- **Key Variables**: PM2.5, PM10, O3, NO2, SO2, CO
- **Description**: OpenAQ aggregates air quality data from government monitoring stations worldwide. Good coverage in urban areas across 100+ countries.

### EPA AQS
- **Domain**: Air Quality
- **Coverage**: United States
- **Authentication**: API Key required
- **Key Variables**: PM2.5, PM10, O3, NO2, SO2, CO, meteorological parameters
- **Description**: EPA Air Quality System provides data from official EPA air monitoring stations across the US. High quality QA/QC'd measurements.

---

## Biodiversity

### GBIF
- **Domain**: Biodiversity
- **Coverage**: Global
- **Authentication**: No
- **Key Variables**: Species occurrences, taxonomy, observation dates
- **Description**: Global Biodiversity Information Facility aggregates species occurrence data from museums, citizen science, and research programs. 2+ billion occurrence records.

---

## Infrastructure & Geospatial Features

### OSM Overpass
- **Domain**: Infrastructure & Points of Interest
- **Coverage**: Global
- **Authentication**: No
- **Key Variables**: Roads, buildings, amenities, land use, waterways
- **Description**: OpenStreetMap (OSM) Overpass API provides geospatial features from the OSM database. Query roads, buildings, amenities, natural features, and more.

---

## Service Selection Guide

### By Coverage
- **Global**: NASA_POWER, SoilGrids (3 types), MODIS (4 types), TerraClimate, WorldClim, GPM, SRTM, Google Embeddings, GBIF, OSM_Overpass, OpenAQ
- **United States**: USGS_NWIS, SSURGO, EPA_AQS, WQP

### By Authentication Requirement
- **No Auth**: NASA_POWER, USGS_NWIS, WQP, SSURGO, GBIF, OSM_Overpass (9 services)
- **API Key**: OpenAQ, EPA_AQS (2 services)
- **Service Account**: SRTM, MODIS_NDVI, MODIS_EVI, MODIS_LST, MODIS_LANDCOVER, TerraClimate, GPM_PRECIP, WORLDCLIM_BIO, SOILGRIDS_TEXTURE, SOILGRIDS_PH, SOILGRIDS_OC, GOOGLE_EMBEDDINGS (5 Earth Engine services, 12 assets total)

### By Domain
- **Climate & Weather**: 4 services (NASA_POWER, TerraClimate, WorldClim, GPM)
- **Satellite & Remote Sensing**: 6 services (SRTM, MODIS NDVI/EVI/LST/Landcover, Google Embeddings)
- **Water**: 2 services (USGS_NWIS, WQP)
- **Soil**: 4 services (SoilGrids Texture/pH/OC, SSURGO)
- **Air Quality**: 2 services (OpenAQ, EPA_AQS)
- **Biodiversity**: 1 service (GBIF)
- **Infrastructure**: 1 service (OSM_Overpass)

---

## Configuration Notes

### Earth Engine Services
All Earth Engine services share quotas and require a service account. For optimal performance:
- Run Earth Engine services sequentially or with increased rate limits when parallel
- Services include: SRTM, MODIS (4 types), TerraClimate, WorldClim, GPM, SoilGrids (3 types), Google Embeddings

### Rate Limiting
Services have built-in rate limits to ensure polite behavior:
- Fast services (0.5-1.0s): NASA_POWER, USGS_NWIS, GBIF, OpenAQ
- Moderate services (2.0-3.0s): WQP, SSURGO, OSM_Overpass, Earth Engine assets
- Slow services (5.0s): Google Embeddings (queries take 44s)

### Temporal Coverage
- **Real-time/Recent**: OpenAQ, USGS_NWIS, WQP, GBIF, NASA_POWER
- **Historical Time Series**: MODIS (2000-present), TerraClimate (1958-present), GPM (2000-present)
- **Static/Climatology**: SRTM, WorldClim, SoilGrids, SSURGO

---

*Last updated: 2025-09-30*