"""
Feature engineering pipeline for the XGBoost model.
Extracts and transforms raw telemetry into the exact feature vector
expected by the trained cleanair_xgb_model.json.

Also provides an extended feature builder for the Virtual Sensor Engine
that combines AQI, weather, historical, Gemini, and satellite features.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
from backend.models.schemas import LiveInferencePayload


# The exact feature order the trained model expects
ORDERED_FEATURES = [
    "us_aqi", "pm10", "pm2_5", "pm2_5_roll3", "carbon_monoxide",
    "nitrogen_dioxide", "sulphur_dioxide", "ozone", "dust",
    "tavg", "prcp", "wind_u", "wind_v", "month",
]


def payload_to_feature_matrix(payload: LiveInferencePayload) -> pd.DataFrame:
    """
    Transforms a validated LiveInferencePayload into the exact feature
    DataFrame expected by the XGBoost model.

    Feature engineering steps:
    1. pm2_5_roll3 — 3-day rolling average of PM2.5
    2. wind_u / wind_v — Decomposed wind vector from speed + direction
    3. month — Current UTC month as a seasonal feature

    Returns:
        pd.DataFrame with one row and 14 ordered feature columns.
    """
    data = payload.model_dump()

    # 1. Rolling 3-day PM2.5 average (current + 2 prior days)
    data["pm2_5_roll3"] = (
        data["pm2_5"] + data["pm2_5_yesterday_1"] + data["pm2_5_yesterday_2"]
    ) / 3.0

    # 2. Decompose wind into U (east-west) and V (north-south) components
    wdir_rad = np.radians(data["wdir"])
    data["wind_u"] = data["wspd"] * np.cos(wdir_rad)
    data["wind_v"] = data["wspd"] * np.sin(wdir_rad)

    # 3. Seasonal feature — current UTC month
    data["month"] = datetime.now(timezone.utc).month

    # Return exactly the columns the model was trained on, in order
    return pd.DataFrame([data])[ORDERED_FEATURES]


def build_payload_from_apis(
    aqi_data: dict,
    weather_data: dict,
    pm2_5_history: list[float],
) -> LiveInferencePayload:
    """
    Constructs a LiveInferencePayload from raw API responses.

    Args:
        aqi_data: Dict from Open-Meteo AQI API (current values)
        weather_data: Dict from Open-Meteo Weather API (current values)
        pm2_5_history: List of last 2 PM2.5 readings [yesterday_1, yesterday_2]

    Returns:
        Validated LiveInferencePayload ready for feature engineering.
    """
    # Safely extract with defaults
    pm2_5_now = float(aqi_data.get("pm2_5", 0.0))
    history = pm2_5_history if len(pm2_5_history) >= 2 else [pm2_5_now, pm2_5_now]

    return LiveInferencePayload(
        us_aqi=float(aqi_data.get("us_aqi", 0.0)),
        pm10=float(aqi_data.get("pm10", 0.0)),
        pm2_5=pm2_5_now,
        carbon_monoxide=float(aqi_data.get("carbon_monoxide", 0.0)),
        nitrogen_dioxide=float(aqi_data.get("nitrogen_dioxide", 0.0)),
        sulphur_dioxide=float(aqi_data.get("sulphur_dioxide", 0.0)),
        ozone=float(aqi_data.get("ozone", 0.0)),
        dust=float(aqi_data.get("dust", 0.0)),
        pm2_5_yesterday_1=float(history[-1]),
        pm2_5_yesterday_2=float(history[-2]),
        tavg=float(weather_data.get("temperature_2m", 0.0)),
        prcp=float(weather_data.get("precipitation", 0.0)),
        wspd=float(weather_data.get("wind_speed_10m", 0.0)),
        wdir=max(0.0, min(360.0, float(weather_data.get("wind_direction_10m", 0.0)))),
    )


# ─────────────────────────────────────────────
# Extended Feature Engineering for Virtual Sensor Engine
# ─────────────────────────────────────────────

def build_extended_feature_dict(
    aqi_data: dict,
    weather_data: dict,
    historical_features: Optional[dict] = None,
    gemini_scores: Optional[dict] = None,
    satellite_features: Optional[dict] = None,
    distance_to_station: float = 0.0,
    citizen_report_density: int = 0,
) -> dict:
    """
    Build the full ~27-feature dictionary for the Virtual Sensor Engine.

    This combines all data sources into a single flat dict of numerical
    features. The existing XGBoost model uses the legacy 14-feature subset;
    the extended features feed into confidence scoring, alert logic,
    and can be used for future model retraining.

    Args:
        aqi_data: Current AQI readings from Open-Meteo
        weather_data: Current weather conditions from Open-Meteo
        historical_features: Time-series features (HistoricalFeatures.model_dump())
        gemini_scores: Numerical scores from GeminiPollutionFeatures.to_numerical_scores()
        satellite_features: SatelliteFeatures.model_dump()
        distance_to_station: Distance to nearest monitoring station (km)
        citizen_report_density: Number of citizen reports within 1 km

    Returns:
        Flat dict of ~27 numerical features.
    """
    now = datetime.now(timezone.utc)
    hist = historical_features or {}
    gem = gemini_scores or {}
    sat = satellite_features or {}

    features = {
        # AQI pollutants
        "pm2_5": float(aqi_data.get("pm2_5", 0.0)),
        "pm10": float(aqi_data.get("pm10", 0.0)),
        "co": float(aqi_data.get("carbon_monoxide", 0.0)),
        "no2": float(aqi_data.get("nitrogen_dioxide", 0.0)),
        "so2": float(aqi_data.get("sulphur_dioxide", 0.0)),
        "ozone": float(aqi_data.get("ozone", 0.0)),
        # Weather
        "temperature": float(weather_data.get("temperature_2m", 0.0)),
        "humidity": float(weather_data.get("relative_humidity_2m", 50.0)),
        "wind_speed": float(weather_data.get("wind_speed_10m", 0.0)),
        "wind_direction": float(weather_data.get("wind_direction_10m", 0.0)),
        "rain": float(weather_data.get("precipitation", 0.0)),
        "pressure": float(weather_data.get("surface_pressure", 1013.0)),
        "cloud_cover": float(weather_data.get("cloud_cover", 50.0)),
        # Historical
        "historical_aqi": float(hist.get("previous_hour_aqi", 0.0)),
        "rolling_avg_3h": float(hist.get("rolling_avg_3h", 0.0)),
        "rolling_avg_24h": float(hist.get("rolling_avg_24h", 0.0)),
        "hour": hist.get("hour", now.hour),
        "weekday": hist.get("weekday", now.weekday()),
        "month": hist.get("month", now.month),
        # Gemini-derived
        "dust_score": float(gem.get("dust_score", 0.0)),
        "smoke_score": float(gem.get("smoke_score", 0.0)),
        "construction_score": float(gem.get("construction_score", 0.0)),
        "traffic_score": float(gem.get("traffic_score", 0.0)),
        "severity_score": float(gem.get("severity_score", 0.0)),
        # Satellite
        "satellite_aod": float(sat.get("aerosol_optical_depth", 0.0)),
        # Spatial
        "distance_to_station": distance_to_station,
        "complaint_density": citizen_report_density,
    }
    return features


def build_historical_features(
    hourly_aqi_values: list[float],
    current_hour: Optional[int] = None,
) -> dict:
    """
    Build time-series features from hourly AQI history.

    Args:
        hourly_aqi_values: List of hourly AQI values, most recent last.
            Ideally 168 values (7 days × 24 hours). Shorter lists
            will produce degraded but valid features.
        current_hour: Current UTC hour (0-23). Auto-detected if None.

    Returns:
        Dict matching HistoricalFeatures fields.
    """
    now = datetime.now(timezone.utc)
    hour = current_hour if current_hour is not None else now.hour
    values = hourly_aqi_values or []

    # Pad with zeros if too short
    if len(values) < 2:
        values = [0.0] * 168

    last = values[-1] if values else 0.0

    # Previous hour (second to last)
    prev_hour = values[-2] if len(values) >= 2 else last

    # Previous day (24 hours ago)
    prev_day = values[-24] if len(values) >= 24 else last

    # Rolling averages
    roll_3h = float(np.mean(values[-3:])) if len(values) >= 3 else last
    roll_24h = float(np.mean(values[-24:])) if len(values) >= 24 else last

    # Same hour yesterday
    same_hour_yesterday = values[-24] if len(values) >= 24 else last

    # Same hour last week
    same_hour_last_week = values[-168] if len(values) >= 168 else last

    return {
        "previous_hour_aqi": prev_hour,
        "previous_day_aqi": prev_day,
        "rolling_avg_3h": round(roll_3h, 1),
        "rolling_avg_24h": round(roll_24h, 1),
        "same_hour_yesterday": same_hour_yesterday,
        "same_hour_last_week": same_hour_last_week,
        "month": now.month,
        "weekday": now.weekday(),
        "hour": hour,
    }
