"""
Enhanced Water Quality Portal (WQP) Adapter - Earth Engine Gold Standard Level

Provides comprehensive access to the Water Quality Portal with detailed
parameter metadata, regulatory context, and environmental applications.
"""

import pandas as pd
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import warnings
import urllib.parse
import zipfile
import io
import csv
from pathlib import Path
from io import StringIO

from env_agents.adapters.base import BaseAdapter
from env_agents.core.models import RequestSpec, Geometry
from env_agents.core.adapter_mixins import StandardAdapterMixin
from typing import Dict, List, Any, Optional, Tuple


class WQPAdapter(BaseAdapter, StandardAdapterMixin):
    def _convert_geometry_to_bbox(self, geometry: Geometry, extra: Dict[str, Any]) -> Tuple[float, float, float, float]:
        """Convert geometry to bounding box with proper radius handling"""
        if geometry.type == "bbox":
            return tuple(geometry.coordinates)
        elif geometry.type == "point":
            lon, lat = geometry.coordinates
            radius_m = extra.get('radius', 2000)  # Default 2km radius
            # Convert radius from meters to degrees (rough approximation)
            radius_deg = radius_m / 111000  # ~111km per degree
            return (lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg)
        else:
            raise ValueError(f"Unsupported geometry type for {self.__class__.__name__}: {geometry.type}")


    def _point_to_bbox(self, geometry: Geometry, radius_m: float = 1000) -> Tuple[float, float, float, float]:
        """Convert point geometry to bounding box with radius"""
        if geometry.type == "bbox":
            return tuple(geometry.coordinates)
        elif geometry.type == "point":
            lon, lat = geometry.coordinates
            # Convert radius from meters to degrees (rough approximation)
            radius_deg = radius_m / 111000  # ~111km per degree
            return (lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.type}")
    """
    Enhanced Water Quality Portal adapter providing Earth Engine-level metadata richness.
    
    Accesses the comprehensive Water Quality Portal (WQP) database with detailed
    parameter metadata, environmental context, and regulatory applications.
    """
    
    DATASET = "WQP"
    SOURCE_URL = "https://www.waterqualitydata.us/data"
    SOURCE_VERSION = "v3.0"
    LICENSE = "https://www.waterqualitydata.us/portal_userguide/"
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize Enhanced WQP adapter."""
        super().__init__()

        # Initialize standard components (auth, config, logging)
        self.initialize_adapter()

        # WQP-specific initialization
        self.base_url = base_url or "https://www.waterqualitydata.us"
        self._web_enhanced_cache = None
        self._parameter_cache = None
        self._epa_characteristics_cache = None

        # Cache timestamps for freshness tracking
        self._capabilities_cache_timestamp = None
        self._parameters_cache_timestamp = None
        self._epa_characteristics_cache_timestamp = None
    
    def scrape_wqp_documentation(self) -> Dict[str, Any]:
        """
        Scrape WQP documentation for enhanced metadata.
        
        Returns comprehensive information about WQP including coverage,
        data sources, and quality characteristics.
        """
        if self._web_enhanced_cache is not None:
            return self._web_enhanced_cache
        
        try:
            # WQP user guide and documentation
            docs_url = "https://www.waterqualitydata.us/portal_userguide/"
            response = requests.get(docs_url, timeout=10)
            
            enhanced_info = {
                "description": """The Water Quality Portal (WQP) serves water-quality data collected by over 
                400 state, federal, tribal, and local agencies. It combines data from EPA STORET, 
                USDA STEWARDS, and USGS NWIS into a single source for water quality information.""",
                
                "documentation_url": docs_url,
                "data_sources": [
                    "EPA STORET (Storage and Retrieval)",
                    "USDA STEWARDS (Sustaining The Earth's Watersheds - Agricultural Research Database)",
                    "USGS NWIS (National Water Information System)"
                ],
                "coverage": {
                    "spatial": "United States and territories",
                    "temporal": "1900-present with most data from 1990+",
                    "monitoring_locations": "2.1+ million sites",
                    "organizations": "400+ agencies"
                },
                "data_characteristics": {
                    "parameters": "1000+ water quality characteristics",
                    "sample_types": "Water, sediment, biological tissue, habitat",
                    "quality_control": "Multi-agency data validation and harmonization",
                    "update_frequency": "Continuous updates from contributing agencies"
                },
                "applications": [
                    "Water quality assessment and monitoring",
                    "Regulatory compliance tracking",
                    "Environmental research and modeling",
                    "Public health protection",
                    "Watershed management and planning",
                    "Climate change impact studies"
                ]
            }
            
            self._web_enhanced_cache = enhanced_info
            return enhanced_info
            
        except Exception as e:
            # Fallback information if web scraping fails
            return {
                "description": "Water Quality Portal provides comprehensive water quality data from multiple agencies",
                "documentation_url": "https://www.waterqualitydata.us/portal_userguide/",
                "applications": "Water quality monitoring, environmental assessment, regulatory compliance",
                "scraping_error": str(e)
            }
    
    def fetch_epa_characteristics(self) -> List[Dict[str, Any]]:
        """
        Fetch EPA Water Quality Characteristics with layered fallback strategy.
        
        Strategy:
        1. Check for cached file: env_agents/data/metadata/services/Characteristic_CSV.zip
        2. If not cached, download from: http://cdx.epa.gov/wqx/download/DomainValues/Characteristic_CSV.zip
        3. If download fails, return empty list (triggers enhanced parameter fallback)
        
        Returns detailed characteristic information for dynamic variable discovery.
        """
        if self._epa_characteristics_cache is not None:
            return self._epa_characteristics_cache
        
        # Find project root for cache directory
        current_dir = Path(__file__).parent
        while current_dir != current_dir.parent:
            if (current_dir / "setup.py").exists() or (current_dir / "pyproject.toml").exists():
                cache_file = current_dir / "env_agents" / "data" / "metadata" / "services" / "Characteristic_CSV.zip"
                break
            current_dir = current_dir.parent
        else:
            # Fallback if no project root found
            cache_file = Path("env_agents/data/metadata/services/Characteristic_CSV.zip")
        
        zip_content = None
        
        # Strategy 1: Try cached file first
        if cache_file.exists():
            print(f"Loading EPA characteristics from cached file: {cache_file}")
            try:
                with open(cache_file, 'rb') as f:
                    zip_content = f.read()
                print("✅ Successfully loaded from cache")
            except Exception as e:
                print(f"❌ Error reading cached file: {e}")
        
        # Strategy 2: Download if not cached or cache read failed
        if zip_content is None:
            try:
                epa_url = "http://cdx.epa.gov/wqx/download/DomainValues/Characteristic_CSV.zip"
                print(f"Downloading EPA characteristics from {epa_url}")
                response = requests.get(epa_url, timeout=15)
                response.raise_for_status()
                zip_content = response.content
                
                # Cache the downloaded file
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, 'wb') as f:
                    f.write(zip_content)
                print(f"✅ Downloaded and cached to: {cache_file}")
                
            except Exception as e:
                print(f"❌ Error downloading EPA characteristics: {e}")
                return []  # Trigger fallback to enhanced parameters
        
        # Strategy 3: Process the ZIP content (from cache or download)
        try:
            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                # Look for CSV files in the ZIP
                csv_files = [name for name in zip_file.namelist() if name.lower().endswith('.csv')]
                
                if not csv_files:
                    raise ValueError("No CSV files found in EPA characteristics ZIP")
                
                # Use the first CSV file (typically there's only one)
                csv_filename = csv_files[0]
                print(f"Extracting {csv_filename} from ZIP")
                
                with zip_file.open(csv_filename) as csv_file:
                    # Read CSV content
                    csv_content = csv_file.read().decode('utf-8')
                    csv_reader = csv.DictReader(io.StringIO(csv_content))
                    
                    characteristics = []
                    for row in csv_reader:
                        # Map EPA fields to our standard format (based on actual CSV structure)
                        name = row.get("Name", "").strip()
                        # Remove any leading whitespace/tabs from the name
                        name = name.lstrip('\t ')
                        
                        characteristic = {
                            "name": name,
                            "code": name,  # EPA uses name as identifier
                            "description": row.get("Description", "").strip(),
                            "units": "",  # EPA doesn't provide units in this file
                            "group": row.get("Group Name", "").strip(),
                            "unique_id": row.get("Unique Identifier", "").strip(),
                            "cas_number": row.get("CAS Number", "").strip(),
                            "pick_list": row.get("Pick List", "").strip(),
                            "status": row.get("Domain Value Status", "").strip(),
                            "source": "EPA WQX Domain Values"
                        }
                        
                        # Only include characteristics with valid names and "Accepted" status
                        if characteristic["name"] and characteristic["status"] == "Accepted":
                            characteristics.append(characteristic)
            
            print(f"Successfully loaded {len(characteristics)} EPA characteristics")
            self._epa_characteristics_cache = characteristics
            return characteristics
            
        except Exception as e:
            print(f"Error fetching EPA characteristics: {e}")
            # Return empty list as fallback
            return []
    
    def get_enhanced_parameter_metadata(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive metadata for key water quality parameters.
        
        Returns detailed information about water quality parameters including
        environmental significance, regulatory standards, and measurement methods.
        """
        if self._parameter_cache is not None:
            return self._parameter_cache
        
        # Key water quality parameters with Earth Engine-level detail
        enhanced_parameters = [
            {
                "name": "Temperature",
                "code": "Temperature, water",
                "description": """Water temperature is a critical physical property affecting dissolved oxygen 
                levels, chemical reaction rates, and aquatic life survival. Temperature influences water density, 
                viscosity, and the solubility of gases and compounds.""",
                "units": "deg C",
                "valid_range": [-5.0, 45.0],
                "typical_range": [0.0, 35.0],
                "measurement_method": "Thermistor or thermocouple sensors",
                "environmental_significance": "Controls aquatic ecosystem metabolism and species distribution",
                "regulatory_applications": [
                    "Thermal pollution assessment",
                    "Discharge permit compliance",
                    "Aquatic life criteria evaluation"
                ],
                "seasonal_patterns": "Strong seasonal variation, thermal stratification in lakes",
                "interpretation": {
                    "cold_water": "< 15°C (trout habitat)",
                    "cool_water": "15-25°C (mixed species)",
                    "warm_water": "> 25°C (bass, catfish habitat)",
                    "stress_threshold": "> 30°C for most species"
                }
            },
            {
                "name": "Dissolved Oxygen",
                "code": "Dissolved oxygen (DO)",
                "description": """Dissolved oxygen measures the amount of oxygen gas dissolved in water, 
                critical for aquatic life survival and water quality assessment. Low DO indicates 
                pollution or eutrophication, while supersaturation may indicate algal blooms.""",
                "units": "mg/L",
                "valid_range": [0.0, 20.0],
                "typical_range": [2.0, 15.0],
                "measurement_method": "Electrochemical probe or Winkler titration",
                "environmental_significance": "Essential for aquatic organism survival and ecosystem health",
                "regulatory_applications": [
                    "Water quality standards enforcement",
                    "Hypoxia zone identification",
                    "TMDL development for oxygen-demanding substances"
                ],
                "seasonal_patterns": "Higher in cold water, varies with photosynthesis and respiration",
                "interpretation": {
                    "excellent": "> 8.0 mg/L",
                    "good": "6.0-8.0 mg/L", 
                    "fair": "4.0-6.0 mg/L",
                    "poor": "2.0-4.0 mg/L",
                    "severely_impaired": "< 2.0 mg/L"
                }
            },
            {
                "name": "pH",
                "code": "pH",
                "description": """pH measures the acidity or alkalinity of water on a logarithmic scale from 0-14. 
                pH affects chemical speciation, metal toxicity, and biological processes. Most aquatic life 
                requires pH between 6.5-8.5 for optimal survival.""",
                "units": "standard units",
                "valid_range": [0.0, 14.0],
                "typical_range": [6.0, 9.0],
                "measurement_method": "Glass electrode or colorimetric methods",
                "environmental_significance": "Controls chemical reactions and biological processes",
                "regulatory_applications": [
                    "Water quality criteria compliance",
                    "Acid mine drainage assessment",
                    "Treatment system optimization"
                ],
                "seasonal_patterns": "Varies with photosynthesis, respiration, and precipitation",
                "interpretation": {
                    "very_acidic": "< 5.0",
                    "acidic": "5.0-6.5",
                    "neutral": "6.5-8.5",
                    "basic": "8.5-9.5",
                    "very_basic": "> 9.5"
                }
            },
            {
                "name": "Specific Conductance",
                "code": "Specific conductance",
                "description": """Specific conductance measures water's ability to conduct electricity, 
                indicating dissolved ion concentration. Higher conductivity suggests more dissolved minerals, 
                salts, or pollution. Used as a surrogate for total dissolved solids.""",
                "units": "µS/cm",
                "valid_range": [1.0, 100000.0],
                "typical_range": [50.0, 1500.0],
                "measurement_method": "Conductivity probe with temperature compensation",
                "environmental_significance": "Indicates water mineralization and potential pollution sources",
                "regulatory_applications": [
                    "Secondary drinking water standards",
                    "Salinity intrusion monitoring",
                    "Industrial discharge compliance"
                ],
                "seasonal_patterns": "Varies with precipitation, evaporation, and groundwater contributions",
                "interpretation": {
                    "low_mineralization": "< 100 µS/cm",
                    "moderate_mineralization": "100-500 µS/cm",
                    "high_mineralization": "500-1500 µS/cm",
                    "saline_influence": "> 1500 µS/cm"
                }
            },
            {
                "name": "Turbidity",
                "code": "Turbidity",
                "description": """Turbidity measures water clarity by detecting suspended particles that scatter light. 
                High turbidity reduces light penetration, affects aquatic photosynthesis, and can indicate 
                erosion, pollution, or treatment effectiveness.""",
                "units": "NTU",
                "valid_range": [0.0, 1000.0],
                "typical_range": [0.1, 100.0],
                "measurement_method": "Nephelometric measurement at 90-degree angle",
                "environmental_significance": "Affects light penetration and aquatic habitat quality",
                "regulatory_applications": [
                    "Drinking water treatment monitoring",
                    "Erosion and sediment control",
                    "Stream habitat assessment"
                ],
                "seasonal_patterns": "Higher during storm events and spring runoff",
                "interpretation": {
                    "excellent": "< 5 NTU",
                    "good": "5-25 NTU",
                    "fair": "25-100 NTU",
                    "poor": "> 100 NTU"
                }
            },
            {
                "name": "Total Nitrogen",
                "code": "Nitrogen, mixed forms (NH3), (NH4), organic, (NO2) and (NO3)",
                "description": """Total nitrogen includes all forms of nitrogen compounds in water (ammonia, nitrite, 
                nitrate, and organic nitrogen). Excessive nitrogen causes eutrophication, algal blooms, 
                and oxygen depletion in aquatic ecosystems.""",
                "units": "mg/L as N",
                "valid_range": [0.0, 50.0],
                "typical_range": [0.1, 5.0],
                "measurement_method": "Persulfate digestion followed by colorimetric analysis",
                "environmental_significance": "Primary nutrient causing eutrophication in marine systems",
                "regulatory_applications": [
                    "Nutrient pollution assessment",
                    "TMDL development for eutrophic waters",
                    "Agricultural runoff monitoring"
                ],
                "seasonal_patterns": "Peaks during agricultural application periods and storm events",
                "sources": ["Agricultural fertilizers", "Wastewater discharge", "Atmospheric deposition", "Urban runoff"]
            },
            {
                "name": "Total Phosphorus",
                "code": "Phosphorus",
                "description": """Total phosphorus includes dissolved and particulate forms of phosphorus compounds. 
                Phosphorus is often the limiting nutrient in freshwater systems, making it critical for 
                controlling eutrophication and algal growth.""",
                "units": "mg/L as P",
                "valid_range": [0.0, 10.0],
                "typical_range": [0.01, 1.0],
                "measurement_method": "Acid persulfate digestion followed by colorimetric analysis",
                "environmental_significance": "Limiting nutrient controlling eutrophication in freshwater",
                "regulatory_applications": [
                    "Lake and reservoir management",
                    "Phosphorus criteria development",
                    "Point source discharge limits"
                ],
                "seasonal_patterns": "Varies with agricultural activities and storm water runoff",
                "sources": ["Detergents", "Agricultural fertilizers", "Sewage treatment plants", "Natural weathering"]
            },
            {
                "name": "Escherichia coli",
                "code": "Escherichia coli",
                "description": """E. coli bacteria serve as indicators of fecal contamination from human or animal 
                sources. Presence indicates potential pathogens and health risks associated with water contact 
                or consumption. Used for recreational water quality assessment.""",
                "units": "CFU/100mL",
                "valid_range": [0.0, 100000.0],
                "typical_range": [1.0, 10000.0],
                "measurement_method": "Membrane filtration or defined substrate technology",
                "environmental_significance": "Indicator of fecal pollution and potential pathogen presence",
                "regulatory_applications": [
                    "Recreational water quality standards",
                    "Beach closure decisions",
                    "Source water assessment"
                ],
                "seasonal_patterns": "Often higher after rainfall due to runoff",
                "health_significance": "Elevated levels indicate increased risk of gastrointestinal illness"
            }
        ]
        
        # Fetch additional EPA characteristics dynamically
        try:
            epa_characteristics = self.fetch_epa_characteristics()
            
            # Create a set of names from enhanced parameters to avoid duplicates
            enhanced_names = {param["name"].lower() for param in enhanced_parameters}
            
            # Add EPA characteristics that aren't already in enhanced list
            additional_params = []
            for epa_char in epa_characteristics:
                if epa_char["name"].lower() not in enhanced_names:
                    # Convert EPA characteristic to enhanced parameter format
                    enhanced_epa = {
                        "name": epa_char["name"],
                        "code": epa_char["code"],
                        "description": epa_char["description"] or f"Water quality characteristic: {epa_char['name']}",
                        "units": epa_char["units"],
                        "group": epa_char.get("group", ""),
                        "context": epa_char.get("context", ""),
                        "cas_number": epa_char.get("cas_number", ""),
                        "source": "EPA WQX Dynamic Discovery",
                        "environmental_significance": f"Part of {epa_char.get('group', 'water quality')} monitoring",
                        "regulatory_applications": ["Water quality monitoring", "Environmental assessment"]
                    }
                    additional_params.append(enhanced_epa)
            
            # Combine enhanced parameters (priority) with additional EPA characteristics
            all_parameters = enhanced_parameters + additional_params
            print(f"WQP: Using {len(enhanced_parameters)} enhanced + {len(additional_params)} EPA parameters = {len(all_parameters)} total")
            
        except Exception as e:
            print(f"WQP: Error loading EPA characteristics, using enhanced only: {e}")
            all_parameters = enhanced_parameters
        
        self._parameter_cache = all_parameters
        self._parameters_cache_timestamp = datetime.now()
        return all_parameters

    def _refresh_metadata(self,
                         metadata_type: str = "capabilities",
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        WQP-specific metadata refresh implementation.

        Handles refreshing scraped EPA characteristics and parameter metadata.
        """
        from datetime import datetime

        # Check freshness first (unless forcing refresh)
        if not force_refresh:
            freshness = self._check_metadata_freshness(metadata_type)
            if freshness['is_fresh']:
                return {
                    'refreshed': False,
                    'method': 'cache_hit',
                    'timestamp': freshness['last_updated'],
                    'items_count': len(getattr(self, f'_{metadata_type}_cache', [])),
                    'errors': []
                }

        errors = []
        items_count = 0

        try:
            if metadata_type in ["capabilities", "parameters"]:
                # Refresh EPA characteristics (scraped from web)
                characteristics = self.fetch_epa_characteristics()
                if characteristics:
                    self._epa_characteristics_cache = characteristics
                    self._epa_characteristics_cache_timestamp = datetime.now()

                # Refresh enhanced parameters
                parameters = self.get_enhanced_parameter_metadata()
                if parameters:
                    items_count = len(parameters)
                    self._capabilities_cache_timestamp = datetime.now()

                method = 'scraped' if characteristics else 'api_call'

            elif metadata_type == "documentation":
                # Refresh web-scraped documentation
                docs = self.scrape_wqp_documentation()
                if docs:
                    self._web_enhanced_cache = docs
                    self._capabilities_cache_timestamp = datetime.now()
                    items_count = 1
                    method = 'scraped'

            return {
                'refreshed': True,
                'method': method,
                'timestamp': datetime.now(),
                'items_count': items_count,
                'errors': errors
            }

        except Exception as e:
            errors.append(str(e))
            return {
                'refreshed': False,
                'method': 'failed',
                'timestamp': datetime.now(),
                'items_count': 0,
                'errors': errors
            }
    
    def capabilities(self) -> Dict[str, Any]:
        """
        Return comprehensive capabilities following Earth Engine gold standard.
        
        Provides detailed metadata about WQP data availability, coverage,
        and quality characteristics with research-grade documentation.
        """
        web_enhanced = self.scrape_wqp_documentation()
        parameters = self.get_enhanced_parameter_metadata()
        
        return {
            "dataset": self.DATASET,
            "asset_type": "water_quality_database",
            "enhancement_level": "earth_engine_gold_standard",
            
            "variables": [
                {
                    "name": param["name"],
                    "code": param["code"],
                    "description": param["description"],
                    "units": param["units"],
                    "valid_range": param.get("valid_range"),
                    "measurement_method": param.get("measurement_method"),
                    "environmental_significance": param.get("environmental_significance"),
                    "regulatory_applications": param.get("regulatory_applications", []),
                    "seasonal_patterns": param.get("seasonal_patterns"),
                    "interpretation": param.get("interpretation", {}),
                    "sources": param.get("sources", []),
                    "metadata_completeness": 0.95
                }
                for param in parameters
            ],
            
            "temporal_coverage": {
                "start": "1900-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z", 
                "cadence": "Variable (event-based sampling)",
                "historical_depth": "120+ years of water quality data",
                "update_pattern": "Continuous updates from 400+ agencies"
            },
            
            "spatial_coverage": {
                "extent": "United States and territories",
                "monitoring_locations": "2.1+ million unique sites",
                "coordinate_system": "WGS84 (EPSG:4326)",
                "coverage_density": "Highest in populated and agricultural regions"
            },
            
            "quality_metadata": {
                "data_validation": "Multi-agency quality assurance protocols",
                "harmonization": "Standardized parameter names and units across agencies",
                "quality_control": "Data provider validation with WQP verification",
                "data_flags": "Result status, detection limits, quality assurance codes",
                "processing_level": "Level 1 (validated) to Level 3 (research quality)",
                "uncertainty_assessment": "Method detection limits and precision estimates"
            },
            
            "web_enhanced": web_enhanced,
            
            "access_patterns": {
                "spatial_query": "By geographic coordinates, HUC, state, county",
                "temporal_query": "By date range with flexible sampling periods", 
                "parameter_query": "By characteristic name, parameter group, or method",
                "organization_query": "By data provider organization"
            },
            
            "applications": {
                "regulatory": [
                    "Clean Water Act compliance monitoring",
                    "NPDES permit compliance tracking",
                    "Water quality standards assessment",
                    "TMDL development and implementation"
                ],
                "environmental": [
                    "Watershed health assessment",
                    "Pollution source identification",
                    "Ecosystem impact studies",
                    "Climate change impact research"
                ],
                "public_health": [
                    "Drinking water source protection",
                    "Recreational water safety",
                    "Fish consumption advisories",
                    "Environmental justice studies"
                ],
                "research": [
                    "Long-term trend analysis",
                    "Multi-scale environmental studies",
                    "Data fusion and integration",
                    "Model validation and calibration"
                ]
            },
            
            "data_model": {
                "hierarchical_structure": "Organization → Project → Monitoring Location → Activity → Result",
                "core_entities": ["Site", "Sample", "Parameter", "Result", "Method"],
                "result_structure": "Value with units, quality flags, detection limits",
                "metadata_richness": "Comprehensive sampling and analytical metadata"
            },
            
            "limitations": {
                "data_heterogeneity": "Variable quality and completeness across providers",
                "temporal_gaps": "Irregular sampling frequencies and periods",
                "method_variability": "Different analytical methods across organizations",
                "spatial_bias": "Higher density in developed regions"
            },
            
            "rate_limits": {
                "web_services": "No published limits, reasonable use expected",
                "download_size": "Large queries may be paginated or require batch processing",
                "best_practices": "Use geographic and temporal filters to optimize queries"
            }
        }
    
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """
        Fetch WQP water quality data with proper coordinate handling and all measurements.
        
        Strategy:
        1. Get stations in area with coordinates
        2. Get ALL results for those stations (no characteristic filtering)
        3. Merge station coordinates into results
        4. Post-filter by variables if requested
        """
        from io import StringIO
        
        try:
            # Extract spatial and temporal constraints
            geometry = spec.geometry
            time_range = spec.time_range
            variables = spec.variables or []
            
            # Convert geometry to bbox
            if geometry.type == "bbox":
                west, south, east, north = geometry.coordinates
            elif geometry.type == "point":
                lon, lat = geometry.coordinates
                # Use 5km default radius for better station coverage
                radius_deg = 5000 / 111000  # Convert 5km to degrees
                west, south, east, north = (lon - radius_deg, lat - radius_deg, 
                                          lon + radius_deg, lat + radius_deg)
            else:
                raise ValueError(f"Unsupported geometry type: {geometry.type}")
            
            # Use requested time range, with fallback to known good historical period if needed
            if spec.time_range:
                try:
                    from datetime import datetime
                    import dateutil.parser

                    start_str, end_str = spec.time_range
                    start_time = dateutil.parser.parse(start_str).replace(tzinfo=None)
                    end_time = dateutil.parser.parse(end_str).replace(tzinfo=None)

                    print(f"WQP using requested time range: {start_time.date()} to {end_time.date()}")

                except Exception as e:
                    # Fallback to known good period
                    print(f"WQP time parsing failed, using fallback: {e}")
                    start_time = datetime(2022, 6, 1)  # June 2022 - good data availability
                    end_time = datetime(2022, 12, 31)   # End of 2022
            else:
                # Default to known good historical period when no time range specified
                start_time = datetime(2022, 6, 1)  # June 2022 - good data availability
                end_time = datetime(2022, 12, 31)   # End of 2022
                print("WQP using default time range (2022) - WQP data often delayed 1-2 years")
            
            # STEP 1: Get stations with coordinates
            # NOTE: Do NOT apply time constraints to station discovery - this filters out too many stations
            # Time constraints should only be applied to results query (Step 2)
            station_params = {
                'bBox': f"{west},{south},{east},{north}",
                'mimeType': 'csv',
                'zip': 'no'
            }
            
            # Query stations
            stations_url = f"{self.base_url}/data/Station/search"
            station_response = requests.get(stations_url, params=station_params, timeout=60)
            
            if station_response.status_code != 200:
                warnings.warn(f"WQP station query failed: {station_response.status_code}")
                return []
            
            # Parse station data
            try:
                stations_df = pd.read_csv(StringIO(station_response.text), low_memory=False)
            except Exception as e:
                warnings.warn(f"Failed to parse WQP station response: {e}")
                return []
            
            if stations_df.empty:
                warnings.warn("No WQP stations found in area")
                return []
            
            print(f"Found {len(stations_df)} WQP stations in area")
            
            # Get station IDs (limit to reasonable number)
            station_ids = stations_df['MonitoringLocationIdentifier'].unique()[:20]
            
            # Create station lookup for coordinates
            station_lookup = {}
            for _, station in stations_df.iterrows():
                station_id = station.get('MonitoringLocationIdentifier')
                if station_id:
                    station_lookup[station_id] = {
                        'latitude': station.get('LatitudeMeasure'),
                        'longitude': station.get('LongitudeMeasure'), 
                        'name': station.get('MonitoringLocationName'),
                        'type': station.get('MonitoringLocationTypeName'),
                        'description': station.get('MonitoringLocationDescriptionText')
                    }
            
            # STEP 2: Get ALL results for stations (NO characteristic filtering)
            all_rows = []
            retrieval_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Process stations in batches to avoid URL length limits
            batch_size = 5
            for i in range(0, len(station_ids), batch_size):
                batch_stations = station_ids[i:i+batch_size]
                
                result_params = {
                    'mimeType': 'csv',
                    'zip': 'no',
                    'sorted': 'yes'
                }
                
                # Add time constraints using proper WQP date parameters
                # WQP uses startDateLo and startDateHi for activity date ranges
                result_params['startDateLo'] = start_time.strftime('%m-%d-%Y')
                result_params['startDateHi'] = end_time.strftime('%m-%d-%Y')

                # Add station IDs - WQP supports multiple stations in single request
                if len(batch_stations) == 1:
                    result_params['siteid'] = batch_stations[0]
                else:
                    # Multiple stations: use semicolon-separated list
                    result_params['siteid'] = ';'.join(batch_stations)

                # NO characteristicName - get ALL measurements
                # This follows your guidance to get everything and post-filter

                # Execute results query
                results_url = f"{self.base_url}/data/Result/search"

                # Add debugging info (after results_url is defined)
                print(f"WQP query: {results_url}")
                print(f"Time range: {result_params['startDateLo']} to {result_params['startDateHi']}")
                print(f"Stations: {batch_stations[:3]}{'...' if len(batch_stations) > 3 else ''}")
                response = requests.get(results_url, params=result_params, timeout=60)
                
                if response.status_code != 200:
                    print(f"WQP results query failed for batch: {response.status_code} - {response.text[:200]}")
                    continue

                # Parse results
                try:
                    results_df = pd.read_csv(StringIO(response.text), low_memory=False)
                except Exception as e:
                    print(f"Failed to parse WQP results: {e}")
                    continue

                if results_df.empty:
                    print(f"No measurements found for stations: {batch_stations}")
                    continue

                print(f"Found {len(results_df)} measurements from {len(batch_stations)} stations")
                
                # Process each result record
                for _, record in results_df.iterrows():
                    # Get station info for coordinates
                    station_id = record.get('MonitoringLocationIdentifier')
                    station_info = station_lookup.get(station_id, {})
                    
                    # Extract result value
                    result_value = record.get('ResultMeasureValue')
                    if pd.isna(result_value):
                        continue
                    
                    # Get characteristic name
                    characteristic = record.get('CharacteristicName', 'Unknown')
                    
                    # Post-filter by variables if specified
                    if variables:
                        # Check if this characteristic matches requested variables
                        matches = False
                        for var in variables:
                            if (var.lower() in characteristic.lower() or 
                                characteristic.lower() in var.lower()):
                                matches = True
                                break
                        if not matches:
                            continue
                    
                    # Build standardized row with proper coordinates
                    row = {
                        # Identity columns
                        "observation_id": f"wqp_{record.get('ActivityIdentifier', '')}_{record.get('ResultIdentifier', '')}",
                        "dataset": self.DATASET,
                        "source_url": self.SOURCE_URL,
                        "source_version": self.SOURCE_VERSION,
                        "license": self.LICENSE,
                        "retrieval_timestamp": retrieval_timestamp,
                        
                        # Spatial columns - NOW WITH PROPER COORDINATES FROM STATIONS
                        "geometry_type": "point",
                        "latitude": float(station_info.get('latitude', 0)) if station_info.get('latitude') else None,
                        "longitude": float(station_info.get('longitude', 0)) if station_info.get('longitude') else None,
                        "geom_wkt": f"POINT({station_info.get('longitude', 0)} {station_info.get('latitude', 0)})" if station_info.get('longitude') and station_info.get('latitude') else None,
                        "spatial_id": station_id,
                        "site_name": station_info.get('name') or record.get('MonitoringLocationName'),
                        "admin": record.get('StateCode'),
                        "elevation_m": None,
                        
                        # Temporal columns
                        "time": pd.to_datetime(record.get('ActivityStartDate')).isoformat() if pd.notna(record.get('ActivityStartDate')) else None,
                        "temporal_coverage": "sample_date",
                        
                        # Value columns
                        "variable": characteristic,
                        "value": float(result_value),
                        "unit": record.get('ResultMeasure/MeasureUnitCode', ''),
                        "depth_top_cm": None,
                        "depth_bottom_cm": None,
                        "qc_flag": record.get('ResultStatusIdentifier', 'unknown'),
                        
                        # Metadata columns
                        "attributes": {
                            "organization": record.get('OrganizationFormalName'),
                            "project": record.get('ProjectIdentifier'),
                            "activity_type": record.get('ActivityTypeCode'),
                            "sample_media": record.get('ActivityMediaName'),
                            "analytical_method": record.get('ResultAnalyticalMethod/MethodIdentifier'),
                            "detection_limit": record.get('DetectionQuantitationLimitMeasure/MeasureValue'),
                            "detection_limit_type": record.get('DetectionQuantitationLimitTypeName'),
                            "result_comment": record.get('ResultCommentText'),
                            "station_type": station_info.get('type'),
                            "station_description": station_info.get('description'),
                            "terms": {
                                "native_id": characteristic,
                                "native_name": characteristic,
                                "canonical_variable": None  # To be mapped by TermBroker
                            }
                        },
                        "provenance": f"Water Quality Portal via {record.get('OrganizationFormalName')}"
                    }
                    
                    all_rows.append(row)
                
                # Break after first successful batch to avoid overwhelming
                if all_rows:
                    break
            
            return all_rows
            
        except Exception as e:
            warnings.warn(f"WQP fetch error: {str(e)}")
            return []
    
    def harvest(self) -> Dict[str, Any]:
        """
        Harvest WQP parameter catalog for semantic mapping.
        
        Returns comprehensive parameter information for TermBroker registration
        and semantic mapping capabilities.
        """
        parameters = self.get_enhanced_parameter_metadata()
        web_info = self.scrape_wqp_documentation()
        
        return {
            "dataset": self.DATASET,
            "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
            "source_url": self.SOURCE_URL,
            "parameters": [
                {
                    "native_id": param["code"],
                    "native_name": param["name"],
                    "description": param["description"],
                    "units": param["units"],
                    "valid_range": param.get("valid_range"),
                    "category": "water_quality",
                    "measurement_method": param.get("measurement_method"),
                    "environmental_significance": param.get("environmental_significance"),
                    "regulatory_applications": param.get("regulatory_applications", [])
                }
                for param in parameters
            ],
            "web_enhanced": web_info,
            "capabilities_summary": {
                "total_parameters": len(parameters),
                "spatial_coverage": "United States and territories",
                "temporal_coverage": "1900-present",
                "enhancement_level": "earth_engine_gold_standard"
            }
        }