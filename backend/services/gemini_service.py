"""
Gemini AI service for municipal report generation, chatbot, and complaint analysis.
Uses Gemini 2.5 Flash for all text generation tasks.
"""

import json
import logging
from typing import Optional, List

from google import genai

from backend.config import get_settings
from backend.models.schemas import (
    CitizenReport,
    HotspotCluster,
    MunicipalDispatch,
    PredictionResult,
)

logger = logging.getLogger(__name__)


def generate_municipal_dispatch(
    prediction: PredictionResult,
    report: Optional[CitizenReport] = None,
    weather_summary: Optional[str] = None,
    client: Optional[genai.Client] = None,
) -> MunicipalDispatch:
    """
    Generate an AI-powered municipal action brief using Gemini.

    Args:
        prediction: XGBoost prediction result with AQI estimate
        report: Optional citizen report that triggered this dispatch
        weather_summary: Current weather conditions text
        client: Pre-initialized Gemini client

    Returns:
        MunicipalDispatch with incident summary, cause analysis,
        recommended actions, and resource deployment instructions.
    """
    settings = get_settings()
    if client is None:
        client = genai.Client()

    report_context = ""
    if report:
        report_context = f"""
        CITIZEN INCIDENT REPORT:
        - Type: {report.pollution_type.value}
        - Severity: {report.severity.value}/5
        - Location: ({report.latitude:.4f}, {report.longitude:.4f})
        - Description: {report.description}
        - Status: {report.status.value}
        """

    prompt = f"""
    You are the AI Dispatch Coordinator for the 'CleanAir & Clear Streets' Municipal Response Platform.
    Generate an official operational dispatch brief based on this data.

    SYSTEM DATA:
    - Predicted Hyperlocal AQI: {prediction.estimated_aqi}
    - Risk Level: {prediction.risk_level}
    - Confidence: {prediction.confidence:.0%}
    - Category: {prediction.category_label}
    - Health Advisory: {prediction.health_advisory}
    {report_context}
    {f'WEATHER: {weather_summary}' if weather_summary else ''}

    Generate a response in this EXACT JSON format:
    {{
        "incident_summary": "(2-3 sentence executive summary)",
        "cause_analysis": "(Likely cause of pollution based on data)",
        "severity_assessment": "(Current severity and projected trajectory)",
        "recommended_actions": ["(action 1)", "(action 2)", "(action 3)"],
        "resource_deployment": ["(resource 1 with quantity)", "(resource 2 with quantity)"],
        "estimated_improvement": "(Estimated % improvement if actions are taken)"
    }}
    Output ONLY raw JSON. No markdown.
    """

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name, contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        parsed = json.loads(raw)
        return MunicipalDispatch(**parsed)

    except Exception as e:
        logger.error("Municipal dispatch generation failed: %s", e)
        return MunicipalDispatch(
            incident_summary=f"AQI alert: Predicted {prediction.estimated_aqi} ({prediction.risk_level} risk)",
            cause_analysis="Automated analysis unavailable. Manual review required.",
            severity_assessment=prediction.category_label,
            recommended_actions=["Deploy monitoring team", "Issue public advisory", "Contact local authority"],
            resource_deployment=["1 monitoring team", "1 mobile AQI unit"],
            estimated_improvement="15-25% with intervention",
        )


def generate_hotspot_report(
    clusters: List[HotspotCluster],
    client: Optional[genai.Client] = None,
) -> str:
    """Generate a comprehensive report for detected hotspot clusters."""
    settings = get_settings()
    if client is None:
        client = genai.Client()

    cluster_data = "\n".join([
        f"- Cluster {c.cluster_id}: {c.report_count} reports, "
        f"severity {c.avg_severity:.1f}/5, type: {c.dominant_pollution_type}, "
        f"radius: {c.radius_km:.1f}km at ({c.center_latitude:.4f}, {c.center_longitude:.4f})"
        for c in clusters
    ])

    prompt = f"""
    You are the AI Analyst for the CleanAir & Clear Streets platform.
    Analyze these detected pollution hotspot clusters and generate a municipal briefing.

    DETECTED HOTSPOTS:
    {cluster_data}

    Generate a comprehensive analysis covering:
    1. Overall situation assessment
    2. Priority ranking of hotspots
    3. Recommended response for each cluster
    4. Resource allocation strategy
    5. Expected timeline for resolution

    Write in a professional, actionable tone for municipal officers.
    """

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name, contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error("Hotspot report generation failed: %s", e)
        return f"Automated analysis unavailable. {len(clusters)} hotspots detected requiring manual review."


def chat_response(
    user_message: str,
    conversation_history: Optional[List[dict]] = None,
    context: Optional[str] = None,
    client: Optional[genai.Client] = None,
) -> str:
    """
    AI chatbot for citizens and municipal officers.
    Context-aware: knows current AQI, hotspots, and recent reports.

    Args:
        user_message: The user's question or message
        conversation_history: List of prior messages [{role, content}]
        context: Current system context (AQI, hotspots, etc.)
        client: Pre-initialized Gemini client

    Returns:
        AI-generated response text.
    """
    settings = get_settings()
    if client is None:
        client = genai.Client()

    system_context = context or "No current system data available."
    history_text = ""
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"\n{role.upper()}: {content}"

    prompt = f"""
    You are the AI Assistant for 'CleanAir & Clear Streets', an air quality monitoring platform
    for Indian cities. You help citizens understand air quality, report pollution, and get health advice.
    You help municipal officers manage incidents and allocate resources.

    CURRENT SYSTEM STATUS:
    {system_context}

    CONVERSATION HISTORY:
    {history_text}

    USER: {user_message}

    Respond helpfully, concisely, and accurately. If asked about AQI predictions, always clarify
    these are AI-estimated values from the Virtual Sensor Network, not official CPCB readings.
    Provide health advice based on the current AQI level.
    Answer in the same language as the user's message when possible.
    """

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name, contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error("Chat response failed: %s", e)
        return "I'm sorry, I'm having trouble connecting right now. Please try again in a moment."


def analyze_complaint(
    text: str,
    client: Optional[genai.Client] = None,
) -> dict:
    """
    Analyze a citizen text complaint for incident classification.
    Returns structured analysis suitable for report creation.
    """
    settings = get_settings()
    if client is None:
        client = genai.Client()

    prompt = f"""
    Analyze this citizen pollution complaint and extract structured data.

    Complaint: "{text}"

    Return a JSON object:
    {{
        "pollution_type": "(Smoke/Dust/Fire/Garbage Burning/Construction Pollution/Industrial Smoke/Vehicle Exhaust/Unknown)",
        "urgency": "(low/medium/high/critical)",
        "severity": (1-5 integer),
        "location_mentioned": "(any location mentioned, or 'not specified')",
        "health_impact_mentioned": (true/false),
        "summary": "(one-line summary)"
    }}
    Output ONLY raw JSON.
    """

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name, contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        return json.loads(raw)
    except Exception as e:
        logger.error("Complaint analysis failed: %s", e)
        return {
            "pollution_type": "Unknown",
            "urgency": "medium",
            "severity": 3,
            "location_mentioned": "not specified",
            "health_impact_mentioned": False,
            "summary": text[:100],
        }
