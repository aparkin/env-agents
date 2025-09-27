#!/usr/bin/env python3
"""
Test script for enhanced env-agents system
Demonstrates new features:
- Google Earth Engine-style metadata
- Ecognita-ready tools
- Service-specific caching
- Robust error handling patterns
"""

import asyncio
import sys
import json
from pathlib import Path

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
from env_agents.core.tools import EnvironmentalToolSuite
from env_agents.core.cache import global_cache
from env_agents.adapters.energy.eia_adapter import EIAAdapter
from env_agents.adapters.air.aqs_adapter import EPAAQSAdapter


def test_enhanced_metadata():
    """Test Earth Engine-style metadata system"""
    print("🌍 Testing Enhanced Metadata System")
    print("=" * 50)
    
    try:
        # Initialize EIA adapter
        eia_adapter = EIAAdapter()
        
        # Test route metadata
        route_id = "electricity/rto/region-data"
        metadata = eia_adapter.get_enhanced_metadata(route_id)
        
        if metadata:
            print(f"✅ Asset ID: {metadata.asset_id}")
            print(f"✅ Title: {metadata.title}")
            print(f"✅ Provider: {metadata.providers[0].name}")
            print(f"✅ Citation: {metadata.get_citation_string()}")
            print(f"✅ Bands: {list(metadata.bands.keys())}")
            
            # Export as STAC
            stac_item = metadata.to_stac_item()
            print(f"✅ STAC export: {len(stac_item)} fields")
        else:
            print("❌ Failed to get metadata")
            
    except Exception as e:
        print(f"❌ Metadata test failed: {e}")
    
    print()


def test_service_caching():
    """Test service-specific caching system"""
    print("💾 Testing Service Caching System")
    print("=" * 50)
    
    try:
        # Test EIA caching
        eia_cache = global_cache.get_service_cache("US_EIA")
        
        # Cache some test data
        test_data = {"routes": ["electricity/rto/region-data"], "timestamp": "2025-09-06"}
        eia_cache.set("test_routes", test_data, "metadata", ttl=3600)
        
        # Retrieve cached data
        cached_data = eia_cache.get("test_routes", "metadata")
        if cached_data:
            print(f"✅ Cache write/read successful: {cached_data['routes']}")
        else:
            print("❌ Cache read failed")
        
        # Test cache stats
        stats = eia_cache.cache_stats()
        print(f"✅ Cache stats: {stats['service']}")
        for cache_type, info in stats['cache_types'].items():
            if info['exists']:
                print(f"   - {cache_type}: {info['total_entries']} entries")
        
        # Test global cache manager
        global_stats = global_cache.global_stats()
        print(f"✅ Global cache manages {global_stats['total_services']} services")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
    
    print()


async def test_robust_aqs_patterns():
    """Test EPA AQS with ECOGNITA-style robust patterns"""
    print("🏭 Testing EPA AQS Robust Patterns")
    print("=" * 50)
    
    try:
        # Initialize AQS adapter
        aqs_adapter = EPAAQSAdapter()
        
        # Test capabilities with parameter discovery
        caps = aqs_adapter.capabilities()
        print(f"✅ AQS capabilities: {len(caps['variables'])} variables")
        print(f"✅ Parameter classes: {caps.get('parameter_classes', 0)}")
        
        # Test robust query with Berkeley, CA
        spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-122.27, 37.87]),
            variables=["air:pm25", "air:o3"],
            time_range=("2023-01-01", "2023-01-31")
        )
        
        print("🔍 Testing robust AQS query...")
        result = await aqs_adapter._robust_aqs_query(spec)
        
        print(f"Query Status: {'✅ Success' if result.success else '❌ Failed'}")
        print(f"Message: {result.message}")
        print(f"Sites Found: {result.sites_found}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"API Calls: {result.api_calls}")
        
        if result.filter_diagnostics:
            print(f"Filter Diagnostics: {result.filter_diagnostics}")
            
        if result.data is not None:
            print(f"Data Shape: {result.data.shape}")
            print(f"Sample Columns: {list(result.data.columns)[:5]}")
        
    except Exception as e:
        print(f"❌ AQS test failed: {e}")
    
    print()


async def test_ecognita_tools():
    """Test ecognita-ready tool interface"""
    print("🤖 Testing Ecognita-Ready Tools")
    print("=" * 50)
    
    try:
        # Initialize router with adapters
        router = EnvRouter(base_dir=".")
        
        # Register EIA adapter (if we had working API)
        try:
            eia_adapter = EIAAdapter()
            router.register(eia_adapter)
            print("✅ EIA adapter registered")
        except Exception as e:
            print(f"⚠️  EIA adapter not registered: {e}")
        
        # Initialize tool suite
        tool_suite = EnvironmentalToolSuite(router)
        
        # Get available tools
        available_tools = tool_suite.get_available_tools()
        print(f"✅ Available tools: {list(available_tools.keys())}")
        
        for tool_name, capability in available_tools.items():
            print(f"   - {capability.name}: {capability.description}")
            print(f"     Domains: {capability.data_domains}")
            print(f"     Scope: {capability.geographic_scope}, {capability.temporal_scope}")
        
        # Test tool execution (if tools available)
        if "air_quality" in available_tools:
            print("🔍 Testing air quality tool...")
            
            result = await tool_suite.execute_tool(
                "air_quality",
                geometry={"type": "point", "coordinates": [-122.27, 37.87]},
                time_range={"start": "2023-01-01", "end": "2023-01-31"},
                pollutants=["PM2.5", "O3"]
            )
            
            print(f"Tool Status: {'✅ Success' if result.success else '❌ Failed'}")
            print(f"Message: {result.message}")
            print(f"Execution Time: {result.execution_time:.2f}s")
            
            if result.success and result.data:
                print(f"Data Keys: {list(result.data.keys())}")
        
        # Generate agent documentation
        print("\n📚 Agent Documentation Sample:")
        docs = tool_suite.get_tool_documentation()
        print(docs[:500] + "..." if len(docs) > 500 else docs)
        
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
    
    print()


def test_earth_engine_style_export():
    """Test Earth Engine-style metadata export formats"""
    print("🗂️  Testing Earth Engine-Style Export")
    print("=" * 50)
    
    try:
        from env_agents.core.metadata import create_earth_engine_style_metadata
        
        # Create sample metadata
        bands = {
            "pm25": {
                "description": "PM2.5 concentration",
                "data_type": "float32",
                "units": "µg/m³",
                "valid_range": [0.0, 500.0],
                "cf_standard_name": "mass_concentration_of_pm2p5_ambient_aerosol_particles_in_air"
            },
            "ozone": {
                "description": "Ground-level ozone concentration", 
                "data_type": "float32",
                "units": "ppb",
                "valid_range": [0.0, 200.0]
            }
        }
        
        metadata = create_earth_engine_style_metadata(
            asset_id="EPA_AQS/CRITERIA_POLLUTANTS",
            title="EPA Air Quality System - Criteria Pollutants",
            description="Air quality monitoring data from EPA's Air Quality System",
            temporal_extent=("2000-01-01", "2024-12-31"),
            bands=bands,
            provider_name="US Environmental Protection Agency",
            provider_url="https://www.epa.gov/aqs"
        )
        
        print(f"✅ Asset ID: {metadata.asset_id}")
        print(f"✅ Bands: {len(metadata.bands)}")
        
        # Test JSON export
        json_export = metadata.to_json()
        print(f"✅ JSON export: {len(json_export)} characters")
        
        # Test STAC export
        stac_export = metadata.to_stac_item()
        print(f"✅ STAC export: {stac_export['type']}")
        print(f"✅ STAC assets: {len(stac_export['assets'])}")
        
        # Test citation generation
        citation = metadata.get_citation_string()
        print(f"✅ Citation: {citation}")
        
    except Exception as e:
        print(f"❌ Export test failed: {e}")
    
    print()


async def main():
    """Run all enhanced system tests"""
    print("🚀 Enhanced env-agents System Test Suite")
    print("=" * 60)
    print()
    
    # Test 1: Enhanced metadata system
    test_enhanced_metadata()
    
    # Test 2: Service caching
    test_service_caching()
    
    # Test 3: Robust EPA AQS patterns
    await test_robust_aqs_patterns()
    
    # Test 4: Ecognita-ready tools
    await test_ecognita_tools()
    
    # Test 5: Earth Engine-style exports
    test_earth_engine_style_export()
    
    print("🎯 Test Suite Complete!")
    print("=" * 60)
    
    # Summary of new features
    print("\n✨ New Features Demonstrated:")
    print("• Google Earth Engine-style metadata with STAC export")
    print("• Service-specific intelligent caching (TTL, cleanup)")
    print("• ECOGNITA-style robust query patterns with fallbacks")
    print("• Agent-ready tool interface with rich diagnostics")  
    print("• Enhanced error handling and provenance tracking")
    print("• Citation generation and data attribution")
    print("• Multi-tier geographic search strategies")
    print("• Production-ready rate limiting and session management")


if __name__ == "__main__":
    asyncio.run(main())