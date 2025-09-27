"""
US Energy Information Administration (EIA) Adapter

Provides access to comprehensive US energy data including:
- Electricity generation, capacity, and consumption
- Natural gas production and consumption  
- Petroleum and renewable energy data
- Energy prices and market data

Uses EIA's v2 API with enhanced metadata in Earth Engine style
"""

from __future__ import annotations
import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from ..base import BaseAdapter
from ...core.models import RequestSpec  
from ...core.errors import FetchError
from ...core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)


class EIAAdapter(BaseAdapter):
    """US Energy Information Administration API Adapter"""
    
    DATASET = "US_EIA"
    SOURCE_URL = "https://api.eia.gov/v2/"
    SOURCE_VERSION = "v2.0"
    LICENSE = "Public Domain"
    REQUIRES_API_KEY = True
    
    # Energy data domains
    ELECTRICITY_ROUTES = [
        "electricity/rto/daily-region-data",
        "electricity/rto/fuel-type-data", 
        "electricity/state-electricity-profiles/emissions-by-state-by-fuel",
        "electricity/electric-power-operational-data/annual-generation"
    ]
    
    NATURAL_GAS_ROUTES = [
        "natural-gas/prod/sum",
        "natural-gas/cons/sum",
        "natural-gas/move/interstate"
    ]
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize EIA adapter
        
        Args:
            api_key: EIA API key (defaults to environment variable)
            cache_dir: Directory for caching metadata (defaults to ./cache)
        """
        super().__init__()
        
        # Initialize logger
        self.logger = logging.getLogger(f"adapter.{self.DATASET.lower()}")
        
        # API key management
        self.api_key = api_key or os.environ.get('EIA_API_KEY', 'iwg624GgGLvgU4gcc8GWFSRy6qJeVrPaGEFJgxo5')
        if not self.api_key:
            raise ValueError("EIA API key required. Set EIA_API_KEY environment variable or pass api_key parameter.")
        
        # Cache setup with robust path resolution
        default_cache = cache_dir or "data/cache"
        if not Path(default_cache).is_absolute():
            # Find project root by looking for setup.py or pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                    default_cache = str(current / default_cache)
                    break
                current = current.parent
        
        self.cache_dir = Path(default_cache)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_cache_file = self.cache_dir / "eia_metadata.json"
        self.routes_cache_file = self.cache_dir / "eia_routes.json"
        
        # Session for requests
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}
        
        # Cached metadata
        self._cached_metadata = None
        self._cached_routes = None
    
    def capabilities(self) -> Dict[str, Any]:
        """Get adapter capabilities with cached route discovery"""
        try:
            # Load cached routes if available
            routes = self._get_available_routes()
            
            variables = []
            for route_info in routes:
                route_id = route_info['id']
                route_name = route_info['name']
                
                # Create canonical variable names from route structure
                # e.g., "electricity/rto/region-data" -> "energy:electricity:rto_region_data"
                canonical_var = f"energy:{route_id.replace('/', ':').replace('-', '_')}"
                
                variables.append({
                    'canonical': canonical_var,
                    'platform': route_id,
                    'unit': 'various',  # EIA has mixed units
                    'description': route_name
                })
            
            return {
                'variables': variables,
                'attributes_schema': {
                    'route_id': 'string',
                    'frequency': 'string', 
                    'facets': 'object',
                    'units': 'string'
                },
                'rate_limits': {
                    'requests_per_hour': 5000,
                    'max_rows_per_request': 5000
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get EIA capabilities: {e}")
            return {'variables': [], 'error': str(e)}
    
    def harvest(self) -> Dict[str, Any]:
        """Harvest EIA API structure for semantic mapping"""
        try:
            routes = self._get_available_routes()
            
            harvest_data = {}
            for route_info in routes:
                route_id = route_info['id']
                
                # Get detailed route information
                route_details = self._describe_route(route_id)
                if route_details:
                    harvest_data[route_id] = {
                        'id': route_id,
                        'label': route_info['name'],
                        'description': route_info.get('description', ''),
                        'unit': 'mixed',  # EIA endpoints have different units
                        'domain': self._infer_domain(route_id),
                        'frequency': route_details.get('defaultFrequency', 'unknown'),
                        'facets': route_details.get('facets', {}),
                        'start_period': route_details.get('startPeriod'),
                        'end_period': route_details.get('endPeriod')
                    }
            
            # Cache harvest results
            with open(self.routes_cache_file, 'w') as f:
                json.dump(harvest_data, f, indent=2, default=str)
            
            return harvest_data
            
        except Exception as e:
            self.logger.error(f"Failed to harvest EIA routes: {e}")
            return {}
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch energy data from EIA API"""
        try:
            rows = []
            
            for variable in spec.variables:
                # Parse canonical variable name
                # e.g., "energy:electricity:rto:region_data" -> "electricity/rto/region-data"
                if variable.startswith('energy:'):
                    route_parts = variable[7:].split(':')  # Remove 'energy:' prefix
                    route_id = '/'.join(route_parts).replace('_', '-')
                else:
                    # Assume it's already a route ID
                    route_id = variable
                
                # Fetch data for this route
                route_data = self._fetch_route_data(route_id, spec)
                if route_data:
                    rows.extend(route_data)
            
            return rows
            
        except Exception as e:
            self.logger.error(f"Failed to fetch EIA data: {e}")
            raise FetchError(f"EIA data fetch failed: {e}")
    
    def _fetch_route_data(self, route_id: str, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch data for a specific EIA route"""
        try:
            # Build API URL
            url = f"{self.SOURCE_URL}{route_id}/data"
            
            # Build query parameters with proper formatting
            params = {
                'frequency': 'monthly',  # Default frequency
                'sort[0][column]': 'period',
                'sort[0][direction]': 'desc'
            }
            
            # Add time filter if specified
            if spec.time_range:
                start_date, end_date = spec.time_range
                if start_date:
                    params['start'] = start_date
                if end_date:
                    params['end'] = end_date
            
            # Add geographic/facet filters from spec.extra
            if spec.extra:
                for key, value in spec.extra.items():
                    if key in ['frequency', 'facets']:
                        params[key] = value
            
            # Make request
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'response' not in data:
                self.logger.warning(f"No response data for route {route_id}")
                return []
            
            # Parse response data
            response_data = data['response']
            raw_data = response_data.get('data', [])
            
            # Check for None or invalid data response
            if raw_data is None:
                self.logger.warning(f"EIA API returned None for data in route {route_id}")
                return []
            
            if not isinstance(raw_data, (list, tuple)):
                self.logger.warning(f"EIA API returned non-iterable data type {type(raw_data)} for route {route_id}")
                return []
            
            rows = []
            retrieval_timestamp = datetime.now(timezone.utc)
            
            for record in raw_data:
                # Create standardized row
                row = {
                    # Identity columns
                    'observation_id': self._generate_observation_id(route_id, record),
                    'dataset': self.DATASET,
                    'source_url': self.SOURCE_URL,
                    'source_version': self.SOURCE_VERSION,
                    'license': self.LICENSE,
                    'retrieval_timestamp': retrieval_timestamp,
                    
                    # Spatial columns (EIA is mostly US-focused)
                    'geometry_type': 'region',
                    'latitude': None,
                    'longitude': None,
                    'geom_wkt': None,
                    'spatial_id': record.get('respondent', ''),  # Often state or region code
                    'site_name': record.get('respondent-name', ''),
                    'admin': 'US',
                    'elevation_m': None,
                    
                    # Temporal columns
                    'time': self._parse_eia_period(record.get('period')),
                    'temporal_coverage': record.get('period'),
                    
                    # Value columns
                    'variable': f"energy:{route_id.replace('/', ':').replace('-', '_')}",
                    'value': record.get('value'),
                    'unit': record.get('units', 'unknown'),
                    'depth_top_cm': None,
                    'depth_bottom_cm': None,
                    'qc_flag': None,
                    
                    # Metadata columns
                    'attributes': {
                        'terms': [f"{self.DATASET}:route:{route_id}"],
                        'route_id': route_id,
                        'frequency': response_data.get('frequency', 'unknown'),
                        'native_record': record  # Preserve full native data
                    },
                    'provenance': f"Retrieved from EIA API v2 route {route_id} on {retrieval_timestamp.isoformat()}"
                }
                
                rows.append(row)
            
            return rows
            
        except requests.RequestException as e:
            self.logger.error(f"HTTP error fetching route {route_id}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error processing route {route_id}: {e}")
            return []
    
    def _get_available_routes(self) -> List[Dict[str, Any]]:
        """Get available EIA API routes with caching"""
        # Check cache first
        if self._cached_routes:
            return self._cached_routes
        
        if self.routes_cache_file.exists():
            try:
                with open(self.routes_cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Convert to list format
                    self._cached_routes = [
                        {'id': route_id, 'name': info.get('label', route_id)}
                        for route_id, info in cached_data.items()
                    ]
                    return self._cached_routes
            except Exception as e:
                self.logger.warning(f"Failed to load cached routes: {e}")
        
        # Fetch from API
        try:
            url = f"{self.SOURCE_URL}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            routes = []
            
            if 'response' in data and 'routes' in data['response']:
                for route in data['response']['routes']:
                    routes.append({
                        'id': route['id'],
                        'name': route.get('name', route['id']),
                        'description': route.get('description', '')
                    })
            
            self._cached_routes = routes
            return routes
            
        except Exception as e:
            self.logger.error(f"Failed to fetch EIA routes: {e}")
            # Return fallback routes
            fallback_routes = []
            for route in self.ELECTRICITY_ROUTES + self.NATURAL_GAS_ROUTES:
                fallback_routes.append({
                    'id': route,
                    'name': route.replace('/', ' ').replace('-', ' ').title()
                })
            return fallback_routes
    
    def _describe_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific route"""
        try:
            url = f"{self.SOURCE_URL}{route_id}/"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            if 'response' in data:
                return data['response']
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Could not describe route {route_id}: {e}")
            return None
    
    def _infer_domain(self, route_id: str) -> str:
        """Infer data domain from route ID"""
        if 'electricity' in route_id:
            return 'electricity'
        elif 'natural-gas' in route_id:
            return 'natural_gas'
        elif 'petroleum' in route_id:
            return 'petroleum'
        elif 'coal' in route_id:
            return 'coal'
        elif 'renewable' in route_id:
            return 'renewable'
        else:
            return 'energy'
    
    def _parse_eia_period(self, period: str) -> Optional[datetime]:
        """Parse EIA period string to datetime"""
        if not period:
            return None
        
        try:
            # EIA uses various formats: "2023", "2023-01", "2023-01-01", etc.
            if len(period) == 4:  # Annual: "2023"
                return datetime(int(period), 1, 1)
            elif len(period) == 7:  # Monthly: "2023-01"  
                year, month = period.split('-')
                return datetime(int(year), int(month), 1)
            elif len(period) == 10:  # Daily: "2023-01-01"
                return datetime.fromisoformat(period)
            else:
                self.logger.warning(f"Unknown EIA period format: {period}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to parse EIA period '{period}': {e}")
            return None
    
    def _generate_observation_id(self, route_id: str, record: Dict[str, Any]) -> str:
        """Generate unique observation ID"""
        # Use route, period, and respondent to create unique ID
        period = record.get('period', 'unknown')
        respondent = record.get('respondent', 'unknown') 
        value_id = f"{route_id}:{period}:{respondent}"
        
        # Create hash for consistent short ID
        import hashlib
        return hashlib.md5(value_id.encode()).hexdigest()[:16]
    
    def get_enhanced_metadata(self, route_id: str) -> Optional[AssetMetadata]:
        """Get Earth Engine-style metadata for a specific route"""
        try:
            # Starting enhanced metadata creation
            
            route_details = self._describe_route(route_id)
            if not route_details:
                self.logger.debug(f"No route details found for {route_id}")
                return None
            
            self.logger.debug(f" Got route details: {type(route_details)} - {route_details}")
            
            # Create asset metadata
            asset_id = f"US_EIA/{route_id.replace('/', '_').upper()}"
            title = route_details.get('name', route_id)
            description = route_details.get('description', f"EIA energy data from {route_id}")
            
            self.logger.debug(f" Asset ID: {asset_id}, Title: {title}")
            
            # Temporal extent
            start_period = route_details.get('startPeriod')
            end_period = route_details.get('endPeriod', datetime.now().strftime('%Y-%m'))
            temporal_extent = (start_period, end_period)
            
            self.logger.debug(f" Temporal extent: {temporal_extent}")
            
            # Create band metadata for each data column
            bands = {}
            facets = route_details.get('facets', {})
            
            self.logger.debug(f" Facets type: {type(facets)}, content: {facets}")
            
            # Default value band
            # Creating default value band
            bands['value'] = BandMetadata(
                description=f"Energy data values from {route_id}",
                data_type='float64',
                units=route_details.get('defaultFrequency', 'mixed'),
                valid_range=[0.0, float('inf')],  # Energy values are typically positive
                cf_standard_name=None
            )
            self.logger.debug(f" Created bands dict: {type(bands)}, keys: {list(bands.keys())}")
            
            # Add facet bands - handle all possible formats
            try:
                if isinstance(facets, dict):
                    # Processing facets as dict
                    for facet_name, facet_info in facets.items():
                        bands[facet_name] = BandMetadata(
                            description=f"Facet: {facet_name}",
                            data_type='string',
                            units='categorical',
                            valid_range=[],
                            cf_standard_name=None
                        )
                elif isinstance(facets, list):
                    # Processing facets as list
                    for i, facet_info in enumerate(facets):
                        if isinstance(facet_info, dict) and 'id' in facet_info:
                            facet_name = facet_info['id']
                            bands[facet_name] = BandMetadata(
                                description=f"Facet: {facet_info.get('name', facet_name)}",
                                data_type='string',
                                units='categorical',
                                valid_range=[],
                                cf_standard_name=None
                            )
                        elif isinstance(facet_info, str):
                            # Handle case where facets is a list of strings
                            bands[f"facet_{i}"] = BandMetadata(
                                description=f"Facet: {facet_info}",
                                data_type='string',
                                units='categorical',
                                valid_range=[],
                                cf_standard_name=None
                            )
                else:
                    self.logger.debug(f" Unknown facets format: {type(facets)}")
            except Exception as facet_error:
                self.logger.debug(f" Error processing facets: {facet_error}, facets: {facets}")
                # Continue without facets
            
            self.logger.debug(f" Final bands dict: {type(bands)}, keys: {list(bands.keys())}")
            
            # Convert BandMetadata objects to dictionaries for create_earth_engine_style_metadata
            # Converting bands to dictionaries
            bands_dict = {}
            for name, band in bands.items():
                self.logger.debug(f" Processing band {name}: {type(band)}")
                bands_dict[name] = {
                    'description': band.description,
                    'data_type': band.data_type,
                    'units': band.units,
                    'valid_range': band.valid_range,
                    'cf_standard_name': band.cf_standard_name,
                    'fill_value': band.fill_value
                }
            
            self.logger.debug(f" About to call create_earth_engine_style_metadata")
            self.logger.debug(f" bands_dict type: {type(bands_dict)}, keys: {list(bands_dict.keys())}")
            
            metadata = create_earth_engine_style_metadata(
                asset_id=asset_id,
                title=title,
                description=description,
                temporal_extent=temporal_extent,
                bands=bands_dict,
                provider_name="US Energy Information Administration",
                provider_url="https://www.eia.gov/"
            )
            
            self.logger.debug(f" Successfully created metadata: {type(metadata)}")
            
            # Add EIA-specific properties
            metadata.properties.update({
                'eia:route_id': route_id,
                'eia:frequency': route_details.get('defaultFrequency'),
                'eia:data_sources': route_details.get('sources', []),
                'system:domain': self._infer_domain(route_id)
            })
            
            self.logger.debug(f" Returning metadata")
            return metadata
            
        except Exception as e:
            self.logger.debug(f" Exception occurred: {e}")
            import traceback
            self.logger.debug(f" Full traceback: {traceback.format_exc()}")
            self.logger.error(f"Failed to create enhanced metadata for {route_id}: {e}")
            return None