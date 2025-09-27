from __future__ import annotations
from typing import Any, Dict, List
from .base import BaseAdapter
from ..core.models import RequestSpec

class NasaFirmsAdapter(BaseAdapter):
    DATASET = "NASA_FIRMS"
    SOURCE_URL = "https://firms.modaps.eosdis.nasa.gov"
    SOURCE_VERSION = "v1"
    LICENSE = "https://earthdata.nasa.gov/earth-observation-data/near-real-time"
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
