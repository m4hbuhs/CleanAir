"""
Pollution Source Attribution Module.

Estimates the proportional contribution of various pollution sources
(e.g., Construction Dust, Vehicle Emissions, Biomass Burning) to a hotspot.
Combines XAI (SHAP) outputs, GEE Satellite data, and Citizen Reports.
"""

import logging
from typing import Dict, Any, List
from backend.models.schemas import UnifiedPollutionObservation

logger = logging.getLogger(__name__)

class AttributionEngine:
    def __init__(self):
        self.categories = [
            "Construction Dust",
            "Vehicle Emissions",
            "Biomass/Garbage Burning",
            "Industrial Smoke",
            "Natural/Background Dust",
            "Unknown"
        ]

    def estimate_contributions(
        self, 
        observation: UnifiedPollutionObservation, 
        shap_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimates the percentage contribution of each pollution source.
        """
        scores = {cat: 0.0 for cat in self.categories}
        
        # 1. Base weights from SHAP
        # Example mapping from feature names to categories
        for contrib in shap_analysis.get("top_contributors", []):
            feat = contrib["feature"]
            impact = contrib["absolute_impact"]
            
            if "pm10" in feat or "dust" in feat:
                scores["Construction Dust"] += impact * 0.5
                scores["Natural/Background Dust"] += impact * 0.5
            elif "no2" in feat or "co" in feat or "traffic" in feat:
                scores["Vehicle Emissions"] += impact
            elif "smoke" in feat or "thermal" in feat or "fire" in feat:
                scores["Biomass/Garbage Burning"] += impact
                
        # 2. Add Gemini Vision signals (high weight if confirmed visually)
        if observation.gemini_features:
            gf = observation.gemini_features
            if gf.construction_detected:
                scores["Construction Dust"] += 20.0
            if gf.vehicle_exhaust_detected or gf.road_activity in ["Heavy", "Gridlock"]:
                scores["Vehicle Emissions"] += 20.0
            if gf.smoke_detected or gf.burning_detected:
                scores["Biomass/Garbage Burning"] += 20.0
                
        # 3. Add GEE Satellite signals
        if observation.satellite_features:
            sf = observation.satellite_features
            if sf.thermal_anomaly or sf.smoke_detected:
                scores["Biomass/Garbage Burning"] += 25.0
                
        # 4. Add Citizen Report signals
        for report in observation.citizen_reports:
            r_type = report.pollution_type.value if hasattr(report.pollution_type, "value") else report.pollution_type
            if "Construction" in r_type:
                scores["Construction Dust"] += 10.0
            elif "Vehicle" in r_type or "Traffic" in r_type:
                scores["Vehicle Emissions"] += 10.0
            elif "Garbage" in r_type or "Fire" in r_type or "Smoke" in r_type:
                scores["Biomass/Garbage Burning"] += 10.0
            elif "Industrial" in r_type:
                scores["Industrial Smoke"] += 15.0

        # Normalize to 100%
        total = sum(scores.values())
        if total == 0:
            return {
                "dominant_source": "Unknown",
                "contributions": {cat: (100.0 if cat == "Unknown" else 0.0) for cat in self.categories},
                "confidence": 0.0
            }
            
        percentages = {k: round((v / total) * 100, 1) for k, v in scores.items()}
        
        # Find dominant
        dominant = max(percentages.items(), key=lambda x: x[1])
        
        # Calculate confidence based on alignment of multiple sources
        # (e.g. if >3 signal types contributed)
        # Simplified confidence for now
        confidence = min(100.0, dominant[1] + (len(observation.citizen_reports) * 5) + (10 if observation.satellite_features else 0))
        
        return {
            "dominant_source": dominant[0],
            "contributions": percentages,
            "confidence": round(confidence, 1)
        }

attribution_engine = AttributionEngine()
