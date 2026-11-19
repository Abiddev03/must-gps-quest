"""Shared geo helpers. Everything here is REUSED from libraries:
- geopy.distance.geodesic  -> distance between two GPS points (metres)
- shapely                  -> zone polygon check, distance from point to road line
- pyproj                   -> convert lat/lon to metres (UTM 53N) so shapely distances are in metres
"""
import json
from pathlib import Path

from geopy.distance import geodesic
from pyproj import Transformer
from shapely.geometry import Point, shape

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# UTM zone 53N covers longitudes 132E to 138E, where the synthetic area sits.
TO_METRIC = Transformer.from_crs("EPSG:4326", "EPSG:32653", always_xy=True)
TO_LATLON = Transformer.from_crs("EPSG:32653", "EPSG:4326", always_xy=True)


def distance_m(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters


def load_geometry(name):
    """Load a GeoJSON geometry (lon/lat) from data/<name>.geojson."""
    with open(DATA_DIR / f"{name}.geojson") as f:
        return shape(json.load(f)["geometry"])


class Map:
    """Zone polygon (lon/lat) and road line (in metres) loaded once."""

    def __init__(self):
        self.zone = load_geometry("zone")
        road_ll = load_geometry("road")
        xs, ys = TO_METRIC.transform(*road_ll.xy)
        from shapely.geometry import LineString
        self.road_m = LineString(list(zip(xs, ys)))

    def in_zone(self, lat, lon):
        return self.zone.covers(Point(lon, lat))

    def offroad_m(self, lat, lon):
        x, y = TO_METRIC.transform(lon, lat)
        return self.road_m.distance(Point(x, y))
