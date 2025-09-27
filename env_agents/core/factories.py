# env_agents/core/factories.py
from .models import Geometry, RequestSpec

def point(lon, lat, **kw):    return RequestSpec(geometry=Geometry("point", [lon, lat]), **kw)
def bbox(minx, miny, maxx, maxy, **kw): return RequestSpec(geometry=Geometry("bbox", [minx, miny, maxx, maxy]), **kw)
def polygon_wkt(wkt_str, **kw): return RequestSpec(geometry=Geometry("polygon", wkt_str), **kw)