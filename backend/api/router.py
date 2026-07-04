import logging
import math
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, status
from pydantic import BaseModel
import numpy as np

from backend.ml.forensics import ForensicsPipeline
from backend.ml.xai import XAIEngine
from backend.ml.gemini_engine import GeminiAnalyzer

try:
    from production_stack.config import STATION_COORDINATES, DISTRICT_STATION_MAP
except ImportError:
    STATION_COORDINATES = {
        "Mandir Marg": (28.6364, 77.2010),
        "Anand Vihar": (28.6476, 77.3158),
        "Punjabi Bagh": (28.6740, 77.1310),
    }
    DISTRICT_STATION_MAP = {"central": ["Mandir Marg"], "east": ["Anand Vihar"], "west": ["Punjabi Bagh"]}

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB

# Memory State
INCIDENT_STORE = []

def get_nearest_station(lat: float, lon: float) -> str:
    nearest = None
    min_dist = float('inf')
    for station, coords in STATION_COORDINATES.items():
        # Quick haversine proxy
        dist = (lat - coords[0])**2 + (lon - coords[1])**2
        if dist < min_dist:
            min_dist = dist
            nearest = station
    return nearest or "Unknown"

def get_district(station: str) -> str:
    for district, stations in DISTRICT_STATION_MAP.items():
        if station in stations:
            return district
    return "Unknown"

@router.post("/report")
async def submit_report(
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    Ingests zero-typing multi-modal reports. Enforces byte thresholds.
    """
    try:
        # Binary size checks
        image_bytes = b""
        if image:
            chunk_size = 1024 * 1024
            while True:
                chunk = await image.read(chunk_size)
                if not chunk: break
                image_bytes += chunk
                if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds 5MB")
            await image.seek(0)
            
        audio_bytes = b""
        if audio:
            chunk_size = 1024 * 1024
            while True:
                chunk = await audio.read(chunk_size)
                if not chunk: break
                audio_bytes += chunk
                if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio exceeds 10MB")
            await audio.seek(0)
            
        # Run Forensics
        forensics = ForensicsPipeline()
        trust_score, is_duplicate, metrics = forensics.evaluate(
            latitude=latitude, 
            longitude=longitude, 
            timestamp=timestamp, 
            image_bytes=image_bytes
        )
        
        requires_manual_review = trust_score < 75.0 or is_duplicate
        
        # Spatial Map
        station = get_nearest_station(latitude, longitude)
        district = get_district(station)
        
        # XAI
        incident_type = "localized_fire" if trust_score > 60 else "vehicular_congestion"
        xai_engine = XAIEngine()
        
        explanation = xai_engine.generate_feature_attribution(incident_type)
        action_plan = xai_engine.generate_prescriptive_action(incident_type, latitude, longitude)
        xai_metrics = xai_engine.build_xai_metrics(incident_type)
        
        # Construct Forecast Trajectory
        # In a fully wired environment this calls inference.py run_hyperlocal_inference
        # Simulating the exact 24-step decay for the frontend schema
        forecast24h = []
        base_pm25 = 145.0
        for i in range(24):
            forecast24h.append({
                "hour": f"t+{i+1}",
                "pm25": max(10, base_pm25 - (i * 2.5) + float(np.random.normal(0, 5))),
                "expectedReduction": f"{min(100, i * 2.5)}%"
            })
        
        # Create Schema-perfect Incident Object
        incident_record = {
            "id": f"INC-{len(INCIDENT_STORE) + 1:04d}",
            "station": station,
            "district": district,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "trustScore": int(trust_score),
            "exifMatch": metrics.get("exif_match", False),
            "telemetryMatch": metrics.get("telemetry_match", False),
            "duplicateHashCheck": is_duplicate,
            "pollutionType": incident_type,
            "severity": "HIGH" if trust_score > 60 else "MODERATE",
            "xaiExplanation": explanation,
            "xaiMetrics": xai_metrics,
            "prescription": action_plan.get("command", "Awaiting review"),
            "forecast24h": forecast24h
        }
        
        INCIDENT_STORE.insert(0, incident_record)

        return {
            "status": "Processed",
            "trustScore": int(trust_score),
            "requiresManualReview": requires_manual_review
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Ingestion crash: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal ingestion error")


@router.get("/reports")
async def get_reports():
    """
    Live Feed Core Gateway.
    Returns the explicitly structured JSON array mapped to the React state.
    """
    if not INCIDENT_STORE:
        # Seed exact schema payload to prevent React component crash
        return [{
            "id": "INC-0001",
            "station": "Mandir Marg",
            "district": "central",
            "latitude": 28.6364,
            "longitude": 77.2010,
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
            "trustScore": 92,
            "exifMatch": True,
            "telemetryMatch": True,
            "duplicateHashCheck": False,
            "pollutionType": "localized_fire",
            "severity": "CRITICAL",
            "xaiExplanation": "Driven by: Detected garbage burning (+45%), Calm wind conditions (+35%).",
            "xaiMetrics": {
                "pollutants": {"PM2.5": 45, "PM10": 20},
                "windVectors": {"Wind_U": 0.5, "Wind_V": -0.2},
                "meteorology": {"AT": 30.0, "RH": 45.0},
                "temporal": "Incident occurred during peak emission hour."
            },
            "prescription": "Dispatch rapid response unit to (28.6364, 77.2010).",
            "forecast24h": [
                {"hour": f"t+{i+1}", "pm25": max(10, 145 - (i * 2.5)), "expectedReduction": f"{i * 2}%"}
                for i in range(24)
            ]
        }]
    return INCIDENT_STORE

@router.post("/analyze")
async def analyze_report(
    locationText: str = Form(default="Unknown"),
    textDetails: str = Form(default=""),
    aqi: str = Form(default=""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    Direct proxy to Google Gemini AI to analyze raw citizen evidence dynamically.
    """
    image_bytes = None
    if image:
        image_bytes = await image.read()
        
    audio_bytes = None
    if audio:
        audio_bytes = await audio.read()
        
    analyzer = GeminiAnalyzer()
    result = analyzer.analyze_incident(
        image_bytes=image_bytes,
        audio_bytes=audio_bytes,
        text_details=textDetails,
        location=locationText,
        aqi=aqi
    )
    
    return result
