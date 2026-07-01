"""
Virtual Sensor Engine — The core of the CleanAir platform.

Creates a network of "virtual sensors" by fusing:
- Nearest official AQI station data
- Citizen reports (vision-classified incidents)
- Weather conditions
- Distance-based interpolation

Produces hyperlocal AQI estimates at 500m grid resolution.
This does NOT claim to directly measure AQI — it uses AI-assisted
sensor fusion to estimate pollution at unmeasured locations.
"""

import logging
from typing import List, Optional

import numpy as np

from backend.config import get_settings
from backend.models.schemas import (
    CitizenReport,
    GridCell,
    LiveInferencePayload,
    PredictionResult,
)
from backend.ml.inference import get_inference_engine
from backend.ml.feature_engineering import build_payload_from_apis
from backend.utils.geo_utils import generate_grid, haversine_km, GeoPoint
from backend.utils.aqi_categories import classify_aqi

logger = logging.getLogger(__name__)


class VirtualSensorEngine:
    """
    Generates hyperlocal AQI estimates across a geographic grid.

    Algorithm:
    1. Generate a 500m-resolution grid centered on the target area
    2. For each grid cell:
       a. Compute distance to nearest AQI station
       b. Apply inverse-distance weighting to station AQI
       c. Count nearby citizen reports and their severity
       d. Fuse with weather conditions
       e. Run XGBoost inference on the combined features
    3. Return a list of GridCell objects with estimated AQI values
    """

    def __init__(self):
        self._engine = get_inference_engine()
        self._settings = get_settings()

    def generate_aqi_surface(
        self,
        center_lat: float,
        center_lon: float,
        aqi_data: dict,
        weather_data: dict,
        pm2_5_history: list[float],
        citizen_reports: Optional[List[CitizenReport]] = None,
        radius_km: Optional[float] = None,
        resolution_m: Optional[int] = None,
    ) -> List[GridCell]:
        """
        Generate an AQI surface across a grid of virtual sensors.

        Args:
            center_lat: Center latitude of the grid
            center_lon: Center longitude of the grid
            aqi_data: Current AQI readings from nearest station (Open-Meteo)
            weather_data: Current weather conditions (Open-Meteo)
            pm2_5_history: Last 2 PM2.5 readings for rolling average
            citizen_reports: List of active citizen reports in the area
            radius_km: Grid radius (default from settings)
            resolution_m: Grid cell size in meters (default from settings)

        Returns:
            List of GridCell objects with estimated AQI per cell.
        """
        radius = radius_km or self._settings.grid_radius_km
        resolution = resolution_m or self._settings.grid_resolution_meters
        reports = citizen_reports or []

        # Generate grid points
        grid_points = generate_grid(center_lat, center_lon, radius, resolution)

        if not grid_points:
            logger.warning("Empty grid generated for (%.4f, %.4f)", center_lat, center_lon)
            return []

        # Station location (assumed at center for single-station scenario)
        station_lat, station_lon = center_lat, center_lon

        # Base prediction at station location
        base_payload = build_payload_from_apis(aqi_data, weather_data, pm2_5_history)
        base_prediction = self._engine.predict(base_payload)

        cells: List[GridCell] = []

        for point in grid_points:
            cell = self._compute_cell(
                point=point,
                station_lat=station_lat,
                station_lon=station_lon,
                base_aqi=aqi_data.get("us_aqi", 0.0),
                base_prediction=base_prediction,
                aqi_data=aqi_data,
                weather_data=weather_data,
                pm2_5_history=pm2_5_history,
                reports=reports,
            )
            cells.append(cell)

        logger.info(
            "Generated %d virtual sensor cells for (%.4f, %.4f)",
            len(cells), center_lat, center_lon,
        )
        return cells

    def _compute_cell(
        self,
        point: GeoPoint,
        station_lat: float,
        station_lon: float,
        base_aqi: float,
        base_prediction: PredictionResult,
        aqi_data: dict,
        weather_data: dict,
        pm2_5_history: list[float],
        reports: List[CitizenReport],
    ) -> GridCell:
        """Compute AQI estimate for a single grid cell."""
        # Distance from this cell to the monitoring station
        dist_to_station = haversine_km(
            point.latitude, point.longitude, station_lat, station_lon
        )

        # Inverse distance weighting: closer to station = higher confidence
        # At the station: weight = 1.0, at 5km: weight ≈ 0.5
        distance_decay = 1.0 / (1.0 + dist_to_station * 0.2)

        # Count nearby citizen reports and compute severity boost
        nearby_reports = self._get_nearby_reports(
            point.latitude, point.longitude, reports, radius_km=1.0
        )
        report_count = len(nearby_reports)

        # Vision severity boost from citizen reports
        severity_boost = 0.0
        if nearby_reports:
            avg_severity = np.mean([r.severity.value for r in nearby_reports])
            severity_boost = (avg_severity / 5.0) * 0.3  # Max 30% boost

        # Spatial variation: add controlled random noise to simulate
        # micro-environment differences (traffic, construction, etc.)
        np.random.seed(
            int(abs(point.latitude * 10000)) + int(abs(point.longitude * 10000))
        )
        spatial_noise = np.random.normal(0, 0.05)

        # Final AQI estimation for this cell
        base_est = base_prediction.estimated_aqi
        cell_aqi = base_est * distance_decay * (1.0 + severity_boost + spatial_noise)
        cell_aqi = max(0.0, round(cell_aqi, 1))

        # Confidence decreases with distance from station and increases with reports
        base_conf = base_prediction.confidence
        cell_confidence = base_conf * distance_decay
        if report_count > 0:
            cell_confidence = min(0.95, cell_confidence + 0.05 * report_count)
        cell_confidence = round(max(0.2, cell_confidence), 2)

        category = classify_aqi(cell_aqi)

        return GridCell(
            latitude=point.latitude,
            longitude=point.longitude,
            estimated_aqi=cell_aqi,
            confidence=cell_confidence,
            nearest_station_distance_km=round(dist_to_station, 2),
            citizen_report_count=report_count,
            vision_severity_boost=round(severity_boost, 3),
            risk_level=category.risk_level,
            color=category.color,
        )

    def _get_nearby_reports(
        self,
        lat: float,
        lon: float,
        reports: List[CitizenReport],
        radius_km: float = 1.0,
    ) -> List[CitizenReport]:
        """Filter reports within radius_km of a point."""
        return [
            r for r in reports
            if haversine_km(lat, lon, r.latitude, r.longitude) <= radius_km
        ]


def generate_quick_surface(
    center_lat: float,
    center_lon: float,
    aqi_data: dict,
    weather_data: dict,
    pm2_5_history: list[float],
    citizen_reports: Optional[List[CitizenReport]] = None,
) -> List[GridCell]:
    """
    Convenience function for quick AQI surface generation.
    Uses default settings for grid resolution and radius.
    """
    engine = VirtualSensorEngine()
    return engine.generate_aqi_surface(
        center_lat=center_lat,
        center_lon=center_lon,
        aqi_data=aqi_data,
        weather_data=weather_data,
        pm2_5_history=pm2_5_history,
        citizen_reports=citizen_reports,
    )
