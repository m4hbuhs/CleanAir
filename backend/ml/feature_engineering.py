"""
feature_engineering.py

Responsible for pulling live telemetry, computing rolling lags, and executing 
Wind Cartesian transformations to output a strict (1, 36) feature matrix.
"""

import math
import logging
from datetime import datetime
from typing import Dict, Any
import os

import pandas as pd
import numpy as np
import httpx
import redis.asyncio as redis

from backend.waqi_client import fetch_waqi_data
from backend.config import get_settings

logger = logging.getLogger(__name__)

# The strict 36-feature contract explicitly required by the District Models
REQUIRED_FEATURES = [
    "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "SO2", "CO", "Ozone", "Benzene", "Toluene",
    "AT", "RH", "TOT-RF", "SR", "BP", 
    "Wind_U", "Wind_V",
    "Month", "Hour", "DayOfWeek",
    "PM25_mean_24",
    "PM25_lag_1", "PM25_lag_2", "PM25_lag_3", "PM25_lag_4", "PM25_lag_5", "PM25_lag_6",
    "PM10_lag_1", "PM10_lag_2", "PM10_lag_3", "PM10_lag_4", "PM10_lag_5", "PM10_lag_6",
    "NO2_lag_1", "NO2_lag_2"
]

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client

def transform_wind_cartesian(ws: float, wd: float) -> tuple[float, float]:
    wd_rad = math.radians(wd)
    wind_u = ws * math.cos(wd_rad)
    wind_v = ws * math.sin(wd_rad)
    return wind_u, wind_v

async def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetch real-time weather including wind direction from OpenWeatherMap."""
    settings = get_settings()
    api_key = settings.openweathermap_api_key
    if not api_key:
        logger.warning("OPENWEATHERMAP_API_KEY not set. Falling back to default wind.")
        return {"wind_speed": 3.2, "wind_deg": 180.0}
        
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            wind = data.get("wind", {})
            return {
                "wind_speed": wind.get("speed", 3.2),
                "wind_deg": wind.get("deg", 180.0)
            }
    except Exception as e:
        logger.error(f"OWM API failed for {lat}, {lon}: {e}")
        return {"wind_speed": 3.2, "wind_deg": 180.0}

async def update_and_get_lags(station: str, current_pm25: float, current_pm10: float, current_no2: float) -> dict:
    """Uses Redis to maintain a 24-hour history window and extract specific lag features."""
    r = get_redis_client()
    
    key_pm25 = f"station:{station}:pm25"
    key_pm10 = f"station:{station}:pm10"
    key_no2 = f"station:{station}:no2"
    
    def safe_str(val):
        return str(val) if not np.isnan(val) else "NaN"
        
    def safe_float(val):
        if not val or val == "NaN":
            return np.nan
        try:
            return float(val)
        except:
            return np.nan

    try:
        # Append current values (left push)
        await r.lpush(key_pm25, safe_str(current_pm25))
        await r.lpush(key_pm10, safe_str(current_pm10))
        await r.lpush(key_no2, safe_str(current_no2))
        
        # Trim to last 24 items
        await r.ltrim(key_pm25, 0, 23)
        await r.ltrim(key_pm10, 0, 23)
        await r.ltrim(key_no2, 0, 23)
        
        # Fetch all items
        pm25_hist = [safe_float(x) for x in await r.lrange(key_pm25, 0, -1)]
        pm10_hist = [safe_float(x) for x in await r.lrange(key_pm10, 0, -1)]
        no2_hist = [safe_float(x) for x in await r.lrange(key_no2, 0, -1)]
    except Exception as e:
        logger.error(f"Redis operation failed: {e}. Returning NaN lags.")
        pm25_hist, pm10_hist, no2_hist = [], [], []
    
    # Pad to avoid index errors on lags 1..6
    pm25_hist += [np.nan] * max(0, 7 - len(pm25_hist))
    pm10_hist += [np.nan] * max(0, 7 - len(pm10_hist))
    no2_hist += [np.nan] * max(0, 3 - len(no2_hist))
    
    # PM25_mean_24 (ignoring NaNs)
    valid_pm25 = [x for x in pm25_hist if not np.isnan(x)]
    pm25_mean = sum(valid_pm25)/len(valid_pm25) if valid_pm25 else np.nan
    
    return {
        "PM25_mean_24": pm25_mean,
        "PM25_lag_1": pm25_hist[1], "PM25_lag_2": pm25_hist[2], "PM25_lag_3": pm25_hist[3], 
        "PM25_lag_4": pm25_hist[4], "PM25_lag_5": pm25_hist[5], "PM25_lag_6": pm25_hist[6],
        "PM10_lag_1": pm10_hist[1], "PM10_lag_2": pm10_hist[2], "PM10_lag_3": pm10_hist[3], 
        "PM10_lag_4": pm10_hist[4], "PM10_lag_5": pm10_hist[5], "PM10_lag_6": pm10_hist[6],
        "NO2_lag_1": no2_hist[1], "NO2_lag_2": no2_hist[2]
    }

async def payload_to_feature_matrix(lat: float, lon: float, station_name: str = "global") -> pd.DataFrame:
    try:
        real_data = await fetch_waqi_data(lat, lon)
        
        weather = await fetch_weather_data(lat, lon)
        ws = weather.get("wind_speed", 3.2)
        wd = weather.get("wind_deg", 180.0)
        
        wind_u, wind_v = transform_wind_cartesian(ws, wd)
        
        now = datetime.now()
        
        current_pm25 = real_data.get("current_pm25", np.nan)
        current_pm10 = real_data.get("pm10", np.nan)
        current_no2 = real_data.get("no2", np.nan)
        
        lags = await update_and_get_lags(station_name, current_pm25, current_pm10, current_no2)
        
        feature_dict = {
            "PM2.5": current_pm25,
            "PM10": current_pm10,
            "NO": np.nan,
            "NO2": current_no2,
            "NOx": np.nan,
            "NH3": np.nan,
            "SO2": real_data.get("so2", np.nan),
            "CO": real_data.get("co", np.nan),
            "Ozone": real_data.get("o3", np.nan),
            "Benzene": np.nan,
            "Toluene": np.nan,
            "AT": real_data.get("temperature", 32.5),
            "RH": real_data.get("humidity", 55.0),
            "TOT-RF": 0.0,
            "SR": 450.0,
            "BP": real_data.get("p", 1005.0),
            "Wind_U": wind_u,
            "Wind_V": wind_v,
            "Month": float(now.month),
            "Hour": float(now.hour),
            "DayOfWeek": float(now.weekday())
        }
        
        feature_dict.update(lags)
        
        row = []
        for feature in REQUIRED_FEATURES:
            row.append(feature_dict.get(feature, np.nan))
            
        df = pd.DataFrame([row], columns=REQUIRED_FEATURES)
        
        if df.shape != (1, 36):
            raise ValueError(f"Feature matrix generation failed. Expected shape (1, 36), got {df.shape}")
            
        return df
        
    except Exception as e:
        logger.error(f"Error building feature matrix for ({lat}, {lon}): {str(e)}", exc_info=True)
        return pd.DataFrame([[np.nan] * 36], columns=REQUIRED_FEATURES)
