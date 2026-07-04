"""
backend.py - Production FastAPI Application Gateway
Exposes structured, type-validated endpoints for the CleanAir UI.
"""

import math
import logging
import base64
import pandas as pd
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from pydantic import BaseModel
from production_stack.config import STATION_COORDINATES, DISTRICT_STATION_MAP, get_aqi_category_for_pm25
from production_stack.predict import predict_next_24h
from production_stack.forensics import calculate_trust_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CleanAir & Clear Streets API", version="2.0")

# --- Pydantic Models ---

class PredictRequest(BaseModel):
    lat: float
    lon: float
    
class PredictResponse(BaseModel):
    nearest_station: str
    district: str
    current_pm25: float
    forecast_24h: List[float]
    forecast_categories: List[str]

class PrescriptiveActionResponse(BaseModel):
    hotspot_zones: List[str]
    allocations: List[dict]

# --- Helper Functions ---

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in kilometers between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_station(lat: float, lon: float) -> str:
    """Finds the nearest physical monitoring station from the config dict."""
    nearest = min(STATION_COORDINATES.items(), key=lambda x: haversine(lat, lon, x[1][0], x[1][1]))
    return nearest[0]

def get_district_for_station(station: str) -> str:
    """Map a station name to its administrative district."""
    for district, stations in DISTRICT_STATION_MAP.items():
        if station in stations:
            return district
    return "central" # Fallback

def fetch_simulated_cpcb_live_data(station: str) -> dict:
    """Simulates fetching real-time data from a CPCB API."""
    # In production, this would make an HTTP request to Open-Meteo or CPCB API
    return {
        "PM2.5 (µg/m³)": 145.0,
        "PM10 (µg/m³)": 250.0,
        "NO (µg/m³)": 25.0,
        "NO2 (µg/m³)": 40.0,
        "AT (°C)": 32.0,
        "RH (%)": 55.0,
        "WS (m/s)": 3.2,
        "Wind_U": 1.5,
        "Wind_V": -1.2,
        "Month": 7,
        "Hour": 12,
        "DayOfWeek": 3
    }

# --- API Endpoints ---

@app.post("/api/predict", response_model=PredictResponse)
def predict_aqi(req: PredictRequest):
    """
    Accepts user coordinates, finds nearest station, simulates CPCB payload,
    calls predict.py for the next 24 hours, and maps to AQI categories.
    """
    try:
        nearest_station = find_nearest_station(req.lat, req.lon)
        district = get_district_for_station(nearest_station)
        
        # 1. Fetch live features
        live_data = fetch_simulated_cpcb_live_data(nearest_station)
        
        # We wrap the dict into a single-row DataFrame for the predictor
        df_input = pd.DataFrame([live_data])
        
        # 2. Invoke vectorized XGBoost prediction
        forecast = predict_next_24h(df_input, district)
        
        # 3. Map to AQI Categories
        categories = [get_aqi_category_for_pm25(val) for val in forecast]
        
        return PredictResponse(
            nearest_station=nearest_station,
            district=district,
            current_pm25=live_data["PM2.5 (µg/m³)"],
            forecast_24h=forecast,
            forecast_categories=categories
        )
    except Exception as e:
        logger.error("Predict endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal prediction engine error")

@app.post("/api/report")
def submit_citizen_report(
    lat: float = Form(...),
    lon: float = Form(...),
    description: str = Form(...),
    claimed_pm25: float = Form(default=150.0), # Example metric client might infer
    image: UploadFile = File(None)
):
    """
    Accepts citizen photo updates and coordinates. Passes parameters directly
    to forensics.py to calculate a trust score.
    """
    try:
        image_bytes = b""
        if image:
            image_bytes = image.file.read()
            
        nearest_station = find_nearest_station(lat, lon)
        nearest_pm25 = fetch_simulated_cpcb_live_data(nearest_station)["PM2.5 (µg/m³)"]
        
        # Calculate fraud/trust score
        trust_score = calculate_trust_score(
            image_bytes=image_bytes,
            claimed_lat=lat,
            claimed_lon=lon,
            claimed_pm25=claimed_pm25,
            nearest_station_pm25=nearest_pm25
        )
        
        status = "REJECTED"
        if trust_score >= 60.0:
            status = "ACCEPTED"
            # In production: log to Database
            
        return {
            "status": status,
            "trust_score": trust_score,
            "message": "Report evaluated successfully."
        }
    except Exception as e:
        logger.error("Report submission failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Report validation failed")

@app.get("/api/prescriptive-action", response_model=PrescriptiveActionResponse)
def get_prescriptive_action():
    """
    Evaluates high-AQI hotspot zones and computes optimized resource allocation
    recommendations (e.g., anti-smog mist cannons).
    """
    # Mocking hotspot evaluations for blueprint
    return PrescriptiveActionResponse(
        hotspot_zones=["Anand Vihar (East)", "Okhla Phase-2 (South)"],
        allocations=[
            {
                "zone": "Anand Vihar (East)",
                "action": "Deploy Anti-Smog Mist Cannon",
                "urgency": "CRITICAL",
                "reason": "PM2.5 forecasted to exceed 250 µg/m³"
            },
            {
                "zone": "Okhla Phase-2 (South)",
                "action": "Dispatch Environmental Crew for Waste Burning Inspection",
                "urgency": "HIGH",
                "reason": "Thermal anomalies detected near industrial zone"
            }
        ]
    )
