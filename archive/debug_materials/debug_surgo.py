#!/usr/bin/env python3
"""
Debug SURGO API responses to understand exact format
"""

import requests
import json

def debug_surgo_api():
    print("🔍 Debugging SURGO API Response Format")
    print("=" * 45)
    
    # Use exact working legacy parameters
    sda_url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
    
    # Davis, CA location  
    lon, lat = -121.74, 38.54
    aoi_wkt = f"POINT ({lon} {lat})"
    aoi_wkt_safe = aoi_wkt.replace("'", "''")
    
    # Simple test query - just get basic info
    sql_query = f"""
    ;WITH aoi AS (
      SELECT DISTINCT mukey
      FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
    )
    SELECT mu.mukey, c.cokey, c.comppct_r, ch.chkey, ch.hzdept_r, ch.hzdepb_r,
           ch.claytotal_r
    FROM aoi
    JOIN mapunit AS mu ON mu.mukey = aoi.mukey
    JOIN component AS c ON c.mukey = mu.mukey AND c.comppct_r IS NOT NULL
    JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE ch.hzdept_r < 30 AND ch.hzdepb_r > 0
    LIMIT 5
    """
    
    # Test different formats
    formats_to_try = [
        "JSON+COLUMNNAME+METADATA",
        "JSON",
        "JSON+COLUMNNAME"
    ]
    
    for fmt in formats_to_try:
        print(f"\n🧪 Testing format: {fmt}")
        print("-" * 30)
        
        payload = {
            "query": sql_query,
            "format": fmt
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                sda_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                        for key, value in data.items():
                            print(f"  {key}: {type(value)} - {len(value) if hasattr(value, '__len__') else str(value)[:50]}")
                    
                    elif isinstance(data, list):
                        print(f"List length: {len(data)}")
                        if data:
                            print(f"First item type: {type(data[0])}")
                            if isinstance(data[0], dict):
                                print(f"First item keys: {list(data[0].keys())}")
                    
                    # Show first few characters of raw response
                    print(f"Raw response preview: {response.text[:200]}...")
                    
                except json.JSONDecodeError:
                    print(f"Invalid JSON. Response: {response.text[:200]}...")
            else:
                print(f"Error response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Request failed: {e}")
    
    print(f"\n✅ SURGO API debug complete!")

if __name__ == "__main__":
    debug_surgo_api()