#!/usr/bin/env python3
"""
Service Coverage Discovery Framework
====================================

Systematically discovers geographic locations and time periods where each 
environmental service actually has data. Creates a validated test matrix 
for comprehensive service evaluation.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import requests
import time

sys.path.insert(0, '.')

# Set up credentials
os.environ['OPENAQ_API_KEY'] = '1dfd14b5aac0cf892b43e575fa4060d6dc4228149751b9362e5e2331ca2fc4ca'
os.environ['EPA_AQS_EMAIL'] = 'aparkin@lbl.gov'
os.environ['EPA_AQS_KEY'] = 'khakimouse81'

from env_agents.core.models import RequestSpec, Geometry

@dataclass
class TestLocation:
    name: str
    latitude: float
    longitude: float
    region: str  # Urban, Rural, Coastal, Mountain, etc.
    country: str
    expected_services: List[str]  # Services we expect to have data here
    description: str

@dataclass
class CoverageResult:
    service: str
    location: TestLocation
    time_period: Tuple[str, str]
    records_found: int
    variables_available: List[str]
    success: bool
    error_msg: Optional[str]
    sample_data: Optional[Dict]

class ServiceCoverageDiscovery:
    """Discovers actual data coverage for environmental services"""
    
    def __init__(self):
        self.results = []
        self.known_good_locations = {}
        
    def get_strategic_test_locations(self) -> List[TestLocation]:
        """
        Carefully selected test locations based on known monitoring infrastructure
        """
        return [
            # US Major Cities (dense monitoring)
            TestLocation("Los Angeles, CA", 34.0522, -118.2437, "Urban-Coastal", "USA",
                        ["OpenAQ", "EPA_AQS", "NASA_POWER", "USGS_NWIS", "SSURGO", "WQP", "GBIF"], 
                        "Major US city with extensive air quality monitoring"),
            
            TestLocation("Chicago, IL", 41.8781, -87.6298, "Urban-Continental", "USA", 
                        ["OpenAQ", "EPA_AQS", "NASA_POWER", "USGS_NWIS", "SSURGO", "WQP", "GBIF"],
                        "Great Lakes region with water and air monitoring"),
            
            TestLocation("Denver, CO", 39.7392, -104.9903, "Urban-Mountain", "USA",
                        ["OpenAQ", "EPA_AQS", "NASA_POWER", "USGS_NWIS", "SSURGO"],
                        "High altitude city with unique atmospheric conditions"),
            
            # International Cities (OpenAQ coverage)
            TestLocation("London, UK", 51.5074, -0.1278, "Urban-European", "GBR",
                        ["OpenAQ", "NASA_POWER", "SoilGrids", "GBIF", "Overpass"],
                        "Major European city with dense sensor networks"),
            
            TestLocation("Delhi, India", 28.7041, 77.1025, "Urban-Developing", "IND",
                        ["OpenAQ", "NASA_POWER", "SoilGrids", "GBIF"],
                        "Heavily polluted megacity with extensive monitoring"),
            
            TestLocation("São Paulo, Brazil", -23.5505, -46.6333, "Urban-Tropical", "BRA",
                        ["OpenAQ", "NASA_POWER", "SoilGrids", "GBIF"],
                        "Southern hemisphere major city"),
            
            # Natural/Research Areas
            TestLocation("Yellowstone NP", 44.4280, -110.5885, "Natural-Mountain", "USA",
                        ["NASA_POWER", "USGS_NWIS", "GBIF", "Earth_Engine"],
                        "Pristine natural area with research monitoring"),
            
            TestLocation("Great Smoky Mountains", 35.6532, -83.5070, "Natural-Appalachian", "USA",
                        ["NASA_POWER", "USGS_NWIS", "GBIF", "EPA_AQS"],
                        "National park with atmospheric research"),
            
            # Agricultural Areas (for SSURGO testing)
            TestLocation("Iowa Corn Belt", 42.0308, -93.6319, "Agricultural", "USA",
                        ["NASA_POWER", "SSURGO", "USGS_NWIS", "SoilGrids"],
                        "Prime agricultural land with soil surveys"),
            
            TestLocation("Central Valley, CA", 36.7378, -119.7871, "Agricultural-Irrigated", "USA",
                        ["NASA_POWER", "SSURGO", "USGS_NWIS", "EPA_AQS"],
                        "Major agricultural region with water management"),
            
            # Coastal/Water Areas  
            TestLocation("San Francisco Bay", 37.8044, -122.2711, "Coastal-Urban", "USA",
                        ["OpenAQ", "EPA_AQS", "USGS_NWIS", "WQP", "GBIF"],
                        "Major estuary with water quality monitoring"),
            
            TestLocation("Chesapeake Bay", 39.0458, -76.6413, "Coastal-Estuary", "USA",
                        ["EPA_AQS", "USGS_NWIS", "WQP", "GBIF", "NASA_POWER"],
                        "Major estuary research area"),
        ]
    
    def get_test_time_periods(self) -> List[Tuple[str, str]]:
        """Strategic time periods for testing"""
        return [
            ("2024-08-01", "2024-08-31"),  # Recent month
            ("2024-01-01", "2024-01-31"),  # Winter conditions  
            ("2023-07-01", "2023-07-31"),  # Summer conditions
            ("2024-01-01", "2024-12-31"),  # Full year (for annual services)
        ]
    
    def test_service_coverage(self, service_name: str, adapter_class, locations: List[TestLocation], 
                            time_periods: List[Tuple[str, str]]) -> List[CoverageResult]:
        """Test a specific service across locations and time periods"""
        results = []
        
        print(f"\n🔍 Testing {service_name} Coverage")
        print("=" * 40)
        
        try:
            adapter = adapter_class()
            
            for location in locations:
                if service_name.replace("Enhanced", "").replace("_", "") not in location.expected_services:
                    continue  # Skip if we don't expect data here
                    
                print(f"\n📍 {location.name} ({location.region})")
                
                for start_date, end_date in time_periods:
                    print(f"  ⏰ {start_date} to {end_date}: ", end="")
                    
                    try:
                        geom = Geometry(type="point", coordinates=[location.longitude, location.latitude])
                        
                        # Service-specific request configuration
                        extra_params = self._get_service_specific_params(service_name, location)
                        
                        spec = RequestSpec(
                            geometry=geom,
                            time_range=(start_date, end_date),
                            variables=self._get_service_variables(service_name),
                            extra=extra_params
                        )
                        
                        # Execute with timeout
                        start_time = time.time()
                        rows = adapter._fetch_rows(spec)
                        query_time = time.time() - start_time
                        
                        if rows and len(rows) > 0:
                            variables = list(set(row.get('variable', 'unknown') for row in rows))
                            sample_data = {
                                'first_record': {k: v for k, v in rows[0].items() if k not in ['attributes', 'provenance']},
                                'query_time_seconds': round(query_time, 2)
                            }
                            
                            result = CoverageResult(
                                service=service_name,
                                location=location,
                                time_period=(start_date, end_date),
                                records_found=len(rows),
                                variables_available=variables,
                                success=True,
                                error_msg=None,
                                sample_data=sample_data
                            )
                            
                            print(f"✅ {len(rows)} records, {len(variables)} vars")
                        else:
                            result = CoverageResult(
                                service=service_name,
                                location=location,
                                time_period=(start_date, end_date),
                                records_found=0,
                                variables_available=[],
                                success=False,
                                error_msg="No data returned",
                                sample_data=None
                            )
                            print("⚠️  No data")
                        
                        results.append(result)
                        
                        # Rate limiting
                        time.sleep(0.5)
                        
                    except Exception as e:
                        result = CoverageResult(
                            service=service_name,
                            location=location,
                            time_period=(start_date, end_date),
                            records_found=0,
                            variables_available=[],
                            success=False,
                            error_msg=str(e)[:200],
                            sample_data=None
                        )
                        results.append(result)
                        print(f"❌ {type(e).__name__}: {str(e)[:50]}...")
                        
        except Exception as e:
            print(f"❌ {service_name} adapter failed to initialize: {e}")
            
        return results
    
    def _get_service_specific_params(self, service_name: str, location: TestLocation) -> Dict:
        """Get appropriate extra parameters for each service"""
        params_map = {
            "OpenAQEnhanced": {"radius": 15000},
            "NASAPOWEREnhanced": {},
            "EPAAQSEnhanced": {"state": self._get_state_code(location), "county": "001"},
            "USGSNWISEnhanced": {"radius": 25000},
            "SoilGridsEnhanced": {"depth": "0-5cm"},
            "SSURGOEnhanced": {"component": "major"},
            "WQPEnhanced": {"radius": 30000},
            "GBIFEnhanced": {"radius": 10000, "limit": 100},
            "OverpassEnhanced": {"radius": 5000},
        }
        return params_map.get(service_name, {})
    
    def _get_service_variables(self, service_name: str) -> List[str]:
        """Get appropriate test variables for each service"""
        variables_map = {
            "OpenAQEnhanced": ["pm25", "pm10"],
            "NASAPOWEREnhanced": ["T2M", "PRECTOTCORR"],
            "EPAAQSEnhanced": ["88101", "44201"],  # PM2.5, Ozone
            "USGSNWISEnhanced": ["00060", "00065"],  # Discharge, gage height
            "SoilGridsEnhanced": ["clay", "sand"],
            "SSURGOEnhanced": ["om_r", "clay_r"],
            "WQPEnhanced": ["Temperature", "pH"],
            "GBIFEnhanced": ["occurrence"],
            "OverpassEnhanced": ["building", "highway"],
        }
        return variables_map.get(service_name, [])
    
    def _get_state_code(self, location: TestLocation) -> str:
        """Get US state code for EPA AQS (simplified mapping)"""
        state_codes = {
            "Los Angeles, CA": "06", "Central Valley, CA": "06", "San Francisco Bay": "06",
            "Chicago, IL": "17", "Denver, CO": "08", "Iowa Corn Belt": "19",
            "Yellowstone NP": "56", "Great Smoky Mountains": "47", "Chesapeake Bay": "24"
        }
        return state_codes.get(location.name, "06")  # Default to California
    
    def generate_coverage_report(self, results: List[CoverageResult]) -> Dict:
        """Generate comprehensive coverage analysis report"""
        
        # Success rates by service
        service_stats = {}
        for service in set(r.service for r in results):
            service_results = [r for r in results if r.service == service]
            successful = [r for r in service_results if r.success]
            
            service_stats[service] = {
                'total_tests': len(service_results),
                'successful_tests': len(successful),
                'success_rate': len(successful) / len(service_results) if service_results else 0,
                'total_records': sum(r.records_found for r in successful),
                'avg_records_per_success': np.mean([r.records_found for r in successful]) if successful else 0,
                'best_locations': sorted([(r.location.name, r.records_found) for r in successful], 
                                       key=lambda x: x[1], reverse=True)[:3]
            }
        
        # Location success rates
        location_stats = {}
        for location in set((r.location.name, r.location.region) for r in results):
            location_results = [r for r in results if r.location.name == location[0]]
            successful = [r for r in location_results if r.success]
            
            location_stats[location[0]] = {
                'region': location[1],
                'services_tested': len(set(r.service for r in location_results)),
                'services_successful': len(set(r.service for r in successful)),
                'total_records': sum(r.records_found for r in successful)
            }
        
        return {
            'test_summary': {
                'total_tests': len(results),
                'successful_tests': len([r for r in results if r.success]),
                'overall_success_rate': len([r for r in results if r.success]) / len(results),
                'total_records_retrieved': sum(r.records_found for r in results)
            },
            'service_performance': service_stats,
            'location_performance': location_stats,
            'recommended_test_matrix': self._generate_test_matrix(results)
        }
    
    def _generate_test_matrix(self, results: List[CoverageResult]) -> Dict:
        """Generate recommended test combinations based on coverage discovery"""
        
        # Find best location-service-time combinations
        successful_results = [r for r in results if r.success and r.records_found > 0]
        
        # Group by service and find best examples
        test_matrix = {}
        for service in set(r.service for r in successful_results):
            service_results = [r for r in successful_results if r.service == service]
            service_results.sort(key=lambda x: x.records_found, reverse=True)
            
            # Take top 3 working combinations for each service
            test_matrix[service] = []
            for result in service_results[:3]:
                test_matrix[service].append({
                    'location': result.location.name,
                    'coordinates': [result.location.longitude, result.location.latitude],
                    'time_period': result.time_period,
                    'expected_records': result.records_found,
                    'variables': result.variables_available,
                    'extra_params': self._get_service_specific_params(service, result.location)
                })
        
        return test_matrix

def main():
    """Run comprehensive service coverage discovery"""
    
    print("🔍 COMPREHENSIVE SERVICE COVERAGE DISCOVERY")
    print("=" * 50)
    
    discovery = ServiceCoverageDiscovery()
    locations = discovery.get_strategic_test_locations()
    time_periods = discovery.get_test_time_periods()
    
    print(f"Testing {len(locations)} locations across {len(time_periods)} time periods")
    print(f"Expected test combinations: {len(locations) * len(time_periods)} per service")
    
    # Import all enhanced adapters
    services_to_test = [
        ("OpenAQEnhanced", "env_agents.adapters.openaq.enhanced_adapter.EnhancedOpenAQAdapter"),
        ("NASAPOWEREnhanced", "env_agents.adapters.power.enhanced_adapter.NASAPOWEREnhancedAdapter"),
        ("SoilGridsEnhanced", "env_agents.adapters.soil.enhanced_soilgrids_adapter.EnhancedSoilGridsAdapter"),
        ("GBIFEnhanced", "env_agents.adapters.gbif.enhanced_adapter.EnhancedGBIFAdapter"),
        # Add others as they're fixed
    ]
    
    all_results = []
    
    for service_name, import_path in services_to_test:
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            adapter_class = getattr(module, class_name)
            
            results = discovery.test_service_coverage(service_name, adapter_class, locations, time_periods)
            all_results.extend(results)
            
        except Exception as e:
            print(f"❌ Failed to test {service_name}: {e}")
    
    # Generate comprehensive report
    print("\n📊 GENERATING COVERAGE ANALYSIS REPORT")
    print("=" * 40)
    
    report = discovery.generate_coverage_report(all_results)
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'coverage_results': [
            {
                'service': r.service,
                'location': r.location.name,
                'region': r.location.region,
                'coordinates': [r.location.longitude, r.location.latitude],
                'time_period': r.time_period,
                'records_found': r.records_found,
                'variables_available': r.variables_available,
                'success': r.success,
                'error_msg': r.error_msg,
                'sample_data': r.sample_data
            }
            for r in all_results
        ],
        'analysis_report': report
    }
    
    with open('service_coverage_discovery_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    # Print summary
    print(f"\n🏆 COVERAGE DISCOVERY SUMMARY")
    print(f"Total Tests: {report['test_summary']['total_tests']}")
    print(f"Overall Success Rate: {report['test_summary']['overall_success_rate']:.1%}")
    print(f"Total Records Retrieved: {report['test_summary']['total_records_retrieved']:,}")
    
    print(f"\n🎯 Service Performance:")
    for service, stats in report['service_performance'].items():
        print(f"  {service}: {stats['success_rate']:.1%} success ({stats['successful_tests']}/{stats['total_tests']})")
        if stats['best_locations']:
            best_loc = stats['best_locations'][0]
            print(f"    Best: {best_loc[0]} ({best_loc[1]} records)")
    
    print(f"\n📍 Top Performing Locations:")
    sorted_locations = sorted(report['location_performance'].items(), 
                            key=lambda x: x[1]['total_records'], reverse=True)
    for loc_name, stats in sorted_locations[:5]:
        print(f"  {loc_name}: {stats['services_successful']}/{stats['services_tested']} services, {stats['total_records']} records")
    
    print(f"\n💾 Detailed results saved to: service_coverage_discovery_results.json")
    print(f"📋 Recommended test matrix available in results file")

if __name__ == "__main__":
    main()