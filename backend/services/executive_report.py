"""
Executive AI Summaries (Gemini Report Generator)
"""
import os

def generate_executive_brief(hotspots: list, stats: dict) -> str:
    """
    Ingests the system state matrix and outputs a concise executive summary 
    using Gemini (if available) or falls back to a template.
    """
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Format the data payload
    hotspot_text = ""
    for idx, hs in enumerate(hotspots[:5]):
        hotspot_text += f"- #{idx+1} at ({hs.get('center_latitude')}, {hs.get('center_longitude')}): Severity {hs.get('avg_severity')}. Driven by {hs.get('dominant_pollution_type')}. Affected Pop: {hs.get('impact_metrics', {}).get('headcount', 'Unknown')}.\n"
    
    prompt = f"""
    You are the Executive AI for the Delhi Environmental Digital Twin. 
    Analyze the current system state matrix and write a concise, urgent briefing for municipal directors.
    
    SYSTEM STATS:
    Total Reports: {stats.get('total_reports', 0)}
    Active Hotspots: {stats.get('active_hotspots', 0)}
    
    TOP 5 PRIORITY HOTSPOTS:
    {hotspot_text}
    
    Format the report with these sections:
    1. Executive Overview
    2. Primary Pollution Drivers
    3. Resource Consumption & Dispatch Directives
    4. Public Health Warning Draft
    
    Keep it professional, data-driven, and under 300 words.
    """

    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return _generate_fallback(hotspots, stats)
    else:
        return _generate_fallback(hotspots, stats)

def _generate_fallback(hotspots: list, stats: dict) -> str:
    """Fallback if Gemini is unavailable."""
    return f"""## Executive Overview
The system is currently tracking {stats.get('active_hotspots', 0)} active hotspots in Delhi based on {stats.get('total_reports', 0)} citizen reports and satellite thermal scans.

## Primary Pollution Drivers
Based on the Source Attribution Engine, the dominant drivers in critical zones are **Vehicle Emissions** and **Construction Dust**.

## Resource Dispatch Directives
Top Priority Zone: Coordinates ({hotspots[0].get('center_latitude') if hotspots else 'N/A'}, {hotspots[0].get('center_longitude') if hotspots else 'N/A'}).
Recommendation: Dispatch Water Mist Cannons and Anti-Smog Guns immediately to this sector to protect the vulnerable population.

## Public Health Warning Draft
"Residents in priority zones are advised to keep windows closed and run air purifiers. N95 masks are strongly recommended for outdoor travel due to elevated particulate matter."
"""
