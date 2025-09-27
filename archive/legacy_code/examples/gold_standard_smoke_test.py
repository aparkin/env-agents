#!/usr/bin/env python3
"""
Enhanced Smoke Test for Gold Standard Environmental Data Services

This comprehensive test validates the three gold standard services (NWIS, OpenAQ, NASA POWER)
and demonstrates the semantic expansion framework for environmental data integration.
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from pprint import pprint

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Core imports
from env_agents.core.models import Geometry, RequestSpec, CORE_COLUMNS
from env_agents.core.router import EnvRouter
from env_agents.core.service_discovery import ServiceDiscoveryEngine, RegistryValidator
from env_agents.core.registry_curation import RegistryCurator, AutoCurationPipeline

# Gold standard adapters
from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter  
from env_agents.adapters.openaq.adapter import OpenaqV3Adapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gold_standard_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_LOCATIONS = {
    "berkeley_ca": [-122.27, 37.87],
    "sacramento_ca": [-121.5, 38.6], 
    "denver_co": [-105.0, 39.7],
    "washington_dc": [-77.0, 38.9]
}

SEMANTIC_COLS = ["observed_property_uri", "unit_uri", "preferred_unit", "canonical_variable"]


def setup_enhanced_router(base_dir: str = ".") -> EnvRouter:
    """Setup router with enhanced discovery and curation capabilities"""
    logger.info("Setting up enhanced environmental data router")
    
    router = EnvRouter(base_dir=base_dir)
    
    # Register gold standard adapters
    router.register(NasaPowerDailyAdapter())
    router.register(UsgsNwisLiveAdapter())
    router.register(OpenaqV3Adapter())
    
    logger.info(f"Registered adapters: {router.list_adapters()}")
    return router


def validate_dataframe_structure(df: pd.DataFrame, service_name: str) -> Dict[str, Any]:
    """Comprehensive DataFrame validation"""
    validation_results = {
        'service': service_name,
        'passed': True,
        'errors': [],
        'warnings': [],
        'row_count': len(df),
        'column_count': len(df.columns),
        'semantic_completeness': 0.0
    }
    
    # Check core columns
    missing_core = [col for col in CORE_COLUMNS if col not in df.columns]
    if missing_core:
        validation_results['errors'].append(f"Missing core columns: {missing_core}")
        validation_results['passed'] = False
    
    # Check semantic columns
    missing_semantic = [col for col in SEMANTIC_COLS if col not in df.columns]
    if missing_semantic:
        validation_results['warnings'].append(f"Missing semantic columns: {missing_semantic}")
    else:
        # Calculate semantic completeness
        semantic_complete_rows = 0
        for _, row in df.iterrows():
            if all(pd.notna(row.get(col)) and row.get(col) != '' for col in SEMANTIC_COLS):
                semantic_complete_rows += 1
        
        if len(df) > 0:
            validation_results['semantic_completeness'] = semantic_complete_rows / len(df)
    
    # Validate data types and structure
    if not df.empty:
        # Check attributes column
        if 'attributes' in df.columns:
            non_dict_attrs = ~df['attributes'].dropna().apply(lambda x: isinstance(x, dict))
            if non_dict_attrs.any():
                validation_results['errors'].append("Some attributes are not dictionaries")
                validation_results['passed'] = False
        
        # Check provenance column
        if 'provenance' in df.columns:
            non_dict_prov = ~df['provenance'].dropna().apply(lambda x: isinstance(x, dict))
            if non_dict_prov.any():
                validation_results['errors'].append("Some provenance entries are not dictionaries")
                validation_results['passed'] = False
        
        # Check observation ID stability
        from env_agents.core.ids import compute_observation_id
        expected_ids = compute_observation_id(df)
        if 'observation_id' in df.columns:
            id_mismatch = ~expected_ids.equals(df['observation_id'])
            if id_mismatch:
                validation_results['errors'].append("Observation ID instability detected")
                validation_results['passed'] = False
    
    # Check DataFrame metadata
    required_attrs = ['schema', 'capabilities', 'variable_registry']
    missing_attrs = [attr for attr in required_attrs if attr not in df.attrs]
    if missing_attrs:
        validation_results['warnings'].append(f"Missing DataFrame attributes: {missing_attrs}")
    
    return validation_results


def test_service_capabilities(router: EnvRouter) -> Dict[str, Any]:
    """Test and compare service capabilities"""
    logger.info("Testing service capabilities and parameter discovery")
    
    capabilities_report = {}
    
    for service_name in router.list_adapters():
        adapter = router.adapters[service_name]
        
        try:
            # Get capabilities
            caps = adapter.capabilities()
            
            # Try harvest if available
            harvest_count = 0
            if hasattr(adapter, 'harvest') and callable(adapter.harvest):
                try:
                    harvested = adapter.harvest()
                    harvest_count = len(harvested) if isinstance(harvested, list) else 0
                except Exception as e:
                    logger.warning(f"Harvest failed for {service_name}: {e}")
            
            capabilities_report[service_name] = {
                'variables_count': len(caps.get('variables', [])),
                'harvest_count': harvest_count,
                'requires_api_key': caps.get('requires_api_key', False),
                'geometry_support': caps.get('geometry', []),
                'temporal_requirements': caps.get('requires_time_range', False),
                'sample_variables': caps.get('variables', [])[:3]  # First 3 for inspection
            }
            
        except Exception as e:
            logger.error(f"Capabilities test failed for {service_name}: {e}")
            capabilities_report[service_name] = {'error': str(e)}
    
    return capabilities_report


def test_semantic_discovery(router: EnvRouter) -> Dict[str, Any]:
    """Test automated semantic discovery and mapping"""
    logger.info("Testing automated semantic discovery pipeline")
    
    # Initialize discovery engine
    discovery_engine = ServiceDiscoveryEngine(router.registry, base_dir=".")
    
    discovery_results = {}
    
    for service_name in ["NASA_POWER", "USGS_NWIS"]:  # Test subset for speed
        if service_name in router.adapters:
            adapter = router.adapters[service_name]
            
            try:
                report = discovery_engine.discover_service_parameters(
                    adapter,
                    auto_accept_threshold=0.90,
                    suggest_threshold=0.60
                )
                
                discovery_results[service_name] = {
                    'discovered_count': report.discovered_count,
                    'auto_accepted': len(report.auto_accepted),
                    'review_queue': len(report.review_queue),
                    'failed_matches': len(report.failed_matches),
                    'execution_time': report.execution_time,
                    'errors': report.errors
                }
                
                # Show sample auto-accepted mappings
                if report.auto_accepted:
                    discovery_results[service_name]['sample_accepted'] = [
                        {
                            'native': match.native_id,
                            'canonical': match.canonical,
                            'confidence': match.score,
                            'reasons': match.reasons[:2]  # First 2 reasons
                        }
                        for match in report.auto_accepted[:3]
                    ]
                
            except Exception as e:
                logger.error(f"Discovery failed for {service_name}: {e}")
                discovery_results[service_name] = {'error': str(e)}
    
    return discovery_results


def test_data_fetching(router: EnvRouter) -> Dict[str, Any]:
    """Test data fetching with semantic validation"""
    logger.info("Testing data fetching across gold standard services")
    
    fetch_results = {}
    berkeley_coords = TEST_LOCATIONS["berkeley_ca"]
    
    # Test NASA POWER
    try:
        power_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=berkeley_coords),
            time_range=("2023-01-01", "2023-01-03"),
            variables=["atm:air_temperature_2m", "atm:precipitation_corrected"]
        )
        power_df = router.fetch("NASA_POWER", power_spec)
        fetch_results["NASA_POWER"] = validate_dataframe_structure(power_df, "NASA_POWER")
        
    except Exception as e:
        logger.error(f"NASA POWER fetch failed: {e}")
        fetch_results["NASA_POWER"] = {'error': str(e)}
    
    # Test USGS NWIS (instantaneous values)
    try:
        nwis_spec = RequestSpec(
            geometry=Geometry(type="point", coordinates=[-121.5, 38.6]),
            time_range=("2023-01-01T00:00:00Z", "2023-01-01T06:00:00Z"),
            variables=["water:discharge_cfs"],
            extra={"sites": ["11447650"], "max_sites": 1}
        )
        nwis_df = router.fetch("USGS_NWIS", nwis_spec)
        fetch_results["USGS_NWIS"] = validate_dataframe_structure(nwis_df, "USGS_NWIS")
        
    except Exception as e:
        logger.error(f"USGS NWIS fetch failed: {e}")
        fetch_results["USGS_NWIS"] = {'error': str(e)}
    
    # Test OpenAQ (conditional on API key)
    if os.getenv("OPENAQ_API_KEY"):
        try:
            openaq_spec = RequestSpec(
                geometry=Geometry(type="point", coordinates=berkeley_coords),
                time_range=("2023-01-01T00:00:00Z", "2023-01-01T12:00:00Z"),
                variables=["air:pm25_mass_concentration", "air:ozone_concentration"],
                extra={"radius_m": 5000, "max_sensors": 2}
            )
            openaq_df = router.fetch("OpenAQ", openaq_spec)
            fetch_results["OpenAQ"] = validate_dataframe_structure(openaq_df, "OpenAQ")
            
        except Exception as e:
            logger.error(f"OpenAQ fetch failed: {e}")
            fetch_results["OpenAQ"] = {'error': str(e)}
    else:
        fetch_results["OpenAQ"] = {'skipped': 'No API key provided'}
    
    return fetch_results


def test_registry_quality(router: EnvRouter) -> Dict[str, Any]:
    """Test registry quality and consistency"""
    logger.info("Testing registry quality and semantic consistency")
    
    validator = RegistryValidator(router.registry)
    
    # Validate consistency
    consistency_issues = validator.validate_registry_consistency()
    
    # Generate quality report
    curator = RegistryCurator(router.registry, "test_curator")
    quality_report = curator.generate_quality_report()
    
    # Get improvement suggestions
    improvements = validator.suggest_registry_improvements()
    
    return {
        'consistency_issues': consistency_issues,
        'quality_metrics': {
            'total_variables': quality_report.total_variables,
            'missing_uris': quality_report.missing_uris,
            'missing_units': quality_report.missing_units,
            'coverage_by_domain': quality_report.coverage_by_domain,
        },
        'improvement_suggestions': improvements,
        'recommendations': quality_report.recommendations
    }


def run_comprehensive_test() -> Dict[str, Any]:
    """Run the complete gold standard test suite"""
    logger.info("Starting comprehensive gold standard test suite")
    start_time = datetime.now()
    
    # Setup
    router = setup_enhanced_router()
    
    # Run test suite
    test_results = {
        'test_run_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'start_time': start_time.isoformat(),
        'capabilities': test_service_capabilities(router),
        'semantic_discovery': test_semantic_discovery(router),
        'data_fetching': test_data_fetching(router),
        'registry_quality': test_registry_quality(router)
    }
    
    # Calculate summary statistics
    end_time = datetime.now()
    test_results['end_time'] = end_time.isoformat()
    test_results['duration_seconds'] = (end_time - start_time).total_seconds()
    
    # Overall success metrics
    fetch_successes = sum(1 for result in test_results['data_fetching'].values() 
                         if isinstance(result, dict) and result.get('passed', False))
    total_services = len(router.list_adapters())
    
    test_results['summary'] = {
        'services_tested': total_services,
        'successful_fetches': fetch_successes,
        'success_rate': fetch_successes / total_services if total_services > 0 else 0,
        'semantic_discovery_rate': len([r for r in test_results['semantic_discovery'].values() 
                                       if isinstance(r, dict) and r.get('auto_accepted', 0) > 0]),
        'overall_status': 'PASS' if fetch_successes >= 2 else 'PARTIAL'  # At least 2 services working
    }
    
    return test_results


def main():
    """Main test execution"""
    print("🧪 Gold Standard Environmental Data Services Test Suite")
    print("=" * 60)
    
    try:
        results = run_comprehensive_test()
        
        # Print summary
        summary = results['summary']
        print(f"\n✅ Test Results Summary:")
        print(f"   Services Tested: {summary['services_tested']}")
        print(f"   Successful Fetches: {summary['successful_fetches']}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print(f"   Overall Status: {summary['overall_status']}")
        print(f"   Duration: {results['duration_seconds']:.1f} seconds")
        
        # Print capabilities summary
        print(f"\n📊 Service Capabilities:")
        for service, caps in results['capabilities'].items():
            if 'error' not in caps:
                print(f"   {service}: {caps['variables_count']} variables, "
                      f"harvest: {caps['harvest_count']}")
        
        # Print semantic discovery results
        print(f"\n🔍 Semantic Discovery:")
        for service, disc in results['semantic_discovery'].items():
            if 'error' not in disc:
                print(f"   {service}: {disc['auto_accepted']} auto-accepted, "
                      f"{disc['review_queue']} for review")
        
        # Print data quality
        quality = results['registry_quality']['quality_metrics']
        print(f"\n📈 Registry Quality:")
        print(f"   Total Variables: {quality['total_variables']}")
        print(f"   Domain Coverage: {list(quality['coverage_by_domain'].keys())}")
        
        # Save detailed results
        import json
        output_file = f"test_results_{results['test_run_id']}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Return appropriate exit code
        sys.exit(0 if summary['overall_status'] == 'PASS' else 1)
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()