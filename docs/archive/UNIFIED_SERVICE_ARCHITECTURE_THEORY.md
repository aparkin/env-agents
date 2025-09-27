# Unified Service Architecture Theory for env-agents

**Version**: 2.1
**Date**: September 21, 2025
**Purpose**: Establish coherent theory for treating meta and unitary services uniformly while respecting scalability constraints

## Overview

This document establishes a unified architectural theory for handling both **unitary services** (single data source) and **meta-services** (multiple assets/datasets) within the env-agents framework. The goal is maximum interface uniformity while respecting the scalability constraint that we cannot treat every asset in meta-services as individual unitary services.

## Core Architectural Principles

### 1. Service Type Classification

**Unitary Services**: Services that provide direct access to a single, coherent dataset
- Examples: NASA_POWER, SoilGrids, OpenAQ, USGS_NWIS
- Characteristics: Fixed variable set, direct parameter access, single API endpoint pattern

**Meta-Services**: Services that provide access to multiple related assets/datasets
- Examples: Google Earth Engine (100+ assets), STAC catalogs, NASA CMR
- Characteristics: Asset discovery required, variable sets depend on selected asset, two-phase access pattern

### 2. Unified Interface Theory

All services, regardless of type, must implement the same core interface while allowing for type-specific optimizations:

```python
class UnifiedServiceInterface:
    def capabilities(self, asset_id: Optional[str] = None, extra: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Unified capabilities interface supporting both service types:

        Unitary Services:
        - asset_id ignored (or can be used for caching optimization)
        - Returns variables directly

        Meta-Services:
        - asset_id=None: Returns asset discovery (assets list)
        - asset_id="specific": Returns variables for that asset
        """

    def fetch(self, spec: RequestSpec) -> pd.DataFrame:
        """
        Unified fetch interface:

        Unitary Services:
        - spec.extra['asset_id'] ignored or used for optimization
        - Variables from spec.variables used directly

        Meta-Services:
        - spec.extra['asset_id'] REQUIRED for data fetching
        - Variables from spec.variables filtered against asset capabilities
        """
```

### 3. Scalability Strategy for Meta-Services

#### Problem Statement
Meta-services like Earth Engine contain 100+ assets. Creating individual adapters for each asset would:
- Create configuration explosion (100+ service registrations)
- Overwhelm discovery interfaces
- Violate DRY principles (duplicate Earth Engine logic)
- Make semantic mapping unmanageable

#### Solution: Layered Asset Management

**Layer 1: Service-Level Registration**
```python
# Single registration per meta-service
router.register(EarthEngineAdapter())  # Handles ALL Earth Engine assets
```

**Layer 2: Asset Discovery**
```python
# Discover available assets through service capabilities
ee_caps = earth_engine_adapter.capabilities()  # Returns asset list
asset_list = ee_caps['assets']  # Climate, imagery, landcover categories with examples
```

**Layer 3: Asset-Specific Operations**
```python
# Create asset-specific request without new adapter registration
spec = RequestSpec(
    geometry=point,
    time_range=time_range,
    variables=['temperature'],
    extra={'asset_id': 'MODIS/061/MOD11A1'}  # Specify asset in request
)
df = router.fetch('EARTH_ENGINE', spec)  # Single service handles asset-specific logic
```

### 4. Uniform Response Architecture

Both service types must return structurally compatible capability responses:

#### Unitary Service Response Pattern
```python
{
    "dataset": "NASA_POWER",
    "service_type": "unitary",
    "variables": [
        {"canonical": "climate:temperature", "name": "Temperature at 2m", ...},
        {"canonical": "climate:precipitation", "name": "Precipitation", ...}
    ],
    "temporal_coverage": {...},
    "spatial_coverage": {...},
    "metadata_freshness": {...}
}
```

#### Meta-Service Discovery Response Pattern
```python
{
    "dataset": "EARTH_ENGINE",
    "service_type": "meta",
    "assets": [
        {"asset_id": "MODIS/061/MOD11A1", "category": "climate", "title": "MODIS LST", ...},
        {"asset_id": "LANDSAT/LC08/C02/T1_L2", "category": "imagery", "title": "Landsat 8", ...}
    ],
    "total_assets": 150,
    "asset_categories": {
        "climate": {"count": 50, "examples": [...]},
        "imagery": {"count": 75, "examples": [...]}
    },
    "discovery_methods": [...],
    "metadata_freshness": {...}
}
```

#### Meta-Service Asset-Specific Response Pattern
```python
{
    "dataset": "EARTH_ENGINE",
    "service_type": "meta",
    "asset_id": "MODIS/061/MOD11A1",
    "variables": [
        {"canonical": "earth_engine:LST_Day_1km", "name": "Land Surface Temperature Day", ...},
        {"canonical": "earth_engine:LST_Night_1km", "name": "Land Surface Temperature Night", ...}
    ],
    "temporal_coverage": {...},
    "spatial_coverage": {...},
    "metadata_freshness": {...}
}
```

## Implementation Patterns

### 1. Adapter Base Class Enhancement

```python
class BaseAdapter(ABC):
    SERVICE_TYPE: str = "unitary"  # or "meta"

    def capabilities(self, asset_id: Optional[str] = None, extra: Optional[Dict] = None) -> Dict[str, Any]:
        """Unified capabilities interface"""
        if self.SERVICE_TYPE == "unitary":
            return self._get_unitary_capabilities(extra)
        elif self.SERVICE_TYPE == "meta":
            if asset_id:
                return self._get_asset_capabilities(asset_id, extra)
            else:
                return self._get_asset_discovery(extra)

    def _create_uniform_response(self, service_type: str, **kwargs) -> Dict[str, Any]:
        """Create standardized response with metadata freshness"""
        base_response = {
            "dataset": self.DATASET,
            "service_type": service_type,
            "metadata_freshness": self._get_metadata_freshness(),
            "source_url": self.SOURCE_URL,
            "license": self.LICENSE,
            "response_timestamp": datetime.now().isoformat()
        }
        base_response.update(kwargs)
        return base_response

    @abstractmethod
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Unified fetch implementation - must handle asset_id for meta-services"""
        pass
```

### 2. Router Integration Pattern

```python
class SimpleEnvRouter:
    def discover(self, include_assets: bool = False) -> List[Dict[str, Any]]:
        """Unified discovery across all service types"""
        discovery_results = []

        for service_name, adapter in self.adapters.items():
            caps = adapter.capabilities()

            if caps.get("service_type") == "unitary":
                discovery_results.append({
                    "service": service_name,
                    "type": "unitary",
                    "variable_count": len(caps.get("variables", [])),
                    "description": caps.get("description", "")
                })

            elif caps.get("service_type") == "meta":
                discovery_results.append({
                    "service": service_name,
                    "type": "meta",
                    "asset_count": caps.get("total_assets", 0),
                    "description": caps.get("description", ""),
                    "categories": list(caps.get("asset_categories", {}).keys())
                })

                # Optionally expand assets for detailed discovery
                if include_assets:
                    for asset in caps.get("assets", []):
                        discovery_results.append({
                            "service": service_name,
                            "type": "meta_asset",
                            "asset_id": asset["asset_id"],
                            "asset_title": asset["title"],
                            "category": asset["category"]
                        })

        return discovery_results

    def fetch(self, dataset: str, spec: RequestSpec) -> pd.DataFrame:
        """Unified fetch handling both service types"""
        adapter = self.adapters.get(dataset)
        if not adapter:
            raise ValueError(f"Unknown dataset: {dataset}")

        # For meta-services, validate asset_id is provided
        if adapter.SERVICE_TYPE == "meta" and not spec.extra.get("asset_id"):
            raise ValueError(f"Meta-service {dataset} requires asset_id in spec.extra")

        # Execute fetch with unified error handling
        rows = adapter._fetch_rows(spec)
        return pd.DataFrame(rows)
```

### 3. Testing Framework Integration

```python
def test_unified_service_interface():
    """Test both unitary and meta-services through unified interface"""

    for service_name, adapter_class in CANONICAL_SERVICES.items():
        adapter = adapter_class()

        # Test basic capabilities
        caps = adapter.capabilities()
        assert "service_type" in caps
        assert caps["service_type"] in ["unitary", "meta"]

        if caps["service_type"] == "unitary":
            assert "variables" in caps
            assert len(caps["variables"]) > 0

        elif caps["service_type"] == "meta":
            assert "assets" in caps or "asset_categories" in caps

            # Test asset-specific capabilities if assets available
            if caps.get("assets"):
                first_asset = caps["assets"][0]
                asset_caps = adapter.capabilities(asset_id=first_asset["asset_id"])
                assert "variables" in asset_caps
                assert asset_caps["asset_id"] == first_asset["asset_id"]
```

## Benefits of This Architecture

### 1. Interface Consistency
- All services use identical `capabilities()` and `fetch()` methods
- Uniform response structures with predictable fields
- Consistent error handling and metadata patterns

### 2. Scalability Management
- Meta-services remain manageable with category-based organization
- Asset discovery prevents capability explosion
- Single registration per meta-service, not per asset

### 3. Semantic Integration
- TermBroker can handle both direct variables (unitary) and asset-scoped variables (meta)
- Registry system scales to handle asset-specific semantic mappings
- Uniform canonical variable naming across service types

### 4. ECOGNITA Integration Ready
- ECOGNITA agents can use identical patterns for both service types
- Asset selection for meta-services can be handled in agent conversation flow
- Uniform asset creation patterns regardless of service type

## Migration Path

### Phase 1: Interface Standardization
1. Add `SERVICE_TYPE` constants to all adapters
2. Standardize `capabilities()` responses with `service_type` field
3. Ensure all responses include `metadata_freshness`

### Phase 2: Meta-Service Pattern Implementation
1. Implement asset discovery for Earth Engine
2. Add asset-specific capabilities handling
3. Update fetch logic to handle `asset_id` in request specs

### Phase 3: Router Enhancement
1. Update router discovery to handle both service types
2. Add validation for meta-service asset requirements
3. Enhance error handling for asset-specific operations

### Phase 4: Testing Integration
1. Extend testing notebook to validate unified interface
2. Add meta-service specific test patterns
3. Validate scalability with asset discovery testing

This unified architecture theory provides a coherent framework for handling both unitary and meta-services while maintaining interface consistency and respecting scalability constraints. The pattern is extensible to future meta-services like STAC catalogs and NASA CMR while preserving the simplicity needed for straightforward unitary services.