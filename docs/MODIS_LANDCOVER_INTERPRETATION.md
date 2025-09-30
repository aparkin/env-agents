# MODIS Land Cover (MCD12Q1) - Value Interpretation Guide

**Asset:** `MODIS/061/MCD12Q1`
**Resolution:** 500m
**Temporal:** Annual (2001-2023+)
**Documentation:** https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1

## Overview

MODIS MCD12Q1 provides **5 different classification schemes** (LC_Type1-5) plus quality/assessment bands. Each classification system categorizes land cover differently - choose the one that fits your analysis needs.

## Data Structure in Database

Our adapter stores **raw categorical values** like:
```json
{
  "variable": "ee:LC_Type1",
  "value": 1.0,
  "time": "2022-01-01"
}
```

The numeric value (1, 2, 3...) is a **category code** that needs interpretation based on the classification scheme.

## Classification Schemes

### LC_Type1: IGBP (International Geosphere-Biosphere Programme)
**Most commonly used, 17 classes**

| Value | Class Name | Description |
|-------|------------|-------------|
| 1 | Evergreen Needleleaf Forests | >60% tree cover, >2m tall, needle leaves, always green |
| 2 | Evergreen Broadleaf Forests | >60% tree cover, >2m tall, broad leaves, always green |
| 3 | Deciduous Needleleaf Forests | >60% tree cover, >2m tall, needle leaves, seasonal |
| 4 | Deciduous Broadleaf Forests | >60% tree cover, >2m tall, broad leaves, seasonal |
| 5 | Mixed Forests | Mix of evergreen/deciduous or needleleaf/broadleaf |
| 6 | Closed Shrublands | >60% shrub cover, <2m tall |
| 7 | Open Shrublands | 10-60% shrub cover |
| 8 | Woody Savannas | 30-60% tree cover, herbaceous understory |
| 9 | Savannas | 10-30% tree cover, herbaceous understory |
| 10 | Grasslands | >10% herbaceous cover, <10% tree/shrub |
| 11 | Permanent Wetlands | Permanently inundated with herbaceous/woody veg |
| 12 | Croplands | >60% cultivated |
| 13 | Urban and Built-up Lands | >30% constructed materials |
| 14 | Cropland/Natural Vegetation Mosaics | 30-60% cropland mixed with natural |
| 15 | Permanent Snow and Ice | >60% snow/ice year-round |
| 16 | Barren | >60% bare soil, sand, rocks |
| 17 | Water Bodies | Oceans, lakes, rivers |
| 255 | Unclassified | No data or fill value |

### LC_Type2: UMD (University of Maryland)
**15 classes, simpler vegetation structure**

| Value | Class Name |
|-------|------------|
| 0 | Water Bodies |
| 1 | Evergreen Needleleaf Forests |
| 2 | Evergreen Broadleaf Forests |
| 3 | Deciduous Needleleaf Forests |
| 4 | Deciduous Broadleaf Forests |
| 5 | Mixed Forests |
| 6 | Closed Shrublands |
| 7 | Open Shrublands |
| 8 | Woody Savannas |
| 9 | Savannas |
| 10 | Grasslands |
| 11 | Permanent Wetlands |
| 12 | Croplands |
| 13 | Urban and Built-up |
| 14 | Cropland/Natural Vegetation Mosaics |
| 15 | Non-Vegetated Lands |

### LC_Type3: LAI (Leaf Area Index)
**10 classes based on biome functional types**

| Value | Class Name |
|-------|------------|
| 0 | Water Bodies |
| 1 | Grasslands |
| 2 | Shrublands |
| 3 | Broadleaf Croplands |
| 4 | Savannas |
| 5 | Evergreen Broadleaf Forests |
| 6 | Deciduous Broadleaf Forests |
| 7 | Evergreen Needleleaf Forests |
| 8 | Deciduous Needleleaf Forests |
| 9 | Non-Vegetated Lands |
| 10 | Urban and Built-up Lands |

### LC_Type4: BGC (Net Primary Production)
**8 classes for biogeochemical modeling**

| Value | Class Name |
|-------|------------|
| 0 | Water Bodies |
| 1 | Evergreen Needleleaf Vegetation |
| 2 | Evergreen Broadleaf Vegetation |
| 3 | Deciduous Needleleaf Vegetation |
| 4 | Deciduous Broadleaf Vegetation |
| 5 | Annual Broadleaf Vegetation |
| 6 | Annual Grass Vegetation |
| 7 | Non-Vegetated Lands |

### LC_Type5: PFT (Plant Functional Types)
**11 classes for ecosystem modeling**

| Value | Class Name |
|-------|------------|
| 0 | Water Bodies |
| 1 | Evergreen Needleleaf Trees |
| 2 | Evergreen Broadleaf Trees |
| 3 | Deciduous Needleleaf Trees |
| 4 | Deciduous Broadleaf Trees |
| 5 | Shrubs |
| 6 | Grass |
| 7 | Cereal Croplands |
| 8 | Broadleaf Croplands |
| 9 | Urban and Built-up Lands |
| 10 | Permanent Snow and Ice |
| 11 | Barren |

## Assessment Bands

### LC_Prop1_Assessment, LC_Prop2_Assessment, LC_Prop3_Assessment
**Quality confidence (0-100%)**
- Values represent the percentage confidence in the classification
- Higher values = more confident classification
- Useful for filtering unreliable classifications

### LC_Prop1, LC_Prop2, LC_Prop3
**Sub-pixel proportions**
- Percentage of each land cover type within pixel
- Used for mixed pixels (e.g., 40% forest, 60% grassland)

## Quality Control

### QC Band
**Bit-packed quality flags**
- Bit 0: Mandatory QA (0=good, 1=other)
- Bits 1-3: Land/water flag
- Bits 4-7: Snow/ice flag
- Bits 8-9: Cloud flag

### LW Band
**Land/Water Mask**
- 0 = Shallow ocean
- 1 = Land
- 2 = Ocean coastlines and lake shorelines
- 3 = Shallow inland water
- 4 = Ephemeral water
- 5 = Deep inland water
- 6 = Moderate/continental ocean
- 7 = Deep ocean

## Usage in Analysis

### Recommended Workflow

1. **Choose Classification Scheme**:
   - General ecology → LC_Type1 (IGBP)
   - Simple vegetation → LC_Type2 (UMD)
   - Carbon/NPP modeling → LC_Type4 (BGC)

2. **Query Database**:
   ```python
   import pandas as pd

   # Get IGBP land cover values
   df = pd.read_parquet("pangenome_env_data.parquet")
   lc = df[df['variable'] == 'ee:LC_Type1'][['cluster_id', 'value', 'time']]
   ```

3. **Map Values to Names**:
   ```python
   IGBP_CLASSES = {
       1: "Evergreen Needleleaf Forest",
       2: "Evergreen Broadleaf Forest",
       # ... etc
       17: "Water Bodies"
   }

   lc['land_cover_name'] = lc['value'].map(IGBP_CLASSES)
   ```

4. **Filter by Quality** (optional):
   ```python
   # Get assessment confidence
   qa = df[df['variable'] == 'ee:LC_Prop1_Assessment'][['cluster_id', 'value']]
   qa.rename(columns={'value': 'confidence'}, inplace=True)

   # Join and filter
   lc_filtered = lc.merge(qa, on='cluster_id')
   lc_filtered = lc_filtered[lc_filtered['confidence'] > 70]  # >70% confident
   ```

### Common Analysis Patterns

**Count samples by land cover type:**
```python
lc_counts = lc.groupby('land_cover_name').size()
```

**Identify urban samples:**
```python
urban = lc[lc['value'] == 13]  # IGBP class 13 = Urban
```

**Find forest samples (any type):**
```python
forest_classes = [1, 2, 3, 4, 5]  # All forest types
forests = lc[lc['value'].isin(forest_classes)]
```

**Agricultural samples:**
```python
ag_classes = [12, 14]  # Croplands and Cropland/Natural mosaics
agriculture = lc[lc['value'].isin(ag_classes)]
```

## Notes

- **Multiple schemes available**: Don't need to choose just one - all 5 schemes are retrieved and stored
- **Temporal changes**: Land cover can change year-to-year (urbanization, deforestation, etc.)
- **Resolution matters**: 500m pixels can contain mixed land covers
- **Assessment bands**: Use `LC_Prop*_Assessment` to filter low-confidence classifications

## References

- **Official Documentation**: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1
- **Algorithm Details**: Friedl, M., Sulla-Menashe, D. (2019). MCD12Q1 MODIS/Terra+Aqua Land Cover Type
- **Classification Guide**: https://lpdaac.usgs.gov/products/mcd12q1v061/