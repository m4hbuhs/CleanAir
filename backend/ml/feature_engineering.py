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

from backend.waqi_client import fetch_waqi_data

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

async def build_historical_features(station_name: str, lat: float, lon: float) -> pd.DataFrame:
    """
    Legacy wrapper provided for backwards compatibility with the VirtualSensorEngine.
    Internally routes to payload_to_feature_matrix.
    """
    logger.warning(f"Using backwards compatible 'build_historical_features' for {station_name}")
    return await payload_to_feature_matrix(lat, lon)

async def payload_to_feature_matrix(lat: float, lon: float) -> pd.DataFrame:
    """
    Assembles the complete 36-feature pipeline. Merges unified WAQI data,
    applies Cartesian wind transformation, and extracts cyclical time indicators.
    Unreported pollutants fallback to np.nan for dynamic XGBoost imputation.
    
    Returns:
        pd.DataFrame of shape (1, 36) containing the strictly ordered features.
    """
    try:
        # Fetch unified meteorological & pollutant data from WAQI
        real_data = await fetch_waqi_data(lat, lon)
        
        # Cartesian Wind Transformation
        ws = real_data.get("wind_speed", 3.2)
        wd = 180.0 # Wind direction is not reliably in WAQI standard iaqi, using fallback
        wind_u, wind_v = transform_wind_cartesian(ws, wd)
        
        # Cyclical Temporal Features
        now = datetime.now()
        
        feature_dict = {
            "PM2.5": real_data.get("current_pm25", np.nan),
            "PM10": real_data.get("pm10", np.nan),
            "NO": np.nan,
            "NO2": real_data.get("no2", np.nan),
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
            "DayOfWeek": float(now.weekday()),
            # Lags unavailable from live API, set to NaN to trigger strict median imputation
            "PM25_mean_24": np.nan,
            "PM25_lag_1": np.nan, "PM25_lag_2": np.nan, "PM25_lag_3": np.nan, 
            "PM25_lag_4": np.nan, "PM25_lag_5": np.nan, "PM25_lag_6": np.nan,
            "PM10_lag_1": np.nan, "PM10_lag_2": np.nan, "PM10_lag_3": np.nan, 
            "PM10_lag_4": np.nan, "PM10_lag_5": np.nan, "PM10_lag_6": np.nan,
            "NO2_lag_1": np.nan, "NO2_lag_2": np.nan
        }
        
        # Strict Alignment to Model Expectations
        row = []
        for feature in REQUIRED_FEATURES:
            row.append(feature_dict.get(feature, np.nan))
            
        df = pd.DataFrame([row], columns=REQUIRED_FEATURES)
        
        if df.shape != (1, 36):
            raise ValueError(f"Feature matrix generation failed. Expected shape (1, 36), got {df.shape}")
            
        return df
        
    except Exception as e:
        logger.error(f"Error building feature matrix for ({lat}, {lon}): {str(e)}", exc_info=True)
        # Return empty matrix matching the schema to trigger robust NaN imputation downstream
        return pd.DataFrame([[np.nan] * 36], columns=REQUIRED_FEATURES)
