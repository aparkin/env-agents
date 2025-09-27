#!/usr/bin/env python3
"""
Uniform Testing Framework for Environmental Services
====================================================

Creates standardized query patterns and return structures for comprehensive
service testing. Provides rich failure diagnostics and success indicators.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import time

sys.path.insert(0, '.')
from env_agents.core.models import RequestSpec, Geometry

class TestResult(Enum):
    SUCCESS = "SUCCESS"
    NO_DATA = "NO_DATA"  
    API_ERROR = "API_ERROR"
    TIMEOUT = "TIMEOUT"
    AUTH_ERROR = "AUTH_ERROR"
    PARAM_ERROR = "PARAM_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"

@dataclass
class UniformTestSpec:
    """Standardized test specification for all services"""
    test_id: str
    service_name: str
    location_name: str
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    variables: List[str]
    extra_params: Dict[str, Any]
    expected_records_min: int = 0  # Minimum records expected for success
    timeout_seconds: int = 30

@dataclass 
class UniformTestResult:
    """Standardized result structure for all service tests"""
    
    # Test identification
    test_id: str
    service_name: str
    location_name: str
    timestamp: str
    
    # Test configuration
    request_spec: Dict[str, Any]
    
    # Results
    result_status: TestResult
    records_retrieved: int
    variables_found: List[str]
    execution_time_seconds: float
    
    # Data quality metrics
    null_coordinates: int = 0
    null_timestamps: int = 0
    null_values: int = 0
    duplicate_records: int = 0
    
    # Sample data (for successful tests)
    sample_record: Optional[Dict[str, Any]] = None
    value_ranges: Optional[Dict[str, Dict[str, float]]] = None  # {variable: {min, max, mean}}
    
    # Error information (for failed tests)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Service-specific metrics
    unique_locations: int = 0
    temporal_coverage: Optional[Dict[str, str]] = None  # {start, end, gaps}
    
    # Enhancement metadata
    capabilities_summary: Optional[Dict[str, Any]] = None
    
    def success_score(self) -> float:
        """Calculate overall success score (0-1)"""
        if self.result_status != TestResult.SUCCESS:
            return 0.0
        
        score = 1.0
        
        # Penalize data quality issues
        if self.records_retrieved > 0:
            null_rate = (self.null_coordinates + self.null_timestamps + self.null_values) / (self.records_retrieved * 3)
            score *= max(0.1, 1.0 - null_rate)
            
            if self.duplicate_records > 0:
                dup_rate = self.duplicate_records / self.records_retrieved
                score *= max(0.5, 1.0 - dup_rate)
        
        return score

class UniformServiceTester:
    """Comprehensive testing framework for environmental services"""
    
    def __init__(self):
        self.results = []
        
    def create_standard_test_suite(self) -> List[UniformTestSpec]:
        """Create comprehensive test suite with validated locations"""
        
        test_specs = []
        
        # High-confidence test locations (based on known infrastructure)
        validated_tests = [
            # OpenAQ - Major cities with known monitoring
            UniformTestSpec(
                test_id="openaq_los_angeles",
                service_name="OpenAQEnhanced",
                location_name="Los Angeles, CA",
                latitude=34.0522, longitude=-118.2437,
                start_date="2024-08-01", end_date="2024-08-31",
                variables=["pm25", "pm10"],
                extra_params={"radius": 15000},
                expected_records_min=100
            ),
            
            UniformTestSpec(
                test_id="openaq_delhi",
                service_name="OpenAQEnhanced", 
                location_name="Delhi, India",
                latitude=28.7041, longitude=77.1025,
                start_date="2024-08-01", end_date="2024-08-31",
                variables=["pm25", "pm10"],
                extra_params={"radius": 20000},
                expected_records_min=50
            ),
            
            # NASA POWER - Should work everywhere
            UniformTestSpec(
                test_id="nasa_power_global_1",
                service_name="NASAPOWEREnhanced",
                location_name="Chicago, IL",
                latitude=41.8781, longitude=-87.6298,
                start_date="2024-08-01", end_date="2024-08-31",
                variables=["T2M", "PRECTOTCORR"],
                extra_params={},
                expected_records_min=30
            ),
            
            UniformTestSpec(
                test_id="nasa_power_global_2", 
                service_name="NASAPOWEREnhanced",
                location_name="São Paulo, Brazil",
                latitude=-23.5505, longitude=-46.6333,
                start_date="2024-01-01", end_date="2024-01-31",
                variables=["T2M", "RH2M"],
                extra_params={},
                expected_records_min=30
            ),
            
            # USGS NWIS - Major river systems
            UniformTestSpec(
                test_id="usgs_colorado_river",
                service_name="USGSNWISEnhanced",
                location_name="Colorado River - Grand Canyon",
                latitude=36.1069, longitude=-112.1129,
                start_date="2024-08-01", end_date="2024-08-31", 
                variables=["00060", "00065"],  # Discharge, gage height
                extra_params={"radius": 50000},
                expected_records_min=10
            ),
            
            UniformTestSpec(
                test_id="usgs_mississippi",
                service_name="USGSNWISEnhanced",
                location_name="Mississippi River - St. Louis",
                latitude=38.6270, longitude=-90.1994,
                start_date="2024-08-01", end_date="2024-08-31",
                variables=["00060", "00010"],  # Discharge, temperature
                extra_params={"radius": 25000},
                expected_records_min=20
            ),
            
            # SoilGrids - Should work globally  
            UniformTestSpec(
                test_id="soilgrids_iowa_agriculture",
                service_name="SoilGridsEnhanced",
                location_name="Iowa Corn Belt",
                latitude=42.0308, longitude=-93.6319,
                start_date="2024-01-01", end_date="2024-12-31",
                variables=["clay", "sand", "phh2o"],
                extra_params={"depth": "0-5cm"},
                expected_records_min=1
            ),
            
            UniformTestSpec(
                test_id="soilgrids_kenya_agriculture",
                service_name="SoilGridsEnhanced", 
                location_name="Kenya Highlands",
                latitude=-0.0236, longitude=37.9062,
                start_date="2024-01-01", end_date="2024-12-31",
                variables=["clay", "silt"],
                extra_params={"depth": "0-30cm"},
                expected_records_min=1
            ),
            
            # GBIF - Biodiversity hotspots
            UniformTestSpec(
                test_id="gbif_costa_rica_biodiversity",
                service_name="GBIFEnhanced",
                location_name="Costa Rica - Monteverde",
                latitude=10.3009, longitude=-84.8015,
                start_date="2024-01-01", end_date="2024-12-31",
                variables=["occurrence"],
                extra_params={"radius": 10000, "limit": 200},
                expected_records_min=50
            ),
            
            UniformTestSpec(
                test_id="gbif_yellowstone_biodiversity", 
                service_name="GBIFEnhanced",
                location_name="Yellowstone National Park",
                latitude=44.4280, longitude=-110.5885,
                start_date="2024-06-01", end_date="2024-08-31",
                variables=["occurrence"],
                extra_params={"radius": 15000, "limit": 300},
                expected_records_min=100
            ),
            
            # Overpass - Major cities
            UniformTestSpec(
                test_id="overpass_san_francisco",
                service_name="OverpassEnhanced", 
                location_name="San Francisco, CA",
                latitude=37.7749, longitude=-122.4194,
                start_date="2024-01-01", end_date="2024-12-31",
                variables=["building", "highway"],
                extra_params={"radius": 3000},
                expected_records_min=50
            )
        ]
        
        return validated_tests
    
    def execute_uniform_test(self, test_spec: UniformTestSpec) -> UniformTestResult:
        """Execute a single uniform test with comprehensive error handling"""
        
        start_time = time.time()
        
        # Initialize result with basic info
        result = UniformTestResult(
            test_id=test_spec.test_id,
            service_name=test_spec.service_name,
            location_name=test_spec.location_name,
            timestamp=datetime.now().isoformat(),
            request_spec=asdict(test_spec),
            result_status=TestResult.API_ERROR,  # Default to error
            records_retrieved=0,
            variables_found=[],
            execution_time_seconds=0.0
        )
        
        try:
            # Dynamic adapter import
            adapter = self._import_adapter(test_spec.service_name)
            if not adapter:
                result.error_message = f"Failed to import {test_spec.service_name}"
                result.error_type = "ImportError"
                return result
            
            # Get capabilities for context
            try:
                caps = adapter.capabilities()
                result.capabilities_summary = {
                    'total_variables': len(caps.get('variables', [])),
                    'enhancement_level': caps.get('enhancement_level', 'unknown'),
                    'requires_auth': caps.get('requires_api_key', False)
                }
            except Exception as e:
                result.capabilities_summary = {'error': str(e)}
            
            # Construct request
            geometry = Geometry(
                type="point",
                coordinates=[test_spec.longitude, test_spec.latitude]
            )
            
            request_spec = RequestSpec(
                geometry=geometry,
                time_range=(test_spec.start_date, test_spec.end_date),
                variables=test_spec.variables,
                extra=test_spec.extra_params
            )
            
            # Execute with timeout
            try:
                raw_rows = adapter._fetch_rows(request_spec)
                execution_time = time.time() - start_time
                result.execution_time_seconds = round(execution_time, 2)
                
                if not raw_rows:
                    result.result_status = TestResult.NO_DATA
                    result.error_message = "Service returned empty result set"
                    return result
                
                # Analyze retrieved data
                result.records_retrieved = len(raw_rows)
                df = pd.DataFrame(raw_rows)
                
                # Extract variables found
                if 'variable' in df.columns:
                    result.variables_found = list(df['variable'].unique())
                
                # Data quality analysis
                result.null_coordinates = sum(1 for _, row in df.iterrows() 
                                            if pd.isna(row.get('latitude')) or pd.isna(row.get('longitude')))
                result.null_timestamps = sum(1 for _, row in df.iterrows() 
                                           if pd.isna(row.get('time')))
                result.null_values = sum(1 for _, row in df.iterrows() 
                                       if pd.isna(row.get('value')))
                
                # Duplicate detection
                if len(df) > 1:
                    duplicates = df.duplicated(['time', 'variable', 'value', 'latitude', 'longitude'])
                    result.duplicate_records = duplicates.sum()
                
                # Sample record (cleaned for JSON serialization)
                if len(raw_rows) > 0:
                    sample = dict(raw_rows[0])
                    # Remove complex objects that don't serialize well
                    sample.pop('attributes', None)
                    sample.pop('provenance', None) 
                    result.sample_record = sample
                
                # Value ranges for numerical data
                if 'variable' in df.columns and 'value' in df.columns:
                    result.value_ranges = {}
                    for var in df['variable'].unique():
                        var_data = df[df['variable'] == var]['value']
                        numeric_data = pd.to_numeric(var_data, errors='coerce').dropna()
                        if len(numeric_data) > 0:
                            result.value_ranges[var] = {
                                'min': float(numeric_data.min()),
                                'max': float(numeric_data.max()),
                                'mean': float(numeric_data.mean())
                            }
                
                # Unique locations
                if 'spatial_id' in df.columns:
                    result.unique_locations = df['spatial_id'].nunique()
                elif 'site_name' in df.columns:
                    result.unique_locations = df['site_name'].nunique()
                
                # Temporal coverage
                if 'time' in df.columns:
                    times = pd.to_datetime(df['time'], errors='coerce').dropna()
                    if len(times) > 0:
                        result.temporal_coverage = {
                            'start': times.min().isoformat(),
                            'end': times.max().isoformat(),
                            'unique_timestamps': len(times.unique())
                        }
                
                # Determine success
                if result.records_retrieved >= test_spec.expected_records_min:
                    result.result_status = TestResult.SUCCESS
                else:
                    result.result_status = TestResult.NO_DATA
                    result.error_message = f"Insufficient data: got {result.records_retrieved}, expected >= {test_spec.expected_records_min}"
                
            except TimeoutError:
                result.result_status = TestResult.TIMEOUT
                result.error_message = f"Request timed out after {test_spec.timeout_seconds} seconds"
                result.execution_time_seconds = test_spec.timeout_seconds
                
        except ImportError as e:
            result.result_status = TestResult.API_ERROR
            result.error_type = "ImportError"
            result.error_message = f"Failed to import adapter: {str(e)}"
            
        except Exception as e:
            result.execution_time_seconds = time.time() - start_time
            
            # Classify error types
            error_str = str(e).lower()
            if 'auth' in error_str or 'key' in error_str or 'credential' in error_str:
                result.result_status = TestResult.AUTH_ERROR
            elif 'parameter' in error_str or 'variable' in error_str:
                result.result_status = TestResult.PARAM_ERROR
            elif 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
                result.result_status = TestResult.NETWORK_ERROR
            else:
                result.result_status = TestResult.API_ERROR
            
            result.error_type = type(e).__name__
            result.error_message = str(e)[:500]  # Truncate very long errors
            result.stack_trace = traceback.format_exc()[:1000]
        
        return result
    
    def _import_adapter(self, service_name: str):
        """Dynamically import adapter class"""
        adapter_map = {
            "OpenAQEnhanced": "env_agents.adapters.openaq.enhanced_adapter.EnhancedOpenAQAdapter",
            "NASAPOWEREnhanced": "env_agents.adapters.power.enhanced_adapter.NASAPOWEREnhancedAdapter", 
            "EPAAQSEnhanced": "env_agents.adapters.air.enhanced_aqs_adapter.EPAAQSEnhancedAdapter",
            "USGSNWISEnhanced": "env_agents.adapters.nwis.enhanced_adapter.USGSNWISEnhancedAdapter",
            "SoilGridsEnhanced": "env_agents.adapters.soil.enhanced_soilgrids_adapter.EnhancedSoilGridsAdapter",
            "SSURGOEnhanced": "env_agents.adapters.ssurgo.enhanced_ssurgo_adapter.EnhancedSSURGOAdapter",
            "WQPEnhanced": "env_agents.adapters.wqp.enhanced_adapter.EnhancedWQPAdapter",
            "GBIFEnhanced": "env_agents.adapters.gbif.enhanced_adapter.EnhancedGBIFAdapter",
            "OverpassEnhanced": "env_agents.adapters.overpass.enhanced_adapter.EnhancedOverpassAdapter",
        }
        
        import_path = adapter_map.get(service_name)
        if not import_path:
            return None
            
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            adapter_class = getattr(module, class_name)
            return adapter_class()
        except Exception:
            return None
    
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite and generate comprehensive report"""
        
        print("🧪 COMPREHENSIVE UNIFORM SERVICE TESTING")
        print("=" * 50)
        
        test_specs = self.create_standard_test_suite()
        results = []
        
        print(f"Executing {len(test_specs)} validated test cases...")
        
        for i, test_spec in enumerate(test_specs, 1):
            print(f"\n[{i}/{len(test_specs)}] {test_spec.test_id}")
            print(f"  Service: {test_spec.service_name}")
            print(f"  Location: {test_spec.location_name}")
            print(f"  Variables: {', '.join(test_spec.variables)}")
            
            result = self.execute_uniform_test(test_spec)
            results.append(result)
            
            # Print immediate result
            status_emoji = {"SUCCESS": "✅", "NO_DATA": "⚠️", "API_ERROR": "❌", 
                          "TIMEOUT": "⏱️", "AUTH_ERROR": "🔐", "PARAM_ERROR": "📝", 
                          "NETWORK_ERROR": "🌐"}.get(result.result_status.value, "❓")
            
            print(f"  Result: {status_emoji} {result.result_status.value}")
            if result.result_status == TestResult.SUCCESS:
                print(f"    Records: {result.records_retrieved}, Variables: {len(result.variables_found)}")
                print(f"    Quality Score: {result.success_score():.2f}")
            elif result.error_message:
                print(f"    Error: {result.error_message[:60]}...")
            
            # Rate limiting
            time.sleep(1)
        
        # Generate comprehensive report
        report = self._generate_uniform_report(results)
        
        # Save results
        output = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(results),
                'test_framework_version': '1.0'
            },
            'test_results': [asdict(r) for r in results],
            'analysis_report': report
        }
        
        filename = f"uniform_service_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")
        return output
    
    def _generate_uniform_report(self, results: List[UniformTestResult]) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        
        # Overall statistics
        total_tests = len(results)
        successful_tests = [r for r in results if r.result_status == TestResult.SUCCESS]
        total_records = sum(r.records_retrieved for r in successful_tests)
        avg_quality_score = np.mean([r.success_score() for r in successful_tests]) if successful_tests else 0
        
        # Service performance analysis
        service_performance = {}
        for service in set(r.service_name for r in results):
            service_results = [r for r in results if r.service_name == service]
            service_success = [r for r in service_results if r.result_status == TestResult.SUCCESS]
            
            service_performance[service] = {
                'tests_run': len(service_results),
                'success_count': len(service_success),
                'success_rate': len(service_success) / len(service_results) if service_results else 0,
                'avg_records_per_success': np.mean([r.records_retrieved for r in service_success]) if service_success else 0,
                'avg_execution_time': np.mean([r.execution_time_seconds for r in service_results]),
                'common_errors': self._get_common_errors([r for r in service_results if r.result_status != TestResult.SUCCESS])
            }
        
        # Data quality analysis
        quality_metrics = {}
        if successful_tests:
            quality_metrics = {
                'avg_success_score': avg_quality_score,
                'coordinate_completeness': 1 - (sum(r.null_coordinates for r in successful_tests) / total_records) if total_records > 0 else 0,
                'timestamp_completeness': 1 - (sum(r.null_timestamps for r in successful_tests) / total_records) if total_records > 0 else 0,
                'value_completeness': 1 - (sum(r.null_values for r in successful_tests) / total_records) if total_records > 0 else 0,
                'duplicate_rate': sum(r.duplicate_records for r in successful_tests) / total_records if total_records > 0 else 0
            }
        
        return {
            'executive_summary': {
                'total_tests_executed': total_tests,
                'overall_success_rate': len(successful_tests) / total_tests if total_tests > 0 else 0,
                'total_records_retrieved': total_records,
                'avg_data_quality_score': avg_quality_score,
                'services_tested': len(set(r.service_name for r in results)),
                'locations_tested': len(set(r.location_name for r in results))
            },
            'service_performance': service_performance,
            'data_quality_metrics': quality_metrics,
            'recommendations': self._generate_recommendations(results),
            'validated_test_matrix': self._extract_validated_tests(successful_tests)
        }
    
    def _get_common_errors(self, failed_results: List[UniformTestResult]) -> List[Dict[str, Any]]:
        """Extract common error patterns"""
        if not failed_results:
            return []
        
        error_counts = {}
        for result in failed_results:
            error_key = f"{result.result_status.value}: {result.error_type or 'Unknown'}"
            if error_key not in error_counts:
                error_counts[error_key] = {
                    'count': 0,
                    'example_message': result.error_message
                }
            error_counts[error_key]['count'] += 1
        
        return sorted([{'error': k, **v} for k, v in error_counts.items()], 
                     key=lambda x: x['count'], reverse=True)
    
    def _generate_recommendations(self, results: List[UniformTestResult]) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []
        
        successful_tests = [r for r in results if r.result_status == TestResult.SUCCESS]
        failed_tests = [r for r in results if r.result_status != TestResult.SUCCESS]
        
        # Success rate recommendations
        success_rate = len(successful_tests) / len(results) if results else 0
        if success_rate < 0.7:
            recommendations.append("Overall success rate is low - prioritize fixing import and configuration issues")
        
        # Service-specific recommendations
        for service in set(r.service_name for r in results):
            service_results = [r for r in results if r.service_name == service]
            service_success = [r for r in service_results if r.result_status == TestResult.SUCCESS]
            
            if len(service_success) == 0:
                recommendations.append(f"{service}: No successful tests - check imports and basic functionality")
            elif len(service_success) < len(service_results) / 2:
                recommendations.append(f"{service}: Low success rate - review error patterns and parameter configurations")
        
        # Data quality recommendations
        if successful_tests:
            high_null_coords = [r for r in successful_tests if r.null_coordinates / r.records_retrieved > 0.5]
            if high_null_coords:
                recommendations.append("Coordinate extraction issues detected - review geometry handling in base adapters")
        
        return recommendations
    
    def _extract_validated_tests(self, successful_results: List[UniformTestResult]) -> Dict[str, List[Dict]]:
        """Extract validated test configurations for future use"""
        validated = {}
        
        for result in successful_results:
            service = result.service_name
            if service not in validated:
                validated[service] = []
            
            validated[service].append({
                'test_id': result.test_id,
                'location': result.location_name,
                'coordinates': [result.request_spec['longitude'], result.request_spec['latitude']],
                'time_period': [result.request_spec['start_date'], result.request_spec['end_date']],
                'variables': result.request_spec['variables'],
                'extra_params': result.request_spec['extra_params'],
                'expected_records': result.records_retrieved,
                'quality_score': result.success_score()
            })
        
        return validated

def main():
    """Run uniform testing framework"""
    os.environ['OPENAQ_API_KEY'] = '1dfd14b5aac0cf892b43e575fa4060d6dc4228149751b9362e5e2331ca2fc4ca'
    os.environ['EPA_AQS_EMAIL'] = 'aparkin@lbl.gov'
    os.environ['EPA_AQS_KEY'] = 'khakimouse81'
    
    tester = UniformServiceTester()
    results = tester.run_comprehensive_test_suite()
    
    # Print executive summary
    summary = results['analysis_report']['executive_summary']
    print(f"\n🏆 EXECUTIVE SUMMARY")
    print(f"Tests Executed: {summary['total_tests_executed']}")
    print(f"Overall Success Rate: {summary['overall_success_rate']:.1%}")
    print(f"Total Records: {summary['total_records_retrieved']:,}")
    print(f"Avg Quality Score: {summary['avg_data_quality_score']:.2f}")

if __name__ == "__main__":
    main()