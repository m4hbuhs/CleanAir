"""
AQI category classification utilities.
Maps numeric AQI values to US EPA standard categories with health advisories.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AQICategory:
    """Immutable AQI category with health guidance."""
    label: str
    color: str          # Hex color for UI rendering
    emoji: str
    risk_level: str     # Low / Moderate / High / Very High / Severe / Emergency
    health_advisory: str
    css_class: str


# US EPA AQI Breakpoints → Category mapping
_AQI_CATEGORIES: list[Tuple[int, AQICategory]] = [
    (50, AQICategory(
        label="Good",
        color="#00E400",
        emoji="🟢",
        risk_level="Low",
        health_advisory="Air quality is satisfactory. No health risk.",
        css_class="aqi-good",
    )),
    (100, AQICategory(
        label="Moderate",
        color="#FFFF00",
        emoji="🟡",
        risk_level="Moderate",
        health_advisory="Acceptable quality. Sensitive individuals may experience minor issues.",
        css_class="aqi-moderate",
    )),
    (150, AQICategory(
        label="Unhealthy for Sensitive Groups",
        color="#FF7E00",
        emoji="🟠",
        risk_level="High",
        health_advisory="Sensitive groups (children, elderly, respiratory conditions) should limit outdoor exertion.",
        css_class="aqi-usg",
    )),
    (200, AQICategory(
        label="Unhealthy",
        color="#FF0000",
        emoji="🔴",
        risk_level="Very High",
        health_advisory="Everyone may begin to experience health effects. Sensitive groups at greater risk.",
        css_class="aqi-unhealthy",
    )),
    (300, AQICategory(
        label="Very Unhealthy",
        color="#8F3F97",
        emoji="🟣",
        risk_level="Severe",
        health_advisory="Health alert: everyone may experience serious health effects. Avoid outdoor activity.",
        css_class="aqi-very-unhealthy",
    )),
    (500, AQICategory(
        label="Hazardous",
        color="#7E0023",
        emoji="⚫",
        risk_level="Emergency",
        health_advisory="EMERGENCY: Entire population at risk. Stay indoors. Seal windows.",
        css_class="aqi-hazardous",
    )),
]


def classify_aqi(aqi_value: float) -> AQICategory:
    """
    Classify a numeric AQI value into a US EPA category.

    Args:
        aqi_value: Numeric AQI (0–500+)

    Returns:
        AQICategory with label, color, risk level, and health advisory.
    """
    clamped = max(0.0, aqi_value)
    for threshold, category in _AQI_CATEGORIES:
        if clamped <= threshold:
            return category
    # Beyond 500 → Hazardous
    return _AQI_CATEGORIES[-1][1]


def get_confidence_label(confidence: float) -> str:
    """Human-readable confidence label."""
    if confidence >= 0.90:
        return "Very High"
    elif confidence >= 0.75:
        return "High"
    elif confidence >= 0.60:
        return "Moderate"
    elif confidence >= 0.40:
        return "Low"
    else:
        return "Very Low"


def get_aqi_color_hex(aqi_value: float) -> str:
    """Returns hex color for a given AQI value for map rendering."""
    return classify_aqi(aqi_value).color


def get_aqi_risk_score(aqi_value: float) -> float:
    """
    Normalizes AQI to a 0.0–1.0 risk score for the reward engine and alerting.
    """
    return min(1.0, max(0.0, aqi_value / 500.0))
