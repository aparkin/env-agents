# Canonical Environmental Services

This document defines the canonical set of environmental data services after Phase 1 normalization.

## Standard Services (10 Services)

| Service | Adapter Class | Location | Auth Required | Domain |
|---------|---------------|----------|---------------|--------|
| **NASA_POWER** | NASAPOWEREnhancedAdapter | `power/adapter.py` | No | Climate/Weather |
| **SoilGrids** | EnhancedSoilGridsAdapter | `soil/adapter.py` | No | Soil Properties |
| **OpenAQ** | OpenaqV3Adapter | `openaq/adapter.py` | API Key | Air Quality |
| **GBIF** | EnhancedGBIFAdapter | `gbif/adapter.py` | No | Biodiversity |
| **WQP** | EnhancedWQPAdapter | `wqp/adapter.py` | No | Water Quality |
| **OSM_Overpass** | EnhancedOverpassAdapter | `overpass/adapter.py` | No | Geospatial Features |
| **EPA_AQS** | EPAAQSEnhancedAdapter | `air/adapter.py` | API Key | EPA Air Monitoring |
| **USGS_NWIS** | USGSNWISEnhancedAdapter | `nwis/adapter.py` | No | USGS Water Data |
| **SSURGO** | EnhancedSSURGOAdapter | `ssurgo/adapter.py` | No | NRCS Soil Data |

## Meta-Services (1 Service)

| Service | Adapter Class | Location | Auth Required | Assets |
|---------|---------------|----------|---------------|--------|
| **EARTH_ENGINE** | EarthEngineGoldStandardAdapter | `earth_engine/gold_standard_adapter.py` | Service Account | 900+ Earth Engine assets |

## Directory Structure Standard

All services follow the pattern: `env_agents/adapters/{service_name}/adapter.py`

## Deprecated Services (Archived)

The following services have been moved to `archive/deprecated/adapters/`:

### Stub Services (Backburner)
- `appeears.py` (NasaAppeearsAdapter)
- `firms.py` (NasaFirmsAdapter)
- `cropscape.py` (UsdaCropscapeAdapter)
- `eia_camd_tri.py` (UsEnergyEmissionsAdapter)
- `energy/` (EIA services - backburner)

### Duplicate/Legacy Services (Replaced by Enhanced Versions)
- `surgo_adapter.py` (UsdaSurgoAdapter) → replaced by EnhancedSSURGOAdapter
- `aqs_adapter.py` (EPAAQSAdapter) → replaced by EPAAQSEnhancedAdapter
- `aqs.py` (EpaAqsV3Adapter) → replaced by EPAAQSEnhancedAdapter
- `gbif.py` (GbifAdapter) → replaced by EnhancedGBIFAdapter
- `wqp.py` (UsgsWqpAdapter) → replaced by EnhancedWQPAdapter
- `overpass.py` (OsmOverpassAdapter) → replaced by EnhancedOverpassAdapter
- `soilgrids_adapter.py` (IsricSoilGridsAdapter) → replaced by EnhancedSoilGridsAdapter
- `adapter_enhanced_backup.py` (EnhancedOpenAQAdapter) → replaced by OpenaqV3Adapter

## Usage with SimpleEnvRouter

```python
from env_agents.core.simple_router import SimpleEnvRouter
from env_agents.adapters.power.adapter import NASAPOWEREnhancedAdapter
from env_agents.adapters.soil.adapter import EnhancedSoilGridsAdapter
# ... import other canonical adapters

router = SimpleEnvRouter(base_dir=".")
router.register(NASAPOWEREnhancedAdapter())
router.register(EnhancedSoilGridsAdapter())
# ... register other services

# Unified interface: discover(), fetch()
services = router.discover()  # ['NASA_POWER_Enhanced', 'SoilGrids_Enhanced', ...]
```

## Next Phases

- **Phase 2**: Authentication abstraction and configuration standardization
- **Phase 3**: Interface standardization and enhanced testing

---

*Updated: Phase 1 Normalization Complete*