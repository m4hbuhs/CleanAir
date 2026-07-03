"""
Google Earth Engine (GEE) Service.

Handles real satellite data extraction for hyperlocal pollution intelligence.
Connects to:
- Sentinel-2 (High-res multispectral for dust/construction)
- Sentinel-5P (NO2, CO, Aerosol Index for traffic/industrial smoke)
- FIRMS/MODIS (Thermal anomalies/active fires)
"""

import ee
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from google.oauth2 import service_account

from backend.models.schemas import SatelliteFeatures

logger = logging.getLogger(__name__)

class GEEService:
    def __init__(self):
        self.is_initialized = False
        self._initialize_ee()

    def _initialize_ee(self):
        """Initializes Google Earth Engine using Service Account or default credentials."""
        try:
            # Try service account first
            sa_path = os.getenv("EE_SERVICE_ACCOUNT_JSON")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "cleanair-hackathon")
            
            if sa_path and os.path.exists(sa_path):
                credentials = service_account.Credentials.from_service_account_file(sa_path)
                ee.Initialize(credentials, project=project_id)
                self.is_initialized = True
                logger.info("Successfully initialized GEE via Service Account.")
            else:
                # Fallback to default local auth
                logger.info("No Service Account found. Attempting default GEE initialization...")
                ee.Initialize(project=project_id)
                self.is_initialized = True
                logger.info("Successfully initialized GEE via default credentials.")
                
        except Exception as e:
            logger.error(
                "Failed to initialize Google Earth Engine. Real satellite data will be disabled. "
                "Run 'earthengine authenticate' locally or set EE_SERVICE_ACCOUNT_JSON. Error: %s", e
            )
            self.is_initialized = False

    def _get_bounding_box(self, lat: float, lon: float, buffer_m: float = 500) -> ee.Geometry:
        """Create a bounding box around a point with a specific buffer in meters."""
        point = ee.Geometry.Point([lon, lat])
        return point.buffer(buffer_m).bounds()

    def fetch_satellite_data(self, lat: float, lon: float) -> SatelliteFeatures:
        """
        Fetches multi-source satellite features for a specific location.
        Returns a structured SatelliteFeatures object.
        """
        if not self.is_initialized:
            logger.warning("GEE not initialized. Returning empty satellite features.")
            return SatelliteFeatures(source="uninitialized")

        try:
            roi = self._get_bounding_box(lat, lon, buffer_m=500)
            
            # Extract features from different datasets
            fire_data = self._check_thermal_anomalies(roi)
            aerosol_data = self._check_aerosols(roi)
            no2_data = self._check_no2(roi)
            
            # Build unified object
            return SatelliteFeatures(
                aerosol_optical_depth=aerosol_data.get("aerosol_index", 0.0),
                dust=aerosol_data.get("dust_estimate", 0.0),
                uv_index=aerosol_data.get("uv_index", 5.0), # Simplified
                land_surface_temp=fire_data.get("lst", 35.0), # Fallback to 35
                thermal_anomaly=fire_data.get("fire_detected", False),
                smoke_detected=aerosol_data.get("smoke_detected", False),
                no2_column_density=no2_data.get("no2", 0.0), # Need to add this to schema if needed
                source="google_earth_engine"
            )

        except Exception as e:
            logger.error("Error fetching GEE data for (%.4f, %.4f): %s", lat, lon, e)
            return SatelliteFeatures(source="gee_error")

    def _check_thermal_anomalies(self, roi: ee.Geometry) -> Dict[str, Any]:
        """Check NASA FIRMS for active fires in the last 48 hours."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=2)
        
        firms = ee.ImageCollection("FIRMS") \
            .filterBounds(roi) \
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        # Check if collection is empty
        count = firms.size().getInfo()
        if count == 0:
            return {"fire_detected": False, "lst": 30.0}
            
        # Get mean confidence
        latest = firms.mean().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=1000
        ).getInfo()
        
        confidence = latest.get("confidence", 0)
        return {
            "fire_detected": confidence > 50 if confidence else False,
            "lst": 45.0 if confidence and confidence > 50 else 30.0 # Heuristic if LST not fetched separately
        }

    def _check_aerosols(self, roi: ee.Geometry) -> Dict[str, Any]:
        """Check Sentinel-5P UV Aerosol Index for smoke/dust."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=2)
        
        s5p = ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_AER_AI") \
            .filterBounds(roi) \
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
            .select("absorbing_aerosol_index")
            
        count = s5p.size().getInfo()
        if count == 0:
            return {"aerosol_index": 0.0, "smoke_detected": False, "dust_estimate": 0.0}
            
        latest = s5p.mean().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=1113.2
        ).getInfo()
        
        aai = latest.get("absorbing_aerosol_index", 0.0) or 0.0
        
        return {
            "aerosol_index": aai,
            "smoke_detected": aai > 1.0,  # High AAI usually indicates smoke/dust
            "dust_estimate": max(0.0, aai * 10) # Simple scaling for now
        }
        
    def _check_no2(self, roi: ee.Geometry) -> Dict[str, Any]:
        """Check Sentinel-5P NO2 for vehicle/industrial emissions."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=2)
        
        s5p = ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2") \
            .filterBounds(roi) \
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
            .select("tropospheric_NO2_column_number_density")
            
        count = s5p.size().getInfo()
        if count == 0:
            return {"no2": 0.0}
            
        latest = s5p.mean().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=1113.2
        ).getInfo()
        
        return {
            "no2": latest.get("tropospheric_NO2_column_number_density", 0.0) or 0.0
        }

# Singleton instance
gee_service = GEEService()
