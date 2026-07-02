"""
Multi-factor confidence scoring for Virtual Sensor AQI estimates.

Computes a composite confidence score from five independent factors,
each weighted to reflect its importance in the overall estimate quality.

Factors and weights:
    Station distance   (30%) — Closer to AQI station = higher confidence
    Citizen reports    (20%) — More nearby reports = more corroboration
    Gemini confidence  (20%) — Vision model self-reported confidence
    Data freshness     (15%) — Stale data degrades reliability
    Missing features   (15%) — Incomplete inputs reduce accuracy
"""

import logging
from typing import Optional

from backend.models.schemas import ConfidenceBreakdown

logger = logging.getLogger(__name__)

# ── Weight configuration ──────────────────────
_WEIGHTS = {
    "station_distance": 0.30,
    "citizen_reports": 0.20,
    "gemini_confidence": 0.20,
    "data_freshness": 0.15,
    "missing_features": 0.15,
}


def compute_confidence(
    distance_to_station_km: float,
    citizen_report_count: int = 0,
    gemini_confidence: Optional[float] = None,
    data_freshness_minutes: float = 0.0,
    missing_feature_count: int = 0,
) -> ConfidenceBreakdown:
    """
    Compute a multi-factor confidence score for an AQI estimate.

    Args:
        distance_to_station_km: Distance from the estimate location
            to the nearest official AQI monitoring station.
        citizen_report_count: Number of citizen reports within 1 km
            of the estimate location.
        gemini_confidence: Gemini Vision's self-reported confidence
            (0.0–1.0). None if no image was analysed.
        data_freshness_minutes: Age of the most recent input data
            in minutes. 0 = completely fresh.
        missing_feature_count: Number of features that were unavailable
            and filled with defaults.

    Returns:
        ConfidenceBreakdown with per-factor scores, overall confidence,
        a human-readable label, and a 0–100% integer.
    """
    # 1. Station distance: 1.0 at 0 km, decays to ~0.2 at 10 km
    station_score = max(0.2, 1.0 / (1.0 + distance_to_station_km * 0.15))

    # 2. Citizen reports: base 0.3, +0.1 per report, capped at 1.0
    report_score = min(1.0, 0.3 + citizen_report_count * 0.1)

    # 3. Gemini confidence: direct pass-through, or 0.5 if no vision input
    gemini_score = gemini_confidence if gemini_confidence is not None else 0.5

    # 4. Data freshness: 1.0 if < 15 min, degrades linearly to 0.2 at 120 min
    if data_freshness_minutes <= 15.0:
        freshness_score = 1.0
    elif data_freshness_minutes >= 120.0:
        freshness_score = 0.2
    else:
        freshness_score = 1.0 - 0.8 * ((data_freshness_minutes - 15.0) / 105.0)

    # 5. Missing features: 1.0 if 0 missing, −0.15 per missing, floor 0.1
    missing_score = max(0.1, 1.0 - missing_feature_count * 0.15)

    # Weighted combination
    overall = (
        station_score * _WEIGHTS["station_distance"]
        + report_score * _WEIGHTS["citizen_reports"]
        + gemini_score * _WEIGHTS["gemini_confidence"]
        + freshness_score * _WEIGHTS["data_freshness"]
        + missing_score * _WEIGHTS["missing_features"]
    )
    overall = round(max(0.0, min(1.0, overall)), 2)

    # Label
    if overall >= 0.75:
        label = "High"
    elif overall >= 0.50:
        label = "Medium"
    else:
        label = "Low"

    return ConfidenceBreakdown(
        station_distance_score=round(station_score, 2),
        citizen_report_score=round(report_score, 2),
        gemini_confidence_score=round(gemini_score, 2),
        data_freshness_score=round(freshness_score, 2),
        missing_features_score=round(missing_score, 2),
        overall_confidence=overall,
        confidence_label=label,
        overall_pct=int(overall * 100),
    )
