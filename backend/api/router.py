import logging
import os
import requests
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, status, Request
from pydantic import BaseModel
import pandas as pd
import numpy as np
from google.cloud import vision
from firebase_admin import firestore

from backend.config import get_aqi_category_for_pm25, STATION_COORDINATES, DISTRICT_STATION_MAP

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

def get_nearest_station(lat: float, lon: float) -> str:
    nearest = None
    min_dist = float('inf')
    for station, coords in STATION_COORDINATES.items():
        dist = (lat - coords[0])**2 + (lon - coords[1])**2
        if dist < min_dist:
            min_dist = dist
            nearest = station
    return nearest or "Unknown"

def get_district_for_station(station: str) -> str:
    for district, stations in DISTRICT_STATION_MAP.items():
        if station in stations:
            return district
    return "global"

def get_reverse_geocode(lat: float, lon: float) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_GEOCODING_API_KEY")
    result = {"street_name": "Unknown Street", "neighborhood": "Unknown"}
    if not api_key:
        logger.warning("GOOGLE_MAPS_GEOCODING_API_KEY not set. Skipping reverse geocoding.")
        return result
        
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            components = data["results"][0].get("address_components", [])
            for comp in components:
                types = comp.get("types", [])
                if "route" in types:
                    result["street_name"] = comp.get("long_name", "Unknown Street")
                if "neighborhood" in types or "sublocality" in types:
                    result["neighborhood"] = comp.get("long_name", "Unknown")
    except Exception as e:
        logger.error(f"Reverse geocoding failed for {lat}, {lon}: {e}")
        
    return result

class PredictRequest(BaseModel):
    lat: float
    lon: float

class PredictResponse(BaseModel):
    nearest_station: str
    current_pm25: float
    forecast_24h: list[float]
    forecast_categories: list[str]

from backend.ml.feature_engineering import payload_to_feature_matrix

@router.post("/predict", response_model=PredictResponse)
async def predict_aqi(req: PredictRequest, request: Request):
    try:
        models_dict = getattr(request.app.state, "models", {})
        if not models_dict:
            raise ValueError("No models loaded in application state.")
            
        nearest_station = get_nearest_station(req.lat, req.lon)
        district = get_district_for_station(nearest_station)
        
        # Fallback to global if district not loaded
        pipeline = models_dict.get(district) or models_dict.get("global")
        if not pipeline or not pipeline.get("models"):
            raise ValueError(f"No XGBoost pipeline found for district '{district}' or 'global'.")
            
        # Fetch 36-feature real-time data asynchronously
        df = await payload_to_feature_matrix(req.lat, req.lon)
        
        # 1. Automated Runtime Imputation Guard
        medians = pipeline.get("medians", {})
        for col in df.columns:
            if pd.isna(df[col].iloc[0]):
                fallback_val = medians.get(col, 0.0)
                logger.warning(f"NaN detected in live stream for {col}. Imputing {fallback_val}")
                df[col] = fallback_val

        current_input = df.to_numpy()
        
        if current_input.shape[1] != 36:
            raise ValueError(f"CRITICAL SHAPE MISMATCH: Expected (1, 36), got {current_input.shape}")

        forecast = []
        
        # 2. Execute the 24-hour forecasting using the autoregressive pipeline models
        for hour_model in pipeline["models"]:
            pred = float(hour_model.predict(current_input)[0])
            pred = max(0.0, pred)
            forecast.append(pred)
            
            # Autoregressive feedback loop: Append this hour's prediction as a new feature
            current_input = np.hstack([current_input, np.array([[pred]])])
            
        # Set current as the first prediction for simplicity
        current_pm25 = forecast[0] if forecast else 100.0
            
        categories = [get_aqi_category_for_pm25(val) for val in forecast]
        
        return PredictResponse(
            nearest_station=nearest_station,
            current_pm25=current_pm25,
            forecast_24h=forecast,
            forecast_categories=categories
        )
    except Exception as e:
        logger.error(f"Predict endpoint failed: {e}", exc_info=True)
        # Raise strict 500 error instead of silent fallback
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report-incident")
async def submit_report(
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    try:
        image_bytes = b""
        if image:
            image_bytes = await image.read()
            if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds 5MB")
        
        is_verified = False
        trust_score = 0.0
        
        if image_bytes:
            try:
                client = vision.ImageAnnotatorClient()
                vision_image = vision.Image(content=image_bytes)
                response = client.label_detection(image=vision_image)
                labels = response.label_annotations
                
                target_labels = {"smoke", "fire", "pollution", "dust", "haze", "smog"}
                for label in labels:
                    if label.description.lower() in target_labels and label.score > 0.75:
                        is_verified = True
                        if label.score > trust_score:
                            trust_score = label.score
            except Exception as e:
                logger.error(f"Cloud Vision API failed: {e}")
                
        station = get_nearest_station(latitude, longitude)
        geo_data = get_reverse_geocode(latitude, longitude)
        
        incident_record = {
            "latitude": latitude,
            "longitude": longitude,
            "street_name": geo_data["street_name"],
            "neighborhood": geo_data["neighborhood"],
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "verified": is_verified,
            "trust_score": trust_score,
            "station": station
        }
        
        try:
            db = firestore.client()
            db.collection("incidents").add(incident_record)
        except Exception as e:
            logger.error(f"Firestore save failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to save incident to database")

        return {
            "status": "Processed",
            "verified": is_verified,
            "trust_score": trust_score
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Ingestion crash: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal ingestion error")

@router.get("/reports")
async def get_reports():
    try:
        db = firestore.client()
        docs = db.collection("incidents").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Firestore fetch failed: {e}")
        return []
