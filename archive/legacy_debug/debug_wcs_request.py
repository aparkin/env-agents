#!/usr/bin/env python3
"""
Debug WCS request to match working code exactly
"""

import requests
import urllib.parse

def test_wcs_request():
    """Test WCS request using the exact pattern from working code"""

    # Exact parameters from working code
    prop = "clay"
    coverage_id = "clay_0-5cm_Q0.5"  # From discovered IDs

    # Better bbox size (Netherlands) - use same as working code
    minx, miny, maxx, maxy = 5.78, 51.98, 5.8, 52.0

    # Method 1: Exactly match working code approach
    print("=== Method 1: Exact working code pattern ===")
    base_url = f"https://maps.isric.org/mapserv"
    params = {
        "map": f"/map/{prop}.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "coverageid": coverage_id,
        "format": "image/tiff",
        "subset": [f"Long({minx},{maxx})", f"Lat({miny},{maxy})"],
        "scaleSize": "Long(100),Lat(100)"  # Limit to 100x100 pixels
    }

    try:
        print(f"URL: {base_url}")
        print(f"Params: {params}")
        response = requests.get(base_url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Final URL: {response.url}")
        if response.status_code != 200:
            print(f"Error response: {response.text[:500]}")
        else:
            print(f"Success! Response size: {len(response.content)} bytes")
    except Exception as e:
        print(f"Request failed: {e}")

    # Method 2: Manual URL construction (what I was trying)
    print("\n=== Method 2: Manual URL construction ===")
    url_parts = [base_url]
    url_parts.append(f"map=/map/{prop}.map")
    url_parts.append("SERVICE=WCS")
    url_parts.append("VERSION=2.0.1")
    url_parts.append("REQUEST=GetCoverage")
    url_parts.append(f"coverageid={coverage_id}")
    url_parts.append("format=image/tiff")
    url_parts.append(f"subset=Long({minx},{maxx})")
    url_parts.append(f"subset=Lat({miny},{maxy})")

    manual_url = "&".join(url_parts)
    print(f"Manual URL: {manual_url}")

    try:
        response = requests.get(manual_url, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        if response.status_code != 200:
            print(f"Error response: {response.text[:200]}")
        else:
            print(f"Success! Response size: {len(response.content)} bytes")
    except Exception as e:
        print(f"Request failed: {e}")

    # Method 3: Test GetCapabilities first
    print("\n=== Method 3: GetCapabilities test ===")
    caps_params = {
        "map": f"/map/{prop}.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCapabilities"
    }

    try:
        response = requests.get(base_url, params=caps_params, timeout=30)
        print(f"GetCapabilities status: {response.status_code}")
        if response.status_code == 200:
            # Look for our coverage ID in the response
            if coverage_id in response.text:
                print(f"✅ Coverage {coverage_id} found in capabilities")
            else:
                print(f"❌ Coverage {coverage_id} NOT found in capabilities")
                # Show available coverages
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response.text)
                    ns = {"wcs": "http://www.opengis.net/wcs/2.0"}
                    coverage_ids = [el.text for el in root.findall(".//wcs:CoverageId", ns)]
                    print(f"Available coverages: {coverage_ids[:5]}...")
                except:
                    print("Could not parse capabilities XML")
        else:
            print(f"GetCapabilities failed: {response.text[:200]}")
    except Exception as e:
        print(f"GetCapabilities failed: {e}")

if __name__ == "__main__":
    test_wcs_request()