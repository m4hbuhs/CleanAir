"""
Municipal Resource Optimizer.

Recommends the most appropriate response resources (fire station, water tanker, etc.)
for a given pollution hotspot, and calculates ETA using Google Maps logic (haversine placeholder).
"""

import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResourceOptimizer:
    def __init__(self):
        # Mock database of available municipal resources in Delhi
        self.municipal_resources = [
            {"id": "RS-01", "type": "Fire Brigade", "lat": 28.6139, "lon": 77.2090, "status": "AVAILABLE"},
            {"id": "RS-02", "type": "Fire Brigade", "lat": 28.5355, "lon": 77.2619, "status": "AVAILABLE"},
            {"id": "RS-03", "type": "Water Mist Cannon", "lat": 28.6448, "lon": 77.2167, "status": "AVAILABLE"},
            {"id": "RS-04", "type": "Water Mist Cannon", "lat": 28.5921, "lon": 77.0460, "status": "AVAILABLE"},
            {"id": "RS-05", "type": "Road Cleaning Vehicle", "lat": 28.6500, "lon": 77.2300, "status": "AVAILABLE"},
            {"id": "RS-06", "type": "Pollution Control Team", "lat": 28.6200, "lon": 77.2200, "status": "AVAILABLE"},
            {"id": "RS-07", "type": "Environmental Inspection", "lat": 28.7041, "lon": 77.1025, "status": "AVAILABLE"},
        ]

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two points."""
        R = 6371.0
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_recommendation(
        self, 
        lat: float, 
        lon: float, 
        dominant_source: str, 
        severity: str
    ) -> Dict[str, Any]:
        """
        Determines the appropriate resource type and finds the closest available unit.
        """
        # 1. Determine Required Department & Priority
        required_type = "Pollution Control Team"
        priority = "Medium"
        manpower = 2
        equipment = "Standard AQI Monitors"
        reasoning = "General pollution investigation required."
        
        if dominant_source == "Biomass/Garbage Burning":
            required_type = "Fire Brigade"
            priority = "Critical"
            manpower = 5
            equipment = "Fire Tender, Foam"
            reasoning = "Active burning detected; requires immediate fire suppression."
        elif dominant_source == "Construction Dust":
            required_type = "Water Mist Cannon"
            priority = "High" if severity in ["High", "Critical"] else "Medium"
            manpower = 2
            equipment = "Anti-Smog Gun, Water Tanker"
            reasoning = "High dust concentration; requires immediate dust settling via water mist."
        elif dominant_source == "Industrial Smoke":
            required_type = "Environmental Inspection"
            priority = "High"
            manpower = 3
            equipment = "Emissions Testing Kit, Drones"
            reasoning = "Industrial emissions detected; requires on-site inspection and potential factory shutdown."
        elif dominant_source == "Vehicle Emissions" or dominant_source == "Natural/Background Dust":
            required_type = "Road Cleaning Vehicle"
            priority = "Medium"
            manpower = 1
            equipment = "Mechanized Sweeper"
            reasoning = "Re-suspended road dust and traffic pollution requires mechanized sweeping."
            
        # 2. Find closest resource
        best_resource = None
        min_dist = float('inf')
        
        for res in self.municipal_resources:
            if res["type"] == required_type and res["status"] == "AVAILABLE":
                dist = self._haversine_distance(lat, lon, res["lat"], res["lon"])
                if dist < min_dist:
                    min_dist = dist
                    best_resource = res
                    
        # 3. Estimate ETA (Assuming average urban speed of 20 km/h in traffic)
        if best_resource:
            eta_minutes = int((min_dist / 20.0) * 60)
            eta_minutes = max(5, eta_minutes) # Minimum 5 minutes
            
            return {
                "priority": priority,
                "required_department": required_type,
                "suggested_manpower": manpower,
                "suggested_equipment": equipment,
                "reasoning": reasoning,
                "closest_unit_id": best_resource["id"],
                "distance_km": round(min_dist, 1),
                "eta_minutes": eta_minutes,
                "dispatched": False
            }
        else:
            return {
                "priority": priority,
                "required_department": required_type,
                "suggested_manpower": manpower,
                "suggested_equipment": equipment,
                "reasoning": reasoning,
                "closest_unit_id": "NONE_AVAILABLE",
                "distance_km": -1,
                "eta_minutes": -1,
                "error": "No available resources of this type found nearby."
            }

resource_optimizer = ResourceOptimizer()
