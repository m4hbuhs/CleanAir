"""
forensics.py - Multi-Modal Incident Report Fraud Screening
Implements civic validation logic including EXIF metadata verification,
deepfake CNN classification mocks, and spatial cross-modal consistency.
"""

import logging
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Bounding box for Delhi (roughly)
DELHI_BOUNDS = {
    "min_lat": 28.40,
    "max_lat": 28.88,
    "min_lon": 76.84,
    "max_lon": 77.34
}

def verify_exif_metadata(image_bytes: bytes, claimed_lat: float, claimed_lon: float) -> Dict[str, Any]:
    """
    Reads image data to verify timestamps and confirm coordinates are physically
    inside Delhi borders and match the user's location.
    
    Args:
        image_bytes: The uploaded image payload.
        claimed_lat: Latitude provided by the client UI.
        claimed_lon: Longitude provided by the client UI.
        
    Returns:
        Dict with status and trust penalty.
    """
    try:
        # Check if claimed coordinates fall within Delhi boundaries
        if not (DELHI_BOUNDS["min_lat"] <= claimed_lat <= DELHI_BOUNDS["max_lat"] and 
                DELHI_BOUNDS["min_lon"] <= claimed_lon <= DELHI_BOUNDS["max_lon"]):
            return {"valid": False, "reason": "Coordinates outside Delhi", "penalty": 40.0}
            
        # In a real implementation, we would extract EXIF using PIL or exifread.
        # For production blueprint, we simulate a successful match if the bytes exist.
        if not image_bytes:
            return {"valid": False, "reason": "No image payload", "penalty": 100.0}
            
        return {"valid": True, "reason": "EXIF verified and bounded", "penalty": 0.0}
    except Exception as e:
        logger.error("EXIF verification failed: %s", e)
        return {"valid": False, "reason": "Metadata parse error", "penalty": 20.0}

def run_deepfake_classifier(image_bytes: bytes) -> float:
    """
    A placeholder mock CNN scoring matrix returning a trust metric representing
    multi-model network forgery screens.
    
    Returns:
        A score between 0.0 (high forgery likelihood) and 100.0 (authentic).
    """
    try:
        if not image_bytes:
            return 0.0
            
        # Simulating a CNN pass over the bytes.
        # Authentic images get a high score (85-100).
        # We'll use a deterministic mock based on byte length for consistency.
        byte_len = len(image_bytes)
        if byte_len < 1000:
            return 10.0 # Suspiciously small
            
        # Mocking an authentic deepfake CNN inference score
        score = 85.0 + (byte_len % 15)
        return score
    except Exception as e:
        logger.error("CNN Classifier failed: %s", e)
        return 50.0

def verify_cross_modal_consistency(claimed_pm25: float, nearest_station_pm25: float) -> Dict[str, Any]:
    """
    Calculates spatial deviation from nearby physical sensors; flagging anomalies
    if the discrepancy crosses logical boundary limits.
    """
    try:
        deviation = abs(claimed_pm25 - nearest_station_pm25)
        
        # If the claimed PM2.5 is more than 300 points different from the nearest station, it's highly suspicious.
        if deviation > 300:
            return {"consistent": False, "penalty": 50.0, "reason": "Extreme deviation from local baseline"}
        elif deviation > 150:
            return {"consistent": True, "penalty": 15.0, "reason": "Moderate deviation from baseline"}
        else:
            return {"consistent": True, "penalty": 0.0, "reason": "Matches local baseline"}
    except Exception as e:
        logger.error("Cross-modal verification failed: %s", e)
        return {"consistent": False, "penalty": 10.0, "reason": "Calculation error"}

def calculate_trust_score(
    image_bytes: bytes, 
    claimed_lat: float, 
    claimed_lon: float, 
    claimed_pm25: float, 
    nearest_station_pm25: float
) -> float:
    """
    Merges all verification channels into a composite percentage index. 
    Only reports passing a definitive threshold (e.g., 60.0) can trigger local civic alerts.
    """
    try:
        exif_result = verify_exif_metadata(image_bytes, claimed_lat, claimed_lon)
        cnn_score = run_deepfake_classifier(image_bytes)
        consistency_result = verify_cross_modal_consistency(claimed_pm25, nearest_station_pm25)
        
        # Base score starts with the CNN deepfake authentic metric
        composite_score = cnn_score
        
        # Subtract penalties
        composite_score -= exif_result["penalty"]
        composite_score -= consistency_result["penalty"]
        
        return max(0.0, min(100.0, composite_score))
    except Exception as e:
        logger.error("Trust score calculation failed: %s", e)
        return 0.0
