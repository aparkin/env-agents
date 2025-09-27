# Extending env-agents with New Services

This guide shows how to add new environmental data services to env-agents using the unified adapter pattern.

## 🎯 Overview

Adding a new service involves:
1. **Creating the adapter class** that inherits from `BaseAdapter`
2. **Implementing required methods** (`capabilities`, `_fetch_rows`)
3. **Adding service to the registry** for automatic discovery
4. **Creating semantic mappings** for variable harmonization
5. **Writing tests** to validate integration

## 📋 Adapter Requirements

All adapters must implement this interface:

```python
from env_agents.adapters.base import BaseAdapter
from env_agents.core.models import RequestSpec
from typing import List, Dict, Any

class YourAdapter(BaseAdapter):
    # Required class constants
    DATASET = "YOUR_SERVICE"
    SOURCE_URL = "https://api.example.com"
    SOURCE_VERSION = "v1.0"
    LICENSE = "Public Domain"

    def capabilities(self) -> Dict[str, Any]:
        """Return service capabilities and available variables"""
        pass

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch data and return as list of standardized dictionaries"""
        pass
```

## 🌡️ Complete Example: NOAA Weather Adapter

Let's create a NOAA weather adapter based on your existing weather agent:

### Step 1: Create the Adapter Class

```python
# env_agents/adapters/noaa/adapter.py

import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

from env_agents.adapters.base import BaseAdapter
from env_agents.core.models import RequestSpec, Geometry

class NOAAAdapter(BaseAdapter):
    """NOAA Climate Data Online (CDO) adapter"""

    DATASET = "NOAA_CDO"
    SOURCE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    SOURCE_VERSION = "2.0"
    LICENSE = "Public Domain"

    def __init__(self, api_token: Optional[str] = None):
        super().__init__()
        self.api_token = api_token or self._get_api_token()
        self.headers = {"token": self.api_token} if self.api_token else {}
        self.base_url = "https://www.ncdc.noaa.gov/cdo-web/api/v2"

        # Rate limiting (NOAA: max 5 requests/second)
        self.last_request_time = 0
        self.min_request_interval = 0.2

    def _get_api_token(self) -> Optional[str]:
        """Get API token from environment or config"""
        import os
        return os.getenv('NOAA_API_TOKEN')

    def _rate_limit(self):
        """Implement NOAA-friendly rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def capabilities(self) -> Dict[str, Any]:
        """Return NOAA CDO capabilities"""
        return {
            "service_name": self.DATASET,
            "description": "NOAA Climate Data Online - weather station data",
            "variables": [
                {"id": "TMAX", "name": "Maximum Temperature", "unit": "celsius"},
                {"id": "TMIN", "name": "Minimum Temperature", "unit": "celsius"},
                {"id": "PRCP", "name": "Precipitation", "unit": "mm"},
                {"id": "SNOW", "name": "Snowfall", "unit": "mm"},
                {"id": "SNWD", "name": "Snow Depth", "unit": "mm"},
                {"id": "AWND", "name": "Average Wind Speed", "unit": "m/s"}
            ],
            "temporal_extent": {"start": "1763-01-01", "end": "present"},
            "spatial_extent": "Global (station-based)",
            "update_frequency": "Daily",
            "authentication_required": True,
            "rate_limits": {"requests_per_second": 5}
        }

    def _get_stations(self, geometry: Geometry, start_date: str, end_date: str,
                     limit: int = 1000) -> List[Dict]:
        """Get weather stations within geometry bounds"""
        self._rate_limit()

        # Convert geometry to NOAA extent format
        if geometry.type == 'bbox':
            extent = f"{geometry.coordinates[0]},{geometry.coordinates[1]},{geometry.coordinates[2]},{geometry.coordinates[3]}"
        else:
            # Convert point to small bounding box
            lon, lat = geometry.coordinates
            extent = f"{lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}"

        params = {
            'datasetid': 'GHCND',  # Global Historical Climate Network Daily
            'startdate': start_date,
            'enddate': end_date,
            'extent': extent,
            'limit': limit
        }

        response = requests.get(
            f"{self.base_url}/stations",
            headers=self.headers,
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            raise Exception(f"NOAA stations API error: {response.status_code}")

    def _fetch_station_data(self, station_id: str, start_date: str, end_date: str,
                           datatypes: List[str]) -> List[Dict]:
        """Fetch data for a specific station"""
        self._rate_limit()

        params = {
            'datasetid': 'GHCND',
            'stationid': station_id,
            'startdate': start_date,
            'enddate': end_date,
            'datatypeid': ','.join(datatypes),
            'limit': 1000,
            'units': 'metric'
        }

        response = requests.get(
            f"{self.base_url}/data",
            headers=self.headers,
            params=params,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return []  # Station might not have data for this period

    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        """Fetch NOAA weather data according to RequestSpec"""

        if not self.api_token:
            raise Exception("NOAA API token required. Set NOAA_API_TOKEN environment variable.")

        # Convert time range to NOAA format
        start_date = spec.time_range[0].split('T')[0]
        end_date = spec.time_range[1].split('T')[0]

        # Get relevant weather stations
        stations = self._get_stations(spec.geometry, start_date, end_date)

        if not stations:
            return []

        # Data types to fetch
        datatypes = ['TMAX', 'TMIN', 'PRCP', 'SNOW', 'SNWD', 'AWND']

        all_observations = []

        for station in stations[:10]:  # Limit stations for demo
            station_id = station.get('id')
            station_name = station.get('name', 'Unknown')
            lat = station.get('latitude')
            lon = station.get('longitude')
            elevation = station.get('elevation')

            # Fetch data for this station
            station_data = self._fetch_station_data(
                station_id, start_date, end_date, datatypes
            )

            # Convert to standardized format
            for record in station_data:
                observation = {
                    # Core schema fields
                    'observation_id': f"NOAA_{station_id}_{record.get('date', '')}_{record.get('datatype', '')}",
                    'dataset': self.DATASET,
                    'source_url': f"{self.SOURCE_URL}/data",
                    'source_version': self.SOURCE_VERSION,
                    'license': self.LICENSE,
                    'retrieval_timestamp': datetime.now().isoformat(),

                    # Spatial fields
                    'geometry_type': 'Point',
                    'latitude': lat,
                    'longitude': lon,
                    'elevation_m': elevation,
                    'site_name': station_name,
                    'spatial_id': station_id,

                    # Temporal fields
                    'time': record.get('date'),
                    'temporal_coverage': 'daily',

                    # Value fields
                    'variable': record.get('datatype'),
                    'value': record.get('value'),
                    'unit': self._get_unit_for_variable(record.get('datatype')),
                    'qc_flag': record.get('qflag'),

                    # Metadata
                    'attributes': {
                        'station_id': station_id,
                        'station_name': station_name,
                        'measurement_flag': record.get('mflag'),
                        'quality_flag': record.get('qflag'),
                        'source_flag': record.get('sflag')
                    },
                    'provenance': {
                        'data_source': 'NOAA Climate Data Online',
                        'station_type': 'weather_station',
                        'collection_method': 'in_situ_measurement'
                    }
                }

                all_observations.append(observation)

        return all_observations

    def _get_unit_for_variable(self, variable: str) -> str:
        """Map NOAA variable codes to standard units"""
        unit_map = {
            'TMAX': 'celsius',
            'TMIN': 'celsius',
            'PRCP': 'mm',
            'SNOW': 'mm',
            'SNWD': 'mm',
            'AWND': 'm/s'
        }
        return unit_map.get(variable, 'unknown')
```

### Step 2: Create Package Structure

```bash
mkdir -p env_agents/adapters/noaa
touch env_agents/adapters/noaa/__init__.py
```

```python
# env_agents/adapters/noaa/__init__.py
from .adapter import NOAAAdapter

__all__ = ['NOAAAdapter']
```

### Step 3: Add to Registry

```python
# env_agents/adapters/__init__.py

# Add to existing imports
from .noaa.adapter import NOAAAdapter as NOAA

# Add to CANONICAL_SERVICES
CANONICAL_SERVICES = {
    # ... existing services ...
    'NOAA': NOAA,
}

# Add to __all__
__all__ = [
    # ... existing exports ...
    'NOAA',
]
```

### Step 4: Create Semantic Mappings

```python
# env_agents/adapters/noaa/rules.py

# Map NOAA variables to canonical environmental terms
CANONICAL_MAP = {
    "TMAX": "air:temperature:maximum_daily",
    "TMIN": "air:temperature:minimum_daily",
    "PRCP": "precipitation:liquid_equivalent",
    "SNOW": "precipitation:snow_depth",
    "SNWD": "snow:depth",
    "AWND": "wind:speed:average"
}

# Unit standardization
UNIT_ALIASES = {
    "degrees C": "celsius",
    "mm": "millimeter",
    "m/s": "meter_per_second"
}

# Label matching hints for semantic discovery
LABEL_HINTS = {
    "temperature": ["temp", "temperature", "air_temperature"],
    "precipitation": ["precip", "rainfall", "precipitation"],
    "wind": ["wind", "wind_speed", "air_movement"]
}
```

### Step 5: Write Tests

```python
# tests/test_noaa_adapter.py

import pytest
from env_agents.adapters.noaa import NOAAAdapter
from env_agents.core.models import RequestSpec, Geometry

@pytest.fixture
def noaa_adapter():
    return NOAAAdapter()

def test_noaa_capabilities(noaa_adapter):
    """Test NOAA capabilities discovery"""
    caps = noaa_adapter.capabilities()

    assert caps['service_name'] == 'NOAA_CDO'
    assert len(caps['variables']) >= 6
    assert 'TMAX' in [v['id'] for v in caps['variables']]

def test_noaa_data_fetch(noaa_adapter):
    """Test NOAA data fetching"""
    # Skip if no API token
    if not noaa_adapter.api_token:
        pytest.skip("NOAA_API_TOKEN not available")

    geometry = Geometry(type='bbox', coordinates=[-74, 40, -73, 41])  # NYC area
    spec = RequestSpec(
        geometry=geometry,
        time_range=("2021-01-01T00:00:00Z", "2021-01-07T23:59:59Z")
    )

    result = noaa_adapter._fetch_rows(spec)

    if result:  # Data availability varies
        assert len(result) > 0

        # Check data structure
        first_obs = result[0]
        required_fields = ['observation_id', 'latitude', 'longitude', 'time', 'variable', 'value']
        for field in required_fields:
            assert field in first_obs
```

## 🔧 Integration Checklist

- [ ] **Adapter Class**: Inherits from `BaseAdapter`, implements required methods
- [ ] **Constants**: Set `DATASET`, `SOURCE_URL`, `SOURCE_VERSION`, `LICENSE`
- [ ] **Capabilities**: Returns comprehensive service metadata
- [ ] **Data Fetching**: `_fetch_rows()` returns standardized dictionaries
- [ ] **Error Handling**: Graceful failure with informative messages
- [ ] **Rate Limiting**: Respects service API limits
- [ ] **Authentication**: Handles API keys/tokens appropriately
- [ ] **Registry**: Added to `CANONICAL_SERVICES` dictionary
- [ ] **Semantic Mapping**: Created rule pack for variable harmonization
- [ ] **Tests**: Integration tests for capabilities and data fetching
- [ ] **Documentation**: Added service to documentation tables

## 📚 Advanced Patterns

### Meta-Service Pattern (Multiple Assets)

For services with multiple datasets/assets (like Earth Engine):

```python
class YourMetaAdapter(BaseAdapter):
    def __init__(self, asset_id: str = None):
        super().__init__()
        self.asset_id = asset_id
        self.available_assets = self._discover_assets()

    def capabilities(self):
        if self.asset_id:
            return self._asset_capabilities(self.asset_id)
        else:
            return self._meta_capabilities()
```

### Caching and Performance

```python
from functools import lru_cache
import pickle
from pathlib import Path

class CachedAdapter(BaseAdapter):
    @lru_cache(maxsize=100)
    def _get_cached_metadata(self, cache_key: str):
        """Cache expensive metadata operations"""
        pass

    def _cache_stations(self, geometry_key: str, stations: List):
        """Cache station lists for repeated queries"""
        cache_file = Path(f"cache/stations_{geometry_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(stations, f)
```

## 🚀 Next Steps

1. **Test Your Adapter**: Use `run_tests.py` to validate integration
2. **Add to Notebooks**: Include in demonstration notebooks
3. **Update Documentation**: Add service to README and docs
4. **Semantic Integration**: Refine variable mappings based on usage
5. **Performance Optimization**: Add caching and batch operations as needed

## 🤝 Contributing Your Adapter

Once your adapter is working:

1. Fork the env-agents repository
2. Create a feature branch: `git checkout -b add-noaa-adapter`
3. Add your adapter following this guide
4. Write comprehensive tests
5. Update documentation
6. Submit a pull request

Your contribution helps make environmental data more accessible to everyone!

---

**Questions?** Check the [Development Guide](DEVELOPMENT.md) or open an issue on GitHub.