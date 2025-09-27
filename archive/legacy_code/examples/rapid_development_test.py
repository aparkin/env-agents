#!/usr/bin/env python3
"""
Rapid Development Testing Framework

Ultra-fast testing cycle for environmental services development:
- Unit tests: < 30 seconds
- Integration tests: < 3 minutes  
- Full validation: < 10 minutes

Usage:
    python rapid_development_test.py --level unit
    python rapid_development_test.py --level integration --service NWIS
    python rapid_development_test.py --level full --parallel
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
import json

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Core imports
from env_agents.core.router import EnvRouter
from env_agents.core.models import Geometry, RequestSpec
from env_agents.core.service_discovery import ServiceDiscoveryEngine

# Adapters
from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
from env_agents.adapters.openaq.adapter import OpenaqV3Adapter  
from env_agents.adapters.power.adapter import NasaPowerDailyAdapter

# New soil adapters (optional - require shapely)
try:
    from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
    from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
    SOIL_ADAPTERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Soil adapters not available: {e}")
    UsdaSurgoAdapter = None
    IsricSoilGridsAdapter = None
    SOIL_ADAPTERS_AVAILABLE = False

logging.basicConfig(level=logging.WARNING)  # Quiet logging for speed
logger = logging.getLogger(__name__)

# Test configurations for different speed/coverage tradeoffs
TEST_CONFIGS = {
    "unit": {
        "max_parameters": 5,
        "sample_locations": 1, 
        "time_range_days": 1,
        "timeout": 10,
        "parallel": False
    },
    "integration": {
        "max_parameters": 20,
        "sample_locations": 2,
        "time_range_days": 3, 
        "timeout": 30,
        "parallel": True
    },
    "full": {
        "max_parameters": None,
        "sample_locations": 5,
        "time_range_days": 7,
        "timeout": 60,
        "parallel": True
    }
}

TEST_LOCATIONS = [
    [-122.27, 37.87],  # Berkeley, CA
    [-121.5, 38.6],    # Sacramento, CA
    [-105.0, 39.7],    # Denver, CO
    [-77.0, 38.9],     # Washington, DC
    [-74.0, 40.7]      # New York, NY
]


class RapidTester:
    """Ultra-fast testing framework for environmental services"""
    
    def __init__(self, test_level: str = "unit"):
        self.config = TEST_CONFIGS[test_level]
        self.test_level = test_level
        self.results = {
            "test_level": test_level,
            "start_time": time.time(),
            "services": {},
            "summary": {}
        }
        
        # Setup router with all services
        self.router = self._setup_router()
        
    def _setup_router(self) -> EnvRouter:
        """Setup router with all available services"""
        router = EnvRouter(base_dir=".")
        
        # Gold standard services
        router.register(UsgsNwisLiveAdapter())
        router.register(OpenaqV3Adapter()) 
        router.register(NasaPowerDailyAdapter())
        
        # New soil services (if available)
        if SOIL_ADAPTERS_AVAILABLE:
            router.register(UsdaSurgoAdapter())
            router.register(IsricSoilGridsAdapter())
        
        return router
    
    def run_tests(self, 
                 service_filter: Optional[str] = None,
                 parallel: Optional[bool] = None) -> Dict[str, Any]:
        """Run test suite with specified configuration"""
        
        use_parallel = parallel if parallel is not None else self.config["parallel"]
        services = self.router.list_adapters()
        
        if service_filter:
            services = [s for s in services if service_filter.upper() in s.upper()]
        
        print(f"🧪 Running {self.test_level} tests for {len(services)} services")
        print(f"⚙️  Config: {self.config}")
        
        if use_parallel and len(services) > 1:
            self._run_parallel_tests(services)
        else:
            self._run_sequential_tests(services)
        
        self._generate_summary()
        return self.results
    
    def _run_parallel_tests(self, services: List[str]):
        """Run tests in parallel for speed"""
        with ThreadPoolExecutor(max_workers=min(len(services), 4)) as executor:
            # Submit all service tests
            future_to_service = {
                executor.submit(self._test_service, service): service 
                for service in services
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_service):
                service = future_to_service[future]
                try:
                    result = future.result(timeout=self.config["timeout"])
                    self.results["services"][service] = result
                    status = "✅" if result["passed"] else "❌"
                    print(f"{status} {service}: {result['execution_time']:.1f}s")
                except Exception as e:
                    self.results["services"][service] = {"error": str(e), "passed": False}
                    print(f"❌ {service}: {e}")
    
    def _run_sequential_tests(self, services: List[str]):
        """Run tests sequentially"""
        for service in services:
            try:
                result = self._test_service(service)
                self.results["services"][service] = result
                status = "✅" if result["passed"] else "❌" 
                print(f"{status} {service}: {result['execution_time']:.1f}s")
            except Exception as e:
                self.results["services"][service] = {"error": str(e), "passed": False}
                print(f"❌ {service}: {e}")
    
    def _test_service(self, service_name: str) -> Dict[str, Any]:
        """Test individual service with rapid validation"""
        start_time = time.time()
        adapter = self.router.adapters[service_name]
        
        test_result = {
            "service": service_name,
            "passed": True,
            "tests": {},
            "warnings": [],
            "errors": []
        }
        
        # Test 1: Capabilities (always fast)
        test_result["tests"]["capabilities"] = self._test_capabilities(adapter)
        
        # Test 2: Harvester (if available)
        if hasattr(adapter, 'harvest'):
            test_result["tests"]["harvest"] = self._test_harvest(adapter)
        elif hasattr(adapter, '_harvest_parameter_codes'):
            test_result["tests"]["harvest"] = self._test_legacy_harvest(adapter, '_harvest_parameter_codes')
        elif hasattr(adapter, '_openaq_parameter_catalog'):
            test_result["tests"]["harvest"] = self._test_legacy_harvest(adapter, '_openaq_parameter_catalog')
        elif hasattr(adapter, '_harvest_power_parameters'):
            test_result["tests"]["harvest"] = self._test_legacy_harvest(adapter, '_harvest_power_parameters')
        
        # Test 3: Data fetching (with appropriate test data)
        if self.test_level in ["integration", "full"]:
            test_result["tests"]["fetch"] = self._test_data_fetch(adapter)
        
        # Test 4: Semantic discovery (integration/full only)
        if self.test_level == "full":
            test_result["tests"]["discovery"] = self._test_semantic_discovery(adapter)
        
        # Overall pass/fail
        test_result["passed"] = all(
            t.get("passed", False) for t in test_result["tests"].values()
        )
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_capabilities(self, adapter) -> Dict[str, Any]:
        """Test adapter capabilities method"""
        try:
            caps = adapter.capabilities()
            
            # Basic structure validation
            required_keys = ["dataset", "variables", "geometry"]
            missing = [k for k in required_keys if k not in caps]
            
            if missing:
                return {"passed": False, "error": f"Missing keys: {missing}"}
            
            variables = caps.get("variables", [])
            variable_count = len(variables)
            
            # Limit for speed in unit tests
            if self.config["max_parameters"]:
                variable_count = min(variable_count, self.config["max_parameters"])
            
            return {
                "passed": True,
                "variable_count": variable_count,
                "geometry_support": caps.get("geometry", []),
                "requires_api_key": caps.get("requires_api_key", False)
            }
            
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _test_harvest(self, adapter) -> Dict[str, Any]:
        """Test formal harvest method"""
        try:
            harvested = adapter.harvest()
            
            if not isinstance(harvested, list):
                return {"passed": False, "error": "harvest() must return list"}
            
            if not harvested:
                return {"passed": True, "harvested_count": 0, "warning": "No parameters harvested"}
            
            # Validate structure of first few items
            sample_size = min(len(harvested), 3)
            for i, item in enumerate(harvested[:sample_size]):
                if not isinstance(item, dict):
                    return {"passed": False, "error": f"Item {i} not a dict"}
                
                required_fields = ["service", "native_id"]
                missing = [f for f in required_fields if f not in item]
                if missing:
                    return {"passed": False, "error": f"Item {i} missing fields: {missing}"}
            
            return {
                "passed": True,
                "harvested_count": len(harvested),
                "sample": harvested[:2]  # First 2 for inspection
            }
            
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _test_legacy_harvest(self, adapter, method_name: str) -> Dict[str, Any]:
        """Test legacy harvesting methods"""
        try:
            method = getattr(adapter, method_name)
            
            # Call with appropriate parameters
            if method_name == '_harvest_parameter_codes':
                result = method(groups="PHY")  # Physical parameters only for speed
            elif method_name == '_openaq_parameter_catalog':
                # This needs headers - skip for unit tests
                if self.test_level == "unit":
                    return {"passed": True, "skipped": "API key required"}
                # Would need API key setup for real test
                return {"passed": True, "skipped": "Requires API key configuration"}
            elif method_name == '_harvest_power_parameters':
                result = method(community="RE")
            else:
                result = method()
            
            count = len(result) if isinstance(result, list) else 0
            
            return {
                "passed": True,
                "method": method_name,
                "harvested_count": count,
                "legacy_method": True
            }
            
        except Exception as e:
            return {"passed": False, "error": str(e), "method": method_name}
    
    def _test_data_fetch(self, adapter) -> Dict[str, Any]:
        """Test data fetching with minimal query"""
        try:
            # Use first test location
            location = TEST_LOCATIONS[0]
            
            # Build appropriate request for service
            spec = self._build_test_request(adapter.DATASET, location)
            
            # Fetch data
            df = self.router.fetch(adapter.DATASET, spec)
            
            # Basic validation
            if df is None:
                return {"passed": False, "error": "fetch() returned None"}
            
            # Check core structure
            from env_agents.core.models import CORE_COLUMNS
            missing_cols = [c for c in CORE_COLUMNS if c not in df.columns]
            
            return {
                "passed": len(missing_cols) == 0,
                "row_count": len(df),
                "column_count": len(df.columns),
                "missing_core_columns": missing_cols,
                "has_data": not df.empty
            }
            
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _build_test_request(self, dataset: str, location: List[float]) -> RequestSpec:
        """Build appropriate test request for each service"""
        
        base_spec = {
            "geometry": Geometry(type="point", coordinates=location),
            "variables": None  # Use service defaults
        }
        
        if dataset == "NASA_POWER":
            base_spec["time_range"] = ("2023-01-01", "2023-01-02")
            base_spec["variables"] = ["atm:air_temperature_2m"]
            
        elif dataset == "USGS_NWIS":
            base_spec["time_range"] = ("2023-01-01T00:00:00Z", "2023-01-01T06:00:00Z")
            base_spec["variables"] = ["water:discharge_cfs"]
            base_spec["extra"] = {"max_sites": 1}
            
        elif dataset == "OpenAQ":
            if not os.getenv("OPENAQ_API_KEY"):
                # Skip if no API key
                raise Exception("OpenAQ requires API key - skipping")
            base_spec["time_range"] = ("2023-01-01T00:00:00Z", "2023-01-01T03:00:00Z")
            base_spec["variables"] = ["air:pm25_mass_concentration"]
            base_spec["extra"] = {"max_sensors": 1}
            
        elif dataset in ["USDA_SURGO", "ISRIC_SoilGrids"]:
            # Soil data doesn't need time range
            base_spec["variables"] = ["soil:clay_content_percent"]
        
        return RequestSpec(**base_spec)
    
    def _test_semantic_discovery(self, adapter) -> Dict[str, Any]:
        """Test semantic discovery pipeline"""
        try:
            discovery_engine = ServiceDiscoveryEngine(self.router.registry, base_dir=".")
            
            report = discovery_engine.discover_service_parameters(
                adapter,
                auto_accept_threshold=0.90,
                suggest_threshold=0.60
            )
            
            return {
                "passed": True,
                "discovered_count": report.discovered_count,
                "auto_accepted": len(report.auto_accepted),
                "review_queue": len(report.review_queue),
                "failed_matches": len(report.failed_matches),
                "execution_time": report.execution_time
            }
            
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _generate_summary(self):
        """Generate test run summary"""
        total_time = time.time() - self.results["start_time"]
        services = self.results["services"]
        
        passed = sum(1 for s in services.values() if s.get("passed", False))
        total = len(services)
        
        self.results["summary"] = {
            "total_time": total_time,
            "services_tested": total,
            "services_passed": passed, 
            "success_rate": passed / total if total > 0 else 0,
            "average_test_time": sum(
                s.get("execution_time", 0) for s in services.values()
            ) / max(total, 1)
        }
        
        print(f"\n📊 Summary:")
        print(f"   Total Time: {total_time:.1f}s")
        print(f"   Services: {passed}/{total} passed ({passed/total:.1%})")
        print(f"   Average: {self.results['summary']['average_test_time']:.1f}s per service")


def main():
    parser = argparse.ArgumentParser(description="Rapid development testing framework")
    parser.add_argument("--level", choices=["unit", "integration", "full"], 
                       default="unit", help="Test level")
    parser.add_argument("--service", help="Test specific service only")
    parser.add_argument("--parallel", action="store_true", help="Force parallel execution")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print(f"🚀 Rapid Development Testing - {args.level.upper()} level")
    print("=" * 50)
    
    tester = RapidTester(args.level)
    results = tester.run_tests(
        service_filter=args.service,
        parallel=args.parallel
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to {args.output}")
    
    # Exit with appropriate code
    success_rate = results["summary"]["success_rate"]
    exit_code = 0 if success_rate >= 0.8 else 1  # 80% pass rate required
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()