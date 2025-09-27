#!/usr/bin/env python3
"""
Discover SURGO API actual limits and available parameters
Test what the API can actually handle, rather than guessing
"""

import requests
import json
from itertools import combinations

def discover_surgo_capabilities():
    print("🔍 Discovering SURGO API Capabilities & Limits")
    print("=" * 50)
    
    sda_url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
    
    # Test location (Davis, CA)
    lon, lat = -121.74, 38.54
    aoi_wkt = f"POINT ({lon} {lat})"
    aoi_wkt_safe = aoi_wkt.replace("'", "''")
    
    # All available SURGO properties
    all_properties = [
        "claytotal_r", "silttotal_r", "sandtotal_r", "om_r", "dbthirdbar_r", 
        "wthirdbar_r", "wfifteenbar_r", "awc_r", "ph1to1h2o_r", "ph01mcacl2_r", 
        "cec7_r", "ecec_r", "sumbases_r", "p_r", "k_r"
    ]
    
    print(f"📊 Testing with {len(all_properties)} known properties")
    
    # Test 1: Discover what properties actually exist in the database
    print(f"\n🔍 Step 1: Parameter Discovery")
    print("-" * 30)
    
    # Query to get available columns from chorizon table
    discovery_query = f"""
    SELECT TOP 1 *
    FROM chorizon 
    WHERE chkey IN (
        SELECT TOP 1 ch.chkey
        FROM mapunit mu
        JOIN component c ON mu.mukey = c.mukey
        JOIN chorizon ch ON c.cokey = ch.cokey
        WHERE mu.mukey IN (
            SELECT DISTINCT mukey 
            FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
        )
    )
    """
    
    try:
        response = requests.post(
            sda_url,
            json={"query": discovery_query, "format": "JSON+COLUMNNAME"},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "Table" in data and len(data["Table"]) > 1:
                available_columns = data["Table"][0]  # First row is headers
                print(f"✅ Found {len(available_columns)} columns in chorizon table")
                
                # Check which of our properties are actually available
                available_properties = [prop for prop in all_properties if prop in available_columns]
                missing_properties = [prop for prop in all_properties if prop not in available_columns]
                
                print(f"   Available from our list: {len(available_properties)}")
                print(f"   Missing from our list: {len(missing_properties)}")
                if missing_properties:
                    print(f"   Missing: {missing_properties}")
                
                # Show some unexpected columns that might be useful
                unexpected = [col for col in available_columns if col not in all_properties + 
                             ["cokey", "chkey", "hzdept_r", "hzdepb_r"]][:10]
                if unexpected:
                    print(f"   Other interesting columns: {unexpected}")
            else:
                print("❌ Failed to parse discovery response")
                available_properties = all_properties
        else:
            print(f"❌ Discovery query failed: {response.status_code}")
            available_properties = all_properties
            
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        available_properties = all_properties
    
    # Test 2: Find actual API limits by testing different property counts
    print(f"\n🔍 Step 2: API Limit Testing")
    print("-" * 30)
    
    test_counts = [1, 3, 5, 8, 10, 12, 15, len(available_properties)]
    successful_counts = []
    
    for count in test_counts:
        if count > len(available_properties):
            continue
            
        properties_subset = available_properties[:count]
        property_columns = ",".join([f"ch.{prop}" for prop in properties_subset])
        
        test_query = f"""
        ;WITH aoi AS (
          SELECT DISTINCT mukey
          FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
        )
        SELECT TOP 5 mu.mukey,c.cokey,c.comppct_r,ch.chkey,ch.hzdept_r,ch.hzdepb_r,
               {property_columns}
        FROM aoi
        JOIN mapunit AS mu ON mu.mukey = aoi.mukey
        JOIN component AS c ON c.mukey = mu.mukey AND c.comppct_r IS NOT NULL
        JOIN chorizon AS ch ON ch.cokey = c.cokey
        WHERE ch.hzdept_r < 30 AND ch.hzdepb_r > 0
        """
        
        try:
            response = requests.post(
                sda_url,
                json={"query": test_query, "format": "JSON+COLUMNNAME"},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "Table" in data and len(data["Table"]) > 1:
                    rows_returned = len(data["Table"]) - 1  # Subtract header row
                    print(f"✅ {count} properties: SUCCESS ({rows_returned} rows)")
                    successful_counts.append(count)
                else:
                    print(f"❌ {count} properties: No data returned")
            else:
                print(f"❌ {count} properties: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {count} properties: {str(e)[:50]}...")
    
    # Determine practical limit
    if successful_counts:
        max_successful = max(successful_counts)
        print(f"\n📊 API can handle up to {max_successful} properties in a single query")
    else:
        max_successful = 3  # Conservative fallback
        print(f"\n❌ Could not determine limits, using conservative fallback: {max_successful}")
    
    # Test 3: Test METADATA format more carefully
    print(f"\n🔍 Step 3: METADATA Format Analysis")
    print("-" * 30)
    
    simple_query = f"""
    SELECT TOP 3 mu.mukey, ch.claytotal_r, ch.ph1to1h2o_r
    FROM mapunit mu
    JOIN component c ON mu.mukey = c.mukey
    JOIN chorizon ch ON c.cokey = ch.cokey
    WHERE mu.mukey IN (
        SELECT DISTINCT mukey 
        FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{aoi_wkt_safe}')
    )
    """
    
    formats_to_test = [
        "JSON+COLUMNNAME",
        "JSON+COLUMNNAME+METADATA"
    ]
    
    for fmt in formats_to_test:
        try:
            response = requests.post(
                sda_url,
                json={"query": simple_query, "format": fmt},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "Table" in data:
                    table = data["Table"]
                    print(f"✅ {fmt}: {len(table)} table rows")
                    
                    # Analyze structure
                    if len(table) > 0:
                        print(f"   Row 0 (headers): {table[0]}")
                        if len(table) > 1:
                            print(f"   Row 1: {str(table[1])[:100]}...")
                        if len(table) > 2:
                            print(f"   Row 2: {str(table[2])[:100]}...")
                            
                    # Check if we can identify metadata rows
                    metadata_rows = []
                    data_rows = []
                    for i, row in enumerate(table[1:], 1):  # Skip header
                        if isinstance(row, list) and len(row) > 0:
                            first_cell = str(row[0])
                            if "ColumnOrdinal=" in first_cell or "ProviderType=" in first_cell:
                                metadata_rows.append(i)
                            else:
                                data_rows.append(i)
                    
                    print(f"   Metadata rows: {metadata_rows}")
                    print(f"   Data rows: {data_rows}")
                    
        except Exception as e:
            print(f"❌ {fmt}: {e}")
    
    return {
        "available_properties": available_properties,
        "max_properties_per_query": max_successful,
        "total_properties_available": len(available_properties)
    }

if __name__ == "__main__":
    results = discover_surgo_capabilities()
    
    print(f"\n🎯 DISCOVERY RESULTS:")
    print(f"• Available properties: {results['total_properties_available']}")
    print(f"• Max per query: {results['max_properties_per_query']}")
    print(f"• Chunking needed: {'Yes' if results['total_properties_available'] > results['max_properties_per_query'] else 'No'}")