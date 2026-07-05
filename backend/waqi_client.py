import requests
import logging
import math
from typing import Dict, Any

logger = logging.getLogger(__name__)

import asyncio

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in kilometers between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

import os
import numpy as np

async def fetch_waqi_data(lat: float, lon: float) -> Dict[str, float]:
    """
    Fetches real-time environmental data from WAQI API.
    Returns temperature, humidity, wind_speed, and pollutants.
    """
    token = os.getenv("WAQI_API_TOKEN")
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    
    try:
        resp = await asyncio.to_thread(requests.get, url, timeout=5)
        resp.raise_for_status()
        json_data = resp.json()
        
        iaqi = json_data.get("data", {}).get("iaqi", {})
        
        # Safely extract with strict fallbacks for weather, NaN for pollutants (triggers median imputation)
        return {
            "temperature": float(iaqi.get("t", {}).get("v", 27.0)),
            "humidity": float(iaqi.get("h", {}).get("v", 60.0)),
            "wind_speed": float(iaqi.get("w", {}).get("v", 3.5)),
            "current_pm25": float(iaqi.get("pm25", {}).get("v", np.nan)),
            "pm10": float(iaqi.get("pm10", {}).get("v", np.nan)),
            "no2": float(iaqi.get("no2", {}).get("v", np.nan)),
            "so2": float(iaqi.get("so2", {}).get("v", np.nan)),
            "co": float(iaqi.get("co", {}).get("v", np.nan)),
            "o3": float(iaqi.get("o3", {}).get("v", np.nan)),
            "p": float(iaqi.get("p", {}).get("v", 1005.0))
        }
    except Exception as e:
        logger.error(f"WAQI fetch failed for {lat}, {lon}: {e}", exc_info=True)
        # Fallbacks so XGBoost doesn't crash
        return {
            "temperature": 27.0,
            "humidity": 60.0,
            "wind_speed": 3.5,
            "p": 1005.0,
            "current_pm25": np.nan,
            "pm10": np.nan,
            "no2": np.nan,
            "so2": np.nan,
            "co": np.nan,
            "o3": np.nan
        }
