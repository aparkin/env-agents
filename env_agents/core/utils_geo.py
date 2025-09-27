try:
    from shapely.geometry import shape, box
    from shapely import wkt
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def centroid_from_geometry(geom_type: str, coordinates):
    if geom_type == "point":
        lon, lat = coordinates
        return lat, lon
    elif geom_type == "bbox":
        minx, miny, maxx, maxy = coordinates
        if SHAPELY_AVAILABLE:
            c = box(minx,miny,maxx,maxy).centroid
            return c.y, c.x
        else:
            # Simple center calculation without shapely
            center_lat = (miny + maxy) / 2
            center_lon = (minx + maxx) / 2
            return center_lat, center_lon
    else:
        if SHAPELY_AVAILABLE:
            g = wkt.loads(coordinates) if isinstance(coordinates, str) else shape(coordinates)
            c = g.centroid
            return c.y, c.x
        else:
            raise RuntimeError("Complex geometry types require shapely library")
