from __future__ import annotations
from typing import Any, Dict, List
from .base import BaseAdapter
from ..core.models import RequestSpec

class UsdaCropscapeAdapter(BaseAdapter):
    DATASET = "USDA_CropScape"
    SOURCE_URL = "https://nassgeodata.gmu.edu/axis2/services/CDLService"
    SOURCE_VERSION = "2024"
    LICENSE = "https://www.nass.usda.gov/About_NASS/Terms_of_Use/index.php"
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
