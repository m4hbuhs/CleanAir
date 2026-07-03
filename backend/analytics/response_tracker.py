"""
Response Effectiveness Tracker.

Logs and analyzes municipal interventions (e.g. water spraying) to see if 
AQI actually improved after the action was taken.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResponseTracker:
    def __init__(self):
        # In a real app, this would be backed by Firestore
        self.intervention_logs = []

    def log_intervention(self, hotspot_id: str, action_taken: str, aqi_before: float) -> str:
        """Logs the start of a municipal intervention."""
        log_id = f"log_{len(self.intervention_logs) + 1}"
        entry = {
            "log_id": log_id,
            "hotspot_id": hotspot_id,
            "action_taken": action_taken,
            "aqi_before": aqi_before,
            "aqi_after": None,
            "timestamp_start": datetime.utcnow(),
            "timestamp_end": None,
            "effectiveness": "Pending"
        }
        self.intervention_logs.append(entry)
        return log_id

    def close_intervention(self, log_id: str, aqi_after: float) -> Dict[str, Any]:
        """Logs the end of an intervention and calculates effectiveness."""
        for log in self.intervention_logs:
            if log["log_id"] == log_id:
                log["aqi_after"] = aqi_after
                log["timestamp_end"] = datetime.utcnow()
                
                delta = log["aqi_before"] - aqi_after
                
                if delta > 50:
                    log["effectiveness"] = "Highly Effective"
                elif delta > 15:
                    log["effectiveness"] = "Effective"
                elif delta > 0:
                    log["effectiveness"] = "Marginally Effective"
                else:
                    log["effectiveness"] = "Ineffective"
                    
                return log
                
        return {"error": "Log ID not found."}
        
    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """Returns aggregate stats on which interventions work best."""
        if not self.intervention_logs:
            return {"message": "No interventions logged yet."}
            
        stats = {}
        for log in self.intervention_logs:
            if log["aqi_after"] is None:
                continue
                
            action = log["action_taken"]
            delta = log["aqi_before"] - log["aqi_after"]
            
            if action not in stats:
                stats[action] = {"count": 0, "total_aqi_reduction": 0}
                
            stats[action]["count"] += 1
            stats[action]["total_aqi_reduction"] += delta
            
        # Calculate averages
        for action, data in stats.items():
            data["avg_reduction"] = round(data["total_aqi_reduction"] / data["count"], 1)
            
        return stats

response_tracker = ResponseTracker()
