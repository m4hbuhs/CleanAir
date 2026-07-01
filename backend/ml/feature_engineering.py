"""
Feature engineering pipeline for the XGBoost model.
Extracts and transforms raw telemetry into the exact feature vector
expected by the trained cleanair_xgb_model.json.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
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
