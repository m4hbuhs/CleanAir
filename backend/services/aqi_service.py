"""
AQI data ingestion service using the Open-Meteo Air Quality API.
Free, no API key required. Returns real-time pollutant concentrations.
"""

import logging
from typing import Optional

import requests

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Open-Meteo Air Quality API base URL
_BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Fields we need for the XGBoost model
_CURRENT_FIELDS = "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust"


def fetch_current_aqi(
    latitude: float,
    longitude: float,
    timeout: Optional[int] = None,
) -> dict:
    """
    Fetch current air quality data from Open-Meteo.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        timeout: Request timeout in seconds

    Returns:
        Dict with keys matching LiveInferencePayload AQI fields:
        {us_aqi, pm10, pm2_5, carbon_monoxide, nitrogen_dioxide,
         sulphur_dioxide, ozone, dust}

    Raises:
        requests.RequestException on network failures.
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": _CURRENT_FIELDS,
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        if not current:
            logger.warning(
                "Open-Meteo AQI returned empty 'current' for (%.4f, %.4f)",
                latitude, longitude,
            )
            return _default_aqi_response()

        return {
            "us_aqi": float(current.get("us_aqi", 0.0)),
            "pm10": float(current.get("pm10", 0.0)),
            "pm2_5": float(current.get("pm2_5", 0.0)),
            "carbon_monoxide": float(current.get("carbon_monoxide", 0.0)),
            "nitrogen_dioxide": float(current.get("nitrogen_dioxide", 0.0)),
            "sulphur_dioxide": float(current.get("sulphur_dioxide", 0.0)),
            "ozone": float(current.get("ozone", 0.0)),
            "dust": float(current.get("dust", 0.0)),
        }

    except requests.RequestException as e:
        logger.error("Failed to fetch AQI data: %s", e)
        raise


def fetch_historical_aqi(
    latitude: float,
    longitude: float,
    days: int = 7,
    timeout: Optional[int] = None,
) -> list[dict]:
    """
    Fetch recent historical AQI (daily) for trend analysis.

    Returns:
        List of daily dicts with pm2_5 values for rolling window.
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds

    from datetime import datetime, timedelta
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "pm2_5",
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        pm25_values = hourly.get("pm2_5", [])

        # Compute daily averages
        daily: dict[str, list[float]] = {}
        for t, v in zip(times, pm25_values):
            date = t[:10]
            if v is not None:
                daily.setdefault(date, []).append(float(v))

        return [
            {"date": date, "pm2_5": sum(vals) / len(vals)}
            for date, vals in sorted(daily.items())
            if vals
        ]

    except requests.RequestException as e:
        logger.error("Failed to fetch historical AQI: %s", e)
        return []


def fetch_hourly_aqi(
    latitude: float,
    longitude: float,
    hours: int = 48,
    timeout: Optional[int] = None,
) -> list[float]:
    """
    Fetch the last N hours of hourly US AQI values for time-series features.

    Used by the Virtual Sensor Engine to build historical features
    (rolling averages, same-hour-yesterday, etc.).

    Args:
        latitude: Location latitude
        longitude: Location longitude
        hours: Number of past hours to fetch (default 48)
        timeout: Request timeout in seconds

    Returns:
        List of hourly US AQI values, oldest first. Empty list on failure.
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds

    from datetime import datetime, timedelta
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    days_needed = (hours // 24) + 2  # Extra day for safety
    start_date = (datetime.utcnow() - timedelta(days=days_needed)).strftime("%Y-%m-%d")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "us_aqi,pm2_5",
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        aqi_values = hourly.get("us_aqi", [])

        # Filter out None values and convert to floats
        result = [float(v) for v in aqi_values if v is not None]

        # Return last N hours
        return result[-hours:] if len(result) > hours else result

    except requests.RequestException as e:
        logger.error("Failed to fetch hourly AQI: %s", e)
        return []


def _default_aqi_response() -> dict:
    """Fallback response when API returns no data."""
    return {
        "us_aqi": 0.0,
        "pm10": 0.0,
        "pm2_5": 0.0,
        "carbon_monoxide": 0.0,
        "nitrogen_dioxide": 0.0,
        "sulphur_dioxide": 0.0,
        "ozone": 0.0,
        "dust": 0.0,
    }
