import math
from typing import Tuple, List, Dict, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the Earth
    in kilometers using the Haversine formula.
    """
    earth_radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(earth_radius_km * c, 2)


def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Returns (min_lat, max_lat, min_lon, max_lon) bounding box
    for fast initial database filtering.
    """
    # 1 deg latitude is approx 111 km
    lat_delta = radius_km / 111.0
    # 1 deg longitude depends on latitude
    lon_delta = radius_km / (111.0 * max(0.01, math.cos(math.radians(lat))))

    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta,
    )
