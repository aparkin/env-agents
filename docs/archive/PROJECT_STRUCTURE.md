# Environmental Services Framework - Project Structure

**Framework**: env-agents v1.0.0  
**Status**: Production Ready - Clean Organized Structure  
**Last Organized**: September 2024

## 📁 Current Project Organization

```
env-agents/                              # Root directory
├── README.md                           # Executive summary & quick start
├── CLAUDE.md                           # Claude Code project instructions  
├── DEVELOPMENT_SUMMARY.md              # Complete development overview
├── PROJECT_STRUCTURE.md                # This file
├── pyproject.toml                      # Package configuration
├── .gitignore                         # Git ignore patterns
│
├── 📊 notebooks/                      # Demonstration notebooks
│   ├── README.md                      # Notebook usage guide
│   ├── Complete_Environmental_Services_Demo_updated.ipynb  # Main demo (100% operational)
│   ├── Service_Capabilities_Demo.ipynb                    # Capability exploration
│   ├── Real_World_Data_Demonstration_Fixed.ipynb          # Practical examples
│   └── Complete_Environmental_Services_Demo.ipynb         # Legacy demo version
│
├── 📚 docs/                           # Comprehensive documentation  
│   ├── ARCHITECTURE.md                # System design & patterns
│   ├── SERVICES.md                    # All 10 service implementations
│   └── ECOGNITA_INTEGRATION.md        # Agent integration vision
│
├── 🧩 env_agents/                     # Core framework code
│   ├── core/                          # Framework core components
│   │   ├── config.py                  # Configuration management
│   │   ├── router.py                  # Unified routing
│   │   ├── term_broker.py             # Semantic matching
│   │   └── models.py                  # Data models
│   │
│   ├── adapters/                      # Service adapters (10 total)
│   │   ├── base.py                    # Base adapter class
│   │   ├── power/                     # NASA POWER (weather/climate)
│   │   ├── epa_aqs/                   # EPA AQS (US air quality)
│   │   ├── usgs_nwis/                 # USGS NWIS (water information)
│   │   ├── ssurgo/                    # SSURGO (soil survey)  
│   │   ├── soilgrids/                 # SoilGrids (global soils)
│   │   ├── gbif/                      # GBIF (biodiversity)
│   │   ├── wqp/                       # Water Quality Portal
│   │   ├── openaq/                    # OpenAQ (community air quality)
│   │   ├── overpass/                  # Overpass (OpenStreetMap)
│   │   └── earth_engine/              # Google Earth Engine
│   │
│   └── credentials/                   # Credential management
│
├── 🔧 config/                         # Configuration files
│   ├── credentials.yaml.template      # Credential template
│   ├── services.yaml                  # Service configurations
│   └── ecognita-470619-e9e223ea70a7.json  # Earth Engine credentials
│
├── 💾 data/                           # Essential metadata & catalogs
│   └── metadata/                      # Service metadata
│       ├── earth_engine/              # Earth Engine catalog system
│       │   ├── catalog.json           # Full EE catalog (997 assets, 734K lines)
│       │   ├── asset_metadata.json    # Rich asset metadata
│       │   └── asset_discovery.json   # Discovery information
│       └── unified/
│           └── all_services.json      # Cross-service metadata
│
├── 🧪 tests/                          # Test suite
│   ├── README.md                      # Test documentation
│   ├── test_phase_i_integration.py    # Integration tests
│   ├── run_validation_suite.py        # Live service validation
│   ├── unit/                          # Unit tests
│   │   ├── test_metadata_schema.py    # Metadata testing
│   │   └── test_discovery_engine.py   # Discovery testing
│   └── integration/                   # Integration test configs
│
├── 📝 examples/                       # Usage examples
│   ├── README.md                      # Example documentation
│   ├── smoke_router.py                # Basic framework test
│   ├── unified_demo.py                # Comprehensive demo
│   └── service_examples/              # Individual service examples
│
├── 📊 registry/                       # Semantic registry
│   ├── registry_seed.json             # Canonical variables
│   ├── registry_overrides.json        # Accepted mappings  
│   └── registry_delta.json            # Pending mappings
│
├── 🔧 scripts/                        # Operational scripts
│   ├── README.md                      # Script documentation
│   ├── refresh_metadata.py            # Update EE catalog
│   └── setup_credentials.py           # Credential setup
│
├── 🗃️ archive/                        # Organized legacy materials
│   ├── legacy_code/                   # Historical development
│   ├── legacy_tests/                  # Old test files
│   ├── legacy_docs/                   # Development documentation
│   ├── legacy_scripts/                # Diagnostic scripts
│   └── debug_materials/               # Debug sessions
│
├── 🚀 Root Level Utilities            # Production utilities
├── run_tests.py                       # Test suite runner
├── comprehensive_earth_engine_test.py # EE validation script
└── cache/                             # Framework cache (runtime)
```

## 🎯 Key Directory Functions

### 📊 `/notebooks/` - Demonstration & Validation
- **Primary Demo**: `Complete_Environmental_Services_Demo_updated.ipynb` showing 100% operational framework
- **Capability Demo**: `Service_Capabilities_Demo.ipynb` for exploring service capabilities  
- **Practical Examples**: `Real_World_Data_Demonstration_Fixed.ipynb` for real-world usage
- **All notebooks have been moved from root to proper organization**

### 📚 `/docs/` - Comprehensive Documentation
- **Architecture**: Complete system design and implementation patterns
- **Services**: Detailed documentation for all 10 environmental services
- **Integration**: ECOGNITA agent integration vision and roadmap

### 🧩 `/env_agents/` - Core Framework
- **100% Operational**: All 10 service adapters working with standardized patterns
- **Unified Interface**: Consistent adapter pattern across government, research, community, and satellite services
- **Rich Metadata**: Earth Engine-level metadata richness across all sources

### 💾 `/data/` - Essential Metadata System
- **Earth Engine Catalog**: 997 assets with full metadata (734K+ lines)
- **Active System**: Used by framework for asset discovery and metadata enrichment
- **Validated**: Confirmed working with `metadata_manager.get_earth_engine_catalog()`

### 🔧 `/config/` - Configuration Management  
- **Credentials**: Service authentication (API keys, service accounts)
- **Configuration**: Service-specific settings and parameters
- **Earth Engine**: Google Cloud service account credentials properly located

### 🧪 `/tests/` - Production Test Suite
- **Integration Tests**: Full framework testing with live services
- **Unit Tests**: Component-level testing for core functionality
- **Validation Suite**: Real-world service testing and reliability checks

## 🔄 Organizational Improvements Made

### ✅ Consolidation Completed
- **Multiple Legacy Directories**: Consolidated from scattered legacy folders into organized `/archive/` 
- **Notebook Organization**: Moved all notebooks from root to `/notebooks/` directory
- **Config Organization**: Moved credentials to proper `/config/` directory
- **Reference Updates**: Updated all documentation references to new locations

### ✅ Cleanup Completed
- **Duplicate Files**: Removed duplicate credentials and configuration files
- **Empty Directories**: Removed unused cache and temporary directories
- **Legacy Materials**: Organized historical development materials in `/archive/`
- **Clear Structure**: Every directory now has clear purpose and documentation

### ✅ Validation Completed
- **Earth Engine Catalog**: Confirmed 997 assets loaded and accessible
- **Service References**: Updated all code references to new file locations
- **Documentation Accuracy**: All paths and references updated in documentation
- **Production Ready**: Clean, organized structure ready for code review

## 🚀 Code Review Entry Points

### Primary Review Files
1. **`notebooks/Complete_Environmental_Services_Demo_updated.ipynb`** - Framework demonstration
2. **`docs/ARCHITECTURE.md`** - System design and patterns  
3. **`docs/SERVICES.md`** - Service implementation details
4. **`env_agents/`** - Core framework code

### Supporting Materials
- **`DEVELOPMENT_SUMMARY.md`** - Complete development overview
- **`tests/README.md`** - Test suite documentation  
- **`scripts/README.md`** - Operational script documentation
- **`docs/ECOGNITA_INTEGRATION.md`** - Agent integration vision

The env-agents framework now has a clean, well-organized structure that separates active production code from legacy development materials while maintaining comprehensive documentation and clear entry points for code reviewers.