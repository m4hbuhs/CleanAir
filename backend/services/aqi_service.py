"""
AQI data ingestion service using the WAQI API (Station-Level Hyperlocal).
Replaces the deprecated Open-Meteo city-wide API to ensure strict spatial resolution.
"""

import logging
from typing import Optional
import requests
import numpy as np

from backend.config import get_settings

logger = logging.getLogger(__name__)

# WAQI Base URL for Geo-Feed
_BASE_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"

def fetch_current_aqi(
    latitude: float,
    longitude: float,
    timeout: Optional[int] = None,
) -> dict:
    """
    Fetch current station-level air quality data from WAQI.

    Returns:
        Dict with keys matching LiveInferencePayload AQI fields:
        {us_aqi, pm10, pm2_5, carbon_monoxide, nitrogen_dioxide,
         sulphur_dioxide, ozone, dust}
    """
    settings = get_settings()
    timeout = timeout or settings.api_timeout_seconds
    
    # In production, this would be an environment variable WAQI_TOKEN
    waqi_token = "demo"
    url = _BASE_URL.format(lat=latitude, lon=longitude)
    params = {"token": waqi_token}

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            logger.warning("WAQI AQI returned non-ok status for (%.4f, %.4f)", latitude, longitude)
            return _default_aqi_response()

        iaqi = data["data"].get("iaqi", {})
        
        return {
            "us_aqi": float(data["data"].get("aqi", 0.0)),
            "pm10": float(iaqi.get("pm10", {}).get("v", 0.0)),
            "pm2_5": float(iaqi.get("pm25", {}).get("v", 0.0)),
            "carbon_monoxide": float(iaqi.get("co", {}).get("v", 0.0)),
            "nitrogen_dioxide": float(iaqi.get("no2", {}).get("v", 0.0)),
            "sulphur_dioxide": float(iaqi.get("so2", {}).get("v", 0.0)),
            "ozone": float(iaqi.get("o3", {}).get("v", 0.0)),
            "dust": 0.0, # Not natively provided by standard WAQI
        }

    except requests.RequestException as e:
        logger.error("Failed to fetch AQI data: %s", e)
        # We must not raise here to prevent breaking the Virtual Sensor Engine fallback
        return _default_aqi_response()


def fetch_historical_aqi(
    latitude: float,
    longitude: float,
    days: int = 7,
    timeout: Optional[int] = None,
) -> list[dict]:
    """
    Simulates recent historical AQI (daily) based on station telemetry.
    (Raw historical WAQI requires an enterprise token).
    """
    from datetime import datetime, timedelta
    
    current_aqi_data = fetch_current_aqi(latitude, longitude, timeout)
    base_pm25 = current_aqi_data.get("pm2_5", 50.0)
    
    # Generate realistic simulated daily history
    np.random.seed(int(latitude * 1000) % (2**32))
    
    history = []
    now = datetime.utcnow()
    
    for i in range(days, 0, -1):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        simulated_pm25 = max(0.0, base_pm25 + np.random.normal(0, 10))
        history.append({"date": date_str, "pm2_5": simulated_pm25})
        
    return history


def fetch_hourly_aqi(
    latitude: float,
    longitude: float,
    hours: int = 48,
    timeout: Optional[int] = None,
) -> list[float]:
    """
    Simulates the last N hours of hourly US AQI values for time-series features.
    (Raw historical WAQI requires an enterprise token).
    """
    current_aqi_data = fetch_current_aqi(latitude, longitude, timeout)
    base_aqi = current_aqi_data.get("us_aqi", 100.0)
    
    # Generate realistic simulated hourly history
    np.random.seed(int(longitude * 1000) % (2**32))
    
    # Create noisy realistic trace ending near current base_aqi
    history = [max(0.0, base_aqi + np.random.normal(0, 15)) for _ in range(hours)]
    
    # Force the last element to closely match the current actual reading
    if history:
        history[-1] = base_aqi
        
    return history


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
