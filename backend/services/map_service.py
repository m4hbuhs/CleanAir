"""
Map Service — Prepares and formats data for the Smart City GIS Dashboard (Google Maps).
"""

import math
from typing import List, Dict, Any
from backend.models.schemas import CitizenReport, HotspotCluster, MunicipalAlert
from backend.utils.geo_utils import GeoPoint
from backend.services.virtual_sensor_engine import VirtualSensorEngine

class MapService:
    def __init__(self):
        # We can instantiate the engine here to use for grid predictions if needed
        self.virtual_sensor_engine = VirtualSensorEngine()

    def get_stations(self) -> List[Dict[str, Any]]:
        """
        Mock official CPCB monitoring stations for the GIS layer.
        In a real app, this would ping CPCB or OpenMeteo APIs for station coordinates.
        """
        return [
            {"id": "cpcb-1", "name": "Anand Vihar", "lat": 28.6476, "lng": 77.3158, "aqi": 312, "pm25": 180, "updated": "Just now"},
            {"id": "cpcb-2", "name": "ITO", "lat": 28.6284, "lng": 77.2403, "aqi": 215, "pm25": 110, "updated": "5 min ago"},
            {"id": "cpcb-3", "name": "Punjabi Bagh", "lat": 28.6740, "lng": 77.1310, "aqi": 180, "pm25": 85, "updated": "10 min ago"},
            {"id": "cpcb-4", "name": "RK Puram", "lat": 28.5632, "lng": 77.1869, "aqi": 150, "pm25": 65, "updated": "Just now"},
            {"id": "cpcb-5", "name": "Okhla Phase-2", "lat": 28.5307, "lng": 77.2723, "aqi": 245, "pm25": 135, "updated": "12 min ago"},
        ]

    def format_reports(self, reports: List[CitizenReport]) -> List[Dict[str, Any]]:
        """Format Citizen Reports for Advanced Markers."""
        formatted = []
        for r in reports:
            formatted.append({
                "id": r.report_id,
                "lat": r.latitude,
                "lng": r.longitude,
                "type": r.pollution_type.value,
                "severity": r.severity.name.title(),
                "description": r.description,
                "confidence": r.confidence,
                "reporter": r.user_id,
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "Unknown"
            })
        return formatted

    def format_hotspots(self, clusters: List[HotspotCluster]) -> List[Dict[str, Any]]:
        """Format Hotspot clusters for translucent circle rendering."""
        formatted = []
        for c in clusters:
            formatted.append({
                "id": str(c.cluster_id),
                "lat": c.center_latitude,
                "lng": c.center_longitude,
                "radius": c.radius_km * 1000,  # convert to meters
                "report_count": c.report_count,
                "severity": c.avg_severity,
                "dominant_type": c.dominant_pollution_type,
                "estimated_aqi": c.estimated_aqi or 150,
            })
        return formatted

    def format_alerts(self, alerts: List[MunicipalAlert]) -> List[Dict[str, Any]]:
        """Format municipal alerts for officer markers."""
        formatted = []
        for a in alerts:
            formatted.append({
                "id": a.alert_id,
                "lat": a.latitude,
                "lng": a.longitude,
                "type": a.pollution_type,
                "aqi": a.estimated_aqi,
                "status": a.dispatch_status,
                "timestamp": a.triggered_at.strftime("%Y-%m-%d %H:%M")
            })
        return formatted

    def generate_grid_for_bounds(self, north: float, south: float, east: float, west: float, resolution_meters: int = 500) -> List[Dict[str, Any]]:
        """
        Generates a grid of prediction rectangles within a bounding box.
        Each cell receives an Estimated AQI and Confidence.
        """
        cells = []
        resolution_km = resolution_meters / 1000.0
        lat_per_km = 1.0 / 111.0
        
        # Center of bounding box
        center_lat = (north + south) / 2.0
        
        # Prevent division by zero or errors at high latitudes
        if math.cos(math.radians(center_lat)) == 0:
            return []
            
        lon_per_km = 1.0 / (111.0 * math.cos(math.radians(center_lat)))
        
        lat_step = resolution_km * lat_per_km
        lon_step = resolution_km * lon_per_km

        # Constrain maximum grid size to avoid performance hangs on large zoom-outs
        max_cells = 400
        lat_diff = abs(north - south)
        lon_diff = abs(east - west)
        
        if lat_step == 0 or lon_step == 0:
            return []
            
        num_lats = int(lat_diff / lat_step)
        num_lons = int(lon_diff / lon_step)
        
        if num_lats * num_lons > max_cells:
            # Increase step size dynamically to fit within 400 cells
            ratio = math.sqrt((num_lats * num_lons) / max_cells)
            lat_step *= ratio
            lon_step *= ratio

        current_lat = south
        while current_lat < north:
            current_lon = west
            while current_lon < east:
                # Mock smooth gradient based on distance from center of New Delhi (28.6139, 77.2090)
                dist = math.sqrt((current_lat - 28.6139)**2 + (current_lon - 77.2090)**2)
                mock_aqi = max(50, 350 - (dist * 1000))
                
                # Simulate some GEE data for the UI representation
                mock_aod = max(0.1, (mock_aqi / 300) * 1.5)
                mock_no2 = max(10, (mock_aqi / 200) * 50)
                mock_thermal = True if mock_aqi > 250 else False

                cells.append({
                    "bounds": {
                        "north": current_lat + lat_step,
                        "south": current_lat,
                        "east": current_lon + lon_step,
                        "west": current_lon
                    },
                    "aqi": mock_aqi,
                    "confidence": 85,
                    "satellite": {
                        "aod": mock_aod,
                        "no2": mock_no2,
                        "thermal_anomaly": mock_thermal
                    }
                })
                current_lon += lon_step
            current_lat += lat_step
            
        return cells
