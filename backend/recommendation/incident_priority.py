"""
Incident Prioritization Engine
"""
from backend.services.population_scorer import get_population_impact

def rank_incidents(hotspots: list) -> list:
    """
    Rank all active hotspots and incidents dynamically using a composite formula: 
    Severity × Local Population Density × Count of Vulnerable Assets (Schools/Hospitals) × Prediction Confidence.
    """
    ranked = []
    for hs in hotspots:
        lat = hs.get("center_latitude", 28.6139)
        lon = hs.get("center_longitude", 77.2090)
        radius = hs.get("radius_km", 1.0)
        severity = hs.get("avg_severity", 3.0)
        confidence = hs.get("confidence_score", 0.8) # Mock confidence if missing
        
        impact = get_population_impact(lat, lon, radius)
        
        # Priority Score = Severity × (Population / 1000) × max(1, Assets) × Confidence
        pop_factor = max(1, impact["headcount"] / 1000)
        asset_factor = max(1, impact["total_vulnerable_assets"])
        
        priority_score = severity * pop_factor * asset_factor * confidence
        
        hs_copy = hs.copy()
        hs_copy["priority_score"] = priority_score
        hs_copy["impact_metrics"] = impact
        ranked.append(hs_copy)
        
    # Sort descending by priority score
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked
