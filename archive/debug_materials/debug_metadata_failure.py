#!/usr/bin/env python3
"""
Debug why METADATA format fails in SURGO API
Compare JSON+COLUMNNAME vs JSON+COLUMNNAME+METADATA
"""

import requests
import json

def debug_metadata_failure():
    print("🔍 Debugging METADATA Format Failure")
    print("=" * 40)
    
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
    SELECT TOP 3 mu.mukey, c.cokey, c.comppct_r, ch.chkey, ch.hzdept_r, ch.hzdepb_r,
           ch.claytotal_r
    FROM aoi
    JOIN mapunit AS mu ON mu.mukey = aoi.mukey
    JOIN component AS c ON c.mukey = mu.mukey AND c.comppct_r IS NOT NULL
    JOIN chorizon AS ch ON ch.cokey = c.cokey
    WHERE ch.hzdept_r < 30 AND ch.hzdepb_r > 0
    """
    
    # Test both formats side by side
    formats = {
        "Working (legacy)": "JSON+COLUMNNAME",
        "Failing (with metadata)": "JSON+COLUMNNAME+METADATA"
    }
    
    for name, fmt in formats.items():
        print(f"\n🧪 Testing {name}: {fmt}")
        print("-" * 50)
        
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
            print(f"Response size: {len(response.text)} chars")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ SUCCESS - Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())}")
                        
                        # Look for Table key (legacy format)
                        if 'Table' in data:
                            table_data = data['Table']
                            print(f"   Table data: {type(table_data)} with {len(table_data) if hasattr(table_data, '__len__') else 'N/A'} items")
                            if isinstance(table_data, list) and table_data:
                                print(f"   Sample row: {table_data[0]}")
                        
                        # Look for metadata info
                        if 'Metadata' in data or 'metadata' in data:
                            metadata = data.get('Metadata') or data.get('metadata')
                            print(f"   Metadata present: {type(metadata)}")
                        
                        # Show all keys and their content types
                        for key, value in data.items():
                            if hasattr(value, '__len__') and not isinstance(value, str):
                                print(f"   {key}: {type(value)} with {len(value)} items")
                                if isinstance(value, list) and value:
                                    print(f"     First item type: {type(value[0])}")
                            else:
                                print(f"   {key}: {type(value)} = {str(value)[:100]}")
                    
                    elif isinstance(data, list):
                        print(f"   List with {len(data)} items")
                        if data:
                            print(f"   First item: {data[0]}")
                    
                    # Show structure differences
                    print(f"   Raw preview: {response.text[:300]}...")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON DECODE ERROR: {e}")
                    print(f"   Raw response: {response.text[:500]}...")
            else:
                print(f"❌ HTTP ERROR: {response.status_code}")
                print(f"   Error response: {response.text[:500]}...")
                
                # Common error analysis
                if response.status_code == 400:
                    print("   → 400 Bad Request - likely query format issue")
                elif response.status_code == 500:
                    print("   → 500 Server Error - likely SQL or internal issue")
                elif response.status_code == 422:
                    print("   → 422 Unprocessable - likely format parameter issue")
                
        except requests.exceptions.Timeout:
            print("❌ REQUEST TIMEOUT")
        except requests.exceptions.RequestException as e:
            print(f"❌ REQUEST ERROR: {e}")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")

    print(f"\n💡 ANALYSIS:")
    print(f"If METADATA format fails with 400/422 errors, it suggests:")
    print(f"  • The USDA SDA API may not support METADATA format for this endpoint")
    print(f"  • The format parameter may have limited valid options")
    print(f"  • Legacy code worked because it used simpler format")
    print(f"  • Adding METADATA might change expected response structure")

if __name__ == "__main__":
    debug_metadata_failure()