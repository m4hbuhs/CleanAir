import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta

# Import config for station coordinates
try:
    from production_stack.config import STATION_COORDINATES
except ImportError:
    # Fallback if config is missing during execution
    STATION_COORDINATES = {
        "Mandir Marg": (28.6364, 77.2010),
        "Anand Vihar": (28.6476, 77.3158),
        "Punjabi Bagh": (28.6740, 77.1310),
    }

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Hyperlocal Command Center",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STATE MANAGEMENT ---
if 'selected_incident' not in st.session_state:
    st.session_state.selected_incident = None

# --- MOCK DATA INJECTORS ---
def get_mock_forecasts():
    """Generates realistic mock forecasts for all stations."""
    data = []
    for station, coords in STATION_COORDINATES.items():
        # Add random noise to baseline 50 PM2.5
        current = max(10, min(300, 50 + np.random.normal(0, 40)))
        # Decay curve
        forecast = [max(10, current - (i * 2) + np.random.normal(0, 5)) for i in range(24)]
        data.append({
            "station": station,
            "lat": coords[0],
            "lon": coords[1],
            "current_pm25": current,
            "forecast_24h": forecast
        })
    return data

def get_mock_incidents():
    """Generates mock citizen reports."""
    return [
        {
            "id": "INC-001",
            "type": "localized_fire",
            "lat": 28.6400,
            "lon": 77.2100,
            "trust_score": 92.5,
            "exif_match": True,
            "telemetry_match": True,
            "explanation": "High PM2.5 forecast is driven by: Detected garbage burning (+45%), Calm wind velocity (+30%), and adjacent industrial plume (+25%).",
            "command": "Dispatch rapid response unit to (28.6400, 77.2100).",
            "expected_reduction": "Expected 25% PM2.5 reduction within 2 hours.",
            "resources": [{"type": "Fire Crew", "quantity": 1}, {"type": "Mist Cannon", "quantity": 2}],
            "timestamp": (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "id": "INC-002",
            "type": "vehicular_congestion",
            "lat": 28.6500,
            "lon": 77.3000,
            "trust_score": 60.0,
            "exif_match": False,
            "telemetry_match": False,
            "explanation": "Elevated NO2 forecast driven by unverified traffic standstill.",
            "command": "Deploy field inspector for manual verification.",
            "expected_reduction": "N/A",
            "resources": [{"type": "Field Inspector", "quantity": 1}],
            "timestamp": (datetime.now() - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M")
        }
    ]

# --- API DATA FETCHERS ---
def fetch_live_forecasts(mock_mode: bool):
    if mock_mode: return get_mock_forecasts()
    try:
        # Expected to point to the actual FastAPI endpoint
        resp = requests.get("http://localhost:8000/api/forecast/live", timeout=3)
        return resp.json()
    except:
        st.sidebar.error("Live API offline. Falling back to mock data.")
        return get_mock_forecasts()

def fetch_live_incidents(mock_mode: bool):
    if mock_mode: return get_mock_incidents()
    try:
        resp = requests.get("http://localhost:8000/api/incidents/recent", timeout=3)
        return resp.json()
    except:
        return get_mock_incidents()

# --- HELPER FUNCTIONS ---
def get_color(pm25):
    """Returns RGB color based on PM2.5 severity."""
    if pm25 < 50: return [0, 255, 0, 160]      # Green
    elif pm25 < 100: return [255, 255, 0, 160] # Yellow
    else: return [255, 0, 0, 160]              # Red

# --- MAIN LAYOUT ---
st.title("🌍 Hyperlocal Environmental Command Center")
st.markdown("Delhi Municipal Officer Dashboard | **Real-Time Forecasting & Incident Response**")

# Sidebar
st.sidebar.header("System Controls")
use_mock = st.sidebar.toggle("Use Mock API Streams", value=True)
st.sidebar.markdown("---")

# Fetch Data
forecasts = fetch_live_forecasts(use_mock)
incidents = fetch_live_incidents(use_mock)

# Split view: Feed on Left, Map/XAI on Right
col_feed, col_map = st.columns([1, 2.5])

# --- 1. MULTI-MODAL INCIDENT FEED ---
with col_feed:
    st.subheader("Live Incident Queue")
    
    # Trust Gate Tabs
    tab_verified, tab_manual = st.tabs(["High-Trust Alerts (≥75%)", "Manual Review (<75%)"])
    
    verified_incidents = [i for i in incidents if i.get("trust_score", 0) >= 75.0]
    manual_incidents = [i for i in incidents if i.get("trust_score", 0) < 75.0]
    
    def render_incident_card(inc):
        score = inc.get('trust_score', 0)
        color = "green" if score >= 75 else "orange" if score >= 50 else "red"
        
        with st.container(border=True):
            st.markdown(f"**{inc['id']}** - {inc['type'].replace('_', ' ').title()}")
            st.caption(f"Filed: {inc['timestamp']}")
            
            # Trust Score Progress Bar
            st.markdown(f"**Trust Score:** <span style='color:{color}'>{score}%</span>", unsafe_allow_html=True)
            st.progress(score / 100)
            
            # Forensic Badges
            exif_badge = "✅" if inc.get("exif_match") else "❌"
            tel_badge = "✅" if inc.get("telemetry_match") else "❌"
            st.markdown(f"<small>📷 EXIF: {exif_badge} | 📡 Telemetry: {tel_badge}</small>", unsafe_allow_html=True)
            
            if st.button(f"Investigate {inc['id']}", key=f"btn_{inc['id']}"):
                st.session_state.selected_incident = inc
                
    with tab_verified:
        if not verified_incidents: st.info("No active verified alerts.")
        for inc in verified_incidents: render_incident_card(inc)
            
    with tab_manual:
        if not manual_incidents: st.info("No incidents awaiting review.")
        for inc in manual_incidents: render_incident_card(inc)

# --- 2. INTERACTIVE GEOGRAPHIC MAP ---
with col_map:
    st.subheader("Spatial Pollution Topography")
    
    # Prepare Map Data
    df_stations = pd.DataFrame(forecasts)
    if not df_stations.empty:
        df_stations['color'] = df_stations['current_pm25'].apply(get_color)
    else:
        df_stations = pd.DataFrame(columns=["station", "lat", "lon", "current_pm25", "color"])
    
    df_incidents = pd.DataFrame(verified_incidents) # Only map verified hotspots
    
    # PyDeck Layers
    layers = []
    
    # Station Layer (Scatterplot)
    if not df_stations.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=df_stations,
                get_position='[lon, lat]',
                get_color='color',
                get_radius=1000, # 1km radius visual block
                pickable=True,
                auto_highlight=True,
                tooltip="station"
            )
        )
        
    # Incident Hotspot Layer (Pulsating Red Markers)
    if not df_incidents.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=df_incidents,
                get_position='[lon, lat]',
                get_color=[255, 0, 0, 255],
                get_radius=400, 
                pickable=True,
                line_width_min_pixels=2,
                stroked=True,
                filled=True,
            )
        )

    view_state = pdk.ViewState(
        latitude=28.6139, 
        longitude=77.2090, 
        zoom=10, 
        pitch=45
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/dark-v10',
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{station}\nPM2.5: {current_pm25}"}
    ))

    # --- 3. XAI NARRATIVE & PRESCRIPTIVE ACTION PANEL ---
    st.divider()
    if st.session_state.selected_incident:
        sel = st.session_state.selected_incident
        st.subheader(f"Incident Analysis: {sel['id']}")
        
        col_xai, col_action = st.columns(2)
        
        with col_xai:
            st.markdown("### 🧠 Explainable AI (SHAP) Narrative")
            st.info(sel['explanation'])
            
            st.markdown("### 📉 Expected Mitigation Decay (24h)")
            # Find closest station to this incident to graph its forecast
            closest = None
            min_dist = float('inf')
            for f in forecasts:
                dist = (f['lat'] - sel['lat'])**2 + (f['lon'] - sel['lon'])**2
                if dist < min_dist:
                    min_dist = dist
                    closest = f
            
            if closest and 'forecast_24h' in closest:
                # Plot the decay curve
                df_curve = pd.DataFrame({
                    "Hour": range(1, 25),
                    "Predicted PM2.5": closest['forecast_24h']
                })
                st.line_chart(df_curve.set_index("Hour"))
                
        with col_action:
            st.markdown("### 🚨 Prescriptive Action Command")
            st.success(f"**Directive:** {sel['command']}\n\n**Impact:** {sel['expected_reduction']}")
            
            st.markdown("**Deployed Resources:**")
            for res in sel['resources']:
                st.markdown(f"- 🔧 **{res['quantity']}x {res['type']}**")
                
            if st.button("Acknowledge & Dispatch Units", type="primary"):
                st.balloons()
                st.success("Units successfully dispatched to coordinates.")
                st.session_state.selected_incident = None
                st.rerun()
    else:
        st.info("Select an incident from the Live Queue to view XAI analysis and dispatch resources.")
