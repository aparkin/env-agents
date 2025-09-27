# SoilGrids WCS Integration Plan

**Date**: September 21, 2025
**Priority**: CRITICAL (Phase 1, Week 1)
**Status**: Ready for Implementation

## Overview

Integration of working WCS-based SoilGrids code into env-agents framework to resolve the critical reliability crisis. The working code uses Web Coverage Service (WCS) instead of the failing REST API and includes sophisticated guard rails for response size management.

## Current Problem Analysis

### **Failing REST API Approach** (current env-agents)
```python
# Consistently fails with 500 server errors
SOURCE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
response = session.get(self.SOURCE_URL, params=params, timeout=60)
# Results in: SoilGrids error on attempt 1: 500 Internal Server Error
```

### **Working WCS Approach** (user's code)
```python
# Robust WCS endpoint designed for spatial data access
base = f"https://maps.isric.org/mapserv?map=/map/{prop}.map"
params = {"service": "WCS", "version": "2.0.1", "request": "GetCoverage", ...}
# Results in: Reliable TIFF raster data retrieval
```

## Integration Architecture

### **1. Core Adapter Replacement**

**Replace**: `env_agents/adapters/soil/adapter.py`
**With**: WCS-based implementation using working code patterns

**Key Changes**:
- **Endpoint Change**: REST API → WCS mapserver
- **Request Format**: JSON params → WCS GetCoverage requests
- **Response Format**: JSON points → TIFF raster coverage
- **Discovery Method**: Static metadata → Dynamic WCS GetCapabilities

### **2. Guard Rails Implementation**

The working code provides excellent response size management:

```python
class SoilGridsWCSAdapter(BaseAdapter, StandardAdapterMixin):
    def __init__(self):
        super().__init__()
        # Circuit breaker for service failures
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=300)

        # Response size limits
        self.max_pixels_default = 1_000_000  # Conservative for env-agents
        self.max_native_pixels = 2_500_000   # For tiling decisions
        self.native_resolution = 0.00225     # SoilGrids native resolution

        # Catalog caching
        self.catalog_cache = None
        self.catalog_timestamp = None
        self.catalog_max_age = 24 * 3600  # 24 hours

    def _get_guard_rail_limits(self, spec: RequestSpec) -> Dict[str, Any]:
        """Calculate appropriate limits based on request"""
        # Extract bbox from geometry
        if spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
            # Use small buffer for point requests
            buffer = 0.01  # ~1km at equator
            bbox = (lon - buffer, lat - buffer, lon + buffer, lat + buffer)
        elif spec.geometry.type == "bbox":
            bbox = tuple(spec.geometry.coordinates)
        else:
            raise ValueError(f"Unsupported geometry type: {spec.geometry.type}")

        # Calculate native pixel count
        minx, miny, maxx, maxy = bbox
        dx, dy = maxx - minx, maxy - miny
        native_pixels = (dx / self.native_resolution) * (dy / self.native_resolution)

        # Determine strategy
        if native_pixels <= self.max_pixels_default:
            return {
                "strategy": "direct",
                "bbox": bbox,
                "tiling": False,
                "resolution": "native"
            }
        elif native_pixels <= self.max_native_pixels:
            return {
                "strategy": "resampled",
                "bbox": bbox,
                "tiling": False,
                "resolution": "auto",
                "target_pixels": self.max_pixels_default
            }
        else:
            return {
                "strategy": "tiled",
                "bbox": bbox,
                "tiling": True,
                "tiles": self._tile_bbox_native(bbox, self.max_native_pixels),
                "resolution": "native"
            }
```

### **3. Metadata Enhancement**

**Current env-agents metadata** (basic):
```python
# Limited metadata with basic descriptions
enhanced_props = [
    {
        "id": "clay",
        "name": "Clay content",
        "description": "Fine mineral particles (<0.002 mm diameter)",
        "unit": "% (mass fraction)"
    }
]
```

**Working code metadata** (comprehensive):
```python
# Rich metadata with agricultural context
SOILGRIDS_METADATA = {
    "clay": {
        "name": "Clay content (<2 µm) mass fraction",
        "units": "%",
        "description": "Mass fraction of clay-sized particles.",
        "depths": ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"],
        "statistics": ["mean", "Q0.05", "Q0.5", "Q0.95", "uncertainty"],
        # Plus agricultural/pedological context from current env-agents
        "pedological_significance": "Controls soil structure formation, swelling/shrinking behavior...",
        "agricultural_applications": ["Irrigation scheduling", "Tillage timing", ...]
    }
}
```

**Integration Strategy**: Combine both for maximum richness
- Use working code's comprehensive base metadata
- Preserve env-agents' agricultural/pedological context
- Add WRB soil classification with enhanced profiles

### **4. Catalog Discovery Integration**

**Current approach**: Static metadata
**Working approach**: Dynamic WCS discovery

```python
def _refresh_metadata(self, metadata_type: str = "capabilities", force_refresh: bool = False):
    """Enhanced metadata refresh using WCS GetCapabilities"""

    if not force_refresh and self._is_catalog_fresh():
        return {"refreshed": False, "method": "cache_hit"}

    try:
        # Discover available coverages using WCS
        catalog = {}
        for prop in SOILGRIDS_SERVICES_ALL:
            coverages = self._get_coverages_for_property(prop)
            catalog[prop] = coverages

        # Cache the catalog
        self.catalog_cache = catalog
        self.catalog_timestamp = datetime.now()

        return {
            "refreshed": True,
            "method": "wcs_discovery",
            "items_count": sum(len(v) for v in catalog.values()),
            "timestamp": self.catalog_timestamp,
            "errors": []
        }

    except Exception as e:
        return {
            "refreshed": False,
            "method": "failed",
            "errors": [str(e)]
        }

def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Enhanced capabilities with dynamic discovery"""

    # Ensure fresh catalog
    refresh_result = self._refresh_metadata()

    # Build variables list from catalog and metadata
    variables = []
    catalog = self.catalog_cache or {}

    for prop, metadata in SOILGRIDS_METADATA.items():
        if prop not in catalog:
            continue

        # Create variable entries for each depth/statistic combination
        if prop == "wrb":
            # Categorical WRB soil classification
            variables.append({
                "canonical": f"soil:wrb",
                "platform_native": prop,
                "name": metadata["name"],
                "description": metadata["description"],
                "unit": "categorical",
                "data_type": "categorical",
                "categories": WRB_CLASSES,
                "coverages_available": len(catalog[prop])
            })
        else:
            # Numeric soil properties
            for depth in metadata.get("depths", []):
                for stat in metadata.get("statistics", []):
                    variables.append({
                        "canonical": f"soil:{prop}",
                        "platform_native": prop,
                        "name": f"{metadata['name']} ({depth}, {stat})",
                        "description": metadata["description"],
                        "unit": metadata["units"],
                        "depth_range": depth,
                        "statistic": stat,
                        "data_type": "numeric"
                    })

    return self._create_uniform_response(
        service_type="unitary",
        variables=variables,
        spatial_coverage={
            "extent": "Global (excluding Antarctica)",
            "resolution": "250m native, configurable resampling",
            "coordinate_system": "WGS84 (EPSG:4326)"
        },
        temporal_coverage={
            "reference_period": "2020-05-18 (model snapshot)",
            "update_frequency": "Static global maps"
        },
        discovery_method="wcs_getcapabilities",
        catalog_freshness=refresh_result
    )
```

### **5. Data Fetching Integration**

**Adapt working `get_soilgrids_data()` for env-agents `_fetch_rows()`**:

```python
def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
    """Fetch SoilGrids data using WCS with guard rails"""

    try:
        # Circuit breaker check
        if self.circuit_breaker.is_open:
            return self._fetch_from_cache(spec)

        with self.circuit_breaker:
            # Get guard rail limits
            limits = self._get_guard_rail_limits(spec)

            # Apply variable filtering
            requested_props = self._map_variables_to_properties(spec.variables)

            # Execute WCS-based data retrieval
            if limits["strategy"] == "direct":
                df = self._fetch_direct_wcs(limits["bbox"], requested_props, limits)
            elif limits["strategy"] == "resampled":
                df = self._fetch_resampled_wcs(limits["bbox"], requested_props, limits)
            elif limits["strategy"] == "tiled":
                df = self._fetch_tiled_wcs(limits["tiles"], requested_props, limits)

            # Transform to env-agents core schema
            return self._transform_to_core_schema(df, spec)

    except CircuitBreakerOpen:
        return self._fetch_from_cache(spec)
    except Exception as e:
        logger.error(f"SoilGrids WCS fetch failed: {e}")
        return []

def _fetch_direct_wcs(self, bbox: Tuple[float, float, float, float],
                     properties: List[str], limits: Dict) -> pd.DataFrame:
    """Direct WCS fetch using working code patterns"""

    # Get catalog for coverage discovery
    catalog = self.catalog_cache or {}

    # Build coverage list
    coverage_pairs = []
    for prop in properties:
        if prop in catalog:
            for coverage_id in catalog[prop]:
                coverage_pairs.append((prop, coverage_id))

    # Fetch coverages using working code pattern
    dfs = []
    for prop, coverage_id in coverage_pairs:
        try:
            df = self._fetch_coverage_to_df(prop, coverage_id, bbox, scalesize=None)
            if df is not None:
                dfs.append(df)
        except Exception as e:
            logger.warning(f"Coverage {prop}:{coverage_id} failed: {e}")
            continue

    if not dfs:
        return pd.DataFrame()

    # Combine all coverages
    result = pd.concat(dfs, ignore_index=True)
    result.attrs["soilgrids_metadata"] = SOILGRIDS_METADATA
    result.attrs["catalog"] = catalog

    return result

def _transform_to_core_schema(self, df: pd.DataFrame, spec: RequestSpec) -> List[Dict[str, Any]]:
    """Transform WCS DataFrame to env-agents core schema"""

    if df.empty:
        return []

    rows = []
    retrieval_timestamp = datetime.now(timezone.utc).isoformat()

    for _, row in df.iterrows():
        # Extract depth information
        depth_top_cm = row.get("top_depth")
        depth_bottom_cm = row.get("bottom_depth")

        # Map to canonical variable
        canonical_var = f"soil:{row['parameter']}"
        if row['parameter'] == 'wrb':
            canonical_var = "soil:wrb_classification"

        # Build core schema row
        core_row = {
            # Identity columns
            "observation_id": f"soilgrids_wcs_{row['latitude']:.6f}_{row['longitude']:.6f}_{row['parameter']}_{row.get('statistic', 'value')}",
            "dataset": self.DATASET,
            "source_url": "https://maps.isric.org/mapserv",
            "source_version": "v2.0_wcs",
            "license": self.LICENSE,
            "retrieval_timestamp": retrieval_timestamp,

            # Spatial columns
            "geometry_type": "point",
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "geom_wkt": f"POINT({row['longitude']} {row['latitude']})",
            "spatial_id": None,
            "site_name": f"SoilGrids location {row['latitude']:.4f}, {row['longitude']:.4f}",
            "admin": None,
            "elevation_m": None,

            # Temporal columns
            "time": row.get("date"),
            "temporal_coverage": "2020-snapshot",

            # Value columns
            "variable": canonical_var,
            "value": float(row["value"]),
            "unit": row.get("unit", ""),
            "depth_top_cm": depth_top_cm,
            "depth_bottom_cm": depth_bottom_cm,
            "qc_flag": "ok",

            # Metadata columns
            "attributes": {
                "parameter": row["parameter"],
                "statistic": row.get("statistic"),
                "coverage_id": row.get("coverageid"),
                "description": row.get("description"),
                "depth_units": row.get("depth_units"),
                "wcs_method": "getcoverage",
                "terms": {
                    "native_id": row["parameter"],
                    "canonical_variable": canonical_var,
                    "mapping_confidence": 0.95
                }
            },
            "provenance": {
                "data_source": "ISRIC SoilGrids v2.0",
                "method": "WCS GetCoverage",
                "api_endpoint": "https://maps.isric.org/mapserv",
                "coverage_id": row.get("coverageid"),
                "retrieval_timestamp": retrieval_timestamp
            }
        }

        rows.append(core_row)

    return rows
```

## Implementation Timeline

### **Week 1: Critical Integration**
- **Day 1**: Implement WCS-based adapter core with guard rails
- **Day 2**: Integrate catalog discovery and metadata enhancement
- **Day 3**: Add circuit breaker and fallback caching
- **Day 4**: Transform data to core schema format
- **Day 5**: Integration testing and validation

### **Success Criteria**
- [ ] **SoilGrids Success Rate**: >80% (from current ~0%)
- [ ] **Response Size Control**: No responses >1M pixels without explicit override
- [ ] **Metadata Richness**: 14 soil properties + WRB classification
- [ ] **Error Recovery**: Circuit breaker prevents cascading failures
- [ ] **Schema Compliance**: 100% core column compliance

## Risk Mitigation

### **High-Risk Scenarios**
1. **WCS Service Instability**: Implement aggressive caching with local fallback data
2. **Large Response Memory Issues**: Enforce strict pixel limits with automatic tiling
3. **Coverage Discovery Failures**: Cache catalog with graceful degradation

### **Fallback Strategies**
1. **Service Failures**: Circuit breaker opens → cached data with staleness indicators
2. **Large Requests**: Automatic tiling → multiple smaller WCS requests
3. **Memory Constraints**: Resolution downsampling → maintains spatial coverage

This integration plan transforms the failing SoilGrids adapter into a robust, production-ready service by leveraging the working WCS approach with comprehensive guard rails and enhanced metadata.