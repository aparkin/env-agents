"""
USDA SURGO (Soil Survey Geographic Database) Adapter

SURGO provides detailed soil information for the United States at scales of 1:24,000 or larger.
Access via USDA Web Soil Survey API and Soil Data Access (SDA) web service.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import requests
import json
from datetime import datetime, timezone

from ..base import BaseAdapter
from ...core.models import RequestSpec
from ...core.errors import FetchError


class UsdaSurgoAdapter(BaseAdapter):
    """USDA SURGO Soil Survey Data Adapter"""
    
    DATASET = "USDA_SURGO"
    SOURCE_URL = "https://sdmdataaccess.sc.egov.usda.gov"  # Soil Data Access
    SOURCE_VERSION = "current" 
    LICENSE = "https://www.usda.gov/policies-and-links/open"
    REQUIRES_API_KEY = False

    # SURGO soil property mappings (validated against actual API)
    SOIL_PROPERTIES = {
        # Physical properties
        "claytotal_r": "soil:clay_content_percent",
        "silttotal_r": "soil:silt_content_percent", 
        "sandtotal_r": "soil:sand_content_percent",
        "om_r": "soil:organic_matter_percent",
        "dbthirdbar_r": "soil:bulk_density_g_cm3",
        "wthirdbar_r": "soil:field_capacity_percent",
        "wfifteenbar_r": "soil:wilting_point_percent",
        "awc_r": "soil:available_water_capacity",
        
        # Chemical properties  
        "ph1to1h2o_r": "soil:ph_h2o",
        "ph01mcacl2_r": "soil:ph_cacl2",
        "cec7_r": "soil:cation_exchange_capacity",
        "ecec_r": "soil:effective_cec",
        "sumbases_r": "soil:sum_of_bases"
        
        # Note: p_r and k_r (phosphorus/potassium) not available in API
    }

    def __init__(self):
        super().__init__()
        # Use exact working URL from legacy (case sensitive!)
        self._sda_url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
        
    def capabilities(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return SURGO service capabilities"""
        
        # Build variables list from soil properties
        variables = []
        for surgo_prop, canonical in self.SOIL_PROPERTIES.items():
            variables.append({
                "canonical": canonical,
                "platform": surgo_prop,
                "unit": self._get_property_unit(surgo_prop),
                "description": self._get_property_description(surgo_prop),
                "domain": "soil"
            })
        
        return {
            "dataset": self.DATASET,
            "geometry": ["point", "bbox", "polygon"],
            "requires_time_range": False,  # Soil data is typically static
            "requires_api_key": False,
            "variables": variables,
            "attributes_schema": {
                "map_unit_key": {"type": "string", "description": "SURGO map unit key"},
                "component_name": {"type": "string", "description": "Soil component name"},
                "horizon_designation": {"type": "string", "description": "Soil horizon (A, B, C, etc.)"},
                "depth_top_cm": {"type": "number", "description": "Top depth of horizon"},
                "depth_bottom_cm": {"type": "number", "description": "Bottom depth of horizon"},
                "component_percent": {"type": "number", "description": "Percent of map unit"}
            },
            "rate_limits": {"notes": "USDA SDA service has query limits"},
            "spatial_resolution": "1:24,000 scale or larger",
            "temporal_coverage": "survey_year_specific",
            "notes": "Detailed soil survey data for continental United States"
        }

    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest SURGO soil property catalog"""
        capabilities = []
        
        for surgo_prop, canonical in self.SOIL_PROPERTIES.items():
            capabilities.append({
                'service': self.DATASET,
                'native_id': surgo_prop,
                'label': self._get_property_description(surgo_prop),
                'unit': self._get_property_unit(surgo_prop),
                'description': self._get_property_description(surgo_prop),
                'domain': 'soil',
                'frequency': 'static',
                'spatial_coverage': 'continental_us',
                'temporal_coverage': 'survey_date_specific',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'canonical': canonical,
                    'data_source': 'soil_survey',
                    'surgo_property': surgo_prop,
                    'measurement_method': 'laboratory_analysis'
                }
            })
            
        return capabilities

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch SURGO soil data for specified location/area"""
        
        if spec.geometry.type not in ["point", "bbox", "polygon"]:
            raise FetchError(f"SURGO: Unsupported geometry type {spec.geometry.type}")
        
        # Get requested soil properties  
        properties = self._get_requested_properties(spec.variables)
        
        # Query SURGO database (pass geometry directly)
        soil_data = self._query_surgo_database(spec.geometry, properties)
        
        # Convert to standardized rows
        rows = self._parse_surgo_data(soil_data, spec)
        
        return rows

    def _build_spatial_query(self, geometry) -> str:
        """Build spatial SQL query for SURGO database"""
        
        if geometry.type == "point":
            lon, lat = geometry.coordinates
            # Use point-in-polygon query for SURGO map units
            return f"""
            SELECT mu.mukey, mu.musym, mu.muname, co.cokey, co.compname, co.comppct_r
            FROM mapunit mu
            INNER JOIN component co ON mu.mukey = co.mukey  
            INNER JOIN muaggatt ma ON mu.mukey = ma.mukey
            WHERE mu.mukey IN (
                SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84(
                    'point({lon} {lat})'
                )
            )
            AND co.majcompflag = 'Yes'
            ORDER BY co.comppct_r DESC
            """.format(lon=lon, lat=lat)
            
        elif geometry.type == "bbox":
            minx, miny, maxx, maxy = geometry.coordinates
            wkt_polygon = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
            
            return f"""
            SELECT mu.mukey, mu.musym, mu.muname, co.cokey, co.compname, co.comppct_r
            FROM mapunit mu  
            INNER JOIN component co ON mu.mukey = co.mukey
            WHERE mu.mukey IN (
                SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84(
                    '{wkt_polygon}'
                )
            )
            AND co.majcompflag = 'Yes'
            ORDER BY co.comppct_r DESC
            """
            
        else:
            raise FetchError(f"Geometry type {geometry.type} not yet implemented for SURGO")

    def _get_requested_properties(self, variables: Optional[List[str]]) -> List[str]:
        """Convert requested variables to SURGO property names"""
        if not variables or variables == ["*"]:
            return list(self.SOIL_PROPERTIES.keys())
        
        # Legacy variable name mappings  
        legacy_mappings = {
            "soil:clay_pct": "claytotal_r",
            "soil:sand_pct": "sandtotal_r", 
            "soil:silt_pct": "silttotal_r",
            "soil:ph_h2o": "ph1to1h2o_r",
            "soil:bulk_density": "dbthirdbar_r",
            "soil:cec": "cec7_r"
        }
        
        surgo_props = []
        for var in variables:
            # Try legacy mapping first
            if var in legacy_mappings:
                surgo_props.append(legacy_mappings[var])
                continue
                
            # Try canonical -> SURGO mapping
            for surgo_prop, canonical in self.SOIL_PROPERTIES.items():
                if var == canonical:
                    surgo_props.append(surgo_prop)
                    break
            else:
                # Try direct SURGO property name
                if var in self.SOIL_PROPERTIES:
                    surgo_props.append(var)
        
        return surgo_props or ["claytotal_r", "om_r", "ph1to1h2o_r"]  # Default properties

    def _query_surgo_database(self, geometry, properties: List[str]) -> List[Dict[str, Any]]:
        """Query SURGO database using Option 2: Adaptive Approach"""
        
        # Build WKT string for geometry
        if geometry.type == "point":
            lon, lat = geometry.coordinates
            aoi_wkt = f"POINT ({lon} {lat})"
        elif geometry.type == "bbox":
            minx, miny, maxx, maxy = geometry.coordinates
            aoi_wkt = f"POLYGON (({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
        else:
            aoi_wkt = geometry.coordinates
        
        # Escape single quotes  
        aoi_wkt_safe = aoi_wkt.replace("'", "''")
        
        # Option 2: Adaptive Approach - Try dynamic query first, fallback to fixed
        try:
            return self._fetch_dynamic_optimized(aoi_wkt_safe, properties)
        except Exception as e:
            # Fallback to fixed query approach
            return self._fetch_fixed_and_filter(aoi_wkt_safe, properties)

    def _api_supports_dynamic_queries(self) -> bool:
        """Check if SURGO API supports dynamic property queries"""
        # Test with a simple 2-property query to see if API is stable
        try:
            test_query = """
            SELECT TOP 1 mu.mukey, ch.claytotal_r, ch.sandtotal_r
            FROM mapunit mu
            JOIN component c ON mu.mukey = c.mukey  
            JOIN chorizon ch ON c.cokey = ch.cokey
            WHERE mu.mukey = '1234567'
            """
            
            payload = {
                "query": test_query,
                "format": "JSON+COLUMNNAME"
            }
            
            response = self._session.post(
                self._sda_url,
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=30
            )
            
            # If we get 200 response with proper JSON, dynamic queries are supported
            return response.status_code == 200 and "application/json" in response.headers.get("content-type", "")
            
        except Exception:
            return False

    def _fetch_dynamic_optimized(self, aoi_wkt_safe: str, properties: List[str]) -> List[Dict[str, Any]]:
        """Attempt intelligent dynamic query with optimized property selection"""
        
        # Map requested properties to valid SURGO columns
        valid_properties = []
        for prop in properties:
            # Try direct SURGO property first (handles * case)
            if prop in self.SOIL_PROPERTIES:
                valid_properties.append(prop)
            else:
                # Try reverse lookup from canonical names
                for surgo_prop, canonical in self.SOIL_PROPERTIES.items():
                    if prop == canonical:
                        valid_properties.append(surgo_prop)
                        break
        
        # If no valid properties found, use default set
        if not valid_properties:
            valid_properties = ["claytotal_r", "ph1to1h2o_r", "om_r"]
        
        # API can handle all 13 available properties - no arbitrary limit needed
        # Discovery shows SURGO can handle up to 13 properties in a single query
        
        # Build dynamic query with requested properties
        property_columns = ",".join([f"ch.{prop}" for prop in valid_properties])
        
        sql_query = f"""
        ;WITH aoi AS (
          SELECT DISTINCT mukey
          FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
        )
        SELECT mu.mukey,c.cokey,c.comppct_r,ch.chkey,ch.hzdept_r,ch.hzdepb_r,
               {property_columns}
        FROM aoi
        JOIN mapunit AS mu ON mu.mukey = aoi.mukey
        JOIN component AS c ON c.mukey = mu.mukey AND c.comppct_r IS NOT NULL
        JOIN chorizon AS ch ON ch.cokey = c.cokey
        WHERE ch.hzdept_r < 30 AND ch.hzdepb_r > 0
        """
        
        return self._execute_surgo_query(sql_query)

    def _fetch_fixed_and_filter(self, aoi_wkt_safe: str, properties: List[str]) -> List[Dict[str, Any]]:
        """Use proven fixed query, then client-side filtering"""
        
        # Use exact working query from legacy - FIXED property list (this is crucial!)
        sql_query = f"""
        ;WITH aoi AS (
          SELECT DISTINCT mukey
          FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
        )
        SELECT mu.mukey,c.cokey,c.comppct_r,ch.chkey,ch.hzdept_r,ch.hzdepb_r,
               ch.claytotal_r,ch.sandtotal_r,ch.silttotal_r,ch.ph1to1h2o_r,ch.dbovendry_r,ch.cec7_r
        FROM aoi
        JOIN mapunit AS mu ON mu.mukey = aoi.mukey
        JOIN component AS c ON c.mukey = mu.mukey AND c.comppct_r IS NOT NULL
        JOIN chorizon  AS ch ON ch.cokey = c.cokey
        WHERE ch.hzdept_r < 30 AND ch.hzdepb_r > 0
        """
        
        return self._execute_surgo_query(sql_query)

    def _execute_surgo_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SURGO query with robust error handling"""
        
        # Try METADATA format first for richer information, fallback to basic format
        return self._execute_with_format_fallback(sql_query)

    def _execute_with_format_fallback(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute query trying METADATA format first, then fallback to basic format"""
        
        # Try formats in order of preference
        formats_to_try = [
            ("JSON+COLUMNNAME+METADATA", "with metadata"),
            ("JSON+COLUMNNAME", "basic format")
        ]
        
        for format_str, description in formats_to_try:
            try:
                payload = {
                    "query": sql_query,
                    "format": format_str
                }
                headers = {
                    "Accept": "application/json", 
                    "Content-Type": "application/json"
                }
                
                response = self._session.post(
                    self._sda_url,
                    json=payload,
                    headers=headers,
                    timeout=120
                )
                response.raise_for_status()
                
                # Check content type
                if "application/json" not in response.headers.get("content-type", "").lower():
                    continue  # Try next format
                
                data = response.json()
                result = self._parse_sda_response_enhanced(data, format_str)
                
                if result:  # Successfully parsed and got data
                    return result
                    
            except Exception:
                continue  # Try next format
        
        raise FetchError(f"All SURGO query formats failed for query")

    def _parse_sda_response_enhanced(self, data, format_str: str) -> List[Dict[str, Any]]:
        """Enhanced SDA response parser that handles metadata rows"""
        
        def _coerce_with_metadata_handling(table_obj):
            """Convert SDA Table format to list of dicts, handling metadata rows"""
            if isinstance(table_obj, list):
                # Handle list of lists format: [["col1","col2"], ["metadata"], ["val1","val2"], ...]
                if table_obj and isinstance(table_obj[0], list):
                    if len(table_obj) > 1:
                        headers = table_obj[0]  # First row is headers
                        rows = table_obj[1:]     # Rest are potential data/metadata rows
                        
                        # Filter out metadata rows if using METADATA format
                        if "METADATA" in format_str:
                            data_rows = []
                            for row in rows:
                                if isinstance(row, list) and len(row) > 0:
                                    first_cell = str(row[0])
                                    # Skip metadata rows containing column information
                                    if ("ColumnOrdinal=" not in first_cell and 
                                        "ProviderType=" not in first_cell and
                                        "NumericPrecision=" not in first_cell):
                                        data_rows.append(row)
                            rows = data_rows
                        
                        return [dict(zip(headers, row)) for row in rows]
                    return []
                
                # Already list of dicts
                if table_obj and isinstance(table_obj[0], dict): 
                    return table_obj
                return [dict(enumerate(row)) for row in table_obj]  # fallback
                
            if isinstance(table_obj, dict):
                cols = table_obj.get("Columns")
                rows = table_obj.get("Rows")
                if isinstance(cols, list) and isinstance(rows, list):
                    if cols and isinstance(cols[0], dict) and "Name" in cols[0]:
                        colnames = [c["Name"] for c in cols]
                    else:
                        colnames = list(cols)
                    out = []
                    for row in rows:
                        if isinstance(row, list):
                            out.append({k: v for k, v in zip(colnames, row)})
                        elif isinstance(row, dict):
                            out.append(row)
                    return out
            return []
        
        # Extract data from various SDA response formats
        if isinstance(data, dict) and "Table" in data: 
            return _coerce_with_metadata_handling(data["Table"])
        if isinstance(data, dict) and "Rows" in data: 
            return _coerce_with_metadata_handling(data)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            first = data[0]
            if "Table" in first: 
                return _coerce_with_metadata_handling(first["Table"])
            if "Rows" in first: 
                return _coerce_with_metadata_handling(first)
        return []

    def _parse_sda_response(self, data) -> List[Dict[str, Any]]:
        """Parse SDA JSON response using legacy approach"""
        
        def _coerce(table_obj):
            """Convert SDA Table format to list of dicts"""
            if isinstance(table_obj, list):
                # Handle list of lists format: [["col1","col2"], ["val1","val2"], ...]
                if table_obj and isinstance(table_obj[0], list):
                    if len(table_obj) > 1:
                        headers = table_obj[0]  # First row is headers
                        rows = table_obj[1:]     # Rest are data rows
                        return [dict(zip(headers, row)) for row in rows]
                    return []
                # Already list of dicts
                if table_obj and isinstance(table_obj[0], dict): 
                    return table_obj
                return [dict(enumerate(row)) for row in table_obj]  # fallback
                
            if isinstance(table_obj, dict):
                cols = table_obj.get("Columns")
                rows = table_obj.get("Rows")
                if isinstance(cols, list) and isinstance(rows, list):
                    if cols and isinstance(cols[0], dict) and "Name" in cols[0]:
                        colnames = [c["Name"] for c in cols]
                    else:
                        colnames = list(cols)
                    out = []
                    for row in rows:
                        if isinstance(row, list):
                            out.append({k: v for k, v in zip(colnames, row)})
                        elif isinstance(row, dict):
                            out.append(row)
                    return out
            return []
        
        # Extract data from various SDA response formats
        if isinstance(data, dict) and "Table" in data: 
            return _coerce(data["Table"])
        if isinstance(data, dict) and "Rows" in data: 
            return _coerce(data)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            first = data[0]
            if "Table" in first: 
                return _coerce(first["Table"])
            if "Rows" in first: 
                return _coerce(first)
        return []

    def _parse_surgo_data(self, soil_data: List[Dict[str, Any]], spec: RequestSpec) -> List[Dict[str, Any]]:
        """Parse SURGO query results using legacy approach with robust data cleaning"""
        if not soil_data:
            return []
            
        import pandas as pd
        
        # Build DataFrame with legacy-style column handling
        df = pd.DataFrame(soil_data)
        expected_cols = ["mukey","cokey","comppct_r","chkey","hzdept_r","hzdepb_r","claytotal_r","sandtotal_r","silttotal_r","ph1to1h2o_r","dbovendry_r","cec7_r"]
        
        # Handle numeric column names (legacy fallback)
        if len(df.columns) == len(expected_cols) and all(str(c).isdigit() for c in df.columns):
            df.columns = expected_cols
            
        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Clean metadata blobs (legacy approach)
        def _clean_cell(v):
            if isinstance(v, dict):
                for k in ("Value", "value", "v"):
                    if k in v: 
                        return v[k]
                return None
            if isinstance(v, str) and "ColumnOrdinal=" in v:
                return None
            return v
        df = df.map(_clean_cell)
        
        # Coerce numerics (legacy approach)
        for c in ["mukey","comppct_r","hzdept_r","hzdepb_r","claytotal_r","sandtotal_r","silttotal_r","ph1to1h2o_r","dbovendry_r","cec7_r"]:
            if c in df.columns: 
                df[c] = pd.to_numeric(df[c], errors="coerce")
        
        # Drop invalid rows
        df = df.dropna(subset=["mukey","comppct_r","hzdept_r","hzdepb_r"])
        if df.empty:
            return []
            
        df["mukey"] = df["mukey"].astype("Int64").astype(str)
        
        # Get geometry info
        if spec.geometry.type == "point":
            lon, lat = spec.geometry.coordinates
        else:
            # Simplified centroid
            lat = lon = None
            
        # Create rows for each requested variable
        # If * was requested, expand to all canonical variables
        if spec.variables == ["*"]:
            variables = [canonical for canonical in self.SOIL_PROPERTIES.values()]
        else:
            variables = spec.variables or ["soil:clay_pct", "soil:ph_h2o"]
        
        # Map legacy variable names to SURGO columns
        legacy_var_map = {
            "soil:clay_pct": "claytotal_r",
            "soil:sand_pct": "sandtotal_r", 
            "soil:silt_pct": "silttotal_r",
            "soil:ph_h2o": "ph1to1h2o_r",
            "soil:bulk_density": "dbovendry_r",
            "soil:cec": "cec7_r"
        }
        
        rows = []
        retrieval_time = datetime.now(timezone.utc).isoformat()
        upstream = {
            "dataset": self.DATASET,
            "endpoint": self.SOURCE_URL,
            "upstream_version": self.SOURCE_VERSION,
            "license": self.LICENSE,
            "citation": "USDA NRCS Soil Survey Geographic Database (SURGO)"
        }
        
        for var in variables:
            # Map variable to column
            col = None
            if var in legacy_var_map:
                col = legacy_var_map[var]
            else:
                # Try canonical mapping
                for surgo_prop, canonical in self.SOIL_PROPERTIES.items():
                    if var == canonical:
                        col = surgo_prop
                        break
                        
            if not col or col not in df.columns:
                continue
                
            # Process each row
            for _, record in df.iterrows():
                prop_value = record.get(col)
                if pd.notna(prop_value):
                    row = {
                        "dataset": self.DATASET,
                        "source_url": self.SOURCE_URL,
                        "source_version": self.SOURCE_VERSION, 
                        "license": self.LICENSE,
                        "retrieval_timestamp": retrieval_time,
                        "geometry_type": spec.geometry.type,
                        "latitude": lat,
                        "longitude": lon, 
                        "spatial_id": record.get('mukey'),
                        "time": None,
                        "variable": var,
                        "value": float(prop_value) if pd.notna(prop_value) else None,
                        "unit": self._get_property_unit(col),
                        "depth_top_cm": record.get('hzdept_r'),
                        "depth_bottom_cm": record.get('hzdepb_r'),
                        "qc_flag": "ok",
                        "attributes": {
                            "map_unit_key": str(record.get('mukey', '')),
                            "component_key": str(record.get('cokey', '')),
                            "component_percent": record.get('comppct_r'),
                            "horizon_key": str(record.get('chkey', '')),
                            "surgo_column": col,
                            "depth_cm": {"top": 0, "bottom": 30}
                        },
                        "provenance": self._prov(spec, upstream)
                    }
                    rows.append(row)
        
        return rows

    def _get_property_unit(self, surgo_property: str) -> str:
        """Get unit for SURGO soil property"""
        unit_map = {
            "claytotal_r": "%",
            "silttotal_r": "%", 
            "sandtotal_r": "%",
            "om_r": "%",
            "dbthirdbar_r": "g/cm³",
            "wthirdbar_r": "%",
            "wfifteenbar_r": "%", 
            "awc_r": "cm/cm",
            "ph1to1h2o_r": "pH",
            "ph01mcacl2_r": "pH",
            "cec7_r": "cmol+/kg",
            "ecec_r": "cmol+/kg", 
            "sumbases_r": "cmol+/kg",
            "p_r": "mg/kg",
            "k_r": "mg/kg"
        }
        return unit_map.get(surgo_property, "unknown")

    def _get_property_description(self, surgo_property: str) -> str:
        """Get description for SURGO soil property"""
        desc_map = {
            "claytotal_r": "Total clay content",
            "silttotal_r": "Total silt content",
            "sandtotal_r": "Total sand content", 
            "om_r": "Organic matter content",
            "dbthirdbar_r": "Bulk density at 1/3 bar",
            "wthirdbar_r": "Water content at 1/3 bar (field capacity)",
            "wfifteenbar_r": "Water content at 15 bar (wilting point)",
            "awc_r": "Available water capacity",
            "ph1to1h2o_r": "pH in water (1:1)",
            "ph01mcacl2_r": "pH in 0.01M CaCl2",
            "cec7_r": "Cation exchange capacity at pH 7",
            "ecec_r": "Effective cation exchange capacity",
            "sumbases_r": "Sum of bases",
            "p_r": "Phosphorus content", 
            "k_r": "Potassium content"
        }
        return desc_map.get(surgo_property, surgo_property)