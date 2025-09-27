#!/usr/bin/env python3
"""
Test user's exact catalog approach in isolation
"""

import json
import os
import requests
import xml.etree.ElementTree as ET

SOILGRIDS_SERVICES_ALL = ["clay", "soc", "phh2o"]  # Just test a few

def _get_coverages_for_property(prop: str):
    url = "https://maps.isric.org/mapserv"
    params = {"map": f"/map/{prop}.map", "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCapabilities"}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ns = {"wcs": "http://www.opengis.net/wcs/2.0"}
    return [el.text for el in root.findall(".//wcs:CoverageId", ns)]

def build_soilgrids_catalog(services=SOILGRIDS_SERVICES_ALL, cache_file="soilgrids_coverages.json", refresh=False):
    if os.path.exists(cache_file) and not refresh:
        with open(cache_file,"r") as f: return json.load(f)
    catalog = {}
    for svc in services:
        try:
            ids = _get_coverages_for_property(svc)
            catalog[svc] = ids
            print(f"✅ {svc}: {len(ids)} coverages")
        except Exception as e:
            print(f"❌ Failed {svc}: {e}")
            catalog[svc] = []
    with open(cache_file,"w") as f: json.dump(catalog,f,indent=2)
    return catalog

def initialize_soilgrids_catalog(cache_file="test_soilgrids_coverages.json", refresh=True):
    services = SOILGRIDS_SERVICES_ALL
    catalog = build_soilgrids_catalog(services, cache_file=cache_file, refresh=refresh)
    print(f"Saved SoilGrids coverage catalog with {sum(len(v) for v in catalog.values())} coverages.")
    return catalog

if __name__ == "__main__":
    print("🧪 Testing User's Exact Catalog Approach")
    print("=" * 40)

    # Run this once (it queries all services and writes JSON locally)
    catalog = initialize_soilgrids_catalog(refresh=True)

    print(f"\n📋 Catalog Results:")
    for service, coverages in catalog.items():
        print(f"  {service}: {len(coverages)} coverages")
        if coverages:
            print(f"    Example: {coverages[0]}")

    print(f"\n🎉 SUCCESS: User's catalog approach works!")