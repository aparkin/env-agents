from __future__ import annotations
from typing import Any, Dict, List
from .base import BaseAdapter
from ..core.models import RequestSpec

class UsgsWqpAdapter(BaseAdapter):
    DATASET = "USGS_WQP"
    SOURCE_URL = "https://www.waterqualitydata.us"
    SOURCE_VERSION = "v3"
    LICENSE = "https://www.waterqualitydata.us/portal_userguide/"
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
