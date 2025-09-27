# Environmental Data Adapter Naming Standards

## Class Naming Convention

**Pattern**: `{Service}Adapter`
- Simple, consistent pattern
- No "Enhanced" or version numbers in class names
- CamelCase with service name first

### Proposed Standardized Class Names:

| Current Class Name | Standardized Class Name | Rationale |
|-------------------|------------------------|-----------|
| `NASAPOWEREnhancedAdapter` | `NASAPowerAdapter` | Remove "Enhanced", normalize case |
| `EnhancedSoilGridsAdapter` | `SoilGridsAdapter` | Remove "Enhanced" prefix |
| `OpenaqV3Adapter` | `OpenAQAdapter` | Remove version, normalize case |
| `EnhancedGBIFAdapter` | `GBIFAdapter` | Remove "Enhanced" prefix |
| `EnhancedWQPAdapter` | `WQPAdapter` | Remove "Enhanced" prefix |
| `EnhancedOverpassAdapter` | `OverpassAdapter` | Remove "Enhanced" prefix |
| `EPAAQSEnhancedAdapter` | `EPAAQSAdapter` | Remove "Enhanced" suffix |
| `USGSNWISEnhancedAdapter` | `USGSNWISAdapter` | Remove "Enhanced" suffix |
| `EnhancedSSURGOAdapter` | `SSURGOAdapter` | Remove "Enhanced" prefix |
| `EarthEngineGoldStandardAdapter` | `EarthEngineAdapter` | Remove "GoldStandard" |

## DATASET Constant Convention

**Pattern**: `{SERVICE_NAME}` (no suffixes)
- Clean service identifiers
- Match configuration keys
- No version numbers or qualifiers

### Proposed Standardized DATASET Values:

| Current DATASET | Standardized DATASET | Rationale |
|----------------|---------------------|-----------|
| `NASA_POWER_Enhanced` | `NASA_POWER` | Remove Enhanced suffix |
| `SoilGrids_Enhanced` | `SoilGrids` | Remove Enhanced suffix |
| `OpenAQ` | `OpenAQ` | Already clean |
| `GBIF_Enhanced` | `GBIF` | Remove Enhanced suffix |
| `WQP_Enhanced` | `WQP` | Remove Enhanced suffix |
| `OSM_Overpass_Enhanced` | `OSM_Overpass` | Remove Enhanced suffix |
| `EPA_AQS_Enhanced` | `EPA_AQS` | Remove Enhanced suffix |
| `USGS_NWIS_Enhanced` | `USGS_NWIS` | Remove Enhanced suffix |
| `SSURGO_Enhanced` | `SSURGO` | Remove Enhanced suffix |
| `EARTH_ENGINE_GOLD` | `EARTH_ENGINE` | Remove Gold suffix |

## Import Alias Convention

**Pattern**: Keep descriptive aliases for backward compatibility
- Import aliases can remain descriptive
- Class names become clean and standard
- Service IDs match DATASET constants

### Example:
```python
from .power.adapter import NASAPowerAdapter as NASA_POWER
from .soil.adapter import SoilGridsAdapter as SoilGrids
```

## Benefits of Standardization

1. **Consistency**: All adapters follow same naming pattern
2. **Clarity**: Class names clearly indicate their purpose
3. **Configuration Alignment**: DATASET constants match config keys
4. **Maintainability**: No confusion about "Enhanced" vs regular versions
5. **API Clarity**: Service IDs are clean and consistent

## Implementation Strategy

1. **Phase 2A**: Rename class names and update imports
2. **Phase 2B**: Update DATASET constants
3. **Phase 2C**: Update configuration references
4. **Phase 2D**: Test functionality after each change

This ensures we maintain functionality while achieving clean naming standards.