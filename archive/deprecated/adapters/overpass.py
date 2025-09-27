from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
import requests
from datetime import datetime, timezone
from .base import BaseAdapter
from ..core.models import RequestSpec
from ..core.cache import global_cache
from ..core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)

class OsmOverpassAdapter(BaseAdapter):
    DATASET = "OSM_Overpass"
    SOURCE_URL = "https://overpass-api.de/api/interpreter"
    SOURCE_VERSION = "2024-07"
    LICENSE = "https://www.openstreetmap.org/copyright"
    REQUIRES_API_KEY = False
    
    # Common OSM feature types
    COMMON_FEATURES = {
        'amenity': ['restaurant', 'cafe', 'hospital', 'school', 'bank', 'pharmacy', 'fuel'],
        'shop': ['supermarket', 'convenience', 'bakery', 'clothes', 'electronics'],
        'tourism': ['hotel', 'museum', 'attraction', 'information'],
        'leisure': ['park', 'playground', 'sports_centre', 'swimming_pool'],
        'natural': ['tree', 'water', 'beach', 'forest'],
        'landuse': ['residential', 'commercial', 'industrial', 'forest', 'farmland']
    }
    
    def __init__(self):
        """Initialize OSM Overpass adapter with enhanced features"""
        super().__init__()
        self.logger = logging.getLogger(f"adapter.{self.DATASET.lower()}")
        self.cache = global_cache.get_service_cache(self.DATASET)
    def capabilities(self, extra=None) -> dict:
        """Return OSM Overpass service capabilities"""
        variables = []
        
        # Generate variables for common feature types
        for category, features in self.COMMON_FEATURES.items():
            for feature in features:
                variables.append({
                    "canonical": f"osm:{category}:{feature}",
                    "platform": f"{category}={feature}",
                    "unit": "count",
                    "description": f"{feature.replace('_', ' ').title()} features from OpenStreetMap",
                    "domain": "geographic_features"
                })
        
        return {
            "dataset": self.DATASET,
            "geometry": ["point", "bbox", "polygon"],
            "requires_time_range": False,  # OSM data is current snapshot
            "requires_api_key": False,
            "variables": variables,
            "attributes_schema": {
                "osm_type": {"type": "string", "description": "OSM element type (node/way/relation)"},
                "osm_id": {"type": "integer", "description": "OSM element ID"},
                "tags": {"type": "object", "description": "All OSM tags for the element"},
                "version": {"type": "integer", "description": "OSM element version"},
                "changeset": {"type": "integer", "description": "OSM changeset ID"},
                "user": {"type": "string", "description": "Last editor username"},
                "timestamp": {"type": "string", "description": "Last modification timestamp"}
            },
            "rate_limits": {
                "requests_per_minute": 60,
                "timeout_seconds": 180,
                "notes": "Fair use policy - avoid heavy queries during peak hours"
            },
            "spatial_resolution": "point_and_polygon_features",
            "spatial_coverage": "global",
            "temporal_coverage": "current_snapshot",
            "notes": "OpenStreetMap geographic features via Overpass API"
        }
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch OpenStreetMap features via Overpass API"""
        try:
            # Build Overpass QL query
            query = self._build_overpass_query(spec)
            if not query:
                return []
            
            # Execute query
            self.logger.debug(f"Executing Overpass query: {query[:200]}...")
            response = self._session.post(
                self.SOURCE_URL,
                data=query,
                headers={'Content-Type': 'text/plain'},
                timeout=180
            )
            
            if response.status_code == 400:
                self.logger.debug(f"Overpass query failed with 400. Query was: {query}")
                self.logger.debug(f"Response: {response.text[:500]}")
                return []  # Return empty results instead of failing
                
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('elements', [])
            
            rows = []
            retrieval_timestamp = datetime.now(timezone.utc)
            
            for element in elements:
                # Extract geometry
                lat = element.get('lat')
                lon = element.get('lon')
                
                # For ways/relations, use center or first node
                if not lat and 'center' in element:
                    lat = element['center']['lat']
                    lon = element['center']['lon']
                elif not lat and element.get('type') == 'way' and 'nodes' in element:
                    # Use first node for geometry (simplified)
                    continue  # Skip ways without center for now
                
                if not (lat and lon):
                    continue
                
                # Extract tags and determine variable
                tags = element.get('tags', {})
                variable = self._determine_variable(tags)
                if not variable:
                    continue
                
                # Generate observation ID
                osm_type = element.get('type', 'unknown')
                osm_id = element.get('id', 'unknown')
                obs_id = f"osm_{osm_type}_{osm_id}"
                
                # Parse timestamp
                timestamp = element.get('timestamp')
                parsed_timestamp = None
                if timestamp:
                    try:
                        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Create standardized row
                row = {
                    # Identity columns
                    'observation_id': obs_id,
                    'dataset': self.DATASET,
                    'source_url': self.SOURCE_URL,
                    'source_version': self.SOURCE_VERSION,
                    'license': self.LICENSE,
                    'retrieval_timestamp': retrieval_timestamp,
                    
                    # Spatial columns
                    'geometry_type': 'point',
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'geom_wkt': f"POINT({lon} {lat})",
                    'spatial_id': f"osm_{osm_type}_{osm_id}",
                    'site_name': tags.get('name', ''),
                    'admin': f"{tags.get('addr:city', '')}, {tags.get('addr:state', '')}".strip(', '),
                    'elevation_m': None,
                    
                    # Temporal columns
                    'time': parsed_timestamp,
                    'temporal_coverage': timestamp,
                    
                    # Value columns
                    'variable': variable,
                    'value': 1,  # Each element represents one feature
                    'unit': 'feature',
                    'depth_top_cm': None,
                    'depth_bottom_cm': None,
                    'qc_flag': 'ok',
                    
                    # Metadata columns
                    'attributes': {
                        'terms': [f"{self.DATASET}:feature:{variable.split(':')[-1]}"],
                        'osm_type': osm_type,
                        'osm_id': osm_id,
                        'version': element.get('version'),
                        'changeset': element.get('changeset'),
                        'user': element.get('user', ''),
                        'tags': tags,
                        'native_record': element  # Preserve full OSM element
                    },
                    'provenance': f"OSM {osm_type} {osm_id} retrieved on {retrieval_timestamp.isoformat()}"
                }
                
                rows.append(row)
            
            return rows[:1000]  # Limit results
            
        except Exception as e:
            self.logger.error(f"Failed to fetch OSM data: {e}")
            return []
    
    def _build_overpass_query(self, spec: RequestSpec) -> Optional[str]:
        """Build Overpass QL query from request specification"""
        try:
            # Determine geographic bounds
            if spec.geometry.type == "bbox":
                minx, miny, maxx, maxy = spec.geometry.coordinates
                bbox = f"({miny},{minx},{maxy},{maxx})"
            elif spec.geometry.type == "point":
                lon, lat = spec.geometry.coordinates
                radius = 1000  # 1km radius
                bbox = f"(around:{radius},{lat},{lon})"
            else:
                # Polygon not directly supported in simple queries
                self.logger.warning("Polygon geometry not yet supported for OSM queries")
                return None
            
            # Determine features to search for
            features_to_search = []
            if spec.variables:
                for var in spec.variables:
                    if var.startswith('osm:'):
                        parts = var.split(':')
                        if len(parts) >= 3:
                            category = parts[1]
                            feature = parts[2]
                            features_to_search.append((category, feature))
            
            # Default to some common features if no specific variables requested
            if not features_to_search:
                features_to_search = [
                    ('amenity', 'restaurant'),
                    ('amenity', 'cafe'),
                    ('shop', 'supermarket'),
                    ('tourism', 'hotel')
                ]
            
            # Build Overpass QL query - use single line format to avoid 400 errors
            query_parts = ['[out:json][timeout:25];(']
            
            for category, feature in features_to_search:
                # Add nodes, ways, and relations for each feature type (single line format)
                query_parts.extend([
                    f'node["{category}"="{feature}"]{bbox};',
                    f'way["{category}"="{feature}"]{bbox};',
                    f'relation["{category}"="{feature}"]{bbox};'
                ])
            
            query_parts.append(');out center meta;')
            
            # Use single line format to avoid parsing issues
            return ''.join(query_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to build Overpass query: {e}")
            return None
    
    def _determine_variable(self, tags: Dict[str, str]) -> Optional[str]:
        """Determine canonical variable from OSM tags"""
        # Check each category for matching tags
        for category, features in self.COMMON_FEATURES.items():
            if category in tags:
                feature_value = tags[category]
                if feature_value in features:
                    return f"osm:{category}:{feature_value}"
                else:
                    # Use the actual value even if not in our common list
                    return f"osm:{category}:{feature_value}"
        
        # Fallback: use first available tag as variable
        for tag_key, tag_value in tags.items():
            if tag_key not in ['name', 'addr:street', 'addr:housenumber', 'addr:city', 'addr:postcode']:
                return f"osm:{tag_key}:{tag_value}"
        
        return None
    
    def get_enhanced_metadata(self) -> Optional[AssetMetadata]:
        """Get Google Earth Engine-style metadata for OSM data"""
        try:
            # Create asset metadata
            asset_id = "OSM/OVERPASS_FEATURES"
            title = "OpenStreetMap Features via Overpass API"
            description = "Geographic features from OpenStreetMap including amenities, shops, natural features, and infrastructure"
            
            # Temporal extent (OSM is current snapshot, but has historical data)
            temporal_extent = ("2004-08-01", datetime.now().strftime('%Y-%m-%d'))
            
            # Create bands for feature categories
            bands_dict = {}
            
            # Feature count bands by category
            for category, features in self.COMMON_FEATURES.items():
                bands_dict[f"{category}_features"] = {
                    'description': f"Count of {category} features",
                    'data_type': 'int32',
                    'units': 'features',
                    'valid_range': [0, 100000],
                    'cf_standard_name': None
                }
                
                # Individual feature type bands
                for feature in features[:3]:  # Limit to first 3 to avoid too many bands
                    bands_dict[f"{category}_{feature}"] = {
                        'description': f"{feature.replace('_', ' ').title()} {category} features",
                        'data_type': 'int32',
                        'units': 'features',
                        'valid_range': [0, 10000],
                        'cf_standard_name': None
                    }
            
            # Data quality bands
            bands_dict['feature_density'] = {
                'description': 'Feature density per square kilometer',
                'data_type': 'float32',
                'units': 'features/km²',
                'valid_range': [0.0, 10000.0],
                'cf_standard_name': None
            }
            
            bands_dict['data_completeness'] = {
                'description': 'OSM data completeness indicator',
                'data_type': 'float32',
                'units': 'score',
                'valid_range': [0.0, 1.0],
                'cf_standard_name': None
            }
            
            bands_dict['last_modified'] = {
                'description': 'Days since last modification',
                'data_type': 'int32',
                'units': 'days',
                'valid_range': [0, 7300],  # ~20 years
                'cf_standard_name': None
            }
            
            # Global spatial extent
            spatial_extent = {
                "type": "Polygon",
                "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]
            }
            
            metadata = create_earth_engine_style_metadata(
                asset_id=asset_id,
                title=title,
                description=description,
                temporal_extent=temporal_extent,
                spatial_extent=spatial_extent,
                bands=bands_dict,
                provider_name="OpenStreetMap Foundation",
                provider_url="https://www.openstreetmap.org/"
            )
            
            # Add OSM-specific properties
            metadata.properties.update({
                'osm:api_version': 'Overpass API 0.7.61',
                'osm:feature_categories': len(self.COMMON_FEATURES),
                'osm:data_types': ['geographic_features', 'points_of_interest', 'infrastructure'],
                'osm:coordinate_system': 'EPSG:4326',
                'osm:update_frequency': 'continuously',
                'system:domain': 'geographic_features',
                'system:data_type': 'vector_features',
                'system:bbox': [-180, -90, 180, 90]
            })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced metadata for OSM: {e}")
            return None
    
    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest OSM feature types for semantic discovery"""
        try:
            capabilities = []
            
            # Generate capabilities for all feature types
            for category, features in self.COMMON_FEATURES.items():
                for feature in features:
                    capabilities.append({
                        'service': self.DATASET,
                        'native_id': f"{category}={feature}",
                        'label': f"{feature.replace('_', ' ').title()} {category}",
                        'unit': 'features',
                        'description': f"{feature.replace('_', ' ').title()} features from OpenStreetMap",
                        'domain': 'geographic_features',
                        'frequency': 'continuous',
                        'spatial_coverage': 'global',
                        'temporal_coverage': 'current_snapshot',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'metadata': {
                            'canonical': f"osm:{category}:{feature}",
                            'feature_category': category,
                            'osm_tag': f"{category}={feature}",
                            'data_types': ['vector_features']
                        }
                    })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"Failed to harvest OSM features: {e}")
            return []
