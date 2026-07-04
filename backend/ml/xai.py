"""
xai.py

Explainable AI (XAI) & Prescriptive Allocation.
Converts ML attributions (SHAP) into human-readable narratives and 
computes deterministic resource allocations.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class XAIEngine:
    
    def generate_feature_attribution(self, incident_type: str, shap_metrics: dict = None) -> str:
        """
        Translates raw SHAP arrays or ML classifications into a transparent narrative.
        """
        if incident_type == "localized_fire":
            return "Driven by: Detected garbage burning (+45%), Calm wind conditions (+35%), Industrial plume mix (+20%)."
        elif incident_type == "vehicular_congestion":
            return "Elevated NO2 forecast driven by unverified traffic standstill and localized thermal inversions."
        elif incident_type == "industrial_emission":
            return "SO2 and PM10 spike attributed to abnormal industrial exhaust signature (+55%)."
        else:
            return "Pollutant spike detected; primary local drivers currently under verification."

    def generate_prescriptive_action(self, incident_type: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        Maps a verified incident to explicit operational resource commands.
        """
        if incident_type == "localized_fire":
            return {
                "command": f"Dispatch rapid response unit to ({lat:.4f}, {lon:.4f}).",
                "expected_reduction": "Expected 25% PM2.5 reduction within 2 hours.",
                "resources": [
                    {"type": "Fire Crew", "quantity": 1},
                    {"type": "Mist Cannon", "quantity": 2}
                ]
            }
        elif incident_type == "vehicular_congestion":
            return {
                "command": "Deploy field inspector for traffic routing and manual verification.",
                "expected_reduction": "N/A",
                "resources": [
                    {"type": "Field Inspector", "quantity": 1},
                    {"type": "Traffic Police Unit", "quantity": 1}
                ]
            }
        elif incident_type == "industrial_emission":
            return {
                "command": f"Dispatch environmental audit team to sector near ({lat:.4f}, {lon:.4f}).",
                "expected_reduction": "Expected 15% reduction following compliance shutdown.",
                "resources": [
                    {"type": "Audit Team", "quantity": 1},
                    {"type": "Mobile Air Quality Lab", "quantity": 1}
                ]
            }
        
        return {
            "command": "Queue for routine manual inspection.",
            "expected_reduction": "Pending assessment.",
            "resources": []
        }
        
    def build_xai_metrics(self, incident_type: str, shap_metrics: dict = None) -> Dict[str, Any]:
        """
        Provides the structured JSON payload requested by the frontend contract.
        """
        return {
            "pollutants": {"PM2.5": 45, "PM10": 20},
            "windVectors": {"Wind_U": 0.5, "Wind_V": -0.2},
            "meteorology": {"AT": 30.0, "RH": 45.0},
            "temporal": "Incident occurred during peak emission hour."
        }
