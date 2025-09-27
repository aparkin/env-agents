"""
GBIF Global Biodiversity Adapter (Enhanced)

Enhanced adapter with Google Earth Engine-style metadata and robust patterns
Provides access to global biodiversity occurrence records from GBIF
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import requests
import logging
from datetime import datetime, timezone
from .base import BaseAdapter
from ..core.models import RequestSpec
from ..core.cache import global_cache
from ..core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)


class GbifAdapter(BaseAdapter):
    """GBIF Global Biodiversity Information Facility Adapter with Enhanced Features"""
    
    DATASET = "GBIF"
    SOURCE_URL = "https://api.gbif.org/v1"
    SOURCE_VERSION = "v1"
    LICENSE = "https://creativecommons.org/licenses/by/4.0/"
    REQUIRES_API_KEY = False
    
    # GBIF taxonomic kingdoms
    KINGDOMS = [
        'Animalia', 'Plantae', 'Fungi', 'Chromista', 
        'Archaea', 'Bacteria', 'Protozoa', 'Viruses'
    ]
    
    # Basis of record types
    BASIS_OF_RECORD = [
        'HUMAN_OBSERVATION', 'MACHINE_OBSERVATION', 'OBSERVATION',
        'PRESERVED_SPECIMEN', 'FOSSIL_SPECIMEN', 'LIVING_SPECIMEN',
        'LITERATURE', 'UNKNOWN'
    ]
    
    def __init__(self):
        """Initialize GBIF adapter with enhanced features"""
        super().__init__()
        self.logger = logging.getLogger(f"adapter.{self.DATASET.lower()}")
        self.cache = global_cache.get_service_cache(self.DATASET)
        
    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return GBIF service capabilities with biodiversity focus"""
        
        # Get cached taxonomic information
        try:
            kingdoms = self.cache.get_or_fetch(
                "taxonomic_kingdoms",
                lambda: self._fetch_kingdoms(),
                "metadata",
                ttl=86400 * 7  # 1 week
            )
        except Exception:
            kingdoms = self.KINGDOMS
        
        variables = []
        for kingdom in kingdoms[:6]:  # Limit for capabilities display
            variables.append({
                "canonical": f"biodiversity:{kingdom.lower()}:occurrence_count",
                "platform": f"occurrenceSearch?kingdom={kingdom}",
                "unit": "count",
                "description": f"{kingdom} occurrence records",
                "domain": "biodiversity"
            })
        
        return {
            "dataset": self.DATASET,
            "geometry": ["point", "bbox", "polygon"],
            "requires_time_range": False,  # Optional for GBIF
            "requires_api_key": False,
            "variables": variables,
            "attributes_schema": {
                "species_key": {"type": "integer", "description": "GBIF species key"},
                "taxon_key": {"type": "integer", "description": "GBIF taxon key"},
                "kingdom": {"type": "string", "description": "Taxonomic kingdom"},
                "scientific_name": {"type": "string", "description": "Scientific name"},
                "basis_of_record": {"type": "string", "description": "Type of record"},
                "coordinate_uncertainty": {"type": "number", "description": "Location uncertainty (m)"},
                "elevation": {"type": "number", "description": "Elevation (m)"},
                "depth": {"type": "number", "description": "Depth (m)"}
            },
            "rate_limits": {
                "requests_per_minute": 300,
                "notes": "Public API with reasonable use policy"
            },
            "spatial_resolution": "point_occurrences",
            "spatial_coverage": "global",
            "temporal_coverage": "historical_present",
            "taxonomic_kingdoms": kingdoms,
            "basis_of_record_types": self.BASIS_OF_RECORD,
            "notes": "Global biodiversity occurrence data from museums, herbaria, observations"
        }
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch biodiversity occurrence data from GBIF"""
        try:
            rows = []
            
            # Build GBIF API parameters
            params = {
                'limit': 300,  # GBIF max per page
                'hasCoordinate': 'true',
                'hasGeospatialIssue': 'false'
            }
            
            # Geographic filtering
            if spec.geometry:
                if spec.geometry.type == "point":
                    lon, lat = spec.geometry.coordinates
                    # Use small radius around point (1km)
                    params.update({
                        'decimalLatitude': f"{lat-0.01},{lat+0.01}",
                        'decimalLongitude': f"{lon-0.01},{lon+0.01}"
                    })
                elif spec.geometry.type == "bbox":
                    # GBIF uses individual lat/lon parameters
                    minLon, minLat, maxLon, maxLat = spec.geometry.coordinates
                    params.update({
                        'decimalLatitude': f"{minLat},{maxLat}",
                        'decimalLongitude': f"{minLon},{maxLon}"
                    })
            
            # Time filtering
            if spec.time_range:
                start_date, end_date = spec.time_range
                if start_date:
                    params['eventDate'] = f"{start_date},{end_date or datetime.now().strftime('%Y-%m-%d')}"
            
            # Variable filtering (kingdom-based)
            kingdoms = []
            for var in spec.variables or []:
                if 'biodiversity:' in var:
                    parts = var.split(':')
                    if len(parts) >= 2:
                        kingdom = parts[1].capitalize()
                        if kingdom in self.KINGDOMS:
                            kingdoms.append(kingdom)
            
            if not kingdoms:
                kingdoms = ['Animalia', 'Plantae']  # Default to animals and plants
            
            # Fetch data for each kingdom
            for kingdom in kingdoms:
                kingdom_params = params.copy()
                kingdom_params['kingdom'] = kingdom
                
                kingdom_data = self._fetch_gbif_occurrences(kingdom_params)
                if kingdom_data:
                    rows.extend(kingdom_data)
            
            return rows[:1000]  # Limit total results
            
        except Exception as e:
            self.logger.error(f"Failed to fetch GBIF data: {e}")
            return []
    
    def _fetch_gbif_occurrences(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch occurrence data from GBIF API"""
        try:
            url = f"{self.SOURCE_URL}/occurrence/search"
            
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            rows = []
            retrieval_timestamp = datetime.now(timezone.utc)
            
            for record in results:
                # Extract key fields
                species_key = record.get('speciesKey')
                taxon_key = record.get('taxonKey')
                scientific_name = record.get('scientificName', 'Unknown')
                kingdom = record.get('kingdom', 'Unknown')
                lat = record.get('decimalLatitude')
                lon = record.get('decimalLongitude')
                
                if not (lat and lon):
                    continue  # Skip records without coordinates
                
                # Generate observation ID
                obs_id = f"gbif_{record.get('key', 'unknown')}_{species_key or 'unknown'}"
                
                # Parse date
                event_date = record.get('eventDate')
                parsed_date = None
                if event_date:
                    try:
                        parsed_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
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
                    'spatial_id': f"gbif_{record.get('key')}",
                    'site_name': record.get('locality', ''),
                    'admin': f"{record.get('country', '')}, {record.get('stateProvince', '')}".strip(', '),
                    'elevation_m': record.get('elevation'),
                    
                    # Temporal columns
                    'time': parsed_date,
                    'temporal_coverage': event_date,
                    
                    # Value columns
                    'variable': f"biodiversity:{kingdom.lower()}:occurrence",
                    'value': 1,  # Each record represents one occurrence
                    'unit': 'occurrence',
                    'depth_top_cm': record.get('depth'),
                    'depth_bottom_cm': record.get('depth'),
                    'qc_flag': 'ok' if not record.get('issues', []) else 'issues_present',
                    
                    # Metadata columns
                    'attributes': {
                        'terms': [f"{self.DATASET}:occurrence:{kingdom}"],
                        'species_key': species_key,
                        'taxon_key': taxon_key,
                        'scientific_name': scientific_name,
                        'kingdom': kingdom,
                        'phylum': record.get('phylum'),
                        'class': record.get('class'),
                        'order': record.get('order'),
                        'family': record.get('family'),
                        'genus': record.get('genus'),
                        'species': record.get('species'),
                        'basis_of_record': record.get('basisOfRecord'),
                        'coordinate_uncertainty': record.get('coordinateUncertaintyInMeters'),
                        'individual_count': record.get('individualCount'),
                        'publisher': record.get('publishingOrgKey'),
                        'dataset_key': record.get('datasetKey'),
                        'native_record': record  # Preserve full GBIF record
                    },
                    'provenance': f"GBIF occurrence {record.get('key')} retrieved on {retrieval_timestamp.isoformat()}"
                }
                
                rows.append(row)
            
            return rows
            
        except Exception as e:
            self.logger.error(f"Failed to fetch GBIF occurrences: {e}")
            return []
    
    def _fetch_kingdoms(self) -> List[str]:
        """Fetch available taxonomic kingdoms from GBIF"""
        try:
            url = f"{self.SOURCE_URL}/enumeration/basic/Kingdom"
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return self.KINGDOMS
    
    def get_enhanced_metadata(self) -> Optional[AssetMetadata]:
        """Get Earth Engine-style metadata for GBIF data"""
        try:
            # Get cached kingdom and basis information
            kingdoms = self.cache.get_or_fetch(
                "kingdoms", 
                self._fetch_kingdoms, 
                "metadata", 
                ttl=86400 * 7
            )
            
            # Create asset metadata
            asset_id = "GBIF/OCCURRENCES_GLOBAL"
            title = "GBIF Global Biodiversity Occurrence Records"
            description = "Global species occurrence records from museums, herbaria, citizen science, and research institutions"
            
            # Temporal extent (GBIF has historical to present data)
            temporal_extent = ("1700-01-01", datetime.now().strftime('%Y-%m-%d'))
            
            # Create bands for each kingdom and data type
            bands_dict = {}
            
            # Kingdom-based occurrence bands
            for kingdom in kingdoms:
                bands_dict[f"{kingdom.lower()}_occurrences"] = {
                    'description': f"{kingdom} species occurrence records",
                    'data_type': 'int32',
                    'units': 'occurrences',
                    'valid_range': [0, 1000000],
                    'cf_standard_name': None
                }
                
                bands_dict[f"{kingdom.lower()}_species_count"] = {
                    'description': f"Unique {kingdom} species count",
                    'data_type': 'int32', 
                    'units': 'species',
                    'valid_range': [0, 100000],
                    'cf_standard_name': None
                }
            
            # Data quality bands
            bands_dict['coordinate_uncertainty'] = {
                'description': 'Coordinate uncertainty in meters',
                'data_type': 'float32',
                'units': 'meters',
                'valid_range': [0.0, 100000.0],
                'cf_standard_name': None
            }
            
            bands_dict['temporal_coverage'] = {
                'description': 'Temporal span of occurrence records',
                'data_type': 'string',
                'units': 'date_range',
                'valid_range': [],
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
                provider_name="Global Biodiversity Information Facility",
                provider_url="https://www.gbif.org/"
            )
            
            # Add GBIF-specific properties
            metadata.properties.update({
                'gbif:kingdoms': len(kingdoms),
                'gbif:basis_of_record_types': len(self.BASIS_OF_RECORD),
                'gbif:api_version': self.SOURCE_VERSION,
                'gbif:data_types': ['occurrence_records', 'taxonomic_data', 'specimen_data'],
                'system:domain': 'biodiversity',
                'system:data_type': 'occurrence_records',
                'system:bbox': [-180, -90, 180, 90]
            })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced metadata for GBIF: {e}")
            return None
