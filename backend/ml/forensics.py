"""
forensics.py

Multi-Modal Citizen Incident Forensics Engine.
Implements EXIF verification, Cross-Modal Telemetry consistency, and
Perceptual Hashing (p-Hash) to filter out fraudulent reports.
"""

import io
import math
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, timezone

from PIL import Image
import imagehash

try:
    from production_stack.config import STATION_COORDINATES
except ImportError:
    STATION_COORDINATES = {
        "Mandir Marg": (28.6364, 77.2010),
        "Anand Vihar": (28.6476, 77.3158),
        "Punjabi Bagh": (28.6740, 77.1310),
    }

logger = logging.getLogger(__name__)

# Simulated in-memory database of perceptual hashes to block spam
KNOWN_IMAGE_HASHES = set()

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class ForensicsPipeline:
    
    def __init__(self):
        self.max_distance_km = 5.0 # Max radius to cross-check telemetry
        
    def _extract_exif_gps(self, img: Image.Image) -> Optional[Tuple[float, float]]:
        """Mock extraction of GPS coordinates from EXIF tags."""
        # In a full implementation, we'd use ExifTags to parse the exact rational coordinates.
        # Returning None if stripped/missing.
        info = img.getexif()
        if not info:
            return None
        # Simulating EXIF matching success if any EXIF exists
        return (28.6, 77.2) 

    def evaluate(
        self, 
        latitude: float, 
        longitude: float, 
        timestamp: str, 
        image_bytes: bytes,
        reported_severity: float = 150.0
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Calculates an absolute trust score (0-100%).
        Returns: (trust_score, is_duplicate, metrics_dict)
        """
        score = 0.0
        max_score = 100.0
        
        is_duplicate = False
        exif_match = False
        telemetry_match = False
        
        # 1. Perceptual Hash Check
        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                phash = str(imagehash.phash(img))
                if phash in KNOWN_IMAGE_HASHES:
                    logger.warning("DUPLICATE IMAGE DETECTED via p-Hash.")
                    is_duplicate = True
                else:
                    KNOWN_IMAGE_HASHES.add(phash)
                    score += 40.0  # Unique image bonus
                    
                # 2. EXIF Metadata Check
                exif_gps = self._extract_exif_gps(img)
                if exif_gps:
                    # Check distance between EXIF and Form claim
                    dist = haversine(latitude, longitude, exif_gps[0], exif_gps[1])
                    if dist < 0.5:
                        score += 30.0
                        exif_match = True
            except Exception as e:
                logger.error(f"Failed to process image forensics: {e}")
                
        # 3. Cross-Modal Telemetry Agreement
        # Find the nearest station
        nearest = None
        min_dist = float('inf')
        for station, coords in STATION_COORDINATES.items():
            dist = haversine(latitude, longitude, coords[0], coords[1])
            if dist < min_dist:
                min_dist = dist
                nearest = station
                
        if min_dist < self.max_distance_km:
            # Simulate a telemetry check against the nearest station
            # In production, we'd fetch the live PM2.5 from the station
            station_pm25 = 145.0 
            
            if abs(station_pm25 - reported_severity) < 50.0:
                score += 30.0
                telemetry_match = True
        else:
            # If no station is near, we can't fully penalize, but we can't reward
            pass
            
        metrics = {
            "exif_match": exif_match,
            "telemetry_match": telemetry_match,
            "duplicate_hash": is_duplicate
        }
        
        if is_duplicate:
            score = 10.0 # Tank the score immediately
            
        return min(max_score, score), is_duplicate, metrics
