"""
Pydantic models for all data contracts in the CleanAir platform.
Expanded from original schemas.py with full platform coverage.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class UserRole(str, Enum):
    CITIZEN = "citizen"
    OFFICER = "officer"
    ADMIN = "admin"


class PollutionType(str, Enum):
    SMOKE = "Smoke"
    DUST = "Dust"
    FIRE = "Fire"
    GARBAGE_BURNING = "Garbage Burning"
    CONSTRUCTION = "Construction Pollution"
    INDUSTRIAL = "Industrial Smoke"
    VEHICLE_EXHAUST = "Vehicle Exhaust"
    UNKNOWN = "Unknown"


class ReportStatus(str, Enum):
    PENDING = "pending"
    AI_VERIFIED = "ai_verified"
    OFFICER_VALIDATED = "officer_validated"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class IncidentSeverity(int, Enum):
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


# ─────────────────────────────────────────────
# Core Inference Payload (your trained model)
# ─────────────────────────────────────────────

class LiveInferencePayload(BaseModel):
    """
    Input payload matching the exact feature set of the trained XGBoost model.
    Validates all fields with domain-specific safety walls.
    """
    # Air Quality Inputs
    us_aqi: float
    pm10: float
    pm2_5: float
    carbon_monoxide: float
    nitrogen_dioxide: float
    sulphur_dioxide: float
    ozone: float
    dust: float = 0.0

    # Historical PM2.5 for rolling window feature
    pm2_5_yesterday_1: float
    pm2_5_yesterday_2: float

    # Real-time weather attributes
    tavg: float
    prcp: float
    wspd: float
    wdir: float

    @field_validator("wdir")
    @classmethod
    def check_wind_direction(cls, value: float) -> float:
        if not (0 <= value <= 360):
            raise ValueError(f"Wind direction must be 0–360°. Got {value}")
        return value

    @field_validator("us_aqi", "pm10", "pm2_5", "wspd", "prcp", "dust")
    @classmethod
    def ensure_positive(cls, value: float, info) -> float:
        if value < 0:
            raise ValueError(f"'{info.field_name}' cannot be negative ({value}).")
        return value


# ─────────────────────────────────────────────
# Prediction Output
# ─────────────────────────────────────────────

class PredictionResult(BaseModel):
    """Structured output from the XGBoost inference engine."""
    estimated_aqi: float
    risk_level: str
    confidence: float
    pm2_5_predicted: Optional[float] = None
    category_label: str = ""
    category_color: str = ""
    health_advisory: str = ""
    is_official: bool = False  # False = AI-estimated, True = from CPCB station
    disclaimer: str = (
        "This is an AI-estimated hyperlocal AQI from the Virtual Sensor Network. "
        "It does NOT replace official CPCB monitoring station readings."
    )


# ─────────────────────────────────────────────
# Citizen Report
# ─────────────────────────────────────────────

class CitizenReport(BaseModel):
    """A citizen-submitted pollution incident report."""
    report_id: str = ""
    user_id: str = "anonymous"
    latitude: float
    longitude: float
    pollution_type: PollutionType = PollutionType.UNKNOWN
    severity: IncidentSeverity = IncidentSeverity.MODERATE
    confidence: float = 0.0
    description: str = ""
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    transcription: Optional[str] = None
    status: ReportStatus = ReportStatus.PENDING
    tokens_awarded: int = 0
    is_fake: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────
# Vision Classification Result
# ─────────────────────────────────────────────

class VisionClassification(BaseModel):
    """Output from Gemini multimodal pollution image analysis."""
    pollution_type: str = Field(description="Detected pollution type")
    severity: int = Field(ge=1, le=5, description="1-5 severity scale")
    confidence: float = Field(ge=0.0, le=1.0)
    severity_multiplier: float = Field(ge=1.0, le=1.5, description="XGBoost AQI boost factor")
    description: str = Field(description="AI's reasoning/description")
    is_fake_upload: bool = Field(default=False, description="True if image doesn't show pollution")
    bounding_box_description: str = Field(default="", description="Where in the image it was found")
    location_mentioned: Optional[str] = Field(default=None, description="Any geographic location/landmark mentioned in the text")
    # Extended Gemini pollution features for the Virtual Sensor Engine
    gemini_pollution_features: Optional["GeminiPollutionFeatures"] = Field(
        default=None, description="Full environmental features extracted by Gemini"
    )


# ─────────────────────────────────────────────
# Hotspot Cluster
# ─────────────────────────────────────────────

class HotspotCluster(BaseModel):
    """A detected pollution hotspot from DBSCAN clustering."""
    cluster_id: int
    center_latitude: float
    center_longitude: float
    radius_km: float
    report_count: int
    avg_severity: float
    dominant_pollution_type: str
    estimated_affected_population: int = 0
    estimated_aqi: Optional[float] = None
    risk_level: str = "Unknown"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────
# EcoToken & Rewards
# ─────────────────────────────────────────────

class EcoTokenTransaction(BaseModel):
    """A single token transaction in a citizen's wallet."""
    transaction_id: str = ""
    user_id: str
    amount: int
    reason: str
    report_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CitizenWallet(BaseModel):
    """Citizen's EcoToken wallet."""
    user_id: str
    display_name: str = "Citizen"
    total_tokens: int = 0
    total_reports: int = 0
    verified_reports: int = 0
    rank: int = 0
    badges: List[str] = Field(default_factory=list)
    transactions: List[EcoTokenTransaction] = Field(default_factory=list)


class RewardItem(BaseModel):
    """A redeemable reward in the EcoToken marketplace."""
    reward_id: str
    name: str
    description: str
    cost_tokens: int
    category: str  # coupon, metro_card, certificate, voucher
    emoji: str = "🎁"
    available: bool = True


# ─────────────────────────────────────────────
# Polluter Violation Record
# ─────────────────────────────────────────────

class ViolationRecord(BaseModel):
    """Tracks repeated pollution violations at a location."""
    location_label: str
    latitude: float
    longitude: float
    violation_type: str
    occurrence_count: int = 1
    last_reported: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    report_ids: List[str] = Field(default_factory=list)
    status: str = "active"


# ─────────────────────────────────────────────
# Municipal Dispatch
# ─────────────────────────────────────────────

class MunicipalDispatch(BaseModel):
    """AI-generated municipal action brief."""
    incident_summary: str
    cause_analysis: str
    severity_assessment: str
    recommended_actions: List[str]
    resource_deployment: List[str]
    estimated_improvement: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────
# Virtual Sensor Grid Cell
# ─────────────────────────────────────────────

class GridCell(BaseModel):
    """A single cell in the Virtual Sensor Network grid."""
    latitude: float
    longitude: float
    estimated_aqi: float
    confidence: float
    nearest_station_distance_km: float
    citizen_report_count: int = 0
    vision_severity_boost: float = 0.0
    risk_level: str = ""
    color: str = "#00E400"


# ─────────────────────────────────────────────
# Gemini Pollution Feature Extraction Output
# ─────────────────────────────────────────────

class GeminiPollutionFeatures(BaseModel):
    """
    Structured environmental features extracted by Gemini Vision.

    Gemini NEVER outputs AQI. Instead, it extracts observable
    pollution indicators that become ML features for the
    Virtual Sensor Engine.
    """
    pollution_type: str = "Unknown"
    severity: str = "Moderate"  # "Low" | "Moderate" | "High" | "Critical"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: str = "Normal"  # "Clear" | "Normal" | "Low" | "Very Low"
    road_activity: str = "Normal"  # "None" | "Light" | "Normal" | "Heavy" | "Gridlock"
    construction_detected: bool = False
    smoke_detected: bool = False
    dust_detected: bool = False
    burning_detected: bool = False
    vehicle_exhaust_detected: bool = False
    description: str = ""
    is_fake_upload: bool = False
    bounding_box_description: str = ""
    location_mentioned: Optional[str] = None

    def to_numerical_scores(self) -> dict:
        """
        Convert qualitative Gemini observations into numerical
        feature scores (0.0–1.0) suitable for ML pipelines.
        """
        severity_map = {"Low": 0.2, "Moderate": 0.5, "High": 0.8, "Critical": 1.0}
        visibility_map = {"Clear": 0.0, "Normal": 0.2, "Low": 0.6, "Very Low": 1.0}
        road_map = {"None": 0.0, "Light": 0.2, "Normal": 0.4, "Heavy": 0.7, "Gridlock": 1.0}

        return {
            "dust_score": 1.0 if self.dust_detected else 0.0,
            "smoke_score": 1.0 if self.smoke_detected else 0.0,
            "construction_score": 1.0 if self.construction_detected else 0.0,
            "burning_score": 1.0 if self.burning_detected else 0.0,
            "vehicle_pollution_score": 1.0 if self.vehicle_exhaust_detected else 0.0,
            "severity_score": severity_map.get(self.severity, 0.5),
            "visibility_score": visibility_map.get(self.visibility, 0.2),
            "traffic_score": road_map.get(self.road_activity, 0.4),
        }

    def to_severity_multiplier(self) -> float:
        """
        Compute the legacy severity_multiplier (1.0–1.5) from the
        extracted features, for backward compatibility with existing
        XGBoost inference.
        """
        scores = self.to_numerical_scores()
        # Weighted average of key indicators
        raw = (
            scores["severity_score"] * 0.35
            + scores["smoke_score"] * 0.15
            + scores["dust_score"] * 0.15
            + scores["burning_score"] * 0.15
            + scores["construction_score"] * 0.10
            + scores["traffic_score"] * 0.10
        )
        # Map 0–1 to 1.0–1.5
        return round(1.0 + raw * 0.5, 2)


# ─────────────────────────────────────────────
# Satellite Features
# ─────────────────────────────────────────────

class SatelliteFeatures(BaseModel):
    """Satellite-derived environmental features."""
    aerosol_optical_depth: float = 0.0
    dust: float = 0.0
    uv_index: float = 0.0
    land_surface_temp: float = 0.0
    thermal_anomaly: bool = False
    smoke_detected: bool = False
    source: str = "mock"  # "mock" | "sentinel_2" | "modis" | "cams"


# ─────────────────────────────────────────────
# Historical Features
# ─────────────────────────────────────────────

class HistoricalFeatures(BaseModel):
    """Time-series features derived from AQI history."""
    previous_hour_aqi: float = 0.0
    previous_day_aqi: float = 0.0
    rolling_avg_3h: float = 0.0
    rolling_avg_24h: float = 0.0
    same_hour_yesterday: float = 0.0
    same_hour_last_week: float = 0.0
    month: int = 1
    weekday: int = 0
    hour: int = 12


# ─────────────────────────────────────────────
# Confidence Breakdown
# ─────────────────────────────────────────────

class ConfidenceBreakdown(BaseModel):
    """
    Multi-factor confidence assessment for an AQI estimate.

    Each component is scored 0.0–1.0, then combined with
    configurable weights to produce the overall confidence.
    """
    station_distance_score: float = 0.5
    citizen_report_score: float = 0.3
    gemini_confidence_score: float = 0.5
    data_freshness_score: float = 1.0
    missing_features_score: float = 1.0
    overall_confidence: float = 0.5
    confidence_label: str = "Medium"  # "High" | "Medium" | "Low"
    overall_pct: int = 50  # 0–100%


# ─────────────────────────────────────────────
# Hourly Forecast Point
# ─────────────────────────────────────────────

class HourlyForecastPoint(BaseModel):
    """A single point in the 24-hour AQI forecast."""
    hour_offset: int = 0  # 0 = current hour, 1 = +1h, ...
    estimated_aqi: float = 0.0
    confidence: float = 0.5
    weather_summary: str = ""


# ─────────────────────────────────────────────
# Virtual Sensor Result (Unified Engine Output)
# ─────────────────────────────────────────────

class VirtualSensorResult(BaseModel):
    """
    Unified output from the Virtual Sensor Engine.

    Contains the estimated AQI, official station AQI, confidence
    breakdown, 24-hour forecast, and all contributing features.
    This is the single object that the UI consumes for display.
    """
    estimated_aqi: float
    official_station_aqi: float
    risk_level: str = ""
    category_label: str = ""
    category_color: str = "#00E400"
    health_advisory: str = ""
    confidence: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    hourly_forecast: List[HourlyForecastPoint] = Field(default_factory=list)
    gemini_features: Optional[GeminiPollutionFeatures] = None
    satellite_features: Optional[SatelliteFeatures] = None
    historical_features: Optional[HistoricalFeatures] = None
    weather_summary: str = ""
    distance_to_station_km: float = 0.0
    citizen_report_count: int = 0
    is_official: bool = False
    disclaimer: str = (
        "This is an AI-estimated hyperlocal AQI from the Virtual Sensor Network. "
        "It combines official monitoring stations, historical pollution patterns, "
        "weather conditions, satellite observations, and citizen reports. "
        "It does NOT replace official CPCB monitoring station readings."
    )


# ─────────────────────────────────────────────
# Municipal Alert
# ─────────────────────────────────────────────

class MunicipalAlert(BaseModel):
    """An automated municipal alert generated when thresholds are breached."""
    alert_id: str = ""
    alert_type: str = "Pollution Hotspot"
    estimated_aqi: float = 0.0
    confidence_pct: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    citizen_complaint_count: int = 0
    pollution_type: str = "Unknown"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
