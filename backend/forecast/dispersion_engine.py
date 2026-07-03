"""
Pollution Dispersion Engine.

Models how pollution plumes (smoke/dust) will spread over time (1h, 3h, 6h, 12h, 24h)
using wind speed, wind direction, and basic Gaussian plume dispersion heuristics.
"""

import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DispersionEngine:
    
    def predict_spread(
        self, 
        source_lat: float, 
        source_lon: float, 
        wind_speed_kmh: float, 
        wind_direction_deg: float, 
        base_aqi: float
    ) -> List[Dict[str, Any]]:
        """
        Generates plume spread projections for upcoming hours.
        Returns a list of projections (lat, lon, radius, expected_aqi).
        """
        projections = []
        
        # Hours into the future to predict
        time_horizons = [1, 3, 6, 12, 24]
        
        # Wind direction is where wind is COMING FROM. 
        # So plume travels in opposite direction.
        travel_direction = (wind_direction_deg + 180) % 360
        bearing_rad = math.radians(travel_direction)
        
        R = 6371.0 # Earth radius in km
        
        for hour in time_horizons:
            # Distance traveled = speed * time
            distance_km = wind_speed_kmh * hour
            
            # Decay of pollution concentration over distance/time
            # Simple inverse square or exponential decay heuristic
            decay_factor = math.exp(-0.1 * hour)
            expected_aqi = base_aqi * decay_factor
            
            if expected_aqi < 50:
                continue # Plume has dissipated below concerning levels
                
            # Calculate new lat/lon
            lat1 = math.radians(source_lat)
            lon1 = math.radians(source_lon)
            
            lat2 = math.asin(
                math.sin(lat1) * math.cos(distance_km / R) +
                math.cos(lat1) * math.sin(distance_km / R) * math.cos(bearing_rad)
            )
            
            lon2 = lon1 + math.atan2(
                math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat1),
                math.cos(distance_km / R) - math.sin(lat1) * math.sin(lat2)
            )
            
            # Plume spreads out laterally over time (radius increases)
            radius_km = 0.5 + (0.2 * hour) 
            
            projections.append({
                "hour": hour,
                "latitude": math.degrees(lat2),
                "longitude": math.degrees(lon2),
                "radius_km": round(radius_km, 2),
                "expected_aqi": round(expected_aqi, 1)
            })
            
        return projections

dispersion_engine = DispersionEngine()
