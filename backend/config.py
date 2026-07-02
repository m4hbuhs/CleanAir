"""
Centralized configuration for CleanAir & Clear Streets AI platform.
Uses Pydantic BaseSettings for environment variable management with validation.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # --- API Keys ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")
    google_cloud_project: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")

    # --- Firebase ---
    firebase_credentials_path: Optional[str] = Field(
        default=None, alias="FIREBASE_CREDENTIALS_PATH"
    )
    firebase_project_id: str = Field(default="", alias="FIREBASE_PROJECT_ID")

    # --- Model Configuration ---
    xgboost_model_path: str = Field(
        default="cleanair_xgb_model.json", alias="XGBOOST_MODEL_PATH"
    )

    # --- Delhi Default Coordinates ---
    default_latitude: float = 28.6139
    default_longitude: float = 77.2090
    default_city: str = "Delhi"

    # --- Virtual Sensor Engine ---
    grid_resolution_meters: int = 500
    grid_radius_km: float = 5.0
    vision_severity_multiplier_min: float = 1.0
    vision_severity_multiplier_max: float = 1.5

    # --- DBSCAN Hotspot Detection ---
    dbscan_eps_km: float = 0.8
    dbscan_min_samples: int = 3

    # --- AQI Thresholds (US EPA standard) ---
    aqi_good: int = 50
    aqi_moderate: int = 100
    aqi_unhealthy_sensitive: int = 150
    aqi_unhealthy: int = 200
    aqi_very_unhealthy: int = 300
    aqi_hazardous: int = 500

    # --- EcoToken Rewards ---
    base_report_tokens: int = 10
    verified_report_bonus: int = 25
    high_severity_bonus: int = 15
    daily_cap_tokens: int = 200

    # --- Gemini Model ---
    gemini_model_name: str = "gemini-2.5-flash"

    # --- Speech-to-Text ---
    supported_languages: list[str] = [
        "hi-IN", "en-IN", "mr-IN", "gu-IN", "ta-IN", "te-IN", "kn-IN", "bn-IN"
    ]

    # --- Virtual Sensor Engine: Alert Thresholds ---
    alert_aqi_threshold: int = 150
    alert_complaint_threshold: int = 3
    alert_confidence_threshold: float = 0.60

    # --- Virtual Sensor Engine: Data Providers ---
    satellite_provider: str = "mock"  # "mock" | "earth_engine" | "cams"

    # --- Virtual Sensor Engine: Forecasting ---
    forecast_hours: int = 24

    # --- API Timeouts ---
    api_timeout_seconds: int = 10
    gemini_timeout_seconds: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# --- Singleton instance ---
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Returns cached Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# --- Project Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MODEL_DIR = PROJECT_ROOT
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
