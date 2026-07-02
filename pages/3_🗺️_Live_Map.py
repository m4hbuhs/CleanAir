"""
🗺️ Live Map — Smart City GIS Dashboard
Professional Google Maps implementation using native components.html (Architecture A)
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path
from backend.config import get_settings

st.set_page_config(page_title="GIS Dashboard | CleanAir", page_icon="🗺️", layout="wide")

# Hide default Streamlit padding for full-screen map experience
st.markdown("""
<style>
    .block-container { padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem; max-width: 100%; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first to initialize the platform.")
    st.stop()

# Get Map Service
from backend.services.map_service import MapService
map_service = MapService()

# Ensure API Key is available directly from settings
settings = get_settings()
api_key = settings.google_maps_api_key

if not api_key:
    st.error("Google Maps API Key missing. Please check your .env file.")
    st.stop()

# ---------------------------------------------------------
# Prepare Data for Injection
# ---------------------------------------------------------
db = st.session_state.db
reports = db.get_all_reports()

from backend.services.hotspot_service import detect_hotspots
hotspots = detect_hotspots(reports) if reports else []
alerts = []

# Generate a city-wide grid for Delhi once, JS will handle lazy rendering via viewport
grid = map_service.generate_grid_for_bounds(
    north=28.9,
    south=28.3,
    east=77.5,
    west=76.8,
    resolution_meters=1000  # slightly lower resolution for full city static load
)

props = {
    "api_key": api_key,
    "stations": map_service.get_stations(),
    "reports": map_service.format_reports(reports),
    "hotspots": map_service.format_hotspots(hotspots),
    "alerts": map_service.format_alerts(alerts),
    "estimated_grid": grid
}

# Serialize to JSON safely
props_json = json.dumps(props)

# ---------------------------------------------------------
# Load and Inject HTML/JS/CSS Assets
# ---------------------------------------------------------
frontend_dir = Path(__file__).parent.parent / "frontend" / "google_maps"

def read_asset(filename):
    path = frontend_dir / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

html_template = read_asset("index.html")
css_content = read_asset("styles.css")
js_utils = read_asset("utils.js")
js_markers = read_asset("markers.js")
js_layers = read_asset("layers.js")
js_popups = read_asset("popups.js")
js_heatmap = read_asset("heatmap.js")
js_hotspots = read_asset("hotspots.js")
js_map = read_asset("map.js")

# Construct the final HTML string by injecting scripts and styles natively
final_html = html_template.replace(
    '<!-- INJECT_CSS -->', 
    f'<style>{css_content}</style>'
).replace(
    '<!-- INJECT_DATA -->',
    f'<script>window.MAP_DATA = {props_json};</script>'
).replace(
    '<!-- INJECT_JS -->',
    f"""
    <script>{js_utils}</script>
    <script>{js_popups}</script>
    <script>{js_markers}</script>
    <script>{js_layers}</script>
    <script>{js_heatmap}</script>
    <script>{js_hotspots}</script>
    <script>{js_map}</script>
    """
)

# Render the HTML using the official lightweight method
components.html(final_html, height=900, scrolling=False)
