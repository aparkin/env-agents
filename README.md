# env-agents: Environmental Data Integration Framework

**Semantics-centered framework for discovering, fetching, and harmonizing public environmental data via uniform adapters**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

## 🌍 Overview

env-agents provides a **unified API** for accessing diverse environmental data sources through standardized adapters. It returns **analysis-ready datasets** with rich, machine-readable metadata using ontology-aware semantic integration.

**Production Scale**: Successfully integrates 10+ environmental services delivering 100K+ observations per query across soil, air, water, weather, biodiversity, and satellite data.

### ✨ Key Features

- 🔌 **Unified API**: Single interface for 10+ heterogeneous environmental data services
- 🌐 **Production Ready**: Handles enterprise-scale workloads (1M+ observations)
- 📊 **Analysis Ready**: Returns standardized pandas DataFrames with consistent schema
- 🔗 **Semantic Integration**: Ontology-aware variable harmonization across services
- 🛰️ **Multi-Modal Data**: Satellite imagery, sensors, surveys, and model outputs
- ⚡ **Optimized Performance**: Service-specific configurations and intelligent caching

## 🚀 Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/aparkin/env-agents
cd env-agents
pip install -e .
```

### Basic Usage

```python
from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters import CANONICAL_SERVICES

# Define your area of interest
geometry = Geometry(type='bbox', coordinates=[-122.5, 37.6, -122.3, 37.8])
time_range = ("2021-06-01T00:00:00Z", "2021-08-31T23:59:59Z")

# Get water quality data
wqp_adapter = CANONICAL_SERVICES['WQP']()
spec = RequestSpec(geometry=geometry, time_range=time_range)
water_data = wqp_adapter.fetch(spec)

# Get satellite data
ee_adapter = CANONICAL_SERVICES['EARTH_ENGINE'](asset_id="MODIS/061/MOD13Q1")
satellite_data = ee_adapter.fetch(spec)

print(f"Water quality: {len(water_data)} observations")
print(f"Satellite data: {len(satellite_data)} observations")
```

## 📊 Supported Data Sources

| Service | Domain | Data Type | Coverage |
|---------|---------|-----------|----------|
| **WQP** | Water Quality | Measurements | Global |
| **OpenAQ** | Air Quality | Sensor data | Global |
| **EARTH_ENGINE** | Satellite/Climate | Multi-modal | Global |
| **SoilGrids** | Soil Properties | Model predictions | Global |
| **GBIF** | Biodiversity | Species occurrences | Global |
| **NASA_POWER** | Weather/Climate | Model reanalysis | Global |
| **EPA_AQS** | Air Quality | EPA monitoring | US |
| **USGS_NWIS** | Hydrology | Stream/groundwater | US |
| **OSM_Overpass** | Infrastructure | Geographic features | Global |
| **SSURGO** | Soil Survey | Detailed soil maps | US |

## 🔬 Production Example

**Multi-service environmental data fusion** returning nearly 1M observations:

```python
from env_agents.adapters import CANONICAL_SERVICES
from env_agents.core.models import RequestSpec, Geometry
import pandas as pd

# Production-scale data collection
geometry = Geometry(type='bbox', coordinates=[-122.8, 37.2, -121.8, 38.2])
fusion_results = []

for service_name, adapter_class in CANONICAL_SERVICES.items():
    adapter = adapter_class()
    spec = RequestSpec(geometry=geometry, time_range=("2021-01-01", "2021-12-31"))

    result = adapter._fetch_rows(spec)
    if result:
        for row in result:
            row['service'] = service_name
        fusion_results.extend(result)

# Create unified dataset
fusion_df = pd.DataFrame(fusion_results)
print(f"Unified dataset: {fusion_df.shape}")
print(f"Services: {fusion_df['service'].nunique()}")
print(f"Variables: {fusion_df['variable'].nunique()}")
```

**Sample Output**:
```
Unified dataset: (999674, 26)
Services: 15 unique
Variables: 190 environmental parameters
```

## 📚 Documentation

**Complete documentation:** [docs/README.md](docs/README.md)

### Quick Links
- **[Installation Guide](docs/INSTALLATION.md)** - Get env-agents installed and running
- **[Quick Start](docs/QUICK_START.md)** - Your first query in 5 minutes
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Services Guide](docs/SERVICES.md)** - All 16+ data sources and capabilities
- **[Credentials Setup](docs/CREDENTIALS.md)** - Configure API keys

### For Developers
- **[Architecture](docs/development/ARCHITECTURE.md)** - System design and components
- **[Adding New Services](docs/EXTENDING_SERVICES.md)** - Create custom adapters
- **[Local Development](docs/development/LOCAL_DEVELOPMENT.md)** - Development environment

### Production Operations
- **[Pangenome Pipeline](docs/operations/PANGENOME_PIPELINE.md)** - Production data acquisition
- **[Database Management](docs/operations/DATABASE_MANAGEMENT.md)** - Managing data storage
- **[Earth Engine Operations](docs/operations/EARTH_ENGINE_NOTES.md)** - EE-specific guidance

## 🧪 Testing

Run the production test suite:

```bash
# Quick test of all services
python run_tests.py

# Full validation suite
python tests/run_validation_suite.py

# Contract tests
python tests/test_contract.py
```

## 🏗️ Architecture

env-agents uses a **unified adapter pattern** with semantic harmonization:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   env-agents     │    │   Applications  │
│                 │    │                  │    │                 │
│ • WQP           │────│ • Adapters       │────│ • Research      │
│ • Earth Engine  │    │ • Semantics      │    │ • Monitoring    │
│ • SoilGrids     │    │ • Harmonization  │    │ • Analysis      │
│ • OpenAQ        │    │ • Caching        │    │ • Visualization │
│ • ...           │    │ • Validation     │    │ • ML/AI         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components

- **BaseAdapter**: Abstract interface for all data sources
- **RequestSpec**: Unified request specification (geometry, time, variables)
- **Semantic Engine**: Variable harmonization and metadata enrichment
- **Registry System**: Ontology-aware variable mapping

## 🌟 Key Advantages

1. **Unified Interface**: One API for 10+ heterogeneous services
2. **Production Scale**: Handles millions of observations efficiently
3. **Semantic Integration**: Harmonized variables across data sources
4. **Analysis Ready**: Clean, standardized output format
5. **Extensible**: Easy to add new data sources
6. **Robust**: Production-tested with comprehensive error handling

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Development Setup

```bash
git clone https://github.com/aparkin/env-agents
cd env-agents
pip install -e ".[dev]"
pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for environmental research and monitoring applications
- Integrates data from NASA, NOAA, EPA, USGS, and other public agencies
- Designed for the ENIGMA project and broader environmental science community

---

**env-agents** - *Unifying environmental data for science and society*