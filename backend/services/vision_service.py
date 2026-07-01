"""
Vision classification service using Gemini 2.5 Flash multimodal.
Classifies citizen-uploaded images for pollution incidents.
"""

import json
import logging
from typing import Optional

from PIL import Image
from google import genai

from backend.config import get_settings
from backend.models.schemas import VisionClassification

logger = logging.getLogger(__name__)


def classify_pollution_image(
    image: Image.Image,
    text_context: Optional[str] = None,
    client: Optional[genai.Client] = None,
) -> VisionClassification:
    """
    Classify a citizen-uploaded image using Gemini multimodal analysis.

    Detects: Smoke, Dust, Fire, Garbage Burning, Construction Pollution,
    Industrial Smoke, Vehicle Exhaust.

    Args:
        image: PIL Image object from citizen upload
        text_context: Optional text description from citizen
        client: Pre-initialized Gemini client (for Streamlit caching)

    Returns:
        VisionClassification with pollution type, severity, confidence,
        and severity multiplier for the XGBoost fusion pipeline.
    """
    settings = get_settings()

    if client is None:
        client = genai.Client()

    contents = [
        _SYSTEM_PROMPT,
        image,
    ]

    if text_context:
        contents.append(f"Citizen's text report: {text_context}")

    contents.append(_EXTRACTION_PROMPT)

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name,
            contents=contents,
        )

        raw_text = response.text.strip()
        # Strip markdown code block markers if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

        parsed = json.loads(raw_text)

        return VisionClassification(
            pollution_type=parsed.get("pollution_type", "Unclassified"),
            severity=max(1, min(5, int(parsed.get("severity", 3)))),
            confidence=max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
            severity_multiplier=max(1.0, min(1.5, float(parsed.get("severity_multiplier", 1.1)))),
            description=parsed.get("description", ""),
            is_fake_upload=bool(parsed.get("is_fake_upload", False)),
            bounding_box_description=parsed.get("bounding_box_description", ""),
        )

    except json.JSONDecodeError as e:
        logger.warning("Gemini returned non-JSON vision response: %s", e)
        return VisionClassification(
            pollution_type="Unclassified Anomaly",
            severity=3,
            confidence=0.3,
            severity_multiplier=1.1,
            description="Unable to parse AI classification. Manual review recommended.",
            is_fake_upload=False,
        )
    except Exception as e:
        logger.error("Vision classification failed: %s", e)
        return VisionClassification(
            pollution_type="Error",
            severity=1,
            confidence=0.0,
            severity_multiplier=1.0,
            description=f"Classification error: {str(e)}",
        )


def classify_text_only(
    description: str,
    client: Optional[genai.Client] = None,
) -> VisionClassification:
    """
    Classify a text-only citizen complaint using Gemini.
    Used when no image is uploaded.
    """
    settings = get_settings()
    if client is None:
        client = genai.Client()

    prompt = f"""
    You are an environmental pollution classifier for an Indian smart city platform.
    Analyze this citizen complaint and extract structured attributes.

    Citizen complaint: "{description}"

    {_EXTRACTION_PROMPT}
    """

    try:
        response = client.models.generate_content(
            model=settings.gemini_model_name,
            contents=prompt,
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

        parsed = json.loads(raw_text)

        return VisionClassification(
            pollution_type=parsed.get("pollution_type", "Unclassified"),
            severity=max(1, min(5, int(parsed.get("severity", 3)))),
            confidence=max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
            severity_multiplier=max(1.0, min(1.5, float(parsed.get("severity_multiplier", 1.1)))),
            description=parsed.get("description", ""),
            is_fake_upload=bool(parsed.get("is_fake_upload", False)),
        )

    except Exception as e:
        logger.error("Text classification failed: %s", e)
        return VisionClassification(
            pollution_type="Unclassified",
            severity=2,
            confidence=0.3,
            severity_multiplier=1.05,
            description=str(description)[:200],
        )


# ── Prompt templates ──────────────────────────

_SYSTEM_PROMPT = """You are a computer vision and environmental analysis agent for the 'CleanAir & Clear Streets' AI platform in India.
You analyze citizen-uploaded images and text reports to classify pollution incidents.

Your detection categories:
- Smoke (visible smoke plumes from any source)
- Dust (construction dust, road dust, agricultural)
- Fire (active flames, burning)
- Garbage Burning (trash fires, waste incineration)
- Construction Pollution (demolition dust, cement mixing)
- Industrial Smoke (factory emissions, chimney smoke)
- Vehicle Exhaust (dense traffic fumes)

If the image shows NO pollution or is clearly unrelated (selfie, food, etc.), mark is_fake_upload as true.
If the image is ambiguous, give a lower confidence score."""

_EXTRACTION_PROMPT = """Extract attributes into a raw minified JSON object with these exact keys:
{
  "pollution_type": "(string: one of Smoke, Dust, Fire, Garbage Burning, Construction Pollution, Industrial Smoke, Vehicle Exhaust, or Unclassified)",
  "severity": "(integer: 1=minimal, 2=low, 3=moderate, 4=high, 5=critical)",
  "confidence": "(float: 0.0 to 1.0, how confident you are in the classification)",
  "severity_multiplier": "(float: 1.0 to 1.5, how much to boost the AQI prediction. 1.0=no boost, 1.5=severe incident)",
  "description": "(string: brief description of what you see)",
  "is_fake_upload": "(boolean: true if image shows no pollution or is unrelated)",
  "bounding_box_description": "(string: where in the image the pollution is visible, e.g. 'center of frame, smoke rising from left')",
  "location_mentioned": "(string: extract the geographic location mentioned in the text and CLEAN/FORMAT it into a standard address with spaces, e.g., 'Uttam Nagar, New Delhi, India', or null if none)"
}
Output ONLY raw JSON. No markdown codeblocks. No explanation."""
