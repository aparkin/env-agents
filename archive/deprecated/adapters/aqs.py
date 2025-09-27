from __future__ import annotations
from typing import Any, Dict, List
from .base import BaseAdapter
from ..core.models import RequestSpec

class EpaAqsV3Adapter(BaseAdapter):
    DATASET = "EPA_AQS_v3"
    SOURCE_URL = "https://aqs.epa.gov/data/api"
    SOURCE_VERSION = "v3"
    LICENSE = "https://www.epa.gov/airdata"
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
