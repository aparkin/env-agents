#!/usr/bin/env python3
"""
Phase I Validation Suite Runner

Comprehensive test runner for validating the Phase I enhanced env-agents framework.
Provides detailed reporting and validation of all core components.
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import argparse

def run_test_suite(test_pattern="test_*.py", verbose=False, integration=False):
    """
    Run the test suite with comprehensive reporting.
    
    Args:
        test_pattern: Pattern for test files to run
        verbose: Enable verbose output
        integration: Include integration tests
        
    Returns:
        Dict with test results and metrics
    """
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Test selection
    if integration:
        cmd.extend(["-m", "not slow"])  # Run all but slow tests
    else:
        cmd.extend(["-m", "not (integration or slow)"])  # Unit tests only
    
    # Use unit tests for validation
    if test_pattern == "test_*.py":
        test_pattern = "tests/unit/"
    elif not test_pattern.startswith("tests/"):
        test_pattern = f"tests/{test_pattern}"
    
    cmd.extend([
        "--tb=short",
        test_pattern
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    start_time = datetime.now()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        end_time = datetime.now()
        
        # Parse results
        test_results = {
            'timestamp': start_time.isoformat(),
            'duration': (end_time - start_time).total_seconds(),
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
        # Parse test results from output
        if result.stdout:
            # Simple parsing of pytest output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'passed' in line or 'failed' in line or 'error' in line:
                    # Try to extract test counts from output
                    import re
                    matches = re.findall(r'(\d+)\s+(passed|failed|error|skipped)', line)
                    if matches:
                        test_results['summary'] = {}
                        for count, status in matches:
                            test_results['summary'][status] = int(count)
                        break
        
        return test_results
        
    except Exception as e:
        return {
            'timestamp': start_time.isoformat(),
            'duration': 0,
            'success': False,
            'error': str(e),
            'return_code': -1
        }


def validate_framework_components():
    """
    Validate that all Phase I framework components are properly integrated.
    
    Returns:
        Dict with validation results
    """
    
    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'components': {},
        'overall_status': 'unknown'
    }
    
    try:
        # Test core imports
        from env_agents import UnifiedEnvRouter, RequestSpec, Geometry
        validation_results['components']['core_imports'] = 'PASS'
        
        # Test router initialization
        router = UnifiedEnvRouter()
        validation_results['components']['router_init'] = 'PASS'
        
        # Test basic functionality
        services = router.list_services()
        validation_results['components']['service_listing'] = 'PASS'
        
        # Test metadata framework
        from env_agents.core.metadata_schema import ServiceMetadata
        validation_results['components']['metadata_framework'] = 'PASS'
        
        # Test discovery engine
        from env_agents.core.discovery_engine import SemanticDiscoveryEngine
        discovery = SemanticDiscoveryEngine(router.service_registry)
        validation_results['components']['discovery_engine'] = 'PASS'
        
        # Test resilient fetcher
        from env_agents.core.resilient_fetcher import ResilientDataFetcher
        validation_results['components']['resilient_fetcher'] = 'PASS'
        
        # Overall status
        all_passed = all(status == 'PASS' for status in validation_results['components'].values())
        validation_results['overall_status'] = 'PASS' if all_passed else 'FAIL'
        
    except ImportError as e:
        validation_results['components']['import_error'] = f'FAIL: {str(e)}'
        validation_results['overall_status'] = 'FAIL'
    except Exception as e:
        validation_results['components']['runtime_error'] = f'FAIL: {str(e)}'
        validation_results['overall_status'] = 'FAIL'
    
    return validation_results


def generate_validation_report(test_results, component_validation):
    """Generate comprehensive validation report"""
    
    report = []
    report.append("=" * 80)
    report.append("ENV-AGENTS PHASE I VALIDATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Component Validation
    report.append("FRAMEWORK COMPONENT VALIDATION")
    report.append("-" * 40)
    
    if component_validation['overall_status'] == 'PASS':
        report.append("✅ All core components loaded successfully")
    else:
        report.append("❌ Component validation failed")
    
    for component, status in component_validation['components'].items():
        symbol = "✅" if status == 'PASS' else "❌"
        report.append(f"{symbol} {component}: {status}")
    
    report.append("")
    
    # Test Results
    report.append("TEST EXECUTION RESULTS")
    report.append("-" * 40)
    
    if test_results['success']:
        report.append("✅ Test suite completed successfully")
    else:
        report.append("❌ Test suite failed")
    
    report.append(f"Duration: {test_results['duration']:.2f} seconds")
    report.append(f"Return code: {test_results['return_code']}")
    
    # Test Summary
    if 'summary' in test_results:
        summary = test_results['summary']
        total = sum(summary.values()) if summary else 0
        report.append("")
        report.append("Test Summary:")
        report.append(f"  Total tests: {total}")
        report.append(f"  Passed: {summary.get('passed', 0)}")
        report.append(f"  Failed: {summary.get('failed', 0)}")
        report.append(f"  Errors: {summary.get('error', 0)}")
        report.append(f"  Skipped: {summary.get('skipped', 0)}")
        
        if total > 0:
            passed = summary.get('passed', 0)
            pass_rate = (passed / total) * 100
            report.append(f"  Pass rate: {pass_rate:.1f}%")
    
    # Test Output
    if test_results.get('stdout'):
        report.append("")
        report.append("TEST OUTPUT:")
        report.append("-" * 20)
        report.append(test_results['stdout'])
    
    if test_results.get('stderr'):
        report.append("")
        report.append("TEST ERRORS:")
        report.append("-" * 20)
        report.append(test_results['stderr'])
    
    # Overall Assessment
    report.append("")
    report.append("OVERALL ASSESSMENT")
    report.append("-" * 40)
    
    overall_pass = (component_validation['overall_status'] == 'PASS' and 
                   test_results['success'])
    
    if overall_pass:
        report.append("✅ Phase I framework validation PASSED")
        report.append("   - All components loaded successfully")
        report.append("   - All tests passed")
        report.append("   - Framework is ready for production use")
    else:
        report.append("❌ Phase I framework validation FAILED")
        if component_validation['overall_status'] != 'PASS':
            report.append("   - Component integration issues detected")
        if not test_results['success']:
            report.append("   - Test failures detected")
        report.append("   - Review errors and fix issues before deployment")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main validation runner"""
    
    parser = argparse.ArgumentParser(description='Run Phase I validation suite')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--integration', '-i', action='store_true',
                       help='Include integration tests')
    parser.add_argument('--pattern', '-p', default='test_*.py',
                       help='Test file pattern (default: test_*.py)')
    parser.add_argument('--report-file', '-r', default='validation_report.txt',
                       help='Output report file (default: validation_report.txt)')
    
    args = parser.parse_args()
    
    print("Starting Phase I validation suite...")
    print()
    
    # Step 1: Component validation
    print("1. Validating framework components...")
    component_validation = validate_framework_components()
    
    if component_validation['overall_status'] == 'PASS':
        print("   ✅ All components validated successfully")
    else:
        print("   ❌ Component validation failed")
        for component, status in component_validation['components'].items():
            if status != 'PASS':
                print(f"      - {component}: {status}")
    
    print()
    
    # Step 2: Test execution
    print("2. Running test suite...")
    test_results = run_test_suite(
        test_pattern=args.pattern,
        verbose=args.verbose,
        integration=args.integration
    )
    
    if test_results['success']:
        print("   ✅ Test suite completed successfully")
    else:
        print("   ❌ Test suite failed")
    
    if 'summary' in test_results:
        summary = test_results['summary']
        total = sum(summary.values()) if summary else 0
        passed = summary.get('passed', 0) if summary else 0
        print(f"   Tests: {passed}/{total} passed")
    
    print()
    
    # Step 3: Generate report
    print("3. Generating validation report...")
    report = generate_validation_report(test_results, component_validation)
    
    # Write report to file
    with open(args.report_file, 'w') as f:
        f.write(report)
    
    print(f"   Report written to: {args.report_file}")
    
    # Display report
    print()
    print(report)
    
    # Exit with appropriate code
    overall_success = (component_validation['overall_status'] == 'PASS' and 
                      test_results['success'])
    
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()