"""
Ecognita-ready tool interface for env-agents
Provides standardized tools that can be easily used by AI agents
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import logging
from datetime import datetime

from .models import Geometry, RequestSpec
from .metadata import AssetMetadata, create_earth_engine_style_metadata

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result from environmental data tools"""
    success: bool
    data: Any = None
    message: str = ""
    metadata: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "data": self.data if not hasattr(self.data, 'to_dict') else self.data.to_dict(),
            "message": self.message,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "warnings": self.warnings,
            "citations": self.citations
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class ToolCapability:
    """Describes what a tool can do (for agent discovery)"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    data_domains: List[str] = field(default_factory=list)  # ["air_quality", "weather", "soil"]
    geographic_scope: str = "global"  # "global", "continental", "national", "regional"
    temporal_scope: str = "historical"  # "historical", "real-time", "forecast"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
            "limitations": self.limitations,
            "data_domains": self.data_domains,
            "geographic_scope": self.geographic_scope,
            "temporal_scope": self.temporal_scope
        }


class EnvironmentalDataTool(ABC):
    """Base class for environmental data tools that can be used by AI agents"""
    
    def __init__(self, router, adapter_name: str):
        self.router = router
        self.adapter_name = adapter_name
        self.logger = logging.getLogger(f"tool.{adapter_name.lower()}")
    
    @abstractmethod
    def get_capabilities(self) -> ToolCapability:
        """Return tool capabilities for agent discovery"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def _create_input_schema(
        self, 
        required_fields: List[str], 
        optional_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Helper to create JSON schema for tool inputs"""
        properties = {}
        
        # Standard geographic fields
        properties["geometry"] = {
            "type": "object",
            "description": "Geographic area (point, bbox, or polygon)",
            "properties": {
                "type": {"type": "string", "enum": ["point", "bbox", "polygon"]},
                "coordinates": {"type": "array", "description": "Coordinates based on geometry type"}
            }
        }
        
        # Standard temporal fields  
        properties["time_range"] = {
            "type": "object",
            "description": "Time period of interest",
            "properties": {
                "start": {"type": "string", "format": "date"},
                "end": {"type": "string", "format": "date"}
            }
        }
        
        # Variables field
        properties["variables"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Environmental variables to retrieve"
        }
        
        # Add optional fields
        if optional_fields:
            properties.update(optional_fields)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required_fields
        }
    
    def _create_success_result(
        self,
        data: Any,
        message: str = "Success",
        metadata: Optional[Dict] = None,
        execution_time: float = 0.0,
        citations: List[str] = None
    ) -> ToolResult:
        """Create a successful tool result"""
        return ToolResult(
            success=True,
            data=data,
            message=message,
            metadata=metadata or {},
            execution_time=execution_time,
            citations=citations or []
        )
    
    def _create_error_result(
        self,
        error_message: str,
        execution_time: float = 0.0,
        warnings: List[str] = None
    ) -> ToolResult:
        """Create an error tool result"""
        return ToolResult(
            success=False,
            message=error_message,
            execution_time=execution_time,
            warnings=warnings or []
        )


class AirQualityTool(EnvironmentalDataTool):
    """Tool for retrieving air quality data"""
    
    def get_capabilities(self) -> ToolCapability:
        return ToolCapability(
            name="get_air_quality_data",
            description="Retrieve air quality measurements from EPA AQS monitoring stations",
            input_schema=self._create_input_schema(
                required_fields=["geometry"],
                optional_fields={
                    "pollutants": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific pollutants (PM2.5, O3, NO2, etc.)",
                        "default": ["PM2.5", "O3"]
                    },
                    "max_distance_km": {
                        "type": "number",
                        "description": "Maximum distance from point for station search",
                        "default": 50
                    }
                }
            ),
            output_schema={
                "type": "object",
                "properties": {
                    "measurements": {"type": "array"},
                    "stations": {"type": "array"},
                    "summary_statistics": {"type": "object"}
                }
            },
            examples=[{
                "input": {
                    "geometry": {"type": "point", "coordinates": [-122.27, 37.87]},
                    "time_range": {"start": "2023-01-01", "end": "2023-01-31"},
                    "pollutants": ["PM2.5", "O3"]
                },
                "output": "DataFrame with air quality measurements"
            }],
            data_domains=["air_quality"],
            geographic_scope="national",
            temporal_scope="historical"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute air quality data retrieval"""
        import time
        start_time = time.time()
        
        try:
            # Extract parameters
            geometry = kwargs.get('geometry')
            time_range = kwargs.get('time_range')
            pollutants = kwargs.get('pollutants', ['PM2.5', 'O3'])
            
            if not geometry:
                return self._create_error_result("Geometry parameter is required")
            
            # Create request spec
            spec = RequestSpec(
                geometry=Geometry(**geometry),
                time_range=(time_range.get('start'), time_range.get('end')) if time_range else None,
                variables=[f"air:{p.lower().replace('.', '').replace('-', '')}" for p in pollutants]
            )
            
            # Fetch data
            df = self.router.fetch(self.adapter_name, spec)
            
            execution_time = time.time() - start_time
            
            if df is None or df.empty:
                return self._create_error_result(
                    "No air quality data found for specified parameters",
                    execution_time=execution_time
                )
            
            # Create summary statistics
            summary_stats = {}
            if 'value' in df.columns:
                summary_stats = {
                    'total_measurements': len(df),
                    'unique_stations': df['spatial_id'].nunique() if 'spatial_id' in df.columns else 0,
                    'date_range': {
                        'start': str(df['time'].min()) if 'time' in df.columns else None,
                        'end': str(df['time'].max()) if 'time' in df.columns else None
                    },
                    'value_statistics': {
                        'mean': float(df['value'].mean()),
                        'min': float(df['value'].min()),
                        'max': float(df['value'].max()),
                        'std': float(df['value'].std())
                    }
                }
            
            # Get citation information
            adapter = self.router.adapters.get(self.adapter_name)
            citation = ""
            if adapter:
                citation = f"EPA Air Quality System. Retrieved {datetime.now().strftime('%Y-%m-%d')}. {adapter.SOURCE_URL}"
            
            return self._create_success_result(
                data={
                    "measurements": df.to_dict('records'),
                    "summary_statistics": summary_stats,
                    "record_count": len(df)
                },
                message=f"Retrieved {len(df)} air quality measurements",
                execution_time=execution_time,
                citations=[citation] if citation else []
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Air quality tool execution failed: {e}")
            return self._create_error_result(
                f"Air quality data retrieval failed: {str(e)}",
                execution_time=execution_time
            )


class WeatherDataTool(EnvironmentalDataTool):
    """Tool for retrieving weather/climate data"""
    
    def get_capabilities(self) -> ToolCapability:
        return ToolCapability(
            name="get_weather_data", 
            description="Retrieve historical weather data from NOAA stations and NASA POWER",
            input_schema=self._create_input_schema(
                required_fields=["geometry"],
                optional_fields={
                    "parameters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Weather parameters (temperature, precipitation, wind, etc.)",
                        "default": ["temperature", "precipitation"]
                    },
                    "data_source": {
                        "type": "string",
                        "enum": ["NOAA_STATIONS", "NASA_POWER", "AUTO"],
                        "description": "Preferred data source",
                        "default": "AUTO"
                    }
                }
            ),
            output_schema={
                "type": "object", 
                "properties": {
                    "weather_data": {"type": "array"},
                    "data_sources": {"type": "array"},
                    "summary_statistics": {"type": "object"}
                }
            },
            data_domains=["weather", "climate"],
            geographic_scope="global",
            temporal_scope="historical"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute weather data retrieval"""
        import time
        start_time = time.time()
        
        try:
            geometry = kwargs.get('geometry')
            time_range = kwargs.get('time_range')
            parameters = kwargs.get('parameters', ['temperature', 'precipitation'])
            data_source = kwargs.get('data_source', 'AUTO')
            
            if not geometry:
                return self._create_error_result("Geometry parameter is required")
            
            # Map parameters to canonical variables
            var_mapping = {
                'temperature': 'atm:air_temperature_2m',
                'precipitation': 'atm:precipitation',
                'wind': 'atm:wind_speed',
                'humidity': 'atm:relative_humidity'
            }
            
            variables = [var_mapping.get(p, p) for p in parameters]
            
            spec = RequestSpec(
                geometry=Geometry(**geometry),
                time_range=(time_range.get('start'), time_range.get('end')) if time_range else None,
                variables=variables
            )
            
            # Try multiple sources based on preference
            sources_to_try = []
            if data_source == "AUTO":
                sources_to_try = ["NASA_POWER", "NOAA_CDO"]
            elif data_source == "NASA_POWER":
                sources_to_try = ["NASA_POWER"]
            elif data_source == "NOAA_STATIONS":
                sources_to_try = ["NOAA_CDO"]
            
            df = None
            successful_source = None
            
            for source in sources_to_try:
                if source in self.router.adapters:
                    try:
                        df = self.router.fetch(source, spec)
                        if df is not None and not df.empty:
                            successful_source = source
                            break
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch from {source}: {e}")
                        continue
            
            execution_time = time.time() - start_time
            
            if df is None or df.empty:
                return self._create_error_result(
                    "No weather data found from any available source",
                    execution_time=execution_time
                )
            
            # Create summary
            summary_stats = {
                'data_source': successful_source,
                'total_records': len(df),
                'date_range': {
                    'start': str(df['time'].min()) if 'time' in df.columns else None,
                    'end': str(df['time'].max()) if 'time' in df.columns else None
                }
            }
            
            return self._create_success_result(
                data={
                    "weather_data": df.to_dict('records'),
                    "data_sources": [successful_source],
                    "summary_statistics": summary_stats
                },
                message=f"Retrieved {len(df)} weather records from {successful_source}",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Weather tool execution failed: {e}")
            return self._create_error_result(
                f"Weather data retrieval failed: {str(e)}",
                execution_time=execution_time
            )


class EnergyDataTool(EnvironmentalDataTool):
    """Tool for retrieving energy data from EIA"""
    
    def get_capabilities(self) -> ToolCapability:
        return ToolCapability(
            name="get_energy_data",
            description="Retrieve energy generation, consumption, and market data from US EIA",
            input_schema=self._create_input_schema(
                required_fields=["energy_sector"],
                optional_fields={
                    "energy_sector": {
                        "type": "string",
                        "enum": ["electricity", "natural_gas", "petroleum", "renewable"],
                        "description": "Energy sector of interest"
                    },
                    "region": {
                        "type": "string", 
                        "description": "Geographic region (state, RTO region, etc.)"
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["generation", "consumption", "price", "capacity"],
                        "description": "Type of energy data"
                    }
                }
            ),
            output_schema={
                "type": "object",
                "properties": {
                    "energy_data": {"type": "array"},
                    "metadata": {"type": "object"}
                }
            },
            data_domains=["energy"],
            geographic_scope="national", 
            temporal_scope="historical"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute energy data retrieval"""
        import time
        start_time = time.time()
        
        try:
            energy_sector = kwargs.get('energy_sector')
            region = kwargs.get('region')
            data_type = kwargs.get('data_type', 'generation')
            time_range = kwargs.get('time_range')
            
            if not energy_sector:
                return self._create_error_result("Energy sector parameter is required")
            
            # Map to canonical variables (to be implemented based on EIA structure)
            variables = [f"energy:{energy_sector}:{data_type}"]
            
            spec = RequestSpec(
                geometry=None,  # EIA is more region-based than geographic
                time_range=(time_range.get('start'), time_range.get('end')) if time_range else None,
                variables=variables,
                extra={"region": region} if region else None
            )
            
            df = self.router.fetch(self.adapter_name, spec)
            execution_time = time.time() - start_time
            
            if df is None or df.empty:
                return self._create_error_result(
                    "No energy data found for specified parameters",
                    execution_time=execution_time
                )
            
            return self._create_success_result(
                data={
                    "energy_data": df.to_dict('records'),
                    "record_count": len(df)
                },
                message=f"Retrieved {len(df)} energy data records",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Energy tool execution failed: {e}")
            return self._create_error_result(
                f"Energy data retrieval failed: {str(e)}",
                execution_time=execution_time
            )


class EnvironmentalToolSuite:
    """Collection of environmental data tools for AI agents"""
    
    def __init__(self, router):
        self.router = router
        self.tools = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register available tools based on router adapters"""
        if "EPA_AQS" in self.router.adapters:
            self.tools["air_quality"] = AirQualityTool(self.router, "EPA_AQS")
        
        if any(adapter in self.router.adapters for adapter in ["NASA_POWER", "NOAA_CDO"]):
            self.tools["weather"] = WeatherDataTool(self.router, "NASA_POWER")  # Default to NASA_POWER
        
        if "US_EIA" in self.router.adapters:
            self.tools["energy"] = EnergyDataTool(self.router, "US_EIA")
    
    def get_available_tools(self) -> Dict[str, ToolCapability]:
        """Get capabilities of all available tools"""
        return {name: tool.get_capabilities() for name, tool in self.tools.items()}
    
    def get_tool(self, tool_name: str) -> Optional[EnvironmentalDataTool]:
        """Get a specific tool by name"""
        return self.tools.get(tool_name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                message=f"Tool '{tool_name}' not available. Available tools: {list(self.tools.keys())}"
            )
        
        return await tool.execute(**kwargs)
    
    def to_agent_schema(self) -> List[Dict[str, Any]]:
        """Export tools in format suitable for AI agent frameworks"""
        agent_tools = []
        
        for name, tool in self.tools.items():
            capability = tool.get_capabilities()
            agent_tools.append({
                "name": capability.name,
                "description": capability.description,
                "input_schema": capability.input_schema,
                "examples": capability.examples
            })
        
        return agent_tools
    
    def get_tool_documentation(self) -> str:
        """Generate markdown documentation for all tools"""
        docs = "# Environmental Data Tools\n\n"
        
        for name, tool in self.tools.items():
            capability = tool.get_capabilities()
            
            docs += f"## {capability.name}\n\n"
            docs += f"**Description:** {capability.description}\n\n"
            docs += f"**Data Domains:** {', '.join(capability.data_domains)}\n"
            docs += f"**Geographic Scope:** {capability.geographic_scope}\n"
            docs += f"**Temporal Scope:** {capability.temporal_scope}\n\n"
            
            if capability.examples:
                docs += "**Example Usage:**\n```json\n"
                docs += json.dumps(capability.examples[0], indent=2)
                docs += "\n```\n\n"
            
            if capability.limitations:
                docs += "**Limitations:**\n"
                for limitation in capability.limitations:
                    docs += f"- {limitation}\n"
                docs += "\n"
        
        return docs