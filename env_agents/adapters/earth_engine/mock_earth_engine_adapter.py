"""
Mock Earth Engine Adapter for Demonstration
Shows what Earth Engine capabilities would look like with proper asset discovery
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..base import BaseAdapter
from ...core.models import RequestSpec

logger = logging.getLogger(__name__)


class MockEarthEngineAdapter(BaseAdapter):
    """
    Mock Earth Engine Adapter demonstrating proper asset discovery
    Shows the structure and capabilities that would be available with authentication
    """
    
    DATASET = "EARTH_ENGINE_MOCK_DEMO"
    SOURCE_URL = "https://earthengine.google.com"
    SOURCE_VERSION = "v1.0"
    LICENSE = "Various (see individual datasets)"
    PROVIDER = "Google Earth Engine"
    
    def __init__(self):
        super().__init__()
        self.mock_assets = self._load_mock_assets()
    
    def _load_mock_assets(self) -> List[Dict]:
        """Load mock Earth Engine assets representing the real catalog"""
        return [
            # MODIS Data
            {
                "id": "MODIS/061/MOD11A1",
                "name": "MODIS Land Surface Temperature",
                "description": "MODIS Terra Daily Land Surface Temperature",
                "domain": "climate",
                "variables": ["LST_Day_1km", "LST_Night_1km", "QC_Day", "QC_Night"],
                "temporal_resolution": "daily",
                "spatial_resolution": "1000m",
                "start_date": "2000-02-24",
                "end_date": "present"
            },
            {
                "id": "MODIS/061/MOD13Q1",
                "name": "MODIS Vegetation Indices",  
                "description": "MODIS Terra Vegetation Indices 16-Day Global 250m",
                "domain": "biodiversity",
                "variables": ["NDVI", "EVI", "VI_Quality", "red_reflectance", "NIR_reflectance"],
                "temporal_resolution": "16_day",
                "spatial_resolution": "250m",
                "start_date": "2000-02-18",
                "end_date": "present"
            },
            
            # Landsat Data
            {
                "id": "LANDSAT/LC08/C02/T1_L2",
                "name": "Landsat 8 Surface Reflectance",
                "description": "Landsat 8 Collection 2 Tier 1 Level-2 Surface Reflectance",
                "domain": "remote_sensing",
                "variables": ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7", "ST_B10"],
                "temporal_resolution": "16_day",
                "spatial_resolution": "30m",
                "start_date": "2013-04-11", 
                "end_date": "present"
            },
            
            # Climate Data
            {
                "id": "ECMWF/ERA5_LAND/DAILY_AGGR",
                "name": "ERA5-Land Daily Aggregated",
                "description": "ERA5-Land is a reanalysis dataset providing hourly data",
                "domain": "climate",
                "variables": ["temperature_2m", "total_precipitation", "surface_pressure", "dewpoint_temperature_2m"],
                "temporal_resolution": "daily",
                "spatial_resolution": "11132m",
                "start_date": "1950-01-01",
                "end_date": "present"
            },
            
            # Sentinel Data
            {
                "id": "COPERNICUS/S2_SR_HARMONIZED",
                "name": "Sentinel-2 Surface Reflectance",
                "description": "Sentinel-2 MultiSpectral Instrument Level-2A Surface Reflectance",
                "domain": "remote_sensing",
                "variables": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B11", "B12"],
                "temporal_resolution": "5_day",
                "spatial_resolution": "10m",
                "start_date": "2017-03-28",
                "end_date": "present"
            },
            
            # Global Datasets
            {
                "id": "WorldPop/GP/100m/pop",
                "name": "WorldPop Global Population",
                "description": "High resolution global gridded population data",
                "domain": "demographics",
                "variables": ["population"],
                "temporal_resolution": "yearly",
                "spatial_resolution": "100m",
                "start_date": "2000-01-01",
                "end_date": "2020-01-01"
            },
            
            # Terrain Data
            {
                "id": "USGS/SRTMGL1_003", 
                "name": "SRTM Digital Elevation Data",
                "description": "NASA Shuttle Radar Topography Mission Global 1 arc second",
                "domain": "terrain",
                "variables": ["elevation"],
                "temporal_resolution": "static",
                "spatial_resolution": "30m",
                "start_date": "2000-02-11",
                "end_date": "2000-02-22"
            },
            
            # Water Data
            {
                "id": "JRC/GSW1_4/GlobalSurfaceWater",
                "name": "JRC Global Surface Water",
                "description": "Global Surface Water Explorer dataset",
                "domain": "water",
                "variables": ["occurrence", "change_abs", "change_norm", "seasonality", "recurrence", "transition", "max_extent"],
                "temporal_resolution": "yearly",
                "spatial_resolution": "30m",
                "start_date": "1984-01-01",
                "end_date": "2021-12-31"
            },
            
            # Fire Data
            {
                "id": "FIRMS/MODIS_FIRE_DAILY",
                "name": "MODIS Thermal Anomalies",
                "description": "MODIS Collection 6 NRT Hotspot/Active Fire Detections",
                "domain": "environment",
                "variables": ["T21", "confidence", "daynight"],
                "temporal_resolution": "daily",
                "spatial_resolution": "1000m", 
                "start_date": "2000-11-01",
                "end_date": "present"
            },
            
            # Soil Data  
            {
                "id": "OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M",
                "name": "OpenLandMap Soil Organic Carbon",
                "description": "Soil organic carbon content in x g/kg at 6 standard depths",
                "domain": "soil",
                "variables": ["b0", "b10", "b30", "b60", "b100", "b200"],
                "temporal_resolution": "static",
                "spatial_resolution": "250m",
                "start_date": "2001-01-01",
                "end_date": "2018-01-01"
            }
        ]
    
    def capabilities(self) -> Dict[str, Any]:
        """Return comprehensive Earth Engine asset capabilities"""
        
        # Convert mock assets to variables format
        variables = []
        asset_categories = {}
        
        for asset in self.mock_assets:
            # Add each variable from each asset
            for var in asset["variables"]:
                variable = {
                    "id": f"{asset['id']}:{var}",
                    "canonical": f"earth_engine:{asset['domain']}:{var}",
                    "name": f"{asset['name']} - {var}",
                    "description": f"{asset['description']} - {var} band/variable",
                    "unit": "varies",
                    "domain": asset["domain"],
                    "asset_id": asset["id"],
                    "temporal_resolution": asset["temporal_resolution"],
                    "spatial_resolution": asset["spatial_resolution"],
                    "start_date": asset["start_date"],
                    "end_date": asset["end_date"]
                }
                variables.append(variable)
            
            # Group by domain for categories
            domain = asset["domain"]
            if domain not in asset_categories:
                asset_categories[domain] = {"count": 0, "assets": []}
            asset_categories[domain]["count"] += 1
            asset_categories[domain]["assets"].append(asset["id"])
        
        return {
            "variables": variables,
            "domains": list(set([asset["domain"] for asset in self.mock_assets])),
            "spatial_coverage": {
                "global": True,
                "extent": "Global coverage with varying spatial resolutions",
                "resolutions": ["10m", "30m", "100m", "250m", "1000m", "11132m"]
            },
            "temporal_coverage": {
                "start": "1950-01-01",
                "end": "present",
                "update_frequency": "varies by dataset"
            },
            "description": "Mock Earth Engine adapter demonstrating 900+ available assets with rich metadata",
            "enhancement_level": "earth_engine_gold_standard",
            "asset_categories": asset_categories,
            "total_assets": len(self.mock_assets),
            "total_variables": len(variables),
            "authentication_status": "Mock mode - no authentication required",
            "usage_notes": [
                "This is a demonstration adapter showing Earth Engine capabilities",
                "Real Earth Engine adapter requires authentication and ee library",
                "Assets shown represent actual Google Earth Engine catalog structure",
                "Each asset contains multiple bands/variables for analysis"
            ]
        }
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict]:
        """Return mock Earth Engine data demonstrating the output format"""
        from datetime import datetime, timedelta
        
        logger.info("Mock Earth Engine adapter returning demonstration data")
        
        mock_rows = []
        start_date = datetime.fromisoformat(spec.time_range[0])
        end_date = datetime.fromisoformat(spec.time_range[1])
        
        # Find matching assets for requested variables
        matching_assets = []
        for asset in self.mock_assets:
            for var in asset["variables"]:
                asset_var_id = f"{asset['id']}:{var}"
                if any(asset_var_id in req_var or var in req_var for req_var in spec.variables):
                    matching_assets.append((asset, var))
                    break
        
        if not matching_assets:
            # Default to MODIS LST if no specific match
            matching_assets = [(self.mock_assets[0], "LST_Day_1km")]
        
        # Generate sample data
        current_date = start_date
        observation_id = 1
        
        while current_date <= end_date and len(mock_rows) < 50:  # Limit for demo
            for asset, variable in matching_assets[:2]:  # Limit assets for demo
                row = {
                    'observation_id': f"EE_MOCK_{observation_id}",
                    'dataset': self.DATASET,
                    'source_url': self.SOURCE_URL,
                    'source_version': self.SOURCE_VERSION,
                    'license': self.LICENSE,
                    'retrieval_timestamp': datetime.now(timezone.utc).isoformat(),
                    'geometry_type': spec.geometry.type,
                    'latitude': spec.geometry.coordinates[1] if spec.geometry.coordinates else 37.7749,
                    'longitude': spec.geometry.coordinates[0] if spec.geometry.coordinates else -122.4194,
                    'geom_wkt': f"POINT({spec.geometry.coordinates[0] if spec.geometry.coordinates else -122.4194} {spec.geometry.coordinates[1] if spec.geometry.coordinates else 37.7749})",
                    'spatial_id': None,
                    'site_name': None,
                    'admin': None,
                    'elevation_m': None,
                    'time': current_date.isoformat(),
                    'temporal_coverage': f"{spec.time_range[0]}/{spec.time_range[1]}",
                    'variable': variable,
                    'value': 285.5 + (observation_id % 20),  # Mock temperature values in Kelvin
                    'unit': 'K' if 'LST' in variable else 'dimensionless',
                    'depth_top_cm': None,
                    'depth_bottom_cm': None,
                    'qc_flag': 'GOOD',
                    'attributes': {
                        'dataset_enhanced': True,
                        'enhancement_level': 'earth_engine_gold_standard',
                        'asset_id': asset['id'],
                        'asset_name': asset['name'],
                        'spatial_resolution': asset['spatial_resolution'],
                        'temporal_resolution': asset['temporal_resolution'],
                        'domain': asset['domain'],
                        'mock_data': True,
                        'earth_engine_metadata': {
                            'scale': 1000,
                            'projection': 'EPSG:4326',
                            'asset_type': 'ImageCollection'
                        }
                    },
                    'provenance': {
                        'processing_level': 'L2',
                        'algorithm_version': 'Collection 6.1',
                        'qa_status': 'VALIDATED',
                        'source_sensor': 'MODIS Terra'
                    }
                }
                mock_rows.append(row)
                observation_id += 1
            
            current_date += timedelta(days=1)
        
        return mock_rows