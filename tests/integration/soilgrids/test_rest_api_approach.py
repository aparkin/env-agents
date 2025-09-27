#!/usr/bin/env python3
"""
Test SoilGrids using your proven REST API approach
This tests the approach from your working legacy code that doesn't time out
"""

import sys
import requests
import time
import random
from pathlib import Path

def test_soilgrids_rest_api():
    """Test SoilGrids using the REST API approach from user's working code"""
    print("🧪 SoilGrids REST API Test (User's Proven Approach)")
    print("=" * 50)

    # Use your proven REST API endpoint
    base_url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    # Test cases with known soil locations (terrestrial, not water)
    test_cases = [
        {
            "name": "Netherlands Farmland",
            "params": {
                "lon": 5.79,
                "lat": 51.99,
                "property": "clay,soc,phh2o",
                "depth": "0-5cm",
                "value": "Q0.5"
            }
        },
        {
            "name": "Iowa Corn Belt",
            "params": {
                "lon": -93.65,
                "lat": 42.03,
                "property": "clay,soc,bdod",
                "depth": "0-5cm",
                "value": "Q0.5"
            }
        },
        {
            "name": "Brazilian Cerrado",
            "params": {
                "lon": -47.92,
                "lat": -15.77,
                "property": "clay,soc,phh2o",
                "depth": "0-5cm",
                "value": "Q0.5"
            }
        }
    ]

    successful_tests = 0
    total_tests = len(test_cases)

    session = requests.Session()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing {test_case['name']}...")

        try:
            # Use your retry logic with exponential backoff
            last_exc = None
            for attempt in range(5):
                try:
                    resp = session.get(base_url, params=test_case['params'], timeout=60)

                    # Handle 5xx as retryable (from your code)
                    if resp.status_code >= 500:
                        raise requests.HTTPError(f"{resp.status_code} {resp.reason}", response=resp)

                    resp.raise_for_status()
                    data = resp.json()
                    break

                except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                    last_exc = e
                    # Only retry on 5xx/connection/timeouts; break on 4xx
                    status = getattr(getattr(e, "response", None), "status_code", None)
                    if isinstance(e, requests.HTTPError) and status and 400 <= status < 500 and status != 429:
                        break
                    sleep = 1.0 + attempt * 0.75 + random.uniform(0, 0.4)
                    time.sleep(min(sleep, 6.0))
            else:
                if last_exc:
                    raise last_exc
                raise RuntimeError("Unknown SoilGrids error")

            print(f"   ✅ API Response: {resp.status_code}")

            # Extract data using your proven approach
            properties = data.get("properties", {})

            real_values_found = False
            for prop_name, prop_data in properties.items():
                if isinstance(prop_data, dict) and "values" in prop_data:
                    depth_data = prop_data["values"].get("0-5cm", {})
                    if isinstance(depth_data, dict):
                        value = depth_data.get("Q0.5")
                        if value is not None and value != 0:
                            print(f"   {prop_name}: {value}")
                            real_values_found = True
                        elif value == 0:
                            print(f"   {prop_name}: 0 (may be valid or no-data)")
                        else:
                            print(f"   {prop_name}: None")

            if real_values_found:
                successful_tests += 1
                print(f"   ✅ SUCCESS: Real soil data retrieved")
            else:
                print(f"   ⚠️  WARNING: Only zeros or nulls returned")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:100]}")

    # Results
    success_rate = successful_tests / total_tests
    print(f"\n{'='*50}")
    print(f"📊 REST API SUCCESS RATE")
    print(f"{'='*50}")
    print(f"Successful requests: {successful_tests}/{total_tests}")
    print(f"Success rate: {success_rate:.1%}")

    if success_rate >= 0.75:
        status = "🎉 EXCELLENT"
    elif success_rate >= 0.50:
        status = "👍 GOOD"
    elif success_rate >= 0.25:
        status = "⚠️ POOR"
    else:
        status = "💥 CRITICAL"

    print(f"Assessment: {status}")

    # Key insight
    if success_rate > 0:
        print(f"\n✅ KEY FINDING: REST API approach works - this is your proven method")
        print(f"   • No catalog discovery needed")
        print(f"   • Direct property queries")
        print(f"   • Point-by-point sampling with rate limiting")
    else:
        print(f"\n❌ UNEXPECTED: REST API approach failed")

    return success_rate > 0

if __name__ == "__main__":
    success = test_soilgrids_rest_api()
    print(f"\n{'🎉 PASS' if success else '💥 FAIL'}: REST API approach test")
    sys.exit(0 if success else 1)