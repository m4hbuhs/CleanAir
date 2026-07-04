import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    pass

# Load from backend directory if that's where the user put it
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini API calls will fail.")
        
        try:
            self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        except NameError:
            logger.error("google-genai package not found. Please install it.")
            self.client = None

    def analyze_incident(self, image_bytes: Optional[bytes], audio_bytes: Optional[bytes], text_details: str, location: str, aqi: str = "") -> Dict[str, str]:
        """
        Sends the provided multimodal evidence to Gemini to generate a verified incident report.
        """
        if not self.client:
            # Fallback if no API key is provided, so the frontend doesn't hard-crash.
            return {
                "vision": f"[API KEY MISSING] Simulated vision response at {location}. Make sure GEMINI_API_KEY is in backend/.env",
                "speech": f"[API KEY MISSING] Simulated speech-to-text transcript." if audio_bytes else None,
                "aqiText": "Earth Engine integration requires ee authentication. Simulated AQI response."
            }

        # Real Gemini Call
        try:
            # Vision Analysis
            vision_text = "No visual evidence provided."
            if image_bytes:
                # Use gemini-1.5-flash for multimodal
                aqi_context = f"The current AQI in this area is {aqi}." if aqi else ""
                prompt = f"""
                Analyze this image of a reported environmental incident. 
                Location: {location}. Additional details: {text_details}. {aqi_context}
                
                Respond ONLY with a valid JSON object matching this schema exactly. Do not include markdown code blocks or conversational filler (e.g. no 'Here is your report').
                {{
                    "corrected_location": "Proper spelling of location",
                    "hazard_classification": "e.g., 'Severe Air Pollution'",
                    "confidence_score": 95,
                    "aqi_impact": {{ "aqi_estimate": "154", "category": "Unhealthy for Sensitive Groups" }},
                    "visibility_gauge": {{ "text": "Critically Low / Barely Visible", "percentage": 15 }},
                    "health_impacts": [
                        "Sensitive Groups Risk: Pre-existing respiratory / cardiovascular alerts.",
                        "Symptom Watch: Discomfort, coughing, and eye irritation (Children/Elderly)."
                    ],
                    "safety_risk": "Road Safety Hazard: Severely reduced visibility for traffic and pedestrians.",
                    "atmospheric_conditions": "Delhi Meteorological Inversion (Low Winds Trap)",
                    "drift_projections": [
                        "Current: AQI 154",
                        "Next 12h: AQI 151-200 (Unhealthy)",
                        "Next 24h: AQI 201-300 (Very Unhealthy)"
                    ],
                    "mcd_playbook": {{
                        "short_term": ["Public Health Advisory", "Construction Dust Freeze", "Waste Burning Ban"],
                        "medium_term": ["Mechanical Road Sweeping", "Water Sprinkling Deployment", "Transit Incentive"],
                        "long_term": ["Landfill Fire Mitigation", "Green Infrastructure Expansion", "Regional Inter-State Sync"]
                    }}
                }}
                """
                
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                        prompt
                    ]
                )
                
                import json
                try:
                    # Strip any potential markdown formatting (like ```json ... ```)
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    vision_text = json.loads(clean_text)
                except json.JSONDecodeError:
                    vision_text = {"corrected_location": location, "hazard_classification": "Unknown", "confidence_score": 0, "analysis": response.text}

            # Speech Analysis
            speech_text = None
            if audio_bytes:
                speech_prompt = "Transcribe this audio clip exactly. If it's noisy, transcribe the clearest spoken words."
                try:
                    audio_response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            types.Part.from_bytes(data=audio_bytes, mime_type='audio/mp3'),
                            speech_prompt
                        ]
                    )
                    speech_text = f"Transcript: \"{audio_response.text.strip()}\""
                except Exception as e:
                    logger.error(f"Speech transcription failed: {e}")
                    speech_text = "[Audio transcription failed]"

            return {
                "vision": vision_text,
                "speech": speech_text,
                "aqiText": "Earth Engine integration pending active service account. Gemini successfully verified multimodal payload."
            }
        except Exception as e:
            logger.error(f"Gemini API failure: {e}")
            return {
                "vision": f"AI Processing Error: {str(e)}",
                "speech": None,
                "aqiText": "Error connecting to Earth Engine."
            }
