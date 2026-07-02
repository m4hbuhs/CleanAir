"""
Municipal Alert Engine for the Virtual Sensor Network.

Evaluates pollution conditions against configurable thresholds and
generates structured alerts for municipal officers when:
- Estimated AQI exceeds the alert threshold AND
- Citizen complaint count exceeds the complaint threshold AND
- Prediction confidence exceeds the confidence threshold

Each alert includes a type classification, reasons, and actionable
suggested responses mapped from the dominant pollution type.
"""

import logging
import uuid
from typing import List, Optional

from backend.config import get_settings
from backend.models.schemas import (
    CitizenReport,
    GeminiPollutionFeatures,
    MunicipalAlert,
)
from backend.utils.geo_utils import haversine_km

logger = logging.getLogger(__name__)


# ── Action mappings by pollution type ──────────

_SUGGESTED_ACTIONS = {
    "Construction Dust": [
        "Inspect construction site for dust control compliance",
        "Deploy water mist cannons",
        "Issue notice to site contractor",
        "Notify local municipal officer",
    ],
    "Garbage Burning": [
        "Deploy fire unit to extinguish burning",
        "Issue fine under Solid Waste Management Rules",
        "Notify local sanitation department",
        "Deploy mobile monitoring unit",
    ],
    "Industrial Smoke": [
        "Inspect factory emission controls",
        "Verify Pollution Under Control certificate",
        "Issue CPCB violation notice",
        "Deploy air quality monitoring van",
    ],
    "Vehicle Exhaust": [
        "Activate traffic diversion plan",
        "Deploy traffic police for congestion control",
        "Activate water sprinkler systems on roads",
        "Issue public advisory for alternate routes",
    ],
    "Smoke": [
        "Identify and locate smoke source",
        "Deploy fire department for assessment",
        "Issue public health advisory",
        "Activate air purifier stations nearby",
    ],
    "Dust": [
        "Deploy mechanical road sweepers",
        "Activate water sprinkler systems",
        "Inspect for unpaved road sections",
        "Issue advisory to construction sites in area",
    ],
    "Fire": [
        "Deploy fire brigade immediately",
        "Evacuate nearby buildings if needed",
        "Set up perimeter safety zone",
        "Issue emergency public advisory",
    ],
}

_DEFAULT_ACTIONS = [
    "Deploy mobile monitoring unit to hotspot",
    "Issue public health advisory via SMS",
    "Notify local municipal officer",
    "Activate water sprinkler systems",
]


def evaluate_alerts(
    estimated_aqi: float,
    confidence_pct: int,
    citizen_reports: List[CitizenReport],
    gemini_features: Optional[GeminiPollutionFeatures] = None,
    latitude: float = 0.0,
    longitude: float = 0.0,
    radius_km: float = 1.0,
) -> List[MunicipalAlert]:
    """
    Evaluate current conditions and generate alerts if thresholds
    are exceeded.

    Logic:
        IF estimated_aqi > alert_aqi_threshold
        AND nearby_complaints >= alert_complaint_threshold
        AND confidence_pct > alert_confidence_threshold * 100
        THEN generate a MunicipalAlert

    Args:
        estimated_aqi: The Virtual Sensor Engine's estimated AQI.
        confidence_pct: Confidence percentage (0–100).
        citizen_reports: All active citizen reports in the system.
        gemini_features: Optional Gemini environmental features.
        latitude: Location latitude for the estimate.
        longitude: Location longitude for the estimate.
        radius_km: Radius to count nearby citizen complaints.

    Returns:
        List of MunicipalAlert objects (may be empty if no thresholds met).
    """
    settings = get_settings()
    alerts: List[MunicipalAlert] = []

    # Count nearby citizen reports
    nearby_count = sum(
        1 for r in citizen_reports
        if haversine_km(latitude, longitude, r.latitude, r.longitude) <= radius_km
    )

    # Check thresholds
    aqi_exceeded = estimated_aqi > settings.alert_aqi_threshold
    complaints_exceeded = nearby_count >= settings.alert_complaint_threshold
    confidence_ok = confidence_pct > int(settings.alert_confidence_threshold * 100)

    if not (aqi_exceeded and complaints_exceeded and confidence_ok):
        return alerts

    # Determine pollution type from Gemini features or nearby reports
    pollution_type = "Unknown"
    if gemini_features and gemini_features.pollution_type != "Unknown":
        pollution_type = gemini_features.pollution_type
    elif citizen_reports:
        # Find dominant type from nearby reports
        nearby_reports = [
            r for r in citizen_reports
            if haversine_km(latitude, longitude, r.latitude, r.longitude) <= radius_km
        ]
        if nearby_reports:
            type_counts: dict[str, int] = {}
            for r in nearby_reports:
                t = r.pollution_type.value
                type_counts[t] = type_counts.get(t, 0) + 1
            pollution_type = max(type_counts, key=type_counts.get) if type_counts else "Unknown"

    # Build reasons list
    reasons = _build_reasons(
        estimated_aqi, nearby_count, pollution_type, gemini_features
    )

    # Get suggested actions
    actions = _SUGGESTED_ACTIONS.get(pollution_type, _DEFAULT_ACTIONS)

    alert = MunicipalAlert(
        alert_id=str(uuid.uuid4())[:8],
        alert_type=f"Possible {pollution_type} Hotspot",
        estimated_aqi=round(estimated_aqi, 1),
        confidence_pct=confidence_pct,
        latitude=latitude,
        longitude=longitude,
        reasons=reasons,
        suggested_actions=actions[:4],  # Max 4 actions
        citizen_complaint_count=nearby_count,
        pollution_type=pollution_type,
    )
    alerts.append(alert)

    logger.info(
        "Municipal alert generated: %s (AQI=%.0f, confidence=%d%%, complaints=%d)",
        alert.alert_type, estimated_aqi, confidence_pct, nearby_count,
    )
    return alerts


def _build_reasons(
    estimated_aqi: float,
    complaint_count: int,
    pollution_type: str,
    gemini_features: Optional[GeminiPollutionFeatures],
) -> List[str]:
    """Build human-readable list of reasons for the alert."""
    reasons = []

    # AQI level
    if estimated_aqi > 300:
        reasons.append(f"Very Unhealthy AQI level ({estimated_aqi:.0f})")
    elif estimated_aqi > 200:
        reasons.append(f"Unhealthy AQI level ({estimated_aqi:.0f})")
    else:
        reasons.append(f"Elevated AQI level ({estimated_aqi:.0f})")

    # Complaints
    reasons.append(f"{complaint_count} citizen complaints in the area")

    # Pollution type specifics
    if pollution_type != "Unknown":
        reasons.append(f"Dominant pollution type: {pollution_type}")

    # Gemini-detected features
    if gemini_features:
        if gemini_features.dust_detected:
            reasons.append("High dust levels detected in citizen imagery")
        if gemini_features.smoke_detected:
            reasons.append("Smoke plumes detected in citizen imagery")
        if gemini_features.burning_detected:
            reasons.append("Active burning detected in citizen imagery")
        if gemini_features.construction_detected:
            reasons.append("Construction activity detected in citizen imagery")
        if gemini_features.visibility == "Very Low":
            reasons.append("Very low visibility reported")
        if gemini_features.road_activity in ("Heavy", "Gridlock"):
            reasons.append(f"{gemini_features.road_activity} traffic detected")

    return reasons
