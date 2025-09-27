"""
Enhanced metadata system inspired by Google Earth Engine
Provides rich, standardized metadata for all environmental data services
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json


@dataclass
class ProviderMetadata:
    """Data provider information"""
    name: str
    roles: List[str]  # ["producer", "licensor", "processor"]
    url: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "roles": self.roles,
            "url": self.url,
            "description": self.description
        }


@dataclass
class BandMetadata:
    """Individual measurement/band metadata (like Earth Engine bands)"""
    description: str
    data_type: str  # "float32", "int16", "string", etc.
    units: str
    valid_range: List[float]
    fill_value: Optional[Union[float, int]] = None
    cf_standard_name: Optional[str] = None
    gee_scale: Optional[float] = None
    gee_offset: Optional[float] = None
    quality_flags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "data_type": self.data_type,
            "units": self.units,
            "valid_range": self.valid_range,
            "fill_value": self.fill_value,
            "cf_standard_name": self.cf_standard_name,
            "gee_scale": self.gee_scale,
            "gee_offset": self.gee_offset,
            "quality_flags": self.quality_flags
        }


@dataclass
class AssetMetadata:
    """Earth Engine-inspired asset metadata"""
    asset_id: str
    type: str  # "image", "timeseries_collection", "table", "vector"
    properties: Dict[str, Any]
    bands: Dict[str, BandMetadata]
    providers: List[ProviderMetadata]
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "asset_id": self.asset_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
            "properties": self.properties,
            "bands": {k: v.to_dict() for k, v in self.bands.items()},
            "providers": [p.to_dict() for p in self.providers]
        }
    
    def to_stac_item(self) -> Dict[str, Any]:
        """Export as STAC (SpatioTemporal Asset Catalog) item"""
        stac_item = {
            "stac_version": "1.0.0",
            "type": "Feature",
            "id": self.asset_id,
            "properties": {
                "title": self.title,
                "description": self.description,
                "created": datetime.now().isoformat(),
                **self.properties
            },
            "assets": {
                band_name: {
                    "type": "application/json",
                    "roles": ["data"],
                    "title": band_meta.description,
                    "raster:bands": [{
                        "data_type": band_meta.data_type,
                        "unit": band_meta.units,
                        "scale": band_meta.gee_scale,
                        "offset": band_meta.gee_offset
                    }]
                }
                for band_name, band_meta in self.bands.items()
            },
            "links": [
                {
                    "rel": "provider",
                    "href": provider.url,
                    "type": "text/html",
                    "title": provider.name
                }
                for provider in self.providers
            ]
        }
        return stac_item
    
    def get_citation_string(self) -> str:
        """Generate proper citation string for data use"""
        primary_provider = self.providers[0] if self.providers else None
        
        if primary_provider:
            year = datetime.now().year
            return (f"{primary_provider.name}. {self.title or self.asset_id}. "
                   f"Retrieved {datetime.now().strftime('%Y-%m-%d')}. "
                   f"{primary_provider.url}")
        else:
            return f"Dataset: {self.asset_id}. Retrieved {datetime.now().strftime('%Y-%m-%d')}."
    
    def get_temporal_extent(self) -> Optional[tuple]:
        """Get temporal extent from properties"""
        start = self.properties.get('system:time_start')
        end = self.properties.get('system:time_end')
        
        if start and end:
            return (start, end)
        return None
    
    def get_spatial_extent(self) -> Optional[Dict[str, Any]]:
        """Get spatial extent from properties"""
        footprint = self.properties.get('system:footprint')
        bbox = self.properties.get('system:bbox')
        
        if footprint:
            return footprint
        elif bbox:
            return {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]], [bbox[2], bbox[1]], 
                    [bbox[2], bbox[3]], [bbox[0], bbox[3]], 
                    [bbox[0], bbox[1]]
                ]]
            }
        return None
    
    @classmethod
    def from_service_response(cls, service_name: str, response: Dict[str, Any]) -> 'AssetMetadata':
        """Convert service-specific metadata to standardized format"""
        
        # Default mappings - can be overridden by specific adapters
        asset_id = f"{service_name}/{response.get('id', 'unknown')}"
        
        properties = {
            "service_name": service_name,
            "native_id": response.get('id'),
            "system:time_start": response.get('startdate'),
            "system:time_end": response.get('enddate'),
        }
        
        # Add all other response fields to properties
        for key, value in response.items():
            if key not in ['id', 'startdate', 'enddate']:
                properties[f"native:{key}"] = value
        
        bands = {}
        providers = [ProviderMetadata(
            name=service_name,
            roles=["producer"],
            url=response.get('url', '')
        )]
        
        return cls(
            asset_id=asset_id,
            type="timeseries_collection",  # Default type
            properties=properties,
            bands=bands,
            providers=providers,
            title=response.get('name'),
            description=response.get('description')
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AssetMetadata':
        """Create from JSON string"""
        data = json.loads(json_str)
        
        # Reconstruct nested objects
        bands = {k: BandMetadata(**v) for k, v in data['bands'].items()}
        providers = [ProviderMetadata(**p) for p in data['providers']]
        
        return cls(
            asset_id=data['asset_id'],
            type=data['type'],
            properties=data['properties'],
            bands=bands,
            providers=providers,
            title=data.get('title'),
            description=data.get('description'),
            keywords=data.get('keywords', [])
        )


def create_earth_engine_style_metadata(
    asset_id: str,
    title: str,
    description: str,
    temporal_extent: tuple,
    spatial_extent: Optional[Dict] = None,
    bands: Optional[Dict[str, Dict]] = None,
    provider_name: str = "Unknown",
    provider_url: str = ""
) -> AssetMetadata:
    """
    Helper function to create Earth Engine-style metadata
    
    Args:
        asset_id: Unique identifier (e.g., "EPA_AQS/PM25_DAILY")
        title: Human-readable title
        description: Detailed description
        temporal_extent: (start_date, end_date) as ISO strings
        spatial_extent: GeoJSON-style geometry
        bands: Dictionary of band definitions
        provider_name: Data provider name
        provider_url: Provider URL
    
    Returns:
        AssetMetadata object with Earth Engine-style structure
    """
    
    properties = {
        "system:time_start": temporal_extent[0],
        "system:time_end": temporal_extent[1],
        "system:asset_size": "unknown"
    }
    
    if spatial_extent:
        properties["system:footprint"] = spatial_extent
    
    band_objects = {}
    if bands:
        for band_name, band_info in bands.items():
            band_objects[band_name] = BandMetadata(
                description=band_info.get('description', ''),
                data_type=band_info.get('data_type', 'float32'),
                units=band_info.get('units', ''),
                valid_range=band_info.get('valid_range', []),
                cf_standard_name=band_info.get('cf_standard_name'),
                fill_value=band_info.get('fill_value')
            )
    
    providers = [ProviderMetadata(
        name=provider_name,
        roles=["producer", "licensor"],
        url=provider_url
    )]
    
    return AssetMetadata(
        asset_id=asset_id,
        type="timeseries_collection",
        title=title,
        description=description,
        properties=properties,
        bands=band_objects,
        providers=providers
    )