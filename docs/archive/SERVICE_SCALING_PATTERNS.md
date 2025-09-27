# Service Scaling Patterns

This document describes proven patterns for handling large-scale environmental services that don't fit standard adapter assumptions.

## Overview

The env-agents framework supports three service patterns:
1. **Standard Services**: Fixed variable sets (most services)
2. **Dynamic Services**: Large variable catalogs requiring caching
3. **Meta-Services**: Multiple datasets requiring context-efficient discovery

## Pattern 1: Dynamic Service Caching (WQP Example)

### Problem
Services like Water Quality Portal (WQP) have 1000+ variables that change over time and are too numerous to hardcode.

### Solution: Layered Fallback Caching

```python
def fetch_external_catalog(self) -> List[Dict[str, Any]]:
    """
    Layered fallback strategy for dynamic variable discovery:
    1. Check local cache first
    2. Download and cache if missing 
    3. Fall back to enhanced hardcoded list if download fails
    """
    
    # Strategy 1: Try cached file first
    cache_file = project_root / "env_agents/data/metadata/services/catalog.zip"
    if cache_file.exists():
        return load_from_cache(cache_file)
    
    # Strategy 2: Download and cache
    try:
        data = download_from_official_source()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        save_to_cache(cache_file, data)
        return data
    except Exception:
        return []  # Triggers enhanced parameter fallback
```

### Implementation Details

**Cache Location**: `env_agents/data/metadata/services/`
- Organized by service name
- Version-controlled alongside code
- Persistent across installations

**Fallback Hierarchy**:
1. **Cache**: Instant loading from local file
2. **Download**: Official source with caching
3. **Enhanced**: Curated high-quality subset 
4. **Minimal**: Basic functionality only

### Benefits
- ✅ **Fast**: Cache provides instant access to full catalog
- ✅ **Current**: Downloads latest when cache missing
- ✅ **Reliable**: Multiple fallback levels ensure service always works
- ✅ **Offline**: Works without internet after initial cache

### WQP Results
- **Before**: 8 hardcoded parameters
- **After**: 22,736 EPA characteristics (8 enhanced + 22,728 EPA)
- **Performance**: Instant loading from cache, graceful degradation

## Pattern 2: Meta-Service Context Management (Earth Engine Example)

### Problem  
Meta-services like Earth Engine provide 900+ individual datasets. Returning all assets in `capabilities()` would:
- Consume massive context (>50KB)
- Slow response times
- Overwhelm users with information

### Solution: Summary Capabilities with Hierarchical Discovery

```python
def capabilities(self) -> Dict[str, Any]:
    return {
        "service_type": "meta",
        "total_asset_count": 900,
        "scaling_strategy": "summary_capabilities",
        "assets": {
            "climate": {
                "count": 200,
                "description": "Weather, temperature, precipitation data",
                "examples": [
                    {"id": "MODIS/061/MOD11A1", "name": "MODIS Temperature"},
                    {"id": "ECMWF/ERA5_LAND/DAILY_AGGR", "name": "ERA5 Reanalysis"}
                ],
                "popular_datasets": ["MODIS temperature", "ERA5", "GPM precipitation"]
            }
            # ... more categories
        },
        "usage_pattern": {
            "step_1": "Choose category from 'assets'",
            "step_2": "Select asset_id from examples", 
            "step_3": "Use RequestSpec with extra={'asset_id': 'asset_id'}"
        }
    }
```

### Contract Compliance
Updated contract tests support both meta-service formats:
- **List format**: `"assets": [...]` (smaller meta-services)
- **Dictionary format**: `"assets": {...}` (large-scale meta-services)

### Implementation Strategy

**Context Efficiency**:
- Return 5 categories instead of 900 assets
- 3 examples per category (total: 15 assets shown)
- Clear discovery instructions

**Hierarchical Structure**:
```
assets/
├── climate/          (200 datasets)
├── imagery/          (400 datasets) 
├── landcover/        (150 datasets)
├── elevation/        (50 datasets)
└── environmental/    (100 datasets)
```

**Usage Flow**:
1. User calls `adapter.capabilities()` → sees categories
2. User selects category (e.g., "climate")
3. User picks example asset_id (e.g., "MODIS/061/MOD11A1") 
4. User calls `adapter.fetch(spec, extra={"asset_id": "MODIS/061/MOD11A1"})`

### Benefits
- ✅ **Context-efficient**: 5 categories vs 900 individual assets
- ✅ **Informative**: Rich category descriptions and examples
- ✅ **Discoverable**: Clear usage patterns and popular datasets
- ✅ **Scalable**: Pattern works for any size meta-service

### Earth Engine Results
- **Before**: 0 variables (contract violation)
- **After**: 5 categories with 900 total assets
- **Context**: ~2KB response vs ~50KB if all assets returned

## Pattern 3: Hybrid Approaches

### When to Combine Patterns

Some services may benefit from combining both approaches:

**Large Meta-Service with Dynamic Catalogs**:
```python
# Example: NASA Data Portal with 100+ missions, each with 1000+ variables
{
    "service_type": "meta",
    "assets": {
        "earth_observation": {
            "missions": ["MODIS", "VIIRS", "Landsat"],
            "catalog_cache": "env_agents/data/metadata/services/nasa_earth_obs.json",
            "discovery_method": "cached_hierarchical"
        }
    }
}
```

## Implementation Guidelines

### For New Services

**1. Assess Service Scale**:
- **< 50 variables**: Standard service pattern
- **50-1000 variables**: Consider dynamic caching
- **> 1000 variables or multiple datasets**: Consider meta-service pattern

**2. Choose Pattern**:
- **Fixed variables**: Standard service
- **Large variable catalog**: Dynamic service with caching
- **Multiple datasets**: Meta-service with summary capabilities
- **Both**: Hybrid approach

**3. Implementation Checklist**:
- [ ] Define SERVICE_TYPE constant
- [ ] Implement appropriate capabilities() structure
- [ ] Add caching if needed (layered fallback)
- [ ] Update contract tests if new pattern
- [ ] Document usage patterns clearly

### Cache Management

**Directory Structure**:
```
env_agents/data/metadata/services/
├── wqp_characteristics.zip          # WQP EPA characteristics
├── nasa_missions_catalog.json       # NASA mission data
└── usgs_collections_summary.yaml    # USGS data collections
```

**Naming Convention**:
- `{service}_{datatype}.{extension}`
- Use official data format when possible
- Include version/date in filename if needed

**Update Strategy**:
- Manual updates for now (place in git)
- Future: automatic cache refresh with TTL
- Always maintain backward compatibility

## Future Patterns

### Pagination Pattern
For services with moderate scale (100-500 items):
```python
def capabilities(self, page: int = 0, limit: int = 50) -> Dict[str, Any]:
    # Return paginated results with next/prev links
```

### Search Pattern  
For services with complex discovery:
```python
def search_assets(self, query: str, category: str = None) -> List[Dict]:
    # Return filtered asset list based on search terms
```

### Lazy Loading Pattern
For services with expensive metadata discovery:
```python
def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
    # Load detailed metadata only when specifically requested
```

## Testing Patterns

All patterns must maintain contract compliance:

```python
# Contract tests automatically validate:
assert adapter.SERVICE_TYPE in ["service", "meta"]

if adapter.SERVICE_TYPE == "service":
    assert "variables" in capabilities and isinstance(capabilities["variables"], list)
elif adapter.SERVICE_TYPE == "meta":
    assert "assets" in capabilities
    # Accept both list and dict formats for assets
```

## Performance Considerations

### Context Usage
- **Standard service**: ~1KB capabilities response
- **Dynamic service**: ~5-10KB (depends on catalog size)
- **Meta-service summary**: ~2-5KB (context-efficient)
- **Meta-service full**: ~50-100KB (avoid this!)

### Response Times
- **Cache hit**: < 100ms
- **Download + cache**: 1-5 seconds (one-time cost)
- **Enhanced fallback**: < 50ms

### Memory Usage
- Cache data in instance variables after first load
- Use generators for very large catalogs
- Consider lazy loading for expensive operations

## Conclusion

These scaling patterns enable the env-agents framework to handle the full spectrum of environmental data services, from simple sensors to complex multi-dataset platforms, while maintaining black box principles and context efficiency.

The patterns are designed to be:
- **Backward compatible**: Existing services continue working
- **Forward compatible**: New patterns can be added
- **Context efficient**: Avoid overwhelming responses
- **User friendly**: Clear discovery and usage patterns
- **Reliable**: Multiple fallback strategies ensure availability