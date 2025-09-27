# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**env-agents** is a semantics-centered framework for discovering, fetching, and harmonizing public environmental data via uniform adapters. It returns tidy, analysis-ready tables with rich, machine-readable metadata using ontology-aware adapters.

**Version 2.0 Features:**
- Meta-service pattern for systematic asset discovery (Earth Engine: 100+ assets)
- Metadata refresh system with freshness tracking for scraped services
- Rate limiting with exponential backoff for API-constrained services
- Uniform interface for both unitary and meta-services
- Enhanced error handling and type checking throughout the system

## Development Commands

### Installation and Setup
```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install pandas>=2.0 pyarrow>=15 requests>=2.32 pydantic>=2.0 shapely>=2.0
```

### Testing
```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_contract.py
```

### CLI Usage
```bash
# List available adapters
ea list

# Show capabilities for all adapters
ea caps

# Use specific base directory
ea --base-dir /path/to/project caps
```

### Running Examples
```bash
# Run the smoke test example
cd examples/
python smoke_router.py
```

## Architecture

### Core Components

- **EnvRouter** (`core/router.py`): Central orchestration component that registers adapters, manages semantics, and provides unified fetch interface
- **BaseAdapter** (`adapters/base.py`): Abstract base class that all environmental data adapters inherit from
- **TermBroker** (`core/term_broker.py`): Semantic matching engine that maps native parameters to canonical variables
- **RegistryManager** (`core/registry.py`): Manages canonical variable registry and ontology mappings

### Data Flow

1. **Adapter Registration**: Adapters register with EnvRouter via `router.register(adapter)`
2. **Capabilities Discovery**: Call `adapter.capabilities()` or `adapter.harvest()` to discover available variables
3. **Semantic Mapping**: TermBroker maps native parameters to canonical variables using rule packs
4. **Data Fetching**: `router.fetch(dataset, spec)` returns standardized DataFrame with core columns
5. **Metadata Attachment**: Router attaches semantics (URIs, units, conversions) to returned data

### Core Data Model

All adapters return DataFrames with these core columns:
- Identity: `observation_id, dataset, source_url, source_version, license, retrieval_timestamp`
- Spatial: `geometry_type, latitude, longitude, geom_wkt, spatial_id, site_name, admin, elevation_m`  
- Temporal: `time, temporal_coverage`
- Values: `variable, value, unit, depth_top_cm, depth_bottom_cm, qc_flag`
- Metadata: `attributes, provenance`

### Registry System

The registry system (`registry/` directory) manages semantic mappings:
- `registry_seed.json`: Curated canonical variables with URIs and preferred units
- `registry_overrides.json`: Accepted mappings from native to canonical variables
- `registry_delta.json`: Suggested mappings pending review (confidence 0.60-0.89)
- `harvest/`: Auto-harvested catalogs from each adapter

### Semantic Matching

The TermBroker scores mappings (0-1) using multiple signals:
- Exact ID matches from service rule packs: +0.95
- Label hints from service rules: +0.70  
- Generic label matching: +0.10-0.25
- Unit compatibility: +0.01-0.03
- Auto-accepts mappings ≥0.90, suggests 0.60-0.89 for review

## Adapter Development

### Creating New Adapters

1. Inherit from `BaseAdapter` in `adapters/base.py`
2. Set class constants: `DATASET, SOURCE_URL, SOURCE_VERSION, LICENSE`
3. Implement required methods:
   - `capabilities()`: Return metadata about available variables
   - `_fetch_rows()`: Return list of dicts matching core schema
4. Optionally implement `harvest()` for better semantic discovery
5. Add rule pack in `adapters/{service}/rules.py` with mappings and unit aliases

### Adapter Structure

```python
class MyAdapter(BaseAdapter):
    DATASET = "MY_SERVICE"
    SOURCE_URL = "https://api.example.com"
    
    def capabilities(self):
        return {
            "variables": [...],  # List of available parameters
            "attributes_schema": {...},  # Native attribute schema
            "rate_limits": {...}  # API limits if any
        }
    
    def _fetch_rows(self, spec: RequestSpec):
        # Fetch from upstream API
        # Return list of dicts with core column keys
        return [...]
```

### Semantic Integration

Add service-specific rule packs (`adapters/{service}/rules.py`):
```python
CANONICAL_MAP = {
    "native_param_id": "canonical:variable:name"
}

UNIT_ALIASES = {
    "deg C": "degC",
    "cubic feet per second": "ft3/s"
}

LABEL_HINTS = {
    "temperature": ["temp", "temperature", "air_temp"]
}
```

## Important Implementation Notes

- All adapters must return data conforming to the core column schema
- Native parameter traceability is maintained via `attributes["terms"]`
- Observation IDs are computed deterministically from core identifying fields
- Registry refresh should be run periodically to discover new upstream parameters
- High-confidence semantic mappings (≥0.90) are auto-accepted to reduce curation overhead
- The system gracefully handles missing semantics by preserving native variable names

## Registry Management

```python
# Refresh capabilities and update semantic mappings
from env_agents.core.router_ext import refresh_capabilities
report = refresh_capabilities(router, auto_accept_threshold=0.9)

# Review pending mappings
ea list-unknowns

# Promote specific mappings  
ea promote --dataset USGS_NWIS --native 00095 --canonical water:specific_conductance_us_cm
```