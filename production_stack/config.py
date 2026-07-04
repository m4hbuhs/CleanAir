"""
config.py - Core Configurations & Spatial Lookup Maps
Contains configurations, administrative mappings, and station coordinates
for the CleanAir & Clear Streets production stack.
"""

from typing import Dict, Tuple

# Official CPCB Indian National AQI Linear Breakpoints for PM2.5 (µg/m³)
# Format: AQI Category -> (PM2.5 Min, PM2.5 Max)
CPCB_AQI_BREAKPOINTS = {
    "Good": (0, 30),
    "Satisfactory": (31, 60),
    "Moderate": (61, 90),
    "Poor": (91, 120),
    "Very Poor": (121, 250),
    "Severe": (251, 9999)
}

def get_aqi_category_for_pm25(pm25: float) -> str:
    """Map raw PM2.5 concentration to CPCB AQI Category."""
    for category, (min_val, max_val) in CPCB_AQI_BREAKPOINTS.items():
        if min_val <= pm25 <= max_val:
            return category
    return "Severe"

# 13 Delhi Administrative Districts and their physical monitoring stations
DISTRICT_STATION_MAP = {
    "central": ["Mandir Marg", "Pusa", "Sirifort", "Jawaharlal Nehru Stadium"],
    "central_north": ["IHBAS", "Shadipur", "DTU"],
    "east": ["Anand Vihar", "Patparganj", "Vivek Vihar"],
    "new_delhi": ["ITO", "Lodhi Road", "Major Dhyan Chand National Stadium", "Connaught Place"],
    "north": ["Alipur", "Narela", "Bawana", "Jehangirpuri", "Rohini"],
    "north_east": ["Sonia Vihar", "Karni Singh Shooting Range"],
    "north_west": ["Ashok Vihar", "Mundka", "Punjabi Bagh"],
    "old_delhi": ["Chandni Chowk", "North Campus"],
    "outer_north": ["Narela", "Satyawati College"],
    "south": ["Aurobindo Marg", "Okhla Phase-2", "Sri Aurobindo Marg", "RK Puram"],
    "south_east": ["Okhla Phase-2", "Nehru Nagar", "Dr. K.S. Shooting Range"],
    "south_west": ["Aya Nagar", "Dwarka-Sector 8", "IGI Airport", "Najafgarh"],
    "west": ["Mundka", "Najafgarh"]
}

# Coordinate dictionary for all 45 physical monitoring stations (Latitude, Longitude)
STATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    "Alipur": (28.8153, 77.1530),
    "Anand Vihar": (28.6476, 77.3158),
    "Ashok Vihar": (28.6954, 77.1817),
    "Aya Nagar": (28.4707, 77.1099),
    "Bawana": (28.7762, 77.0511),
    "Chandni Chowk": (28.6565, 77.2273),
    "Connaught Place": (28.6315, 77.2167),
    "Dr. K.S. Shooting Range": (28.4986, 77.2648),
    "DTU": (28.7501, 77.1177),
    "Dwarka-Sector 8": (28.5710, 77.0719),
    "IHBAS": (28.6812, 77.3025),
    "IGI Airport": (28.5562, 77.1000),
    "ITO": (28.6284, 77.2403),
    "Jawaharlal Nehru Stadium": (28.5828, 77.2344),
    "Jehangirpuri": (28.7328, 77.1706),
    "Karni Singh Shooting Range": (28.4986, 77.2648),
    "Lodhi Road": (28.5883, 77.2218),
    "Major Dhyan Chand National Stadium": (28.6112, 77.2372),
    "Mandir Marg": (28.6364, 77.2010),
    "Mundka": (28.6847, 77.0253),
    "Najafgarh": (28.6112, 76.9855),
    "Narela": (28.8228, 77.1019),
    "Nehru Nagar": (28.5679, 77.2505),
    "North Campus": (28.6866, 77.2078),
    "Okhla Phase-2": (28.5307, 77.2723),
    "Patparganj": (28.6238, 77.2872),
    "Punjabi Bagh": (28.6740, 77.1310),
    "Pusa": (28.6396, 77.1463),
    "RK Puram": (28.5632, 77.1869),
    "Rohini": (28.7325, 77.1199),
    "Satyawati College": (28.6921, 77.1798),
    "Shadipur": (28.6515, 77.1473),
    "Sirifort": (28.5504, 77.2159),
    "Sonia Vihar": (28.7105, 77.2495),
    "Sri Aurobindo Marg": (28.5313, 77.1901),
    "Vivek Vihar": (28.6723, 77.3153)
}
