"""
Geospatial utility functions for the Virtual Sensor Network.
Haversine distance, grid generation, coordinate transforms.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GeoPoint:
    """A geographic coordinate with optional metadata."""
    latitude: float
    longitude: float
    label: str = ""
    weight: float = 1.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth (km).

    Uses the Haversine formula. Accurate to ~0.5% for most practical uses.
    """
    R = 6371.0  # Earth's mean radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def generate_grid(
    center_lat: float,
    center_lon: float,
    radius_km: float = 5.0,
    resolution_meters: int = 500,
) -> List[GeoPoint]:
    """
    Generate a rectangular grid of GeoPoints centered on a location.

    Args:
        center_lat: Center latitude (decimal degrees)
        center_lon: Center longitude (decimal degrees)
        radius_km: Radius of the grid in each direction (km)
        resolution_meters: Spacing between grid points (meters)

    Returns:
        List of GeoPoints covering the specified area.
    """
    points: List[GeoPoint] = []
    resolution_km = resolution_meters / 1000.0

    # Approximate degree offsets
    lat_per_km = 1.0 / 111.0  # ~111 km per degree latitude
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(center_lat)))

    steps = int(radius_km / resolution_km)

    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            lat = center_lat + (i * resolution_km * lat_per_km)
            lon = center_lon + (j * resolution_km * lon_per_km)

            # Only include points within circular radius
            dist = haversine_km(center_lat, center_lon, lat, lon)
            if dist <= radius_km:
                points.append(GeoPoint(
                    latitude=round(lat, 6),
                    longitude=round(lon, 6),
                    label=f"grid_{i}_{j}",
                ))

    return points


def find_nearest_station(
    lat: float,
    lon: float,
    stations: List[dict],
) -> Tuple[dict, float]:
    """
    Find the nearest monitoring station to a given coordinate.

    Args:
        lat: Query latitude
        lon: Query longitude
        stations: List of dicts with 'latitude' and 'longitude' keys

    Returns:
        Tuple of (nearest_station_dict, distance_km)
    """
    if not stations:
        return {}, float('inf')

    best_station = stations[0]
    best_dist = float('inf')

    for station in stations:
        dist = haversine_km(lat, lon, station["latitude"], station["longitude"])
        if dist < best_dist:
            best_dist = dist
            best_station = station

    return best_station, best_dist


def meters_to_degrees_lat(meters: float) -> float:
    """Convert meters to approximate degrees of latitude."""
    return meters / 111_000.0


def meters_to_degrees_lon(meters: float, latitude: float) -> float:
    """Convert meters to approximate degrees of longitude at given latitude."""
    return meters / (111_000.0 * math.cos(math.radians(latitude)))


def bounding_box(
    lat: float, lon: float, radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Returns (min_lat, min_lon, max_lat, max_lon) for a bounding box
    centered on (lat, lon) with the given radius.
    """
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def extract_exif_location(image) -> Tuple[float, float]:
    """
    Extract GPS location from PIL Image EXIF data.
    Returns (latitude, longitude) or (None, None) if not found.
    """
    try:
        from PIL.ExifTags import TAGS, GPSTAGS
        
        exif = image._getexif()
        if not exif:
            return None, None
            
        gps_info = None
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if decoded == 'GPSInfo':
                gps_info = value
                break
                
        if not gps_info:
            return None, None
            
        gps_data = {}
        for t in gps_info:
            sub_decoded = GPSTAGS.get(t, t)
            gps_data[sub_decoded] = gps_info[t]
            
        if 'GPSLatitude' not in gps_data or 'GPSLongitude' not in gps_data:
            return None, None
            
        def convert_to_degrees(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
            
        lat = convert_to_degrees(gps_data['GPSLatitude'])
        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
        if lat_ref != 'N': lat = -lat
        
        lon = convert_to_degrees(gps_data['GPSLongitude'])
        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        if lon_ref != 'E': lon = -lon
        
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None


def geocode_address(address: str) -> Tuple[float, float]:
    """
    Convert a text address to (latitude, longitude) using OpenStreetMap Nominatim.
    Returns (None, None) if not found.
    """
    import requests
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": "CleanAirHackathonApp/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None
