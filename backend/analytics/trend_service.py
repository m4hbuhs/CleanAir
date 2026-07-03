"""
Pollution Trend Service.

Determines whether pollution is increasing, stable, improving, 
or rapidly worsening by analyzing historical AQI values, virtual 
sensor predictions, and citizen report velocity.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

class TrendService:
    
    def analyze_trend(self, current_aqi: float, historical_aqis: List[float]) -> str:
        """
        Determines trend based on recent historical AQI data points.
        historical_aqis should be ordered from oldest to newest (e.g. [-3h, -2h, -1h])
        """
        if not historical_aqis or len(historical_aqis) < 2:
            return "Stable"
            
        recent_avg = sum(historical_aqis[-2:]) / 2.0
        older_avg = sum(historical_aqis[:-2]) / len(historical_aqis[:-2]) if len(historical_aqis) > 2 else historical_aqis[0]
        
        # Calculate rate of change over the window
        delta = current_aqi - recent_avg
        
        if delta > 30:
            return "Rapidly Worsening"
        elif delta > 10:
            return "Increasing"
        elif delta < -20:
            return "Improving"
        else:
            return "Stable"

trend_service = TrendService()
