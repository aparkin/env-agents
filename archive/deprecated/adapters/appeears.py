from __future__ import annotations
from typing import Any, Dict, List
from .base import BaseAdapter
from ..core.models import RequestSpec

class NasaAppeearsAdapter(BaseAdapter):
    DATASET = "NASA_AppEEARS"
    SOURCE_URL = "https://appeears.earthdatacloud.nasa.gov/api"
    SOURCE_VERSION = "v2"
    LICENSE = "https://earthdata.nasa.gov/earth-observation-data/standards-and-policies"
    REQUIRES_API_KEY = False
    def capabilities(self, extra=None) -> dict:
        return {
            "dataset": self.DATASET,
            "geometry": ["point","bbox","polygon"],
            "requires_time_range": True,
            "requires_api_key": self.REQUIRES_API_KEY,
            "variables": [],
            "attributes_schema": {},
            "rate_limits": {"notes": ""},
            "notes": "stub"
        }
    def _fetch_rows(self, spec: RequestSpec) -> List[Dict[str, Any]]:
        return []
