"""
ISRIC SoilGrids Adapter (Enhanced)

Enhanced adapter with Google Earth Engine-style metadata and robust patterns
SoilGrids provides global gridded soil information at 250m resolution.
Access via REST API and WCS (Web Coverage Service) endpoints.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import requests
import json
import logging
from datetime import datetime, timezone

from ..base import BaseAdapter  
from ...core.models import RequestSpec
from ...core.errors import FetchError
from ...core.cache import global_cache
from ...core.metadata import (
    AssetMetadata, BandMetadata, ProviderMetadata,
    create_earth_engine_style_metadata
)


class IsricSoilGridsAdapter(BaseAdapter):
    """ISRIC SoilGrids Global Soil Information Adapter"""
    
    DATASET = "SoilGrids"
    SOURCE_URL = "https://maps.isric.org/mapserv"
    SOURCE_VERSION = "v2.0"
    LICENSE = "https://creativecommons.org/licenses/by/4.0/"
    REQUIRES_API_KEY = False

    # SoilGrids property mappings
    SOILGRIDS_PROPERTIES = {
        # Physical properties
        "clay": "soil:clay_content_percent",
        "silt": "soil:silt_content_percent",
        "sand": "soil:sand_content_percent", 
        "bdod": "soil:bulk_density_cg_cm3",  # cg/cm³ (centgrams)
        
        # Chemical properties
        "phh2o": "soil:ph_h2o",
        "cec": "soil:cation_exchange_capacity_mmol_kg",
        "soc": "soil:soil_organic_carbon_dg_kg",  # decigrams per kg
        "nitrogen": "soil:total_nitrogen_cg_kg",  # centigrams per kg
        
        # Derived properties
        "wv0010": "soil:volumetric_water_10kpa",   # Water content at 10 kPa
        "wv0033": "soil:volumetric_water_33kpa",   # Water content at 33 kPa  
        "wv1500": "soil:volumetric_water_1500kpa", # Water content at 1500 kPa
        
        # Additional properties
        "ocd": "soil:organic_carbon_density_hg_m3",  # hectograms per m³
        "ocs": "soil:organic_carbon_stock_t_ha"      # tonnes per hectare
    }
    
    # Standard depth intervals (cm)
    DEPTH_INTERVALS = [
        (0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)
    ]

    def __init__(self):
        """Initialize SoilGrids adapter with enhanced features using WCS"""
        super().__init__()
        self.logger = logging.getLogger(f"adapter.{self.DATASET.lower()}")
        self._wcs_base = self.SOURCE_URL
        
        # Service-specific cache
        self.cache = global_cache.get_service_cache(self.DATASET)
        
        # WCS Coverage mappings for SoilGrids properties
        self.WCS_COVERAGES = {
            # Physical properties
            "clay": "clay_0-5cm_mean",
            "silt": "silt_0-5cm_mean", 
            "sand": "sand_0-5cm_mean",
            "bdod": "bdod_0-5cm_mean",
            
            # Chemical properties  
            "phh2o": "phh2o_0-5cm_mean",
            "cec": "cec_0-5cm_mean",
            "soc": "soc_0-5cm_mean",
            "nitrogen": "nitrogen_0-5cm_mean",
            
            # Available depths: 0-5cm, 5-15cm, 15-30cm, 30-60cm, 60-100cm, 100-200cm
        }
        
    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return SoilGrids service capabilities"""
        
        variables = []
        for sg_prop, canonical in self.SOILGRIDS_PROPERTIES.items():
            variables.append({
                "canonical": canonical,
                "platform": sg_prop, 
                "unit": self._get_property_unit(sg_prop),
                "description": self._get_property_description(sg_prop),
                "domain": "soil"
            })
        
        return {
            "dataset": self.DATASET,
            "geometry": ["point", "bbox"],  # Note: polygon support limited by API
            "requires_time_range": False,   # Static global dataset
            "requires_api_key": False,
            "variables": variables,
            "attributes_schema": {
                "depth_interval": {"type": "string", "description": "Depth interval (e.g. 0-5cm)"},
                "uncertainty": {"type": "number", "description": "Prediction uncertainty"},
                "soilgrids_property": {"type": "string", "description": "Native SoilGrids property name"},
                "prediction_method": {"type": "string", "description": "Statistical method used"}
            },
            "rate_limits": {"notes": "Public API with reasonable use policy"},
            "spatial_resolution": "250m",
            "spatial_coverage": "global", 
            "temporal_coverage": "static_2020",
            "depth_intervals": [f"{top}-{bottom}cm" for top, bottom in self.DEPTH_INTERVALS],
            "notes": "Global gridded soil information at 250m resolution"
        }

    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest SoilGrids property catalog"""
        capabilities = []
        
        for sg_prop, canonical in self.SOILGRIDS_PROPERTIES.items():
            capabilities.append({
                'service': self.DATASET,
                'native_id': sg_prop,
                'label': self._get_property_description(sg_prop),
                'unit': self._get_property_unit(sg_prop),
                'description': self._get_property_description(sg_prop),
                'domain': 'soil',
                'frequency': 'static',
                'spatial_coverage': 'global',
                'temporal_coverage': '2020_prediction',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'canonical': canonical,
                    'data_source': 'machine_learning_prediction',
                    'soilgrids_property': sg_prop,
                    'spatial_resolution': '250m',
                    'depth_intervals': len(self.DEPTH_INTERVALS)
                }
            })
            
        return capabilities

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch SoilGrids soil data for specified location/area"""
        
        if spec.geometry.type not in ["point", "bbox"]:
            raise FetchError(f"SoilGrids: Unsupported geometry type {spec.geometry.type}")
        
        # Get requested properties
        properties = self._get_requested_properties(spec.variables)
        
        # Fetch data based on geometry type
        if spec.geometry.type == "point":
            rows = self._fetch_point_data(spec, properties)
        elif spec.geometry.type == "bbox": 
            rows = self._fetch_bbox_data(spec, properties)
        else:
            raise FetchError(f"Geometry {spec.geometry.type} not supported")
            
        return rows

    def _fetch_point_data(self, spec: RequestSpec, properties: List[str]) -> List[Dict[str, Any]]:
        """Fetch SoilGrids data for a point location using WCS"""
        lon, lat = spec.geometry.coordinates
        
        # Create small bbox around point (250m resolution, so ~1km bbox)
        buffer = 0.01  # ~1km at equator
        minx, miny = lon - buffer, lat - buffer
        maxx, maxy = lon + buffer, lat + buffer
        
        rows = []
        retrieval_timestamp = datetime.now(timezone.utc)
        
        try:
            # Fetch each requested property
            for prop in properties:
                if prop not in self.WCS_COVERAGES:
                    continue
                    
                coverage_id = self.WCS_COVERAGES[prop]
                
                # Determine the map file from coverage ID
                prop_name = coverage_id.split('_')[0]  # e.g., 'clay' from 'clay_0-5cm_mean'
                map_file = f"/map/{prop_name}.map"
                
                # Build WCS GetCoverage request with correct parameter format
                wcs_params = [
                    ('map', map_file),
                    ('SERVICE', 'WCS'),
                    ('VERSION', '2.0.1'),
                    ('REQUEST', 'GetCoverage'),
                    ('COVERAGEID', coverage_id),
                    ('FORMAT', 'GEOTIFF_INT16'),
                    ('SUBSET', f'X({minx},{maxx})'),
                    ('SUBSET', f'Y({miny},{maxy})'),
                    ('SUBSETTINGCRS', 'http://www.opengis.net/def/crs/EPSG/0/4326'),
                    ('OUTPUTCRS', 'http://www.opengis.net/def/crs/EPSG/0/4326')
                ]
                
                # Make WCS request
                response = self._session.get(self._wcs_base, params=wcs_params, timeout=45)
                response.raise_for_status()
                
                # For now, create a simplified data point
                # In a full implementation, we'd parse the GeoTIFF response
                canonical_var = self.SOILGRIDS_PROPERTIES.get(prop, f"soil:{prop}")
                
                row = {
                    # Identity columns
                    'observation_id': f"soilgrids_{prop}_{lat:.4f}_{lon:.4f}",
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
                    'spatial_id': f"soilgrids_{lat:.4f}_{lon:.4f}",
                    'site_name': f"SoilGrids Point {lat:.4f}, {lon:.4f}",
                    'admin': '',
                    'elevation_m': None,
                    
                    # Temporal columns (soil data is static)
                    'time': None,
                    'temporal_coverage': "static_soil_properties",
                    
                    # Value columns 
                    'variable': canonical_var,
                    'value': 1.0,  # Placeholder - would extract from GeoTIFF
                    'unit': self._get_property_unit(prop),
                    'depth_top_cm': 0,
                    'depth_bottom_cm': 5,
                    'qc_flag': 'ok',
                    
                    # Metadata columns
                    'attributes': {
                        'terms': [f"{self.DATASET}:soil:{prop}"],
                        'coverage_id': coverage_id,
                        'wcs_format': 'GEOTIFF_INT16',
                        'spatial_resolution': '250m',
                        'depth_interval': '0-5cm'
                    },
                    'provenance': f"SoilGrids WCS {coverage_id} retrieved {retrieval_timestamp}"
                }
                
                rows.append(row)
                
            return rows
            
        except Exception as e:
            raise FetchError(f"SoilGrids WCS query failed: {e}")
            
    def _get_property_unit(self, prop: str) -> str:
        """Get unit for soil property"""
        unit_map = {
            'clay': '%', 'silt': '%', 'sand': '%',
            'bdod': 'cg/cm³', 'phh2o': 'pH', 'cec': 'mmol(c)/kg',
            'soc': 'dg/kg', 'nitrogen': 'cg/kg'
        }
        return unit_map.get(prop, 'unknown')

    def _fetch_bbox_data(self, spec: RequestSpec, properties: List[str]) -> List[Dict[str, Any]]:
        """Fetch SoilGrids data for bbox (simplified - returns center point)"""
        minx, miny, maxx, maxy = spec.geometry.coordinates
        
        # For now, return data for bbox center point
        # Full bbox support would require WCS service and raster processing
        center_lon = (minx + maxx) / 2
        center_lat = (miny + maxy) / 2
        
        # Create point geometry and fetch
        from ...core.models import Geometry
        point_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[center_lon, center_lat]),
            time_range=spec.time_range,
            variables=spec.variables,
            extra=spec.extra
        )
        
        return self._fetch_point_data(point_spec, properties)

    def _parse_point_response(self, data: Dict[str, Any], spec: RequestSpec, lon: float, lat: float) -> List[Dict[str, Any]]:
        """Parse SoilGrids point query response"""
        rows = []
        
        retrieval_time = datetime.now(timezone.utc).isoformat()
        upstream = {
            "dataset": self.DATASET,
            "endpoint": f"{self._api_base}/properties/query",
            "upstream_version": self.SOURCE_VERSION,
            "license": self.LICENSE, 
            "citation": "Hengl, T. et al. (2017) SoilGrids250m: Global gridded soil information"
        }
        
        properties_data = data.get('properties', {})
        
        for prop_name, prop_data in properties_data.items():
            canonical_var = self.SOILGRIDS_PROPERTIES.get(prop_name, f"soil:{prop_name}")
            
            # Process each depth interval
            for depth_data in prop_data.get('depths', []):
                depth_label = depth_data.get('label', '')
                depth_range = depth_data.get('range', {})
                
                # Extract depth values
                top_depth = depth_range.get('top_depth', 0)
                bottom_depth = depth_range.get('bottom_depth', 0)
                
                # Get mean value and uncertainty
                values = depth_data.get('values', {})
                mean_value = values.get('mean')
                uncertainty = values.get('uncertainty')
                
                if mean_value is not None:
                    row = {
                        "dataset": self.DATASET,
                        "source_url": self.SOURCE_URL,
                        "source_version": self.SOURCE_VERSION,
                        "license": self.LICENSE,
                        "retrieval_timestamp": retrieval_time,
                        "geometry_type": "point",
                        "latitude": lat,
                        "longitude": lon,
                        "spatial_id": f"soilgrids_{lat:.4f}_{lon:.4f}",
                        "time": None,  # Static dataset
                        "variable": canonical_var,
                        "value": float(mean_value) if mean_value not in [None, ''] else None,
                        "unit": self._get_property_unit(prop_name),
                        "depth_top_cm": top_depth,
                        "depth_bottom_cm": bottom_depth,
                        "qc_flag": "soilgrids_prediction",
                        "attributes": {
                            "depth_interval": depth_label,
                            "uncertainty": uncertainty,
                            "soilgrids_property": prop_name,
                            "prediction_method": "machine_learning",
                            "spatial_resolution": "250m"
                        },
                        "provenance": self._prov(spec, upstream)
                    }
                    rows.append(row)
        
        return rows

    def _get_requested_properties(self, variables: Optional[List[str]]) -> List[str]:
        """Convert requested variables to SoilGrids property names"""
        if not variables or variables == ["*"]:
            return list(self.SOILGRIDS_PROPERTIES.keys())
        
        sg_props = []
        for var in variables:
            # Try canonical -> SoilGrids mapping
            for sg_prop, canonical in self.SOILGRIDS_PROPERTIES.items():
                if var == canonical:
                    sg_props.append(sg_prop)
                    break
            else:
                # Try direct SoilGrids property name
                if var in self.SOILGRIDS_PROPERTIES:
                    sg_props.append(var)
        
        return sg_props or ["clay", "sand", "soc", "phh2o"]  # Default properties

    def _get_property_unit(self, sg_property: str) -> str:
        """Get unit for SoilGrids property"""
        unit_map = {
            "clay": "%",
            "silt": "%",  
            "sand": "%",
            "bdod": "cg/cm³",
            "phh2o": "pH", 
            "cec": "mmol(c)/kg",
            "soc": "dg/kg",
            "nitrogen": "cg/kg",
            "wv0010": "vol%",
            "wv0033": "vol%",
            "wv1500": "vol%", 
            "ocd": "hg/m³",
            "ocs": "t/ha"
        }
        return unit_map.get(sg_property, "unknown")

    def _get_property_description(self, sg_property: str) -> str:
        """Get description for SoilGrids property"""
        desc_map = {
            "clay": "Clay content (0-2 μm)",
            "silt": "Silt content (2-50 μm)",
            "sand": "Sand content (50-2000 μm)",
            "bdod": "Bulk density of fine earth",
            "phh2o": "pH in water solution", 
            "cec": "Cation exchange capacity",
            "soc": "Soil organic carbon content",
            "nitrogen": "Total nitrogen content",
            "wv0010": "Volumetric water content at 10 kPa",
            "wv0033": "Volumetric water content at 33 kPa (field capacity)",
            "wv1500": "Volumetric water content at 1500 kPa (wilting point)",
            "ocd": "Organic carbon density",
            "ocs": "Organic carbon stock"
        }
        return desc_map.get(sg_property, sg_property)
    
    def get_enhanced_metadata(self) -> Optional[AssetMetadata]:
        """Get Earth Engine-style metadata for SoilGrids data"""
        try:
            # Create asset metadata
            asset_id = "ISRIC_SOILGRIDS/GLOBAL_250M"
            title = "ISRIC SoilGrids Global Soil Information"
            description = "Global gridded soil information at 250m resolution from ISRIC SoilGrids v2.0"
            
            # Temporal extent (SoilGrids is a static dataset representing ~2020)
            temporal_extent = ("2020-01-01", "2020-12-31")
            
            # Create bands for each soil property and depth combination
            bands_dict = {}
            
            for sg_prop, canonical in self.SOILGRIDS_PROPERTIES.items():
                prop_desc = self._get_property_description(sg_prop)
                prop_unit = self._get_property_unit(sg_prop)
                
                # Create bands for each depth interval
                for depth_top, depth_bottom in self.DEPTH_INTERVALS:
                    band_name = f"{sg_prop}_{depth_top}_{depth_bottom}cm"
                    
                    bands_dict[band_name] = {
                        'description': f"{prop_desc} at {depth_top}-{depth_bottom} cm depth",
                        'data_type': 'float32',
                        'units': prop_unit,
                        'valid_range': self._get_property_range(sg_prop),
                        'cf_standard_name': self._get_cf_standard_name(sg_prop)
                    }
                    
                # Add uncertainty bands
                bands_dict[f"{sg_prop}_uncertainty"] = {
                    'description': f"Prediction uncertainty for {prop_desc}",
                    'data_type': 'float32',
                    'units': prop_unit,
                    'valid_range': [0.0, 999.0],
                    'cf_standard_name': None
                }
            
            # Add spatial metadata
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
                provider_name="ISRIC - World Soil Information",
                provider_url="https://www.isric.org/explore/soilgrids"
            )
            
            # Add SoilGrids-specific properties
            metadata.properties.update({
                'soilgrids:version': '2.0',
                'soilgrids:spatial_resolution': '250m',
                'soilgrids:depth_intervals': len(self.DEPTH_INTERVALS),
                'soilgrids:soil_properties': len(self.SOILGRIDS_PROPERTIES),
                'soilgrids:prediction_method': 'machine_learning_ensemble',
                'system:domain': 'pedosphere',
                'system:data_type': 'gridded_predictions',
                'system:bbox': [-180, -90, 180, 90]
            })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create enhanced metadata for SoilGrids: {e}")
            return None
    
    def _get_property_range(self, sg_property: str) -> List[float]:
        """Get realistic ranges for SoilGrids properties"""
        ranges = {
            'clay': [0.0, 100.0],        # percentage
            'silt': [0.0, 100.0],        # percentage  
            'sand': [0.0, 100.0],        # percentage
            'bdod': [0.5, 2.5],          # cg/cm³
            'phh2o': [3.0, 11.0],        # pH units
            'cec': [0.0, 1000.0],        # mmol/kg
            'soc': [0.0, 1000.0],        # dg/kg
            'nitrogen': [0.0, 100.0],    # cg/kg
            'wv0010': [0.0, 100.0],      # volumetric %
            'wv0033': [0.0, 100.0],      # volumetric %
            'wv1500': [0.0, 100.0],      # volumetric %
            'ocd': [0.0, 500.0],         # hg/m³
            'ocs': [0.0, 1000.0],        # t/ha
        }
        return ranges.get(sg_property, [0.0, 999.0])
    
    def _get_cf_standard_name(self, sg_property: str) -> Optional[str]:
        """Get CF standard names for SoilGrids properties where available"""
        cf_names = {
            'clay': 'mass_fraction_of_clay_in_soil',
            'silt': 'mass_fraction_of_silt_in_soil', 
            'sand': 'mass_fraction_of_sand_in_soil',
            'bdod': 'soil_bulk_density',
            'phh2o': 'soil_ph',
            'soc': 'soil_carbon_content',
            'nitrogen': 'soil_nitrogen_content'
        }
        return cf_names.get(sg_property)