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
