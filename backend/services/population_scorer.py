"""
Population Impact Scorer (Mock OSM/Census spatial query engine)
"""

def get_population_impact(lat: float, lon: float, radius_km: float) -> dict:
    """
    Simulates a spatial query to OpenStreetMap or Census block data
    to count population and vulnerable assets within the hazard envelope.
    """
    # Deterministic mock based on coordinates to keep it consistent
    # For a real implementation, this would use PostGIS or an OSM API like Overpass
    
    # Rough estimate logic based on Delhi avg density (11,000 / km^2)
    area = 3.14159 * (radius_km ** 2)
    
    # Add some variation based on coordinates
    variation = (lat * lon) % 1.5 + 0.5 
    
    affected_headcount = int(area * 11000 * variation)
    schools = int((area * 2) * variation)
    hospitals = int((area * 0.5) * variation)
    
    return {
        "headcount": affected_headcount,
        "schools": schools,
        "hospitals": hospitals,
        "total_vulnerable_assets": schools + hospitals
    }
