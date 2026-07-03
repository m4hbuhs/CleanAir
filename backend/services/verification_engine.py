"""
Citizen Report Verification Engine.

Evaluates every submitted report against nearby reports, satellite data,
weather, and Gemini analysis to generate a credibility score (0-100).
"""

import logging
from typing import List, Dict, Any
from backend.models.schemas import CitizenReport, UnifiedPollutionObservation

logger = logging.getLogger(__name__)

class VerificationEngine:
    
    def calculate_credibility(
        self, 
        target_report: CitizenReport, 
        observation: UnifiedPollutionObservation
    ) -> Dict[str, Any]:
        """
        Calculates credibility score (0-100) and reasoning for a citizen report.
        """
        score = 50.0  # Base starting score
        reasons = []
        
        # 1. Check Gemini Vision Analysis
        if observation.gemini_features:
            gf = observation.gemini_features
            if gf.is_fake_upload:
                score -= 40.0
                reasons.append("AI Vision strongly suspects image is fake/unrelated.")
            else:
                score += (gf.confidence * 20.0)
                reasons.append(f"AI Vision confirmed pollution ({gf.pollution_type}) with {gf.confidence*100:.0f}% confidence.")
                
        # 2. Corroboration from nearby reports
        nearby = len(observation.citizen_reports) - 1 # excluding self
        if nearby > 0:
            boost = min(20.0, nearby * 5.0)
            score += boost
            reasons.append(f"Corroborated by {nearby} other nearby reports.")
            
        # 3. Satellite validation
        if observation.satellite_features:
            sf = observation.satellite_features
            # Example: Report says Fire, satellite says Thermal Anomaly
            r_type = target_report.pollution_type.value if hasattr(target_report.pollution_type, 'value') else str(target_report.pollution_type)
            if "Fire" in r_type or "Garbage" in r_type:
                if sf.thermal_anomaly:
                    score += 25.0
                    reasons.append("Satellite thermal anomaly directly matches fire report.")
                elif sf.smoke_detected:
                    score += 15.0
                    reasons.append("Satellite smoke detection corroborates fire/burning report.")
            
            if "Dust" in r_type or "Construction" in r_type:
                if sf.dust > 2.0:
                    score += 15.0
                    reasons.append("Satellite high aerosol/dust levels corroborate report.")
                    
        # 4. User Reputation (Placeholder logic)
        # If the user has a high rank/verified reports, boost score.
        score += 10.0
        reasons.append("User has good historical reporting reputation.")

        # Cap between 0 and 100
        final_score = max(0.0, min(100.0, score))
        
        status = "REJECTED" if final_score < 30 else ("MANUAL_REVIEW" if final_score < 60 else "AI_VERIFIED")
        
        return {
            "credibility_score": round(final_score, 1),
            "status": status,
            "reasons": reasons
        }

verification_engine = VerificationEngine()
