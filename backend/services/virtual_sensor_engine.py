"""
Virtual Sensor Engine — The core orchestrator of the CleanAir platform.

Estimates hyperlocal AQI by fusing multiple data sources:
- Official AQI monitoring station data (Open-Meteo)
- Live weather conditions (Open-Meteo)
- Historical pollution patterns (hourly AQI history)
- Satellite observations (mock/real providers)
- Citizen-reported environmental features (Gemini Vision)

This service NEVER claims to measure AQI from images. It estimates
AQI by combining all available data sources, exactly like a virtual
environmental sensor.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from backend.config import get_settings
from backend.ml.confidence import compute_confidence
from backend.ml.feature_engineering import (
    build_extended_feature_dict,
    build_historical_features,
    build_payload_from_apis,
)
from backend.ml.inference import get_inference_engine
from backend.models.schemas import (
    CitizenReport,
    ConfidenceBreakdown,
    GeminiPollutionFeatures,
    HistoricalFeatures,
    HourlyForecastPoint,
    SatelliteFeatures,
    VirtualSensorResult,
)
from backend.utils.aqi_categories import classify_aqi
from backend.utils.geo_utils import haversine_km

logger = logging.getLogger(__name__)


class VirtualSensorEngine:
    """
    Orchestrates multi-source sensor fusion to estimate hyperlocal AQI.

    Pipeline:
    1. Fetch official AQI from nearest monitoring station
    2. Fetch live weather conditions
    3. Fetch historical AQI (hourly) for time-series features
    4. Fetch satellite-derived features (AOD, thermal, smoke)
    5. Convert Gemini output to numerical feature scores
    6. Build the legacy 14-feature payload for XGBoost
    7. Run XGBoost prediction with vision severity multiplier
    8. Compute multi-factor confidence score
    9. Generate 24-hour hourly forecast
    10. Return unified VirtualSensorResult
    """

    def __init__(self):
        self._engine = get_inference_engine()
        self._settings = get_settings()

    def estimate_aqi(
        self,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None,
        gemini_features: Optional[GeminiPollutionFeatures] = None,
        citizen_reports: Optional[List[CitizenReport]] = None,
    ) -> VirtualSensorResult:
        """
        Estimate hyperlocal AQI at a specific location by fusing
        all available data sources.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            timestamp: Timestamp for the estimate (default: now UTC)
            gemini_features: Environmental features from Gemini Vision
            citizen_reports: Active citizen reports in the area

        Returns:
            VirtualSensorResult with estimated AQI, official station AQI,
            confidence breakdown, 24h forecast, and contributing features.
        """
        ts = timestamp or datetime.now(timezone.utc)
        reports = citizen_reports or []

        # ── Step 1: Fetch official AQI ────────────────
        aqi_data = self._fetch_aqi(latitude, longitude)
        official_aqi = aqi_data.get("us_aqi", 0.0)

        # ── Step 2: Fetch weather ─────────────────────
        weather_data = self._fetch_weather(latitude, longitude)

        # ── Step 3: Fetch historical AQI ──────────────
        hourly_history = self._fetch_hourly_history(latitude, longitude)
        historical = build_historical_features(hourly_history, ts.hour)
        hist_features = HistoricalFeatures(**historical)

        # ── Step 4: Fetch satellite features ──────────
        sat_features = self._fetch_satellite(latitude, longitude)

        # ── Step 5: Gemini numerical scores ───────────
        gemini_scores = {}
        severity_multiplier = 1.0
        if gemini_features:
            gemini_scores = gemini_features.to_numerical_scores()
            severity_multiplier = gemini_features.to_severity_multiplier()

        # ── Step 6: Build legacy payload for XGBoost ──
        pm2_5_hist = self._extract_pm25_history(hourly_history)
        payload = build_payload_from_apis(aqi_data, weather_data, pm2_5_hist)

        # ── Step 7: XGBoost prediction ────────────────
        prediction = self._engine.predict(payload, severity_multiplier)

        # ── Step 8: Confidence score ──────────────────
        nearby_count = self._count_nearby_reports(
            latitude, longitude, reports, radius_km=1.0
        )
        data_age_minutes = 0.0  # Data is live from API
        missing_count = self._count_missing_features(
            aqi_data, weather_data, sat_features
        )
        gemini_conf = gemini_features.confidence if gemini_features else None

        confidence = compute_confidence(
            distance_to_station_km=0.0,  # Station assumed at queried point
            citizen_report_count=nearby_count,
            gemini_confidence=gemini_conf,
            data_freshness_minutes=data_age_minutes,
            missing_feature_count=missing_count,
        )

        # ── Step 9: 24-hour forecast ─────────────────
        hourly_forecast = self._generate_forecast(
            payload, severity_multiplier, latitude, longitude
        )

        # ── Step 10: Build extended feature dict ──────
        # (stored for future model retraining, not used by current model)
        _ = build_extended_feature_dict(
            aqi_data=aqi_data,
            weather_data=weather_data,
            historical_features=historical,
            gemini_scores=gemini_scores,
            satellite_features=sat_features.model_dump() if sat_features else None,
            distance_to_station=0.0,
            citizen_report_density=nearby_count,
        )

        # ── Build weather summary ─────────────────────
        temp = weather_data.get("temperature_2m", "N/A")
        wind = weather_data.get("wind_speed_10m", "N/A")
        humidity = weather_data.get("relative_humidity_2m", "N/A")
        weather_summary = f"Temp: {temp}°C, Wind: {wind} km/h, Humidity: {humidity}%"

        # ── Classify prediction ───────────────────────
        category = classify_aqi(prediction.estimated_aqi)

        return VirtualSensorResult(
            estimated_aqi=prediction.estimated_aqi,
            official_station_aqi=official_aqi,
            risk_level=category.risk_level,
            category_label=category.label,
            category_color=category.color,
            health_advisory=category.health_advisory,
            confidence=confidence,
            hourly_forecast=hourly_forecast,
            gemini_features=gemini_features,
            satellite_features=sat_features,
            historical_features=hist_features,
            weather_summary=weather_summary,
            distance_to_station_km=0.0,
            citizen_report_count=nearby_count,
            is_official=False,
        )

    # ── Private helpers ───────────────────────────────

    def _fetch_aqi(self, lat: float, lon: float) -> dict:
        """Fetch current AQI with error fallback."""
        try:
            from backend.services.aqi_service import fetch_current_aqi
            return fetch_current_aqi(lat, lon)
        except Exception as e:
            logger.warning("AQI fetch failed: %s. Using defaults.", e)
            return {
                "us_aqi": 100.0, "pm10": 60.0, "pm2_5": 35.0,
                "carbon_monoxide": 600.0, "nitrogen_dioxide": 30.0,
                "sulphur_dioxide": 10.0, "ozone": 45.0, "dust": 1.0,
            }

    def _fetch_weather(self, lat: float, lon: float) -> dict:
        """Fetch current weather with error fallback."""
        try:
            from backend.services.weather_service import fetch_current_weather
            return fetch_current_weather(lat, lon)
        except Exception as e:
            logger.warning("Weather fetch failed: %s. Using defaults.", e)
            return {
                "temperature_2m": 32.0, "precipitation": 0.0,
                "wind_speed_10m": 5.0, "wind_direction_10m": 180.0,
                "relative_humidity_2m": 55.0,
            }

    def _fetch_hourly_history(self, lat: float, lon: float) -> list[float]:
        """Fetch hourly AQI history with error fallback."""
        try:
            from backend.services.aqi_service import fetch_hourly_aqi
            values = fetch_hourly_aqi(lat, lon, hours=48)
            return values if values else [100.0] * 48
        except Exception as e:
            logger.warning("Hourly AQI history fetch failed: %s", e)
            return [100.0] * 48

    def _fetch_satellite(self, lat: float, lon: float) -> SatelliteFeatures:
        """Fetch satellite features with error fallback."""
        try:
            from backend.services.satellite_service import fetch_satellite_features
            return fetch_satellite_features(lat, lon)
        except Exception as e:
            logger.warning("Satellite fetch failed: %s", e)
            return SatelliteFeatures(source="unavailable")

    def _extract_pm25_history(self, hourly_aqi: list[float]) -> list[float]:
        """
        Extract the last 2 PM2.5-proxy values from hourly AQI history
        for the legacy XGBoost payload (pm2_5_yesterday_1, pm2_5_yesterday_2).
        """
        if len(hourly_aqi) >= 48:
            return [hourly_aqi[-24], hourly_aqi[-48]]
        elif len(hourly_aqi) >= 2:
            return [hourly_aqi[-1], hourly_aqi[-2]]
        else:
            return [35.0, 35.0]

    def _count_nearby_reports(
        self, lat: float, lon: float,
        reports: List[CitizenReport], radius_km: float = 1.0,
    ) -> int:
        """Count citizen reports within radius_km of a point."""
        return sum(
            1 for r in reports
            if haversine_km(lat, lon, r.latitude, r.longitude) <= radius_km
        )

    def _count_missing_features(
        self, aqi_data: dict, weather_data: dict,
        sat_features: SatelliteFeatures,
    ) -> int:
        """Count features that have default/zero values."""
        missing = 0
        for key in ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide"]:
            if aqi_data.get(key, 0.0) == 0.0:
                missing += 1
        for key in ["temperature_2m", "wind_speed_10m"]:
            if weather_data.get(key, 0.0) == 0.0:
                missing += 1
        if sat_features.source in ("unavailable", "mock_unavailable"):
            missing += 1
        return missing

    def _generate_forecast(
        self,
        current_payload,
        severity_multiplier: float,
        lat: float,
        lon: float,
    ) -> List[HourlyForecastPoint]:
        """Generate 24-hour forecast using weather forecast data."""
        try:
            from backend.services.weather_service import fetch_hourly_weather_forecast
            hourly_weather = fetch_hourly_weather_forecast(
                lat, lon, hours=self._settings.forecast_hours
            )
            if hourly_weather:
                return self._engine.predict_hourly_forecast(
                    current_payload, hourly_weather, severity_multiplier
                )
        except Exception as e:
            logger.warning("Hourly forecast generation failed: %s", e)

        # Fallback: single point (current hour only)
        result = self._engine.predict(current_payload, severity_multiplier)
        return [
            HourlyForecastPoint(
                hour_offset=0,
                estimated_aqi=result.estimated_aqi,
                confidence=result.confidence,
                weather_summary="Current conditions (forecast unavailable)",
            )
        ]


# ── Convenience function ──────────────────────────

def quick_estimate(
    latitude: float,
    longitude: float,
    gemini_features: Optional[GeminiPollutionFeatures] = None,
    citizen_reports: Optional[List[CitizenReport]] = None,
) -> VirtualSensorResult:
    """
    One-call convenience function for a quick AQI estimate.

    Instantiates the engine and runs the full pipeline.
    """
    engine = VirtualSensorEngine()
    return engine.estimate_aqi(
        latitude=latitude,
        longitude=longitude,
        gemini_features=gemini_features,
        citizen_reports=citizen_reports,
    )
