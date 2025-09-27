from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Literal, FrozenSet
# --- add imports once in the module ---
import hashlib, pandas as pd, numpy as np
from .ids import compute_observation_id

GeometryType = Literal["point","bbox","polygon"]

@dataclass
class Geometry:
    type: GeometryType
    coordinates: Any  # [lon,lat] | [minx,miny,maxx,maxy] | WKT/GeoJSON
    
    def __hash__(self):
        # Convert coordinates to tuple for hashing
        coords_tuple = tuple(self.coordinates) if hasattr(self.coordinates, '__iter__') and not isinstance(self.coordinates, str) else self.coordinates
        return hash((self.type, coords_tuple))

@dataclass
class RequestSpec:
    geometry: Geometry
    time_range: Optional[Tuple[str,str]] = None
    variables: Optional[List[str]] = None
    depth_cm: Optional[Dict[str,int]] = None
    resolution: Optional[str] = None
    filters: Optional[Dict[str,Any]] = None
    extra: Optional[Dict[str,Any]] = None
    
    def __hash__(self):
        # Create a hash from immutable components
        variables_tuple = tuple(self.variables) if self.variables else None
        depth_tuple = tuple(sorted(self.depth_cm.items())) if self.depth_cm else None
        filters_tuple = tuple(sorted(self.filters.items())) if self.filters else None
        extra_tuple = tuple(sorted(self.extra.items())) if self.extra else None
        
        return hash((
            self.geometry,
            self.time_range,
            variables_tuple,
            depth_tuple,
            self.resolution,
            filters_tuple,
            extra_tuple
        ))


CORE_COLUMNS = [
    "observation_id","dataset","source_url","source_version","license",
    "retrieval_timestamp","geometry_type","latitude","longitude","geom_wkt",
    "spatial_id","site_name","admin","elevation_m","time","temporal_coverage",
    "variable","value","unit","depth_top_cm","depth_bottom_cm","qc_flag",
    "attributes","provenance"
]
