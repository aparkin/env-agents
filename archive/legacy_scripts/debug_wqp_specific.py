#!/usr/bin/env python3
"""
Debug WQP Specific Issues
"""
import requests
import pandas as pd
from io import StringIO
from datetime import datetime

print('🔬 WQP STEP-BY-STEP DEBUG')
print('=' * 30)

# Test ECOGNITA proven coordinates that work externally
test_coords = [-77.0369, 38.9072]  # Washington DC
base_url = "https://www.waterqualitydata.us"

# Step 1: Test station query directly
print('\n🧪 STEP 1: Station Query')
radius_deg = 2000 / 111000  # 2km radius
west, south, east, north = (
    test_coords[0] - radius_deg, 
    test_coords[1] - radius_deg,
    test_coords[0] + radius_deg, 
    test_coords[1] + radius_deg
)

station_params = {
    'bBox': f"{west},{south},{east},{north}",
    'mimeType': 'csv',
    'zip': 'no',
    'startDateLo': '01-01-2023',  # MM-DD-YYYY format
    'startDateHi': '08-31-2024'
}

print(f'  Bbox: {west:.6f},{south:.6f},{east:.6f},{north:.6f}')
print(f'  Date range: {station_params["startDateLo"]} to {station_params["startDateHi"]}')

stations_url = f"{base_url}/data/Station/search"
print(f'  URL: {stations_url}')

try:
    station_response = requests.get(stations_url, params=station_params, timeout=60)
    print(f'  Status: {station_response.status_code}')
    
    if station_response.status_code == 200:
        stations_df = pd.read_csv(StringIO(station_response.text), low_memory=False)
        print(f'  ✅ Stations found: {len(stations_df)}')
        
        if len(stations_df) > 0:
            # Show first few station IDs
            station_ids = stations_df['MonitoringLocationIdentifier'].unique()[:3]
            print(f'  Sample station IDs: {list(station_ids)}')
            
            # Step 2: Test results query for first station
            print(f'\n🧪 STEP 2: Results Query (first station)')
            
            result_params = {
                'mimeType': 'csv',
                'zip': 'no', 
                'sorted': 'yes',
                'startDateLo': '01-01-2023',
                'startDateHi': '08-31-2024',
                'siteid': station_ids[0],  # Use first station
                'characteristicName': 'Temperature, water'
            }
            
            results_url = f"{base_url}/data/Result/search" 
            print(f'  Station ID: {station_ids[0]}')
            print(f'  Parameter: Temperature, water')
            
            result_response = requests.get(results_url, params=result_params, timeout=60)
            print(f'  Status: {result_response.status_code}')
            
            if result_response.status_code == 200:
                results_df = pd.read_csv(StringIO(result_response.text), low_memory=False)
                print(f'  ✅ Results found: {len(results_df)}')
                
                if len(results_df) > 0:
                    print(f'  Sample columns: {list(results_df.columns)[:5]}...')
                    if 'ResultMeasureValue' in results_df.columns:
                        values = results_df['ResultMeasureValue'].dropna()
                        print(f'  Temperature values: {len(values)} measurements')
                        if len(values) > 0:
                            print(f'  Range: {values.min():.2f} to {values.max():.2f}')
                else:
                    print(f'  ⚠️ Results query returned empty DataFrame')
            else:
                print(f'  ❌ Results query failed: {result_response.status_code}')
                print(f'  Response: {result_response.text[:200]}...')
        else:
            print(f'  ⚠️ Station query returned empty DataFrame')
    else:
        print(f'  ❌ Station query failed: {station_response.status_code}')
        print(f'  Response: {station_response.text[:200]}...')
        
except Exception as e:
    print(f'  ❌ Error: {e}')

print('\n🎯 CONCLUSION:')
print('If this works but notebook fails, the issue is in adapter implementation details')