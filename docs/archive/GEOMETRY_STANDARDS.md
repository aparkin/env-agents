# Geometry Handling Standards - env-agents Framework

## Overview

All environmental services must handle both `bbox` and `point` geometry types uniformly and predictably.

## Standard Geometry Types

### 1. Point Geometry
```python
Geometry(type="point", coordinates=[-122.41, 37.77])  # [longitude, latitude]
```

### 2. Bounding Box Geometry
```python
Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.40, 37.78])  # [west, south, east, north]
```

## Coordinate Order Convention

**CRITICAL**: All services must use consistent coordinate order:
- **Point coordinates**: `[longitude, latitude]` (x, y)
- **Bbox coordinates**: `[west, south, east, north]` (minX, minY, maxX, maxY)
- **This matches GeoJSON and WGS84 standards**

## Required Adapter Methods

All adapters MUST implement these geometry handling methods:

### 1. `_convert_geometry_to_bbox(geometry, extra)`
```python
def _convert_geometry_to_bbox(self, geometry: Geometry, extra: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Convert any geometry to bbox (west, south, east, north)"""
    if geometry.type == "bbox":
        return tuple(geometry.coordinates)  # [west, south, east, north]
    elif geometry.type == "point":
        return self._point_to_bbox(geometry, radius_m=extra.get('radius_m', 1000))
    else:
        raise ValueError(f"Unsupported geometry type: {geometry.type}")
```

### 2. `_point_to_bbox(geometry, radius_m)`
```python
def _point_to_bbox(self, geometry: Geometry, radius_m: float = 1000) -> Tuple[float, float, float, float]:
    """Convert point to bbox with radius in meters"""
    lon, lat = geometry.coordinates

    # Convert radius from meters to degrees (approximate)
    lat_deg = radius_m / 111000  # ~111km per degree latitude
    lon_deg = radius_m / (111000 * abs(cos(radians(lat))))  # longitude varies by latitude

    west = lon - lon_deg
    south = lat - lat_deg
    east = lon + lon_deg
    north = lat + lat_deg

    return (west, south, east, north)
```

### 3. `_validate_geometry(geometry)`
```python
def _validate_geometry(self, geometry: Geometry) -> bool:
    """Validate geometry coordinates are in valid ranges"""
    if geometry.type == "point":
        lon, lat = geometry.coordinates
        return -180 <= lon <= 180 and -90 <= lat <= 90
    elif geometry.type == "bbox":
        west, south, east, north = geometry.coordinates
        return (-180 <= west <= 180 and -90 <= south <= 90 and
                -180 <= east <= 180 and -90 <= north <= 90 and
                west < east and south < north)
    return False
```

## Service-Specific Requirements

### API Services (EPA_AQS, OpenAQ, etc.)
- Convert geometries to service-specific parameter format
- Ensure coordinate order matches API expectations
- Handle coordinate precision limits

### Raster Services (NASA_POWER, SoilGrids, etc.)
- Support both point and bbox queries
- Handle resolution/pixel alignment
- Manage large bbox size limits

### Vector Services (OSM_Overpass, GBIF, etc.)
- Support spatial filtering with geometries
- Handle coordinate reference system conversion
- Manage query complexity for large areas

### Meta-Services (Earth Engine)
- Support geometry as region parameter
- Handle asset-specific coordinate requirements
- Manage Earth Engine geometry objects

## Error Handling

### Invalid Coordinates
```python
if not self._validate_geometry(spec.geometry):
    raise ValueError(f"Invalid geometry coordinates: {spec.geometry.coordinates}")
```

### Coordinate Order Errors
- Services should detect and fix common lat/lon swap errors
- Log warnings when coordinate order appears incorrect
- Provide helpful error messages

### Size Limits
```python
west, south, east, north = bbox
if (east - west) * (north - south) > MAX_AREA_DEGREES:
    raise ValueError(f"Bounding box too large. Max area: {MAX_AREA_DEGREES} square degrees")
```

## Testing Requirements

All adapters must pass both geometry types:

```python
# Test both geometries
bbox_test = RequestSpec(geometry=Geometry(type="bbox", coordinates=[-122.42, 37.77, -122.40, 37.78]))
point_test = RequestSpec(geometry=Geometry(type="point", coordinates=[-122.41, 37.77]))

# Both should return data or fail gracefully
bbox_result = adapter._fetch_rows(bbox_test)
point_result = adapter._fetch_rows(point_test)
```

## Migration Plan

### Phase 1: Audit Current State ✅
- Identify services with geometry handling issues
- Document coordinate order problems
- Test both bbox and point support

### Phase 2: Standardize Core Methods
- Add required geometry methods to all adapters
- Fix coordinate order bugs (EPA_AQS priority)
- Implement consistent validation

### Phase 3: Comprehensive Testing
- Test all services with both geometry types
- Validate coordinate order consistency
- Performance test with various geometry sizes

### Phase 4: Documentation & Training
- Update service documentation
- Create geometry handling examples
- Document service-specific requirements

## Common Patterns

### Good Examples
- **SSURGO**: Has proper `_convert_geometry_to_bbox()` and `_point_to_bbox()`
- **WQP**: Consistent geometry handling methods

### Needs Standardization
- **EPA_AQS**: Fix coordinate order (lat/lon swap bug)
- **OSM_Overpass**: Add point geometry support
- **Earth Engine**: Standardize geometry parameter handling

---

*This document defines the required standards for geometry handling across all env-agents services.*