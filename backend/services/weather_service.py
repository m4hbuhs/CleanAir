"""
Weather data ingestion service using the Open-Meteo Weather API.
Free, no API key required. Returns real-time meteorological data.
"""

import logging
from typing import Optional

import requests

from backend.config import get_settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_CURRENT_FIELDS = "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,relative_humidity_2m,apparent_temperature"


def fetch_current_weather(
    latitude: float,
    longitude: float,
    timeout: Optional[int] = None,
) -> dict:
    """
    Fetch current weather conditions from Open-Meteo.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        timeout: Request timeout in seconds

    Returns:
        Dict with weather fields needed for XGBoost:
        {temperature_2m, precipitation, wind_speed_10m, wind_direction_10m,
         relative_humidity_2m, apparent_temperature}
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
                "Open-Meteo Weather returned empty for (%.4f, %.4f)",
                latitude, longitude,
            )
            return _default_weather()

        return {
            "temperature_2m": float(current.get("temperature_2m", 30.0)),
            "precipitation": float(current.get("precipitation", 0.0)),
            "wind_speed_10m": float(current.get("wind_speed_10m", 5.0)),
            "wind_direction_10m": float(current.get("wind_direction_10m", 180.0)),
            "relative_humidity_2m": float(current.get("relative_humidity_2m", 50.0)),
            "apparent_temperature": float(current.get("apparent_temperature", 32.0)),
        }

    except requests.RequestException as e:
        logger.error("Failed to fetch weather data: %s", e)
        raise


def fetch_weather_forecast(
    latitude: float,
    longitude: float,
    days: int = 3,
    timeout: Optional[int] = None,
) -> list[dict]:
    """
    Fetch multi-day weather forecast for trend predictions.

    Returns:
        List of daily forecast dicts.
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_direction_10m_dominant",
        "forecast_days": days,
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])

        forecasts = []
        for i, date in enumerate(dates):
            forecasts.append({
                "date": date,
                "temp_max": daily.get("temperature_2m_max", [0])[i],
                "temp_min": daily.get("temperature_2m_min", [0])[i],
                "precipitation": daily.get("precipitation_sum", [0])[i],
                "wind_speed_max": daily.get("wind_speed_10m_max", [0])[i],
                "wind_direction": daily.get("wind_direction_10m_dominant", [0])[i],
            })
        return forecasts

    except requests.RequestException as e:
        logger.error("Failed to fetch weather forecast: %s", e)
        return []


def fetch_hourly_weather_forecast(
    latitude: float,
    longitude: float,
    hours: int = 24,
    timeout: Optional[int] = None,
) -> list[dict]:
    """
    Fetch hourly weather forecast for the next N hours.

    Used by the Virtual Sensor Engine for recursive hourly
    AQI forecasting. Returns weather conditions per hour.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        hours: Number of forecast hours (default 24)
        timeout: Request timeout in seconds

    Returns:
        List of hourly dicts with keys: temperature_2m, precipitation,
        wind_speed_10m, wind_direction_10m, relative_humidity_2m,
        surface_pressure, cloud_cover.
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,precipitation,wind_speed_10m,"
            "wind_direction_10m,relative_humidity_2m,"
            "surface_pressure,cloud_cover"
        ),
        "forecast_days": max(1, (hours // 24) + 1),
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])

        forecasts = []
        for i in range(min(len(times), hours)):
            forecasts.append({
                "time": times[i],
                "temperature_2m": _safe_float(hourly.get("temperature_2m", []), i, 30.0),
                "precipitation": _safe_float(hourly.get("precipitation", []), i, 0.0),
                "wind_speed_10m": _safe_float(hourly.get("wind_speed_10m", []), i, 5.0),
                "wind_direction_10m": _safe_float(hourly.get("wind_direction_10m", []), i, 180.0),
                "relative_humidity_2m": _safe_float(hourly.get("relative_humidity_2m", []), i, 50.0),
                "surface_pressure": _safe_float(hourly.get("surface_pressure", []), i, 1013.0),
                "cloud_cover": _safe_float(hourly.get("cloud_cover", []), i, 50.0),
            })

        return forecasts

    except requests.RequestException as e:
        logger.error("Failed to fetch hourly weather forecast: %s", e)
        return []


def _safe_float(values: list, index: int, default: float) -> float:
    """Safely extract a float from a list by index."""
    try:
        val = values[index]
        return float(val) if val is not None else default
    except (IndexError, TypeError):
        return default


def _default_weather() -> dict:
    """Fallback with typical Delhi values."""
    return {
        "temperature_2m": 32.0,
        "precipitation": 0.0,
        "wind_speed_10m": 5.0,
        "wind_direction_10m": 180.0,
        "relative_humidity_2m": 55.0,
        "apparent_temperature": 35.0,
    }
