"""
feature_engineering.py

Responsible for pulling live telemetry, computing rolling lags, and executing 
Wind Cartesian transformations to output a strict (1, 36) feature matrix.
"""

import math
import logging
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import numpy as np

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

def fetch_waqi_pollution_data(lat: float, lon: float) -> Dict[str, float]:
    """
    CRITICAL CONSTRAINT: Pulls pollutant features exclusively from station-level 
    WAQI or CPCB APIs. Open-Meteo is strictly banned for pollutants.
    """
    # Placeholder for actual WAQI API call.
    # In production, replace with `requests.get(f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}")`
    logger.info(f"Fetching WAQI live telemetry for coordinates ({lat}, {lon})")
    
    # Simulating the exact pollutant keys required
    return {
        "PM2.5": 145.0,
        "PM10": 210.0,
        "NO": 18.5,
        "NO2": 45.0,
        "NOx": 32.0,
        "NH3": 12.0,
        "SO2": 15.0,
        "CO": 1.2,
        "Ozone": 40.0,
        "Benzene": 2.1,
        "Toluene": 5.4,
        # Simulate lags returning from local cache/db query
        "PM25_mean_24": 150.0,
        "PM25_lag_1": 140.0, "PM25_lag_2": 138.0, "PM25_lag_3": 142.0, 
        "PM25_lag_4": 148.0, "PM25_lag_5": 155.0, "PM25_lag_6": 160.0,
        "PM10_lag_1": 200.0, "PM10_lag_2": 195.0, "PM10_lag_3": 205.0, 
        "PM10_lag_4": 215.0, "PM10_lag_5": 225.0, "PM10_lag_6": 230.0,
        "NO2_lag_1": 42.0, "NO2_lag_2": 40.0
    }

def fetch_openmeteo_weather_data(lat: float, lon: float) -> Dict[str, float]:
    """
    CRITICAL CONSTRAINT: Open-Meteo is strictly restricted to meteorological 
    variables ONLY (AT, RH, Rain, Solar Radiation, Pressure, Wind Speed, Wind Direction).
    """
    # Placeholder for actual Open-Meteo API call.
    logger.info(f"Fetching Open-Meteo weather data for coordinates ({lat}, {lon})")
    
    return {
        "AT": 32.5,
        "RH": 55.0,
        "TOT-RF": 0.0,
        "SR": 450.0,
        "BP": 1005.0,
        "WS": 3.2,     # Wind Speed in m/s
        "WD": 180.0    # Wind Direction in degrees (South)
    }

def transform_wind_cartesian(ws: float, wd: float) -> tuple[float, float]:
    """
    Eliminates angular discontinuities (359 -> 1) by mapping speed and direction 
    into linear U and V vectors.
    """
    # Convert degrees to radians
    wd_rad = math.radians(wd)
    wind_u = ws * math.cos(wd_rad)
    wind_v = ws * math.sin(wd_rad)
    return wind_u, wind_v

def build_historical_features(station_name: str, lat: float, lon: float) -> pd.DataFrame:
    """
    Legacy wrapper provided for backwards compatibility with the VirtualSensorEngine.
    Internally routes to payload_to_feature_matrix.
    """
    logger.warning(f"Using backwards compatible 'build_historical_features' for {station_name}")
    return payload_to_feature_matrix(lat, lon)

def payload_to_feature_matrix(lat: float, lon: float) -> pd.DataFrame:
    """
    Assembles the complete 36-feature pipeline. Merges WAQI pollutants with 
    Open-Meteo weather, applies Cartesian wind transformation, and extracts 
    cyclical time indicators.
    
    Returns:
        pd.DataFrame of shape (1, 36) containing the strictly ordered features.
    """
    try:
        # 1. Fetch exact isolated sources
        pollutants = fetch_waqi_pollution_data(lat, lon)
        weather = fetch_openmeteo_weather_data(lat, lon)
        
        # 2. Cartesian Wind Transformation
        wind_u, wind_v = transform_wind_cartesian(weather.get("WS", 0), weather.get("WD", 0))
        
        # 3. Cyclical Temporal Features (Omit Year and Day)
        now = datetime.now()
        
        feature_dict = {
            **pollutants,
            "AT": weather.get("AT", 25.0),
            "RH": weather.get("RH", 50.0),
            "TOT-RF": weather.get("TOT-RF", 0.0),
            "SR": weather.get("SR", 0.0),
            "BP": weather.get("BP", 1013.25),
            "Wind_U": wind_u,
            "Wind_V": wind_v,
            "Month": float(now.month),
            "Hour": float(now.hour),
            "DayOfWeek": float(now.weekday())
        }
        
        # 4. Strict Alignment to Model Expectations
        # Ensure we construct the DataFrame exactly in the order the XGBoost expects
        row = []
        for feature in REQUIRED_FEATURES:
            val = feature_dict.get(feature, np.nan)
            row.append(val)
            
        df = pd.DataFrame([row], columns=REQUIRED_FEATURES)
        
        if df.shape != (1, 36):
            raise ValueError(f"Feature matrix generation failed. Expected shape (1, 36), got {df.shape}")
            
        return df
        
    except Exception as e:
        logger.error(f"Error building feature matrix for ({lat}, {lon}): {str(e)}", exc_info=True)
        # Return empty matrix matching the schema to trigger robust NaN imputation downstream
        return pd.DataFrame([[np.nan] * 36], columns=REQUIRED_FEATURES)
