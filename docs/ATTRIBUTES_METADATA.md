# Attributes Metadata Documentation

## Overview

The `attributes` column in `env_observations` table stores service-specific metadata as JSON. This document catalogs what metadata each service stores.

**Database Schema**:
```sql
CREATE TABLE env_observations (
    obs_id TEXT,
    cluster_id INTEGER,
    service_name TEXT,
    variable TEXT,
    value REAL,
    unit TEXT,
    time_stamp TEXT,
    lat REAL,
    lon REAL,
    attributes TEXT,  -- JSON-serialized service-specific metadata
    PRIMARY KEY (cluster_id, service_name, variable, time_stamp, obs_id)
);
```

---

## Service-Specific Attributes

### GBIF (Biodiversity Occurrences)

**Purpose**: Preserves full taxonomic hierarchy and specimen provenance.

**Attributes Schema**:
```json
{
  "gbif_id": 1632777577,
  "dataset_key": "fa375330-6c8a-11de-8226-b8a03c50a862",
  "publishing_org": "South Australian Museum",
  "basis_of_record": "PRESERVED_SPECIMEN",
  "occurrence_status": "PRESENT",

  "species": "Colepia rufiventris",
  "scientific_name": "Colepia rufiventris (Macquart, 1838)",
  "kingdom": "Animalia",
  "phylum": "Arthropoda",
  "class": "Insecta",
  "order": "Diptera",
  "family": "Asilidae",
  "genus": "Colepia",
  "taxon_rank": "SPECIES",

  "coordinate_uncertainty": 10000.0,
  "year": 2025,
  "month": 1,
  "day": 24,

  "recorded_by": "Gibbons, Charles",
  "identified_by": null,
  "collection_code": "Entomology",
  "institution_code": "SAMA",

  "ecological_significance": null,
  "conservation_applications": [],

  "terms": {
    "native_id": 1632777577,
    "native_name": "d_unknown;k_Animalia;p_Arthropoda;c_Insecta;o_Diptera;f_Asilidae;g_Colepia;s_Colepia rufiventris",
    "canonical_variable": null
  }
}
```

**Key Fields**:
- **Taxonomy**: `species`, `scientific_name`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `taxon_rank`
- **Specimen Info**: `basis_of_record` (PRESERVED_SPECIMEN, OBSERVATION, etc.), `collection_code`, `institution_code`
- **Observation Details**: `coordinate_uncertainty`, `year`, `month`, `day`, `recorded_by`, `identified_by`
- **Data Provenance**: `gbif_id`, `dataset_key`, `publishing_org`

**Use Cases**:
- Extract full taxonomic lineage for phylogenetic analysis
- Filter by observation type (specimens vs field observations)
- Assess data quality via coordinate uncertainty and institution reputation
- Track specimen provenance for reproducibility

---

### NASA_POWER (Climate Data)

**Expected Attributes** (to be populated during re-acquisition):
```json
{
  "data_quality": {
    "qa_flag": "validated",
    "uncertainty": 0.05,
    "measurement_method": "satellite_derived"
  },
  "temporal_aggregation": {
    "source_cadence": "daily",
    "aggregation_method": "mean",
    "coverage_days": 365
  },
  "spatial_resolution": {
    "native_resolution_deg": 0.5,
    "interpolation_method": "bilinear"
  },
  "terms": {
    "native_id": "T2M",
    "native_name": "Temperature at 2 Meters",
    "canonical_variable": "temperature"
  }
}
```

**Key Fields**:
- **Quality**: QA flags, uncertainty estimates
- **Temporal**: Source cadence, aggregation method, temporal coverage
- **Spatial**: Native resolution, interpolation details
- **Provenance**: Native parameter IDs and names

---

### MODIS (Vegetation Indices)

**Expected Attributes**:
```json
{
  "image_metadata": {
    "acquisition_date": "2024-01-15",
    "processing_level": "MOD13Q1",
    "tile_id": "h12v09",
    "pixel_reliability": "good"
  },
  "quality_bands": {
    "SummaryQA": 0,
    "DetailedQA": 2048,
    "cloud_cover_pct": 5.2
  },
  "viewing_geometry": {
    "solar_zenith": 45.3,
    "view_zenith": 12.1,
    "relative_azimuth": 180.5
  },
  "spatial_resolution": {
    "native_m": 250,
    "aggregation_method": "mean"
  },
  "terms": {
    "native_id": "ee:NDVI",
    "native_name": "Normalized Difference Vegetation Index",
    "canonical_variable": "vegetation:ndvi"
  }
}
```

**Key Fields**:
- **Image Metadata**: Acquisition date, processing level, tile ID
- **Quality**: Pixel reliability, QA bands, cloud cover
- **Geometry**: Solar/view angles for atmospheric correction assessment
- **Resolution**: Native pixel size, aggregation method

---

### SOILGRIDS (Soil Properties)

**Expected Attributes**:
```json
{
  "depth_info": {
    "depth_cm": "0-5",
    "depth_code": "b0",
    "standard_depth": true
  },
  "prediction_quality": {
    "model_version": "2.0",
    "prediction_method": "machine_learning",
    "uncertainty_pct": 15.3,
    "confidence_interval_90": [5.2, 6.8]
  },
  "spatial_resolution": {
    "native_m": 250,
    "coordinate_system": "EPSG:4326"
  },
  "data_source": {
    "profile_count": 150000,
    "coverage_year": 2017
  },
  "terms": {
    "native_id": "phh2o_0-5cm_mean",
    "native_name": "Soil pH (H2O) 0-5cm",
    "canonical_variable": "soil:ph"
  }
}
```

**Key Fields**:
- **Depth**: Depth range, standardized depth codes
- **Quality**: Model version, prediction method, uncertainty, confidence intervals
- **Resolution**: Native resolution, coordinate system
- **Provenance**: Source profile counts, reference year

---

### TERRACLIMATE (Climate Normals)

**Expected Attributes**:
```json
{
  "temporal_coverage": {
    "period": "monthly",
    "reference_period": "1958-2021",
    "climatology_type": "long_term_mean"
  },
  "derived_variable": {
    "source_variables": ["precipitation", "pet"],
    "calculation_method": "water_balance",
    "units_info": "deficit/surplus in mm"
  },
  "spatial_resolution": {
    "native_km": 4,
    "downscaling_method": "climatically_aided_interpolation"
  },
  "terms": {
    "native_id": "def",
    "native_name": "Climate Water Deficit",
    "canonical_variable": "climate:water_deficit"
  }
}
```

**Key Fields**:
- **Temporal**: Period, reference timespan, climatology type
- **Derivation**: Source variables, calculation methods
- **Resolution**: Native resolution, downscaling approach

---

### WORLDCLIM_BIO (Bioclimatic Variables)

**Expected Attributes**:
```json
{
  "bioclim_variable": {
    "bio_number": "BIO1",
    "description": "Annual Mean Temperature",
    "calculation": "mean_of_monthly_means"
  },
  "temporal_coverage": {
    "reference_period": "1970-2000",
    "source_data": "WorldClim 2.1"
  },
  "spatial_resolution": {
    "native_arcsec": 30,
    "native_m": 1000,
    "interpolation": "thin_plate_splines"
  },
  "derived_info": {
    "source_variables": ["tmin", "tmax"],
    "calculation_basis": "monthly_climatologies"
  },
  "terms": {
    "native_id": "bio01",
    "native_name": "Annual Mean Temperature",
    "canonical_variable": "climate:temp_annual_mean"
  }
}
```

**Key Fields**:
- **Bioclim**: BIO variable number, description, calculation method
- **Temporal**: Reference period, source dataset version
- **Spatial**: Native resolution in arcseconds and meters, interpolation method
- **Derivation**: Source variables, calculation basis

---

### GOOGLE_EMBEDDINGS (Environmental Features)

**Expected Attributes**:
```json
{
  "embedding_metadata": {
    "model_version": "geographic_embeddings_v1",
    "feature_dimension": 64,
    "training_data": "global_satellite_imagery",
    "spatial_scale_m": 250
  },
  "image_source": {
    "satellite": "Sentinel-2",
    "acquisition_window": "2020-2023",
    "cloud_cover_max_pct": 20,
    "composite_method": "median"
  },
  "feature_extraction": {
    "architecture": "ResNet50",
    "layer": "avgpool",
    "normalization": "L2"
  },
  "terms": {
    "native_id": "emb_dim_0",
    "native_name": "Embedding Dimension 0",
    "canonical_variable": "features:embedding_0"
  }
}
```

**Key Fields**:
- **Model**: Version, dimensionality, training data
- **Image Source**: Satellite, time window, quality filters
- **Extraction**: Neural network architecture, layer, normalization

---

### SRTM (Elevation)

**Expected Attributes**:
```json
{
  "dem_metadata": {
    "mission": "Shuttle Radar Topography Mission",
    "acquisition_year": 2000,
    "vertical_datum": "EGM96",
    "vertical_accuracy_m": 16
  },
  "spatial_resolution": {
    "native_arcsec": 3,
    "native_m": 90,
    "void_filled": true,
    "fill_method": "interpolation"
  },
  "processing": {
    "resampling": "bilinear",
    "coordinate_system": "EPSG:4326"
  },
  "terms": {
    "native_id": "ee:elevation",
    "native_name": "Elevation",
    "canonical_variable": "terrain:elevation"
  }
}
```

**Key Fields**:
- **Mission**: SRTM mission, acquisition year, vertical datum, accuracy
- **Resolution**: Native resolution, void filling status and method
- **Processing**: Resampling method, coordinate system

---

### MODIS_LANDCOVER

**Expected Attributes**:
```json
{
  "classification": {
    "scheme": "IGBP",
    "num_classes": 17,
    "class_name": "Evergreen Broadleaf Forest",
    "class_code": 2
  },
  "image_metadata": {
    "product": "MCD12Q1",
    "processing_level": "L3",
    "year": 2020,
    "collection": "6"
  },
  "quality": {
    "qa_confidence": "high",
    "algorithm": "supervised_classification"
  },
  "spatial_resolution": {
    "native_m": 500,
    "majority_filter": true
  },
  "terms": {
    "native_id": "LC_Type1",
    "native_name": "Land Cover Type 1 (IGBP)",
    "canonical_variable": "landcover:igbp_class"
  }
}
```

**Key Fields**:
- **Classification**: Scheme, class name/code, number of classes
- **Image**: Product name, processing level, year, collection
- **Quality**: QA confidence, classification algorithm
- **Resolution**: Native resolution, post-processing filters

---

## Future Services (Attributes Not Yet Implemented)

The following services need attributes fields defined during re-acquisition:

### To Implement:
- **OpenAQ**: Air quality sensor metadata, measurement precision, data provenance
- **WQP**: Water quality sampling protocols, lab methods, detection limits
- **SSURGO**: Soil survey metadata, mapping confidence, source survey dates
- **OSM**: OpenStreetMap feature types, tags, contributor information

---

## Using Attributes in Analysis

### Example 1: Filter GBIF by Observation Type
```python
import json
import pandas as pd
import sqlite3

conn = sqlite3.connect('pangenome_env.db')
query = "SELECT * FROM env_observations WHERE service_name = 'GBIF'"
df = pd.read_sql(query, conn)

# Parse attributes
df['attrs'] = df['attributes'].apply(lambda x: json.loads(x) if x else {})

# Filter to preserved specimens only
specimens = df[df['attrs'].apply(lambda x: x.get('basis_of_record') == 'PRESERVED_SPECIMEN')]
```

### Example 2: Extract Taxonomic Hierarchy
```python
# Get full taxonomic lineage
df['kingdom'] = df['attrs'].apply(lambda x: x.get('kingdom'))
df['phylum'] = df['attrs'].apply(lambda x: x.get('phylum'))
df['class'] = df['attrs'].apply(lambda x: x.get('class'))
df['order'] = df['attrs'].apply(lambda x: x.get('order'))
df['family'] = df['attrs'].apply(lambda x: x.get('family'))
df['genus'] = df['attrs'].apply(lambda x: x.get('genus'))
df['species'] = df['attrs'].apply(lambda x: x.get('species'))

# Group by taxonomic level
phylum_counts = df.groupby('phylum').size()
```

### Example 3: Quality Filter by Coordinate Uncertainty
```python
# Filter GBIF observations with high spatial precision
high_precision = df[
    df['attrs'].apply(lambda x:
        x.get('coordinate_uncertainty', float('inf')) < 1000  # < 1km uncertainty
    )
]
```

### Example 4: Extract MODIS Quality Flags
```python
modis = df[df['service_name'] == 'MODIS_NDVI']
modis['cloud_cover'] = modis['attrs'].apply(lambda x: x.get('quality_bands', {}).get('cloud_cover_pct', 100))

# Filter to cloud-free observations
clear_sky = modis[modis['cloud_cover'] < 10]
```

---

## Maintenance Notes

**When adding new services**:
1. Document attributes schema in this file
2. Ensure adapter populates `attributes` dict in `_fetch_rows()`
3. Test JSON serialization with complex types (nested dicts, lists, None values)
4. Add example queries showing how to use attributes in analysis

**When updating existing services**:
1. Document schema changes with version notes
2. Maintain backward compatibility when possible
3. Update example queries if attribute structure changes
4. Consider migration script if breaking changes are needed

---

## Genome Sample Metadata

### Environment Classification (`env_class`)

**Purpose**: Distinguish samples from natural environments vs. human-modified settings for filtering analysis datasets.

**Schema** (in `df_gtdb_tagged_cleaneed.tsv` and `genome_samples` table):
```
genome_id, lat, lon, env_class, env_tags, ...
```

**Classification Logic** (see `analysis/notebooks/01_data_prep/00_environment_classification.ipynb`):

```python
def classify_environment_osm(df, lat_col="lat", lon_col="lon", radius=100):
    """
    Classify coordinates using OpenStreetMap Overpass API.

    Query detects:
    - Buildings (node/way/relation[building])
    - Universities (amenity=university)
    - Industrial sites (industrial=*)

    Within 100m radius of sample coordinates.
    """
```

**Values**:
- **`"free_environment"`**: No buildings, universities, or industrial sites within 100m
  - Natural habitats (forests, grasslands, water bodies)
  - Remote locations away from human infrastructure
  - Agricultural fields (no buildings)

- **`"other"`**: Human-modified environment detected
  - Urban/suburban areas with buildings
  - University campuses and research stations
  - Industrial sites and factories
  - Hospitals and labs (detected via building tags)

- **`"error"`**: OSM API query failed (network timeout, invalid coordinates, etc.)

**`env_tags` Field**: List of OpenStreetMap feature tags for detected structures (JSON-serialized).

Example:
```json
[
  {"building": "yes", "addr:city": "Berkeley", "name": "Stanley Hall"},
  {"amenity": "university", "name": "University of California Berkeley"}
]
```

**Use Cases**:

1. **Filter to environmental samples only**:
   ```python
   df_natural = df[df['env_class'] == 'free_environment']
   ```

2. **Compare host-associated vs. environmental microbes**:
   ```python
   # Assuming host data also available
   natural_microbes = df[df['env_class'] == 'free_environment']
   host_associated = df[df['host_harmonized'].notna()]
   ```

3. **Exclude lab contaminants**:
   ```python
   # Exclude samples near universities/labs
   field_samples = df[
       (df['env_class'] == 'free_environment') |
       (df['env_tags'].apply(lambda x: 'university' not in str(x)))
   ]
   ```

4. **Analyze urbanization gradient**:
   ```python
   # Count nearby buildings as urbanization proxy
   df['building_count'] = df['env_tags'].apply(
       lambda x: sum(1 for tag in x if 'building' in tag)
   )
   ```

**Data Quality Notes**:
- Classification relies on OpenStreetMap completeness (varies by region)
- Urban areas: high OSM coverage, reliable classification
- Remote areas: lower OSM coverage, may miss small structures
- 100m radius chosen to balance:
  - **Sensitivity**: Detect nearby human activity
  - **Specificity**: Avoid false positives from distant buildings

**Processing Details**:
- Unique coordinates queried once (deduplicated)
- Results cached and mapped back to all genomes at that location
- Total queries: ~40,000 unique locations (from 83,227 genomes)
- Rate limited to respect OSM Overpass API limits (1 query/2 seconds)
- Total processing time: ~22 hours

**Source**: `notebooks/GTB Pangenome Environment Linkage.ipynb` (original, 89MB with outputs)
**Clean version**: `analysis/notebooks/01_data_prep/00_environment_classification.ipynb` (outputs stripped)
