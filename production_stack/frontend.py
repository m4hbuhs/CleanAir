"""
frontend.py - Interactive Streamlit Dashboard Map Environment
Optimized for desktop and low-literacy field access.
"""

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
import json
import random
from production_stack.config import STATION_COORDINATES, get_aqi_category_for_pm25

st.set_page_config(page_title="CleanAir AI", layout="wide", page_icon="🍃")

# --- UI Language Configuration ---

st.sidebar.title("🌍 Language / भाषा")
language = st.sidebar.radio("Select Language", ["English", "Hindi (हिंदी)"])

STRINGS = {
    "English": {
        "title": "CleanAir & Clear Streets AI",
        "subtitle": "Hyperlocal pollution monitoring & 24-hour forecasting for Delhi.",
        "map_header": "🗺️ Live Environmental Twin",
        "report_header": "📸 Accessible Reporting Portal",
        "report_btn": "Submit Incident",
        "photo_label": "Take a photo of pollution",
        "desc_label": "Describe what you see",
        "forecast_header": "📈 24-Hour Forecast Horizon",
        "xai_header": "🧠 Explainable AI Analysis",
        "success": "Report submitted successfully! Trust Score:"
    },
    "Hindi (हिंदी)": {
        "title": "क्लीनएयर एंड क्लियर स्ट्रीट्स AI",
        "subtitle": "दिल्ली के लिए हाइपरलोकल प्रदूषण निगरानी और 24-घंटे का पूर्वानुमान।",
        "map_header": "🗺️ लाइव पर्यावरण ट्विन",
        "report_header": "📸 रिपोर्टिंग पोर्टल",
        "report_btn": "घटना दर्ज करें",
        "photo_label": "प्रदूषण की तस्वीर लें",
        "desc_label": "आप क्या देखते हैं उसका वर्णन करें",
        "forecast_header": "📈 24-घंटे का पूर्वानुमान",
        "xai_header": "🧠 AI विश्लेषण",
        "success": "रिपोर्ट सफलतापूर्वक जमा की गई! ट्रस्ट स्कोर:"
    }
}
t = STRINGS[language]

st.title(t["title"])
st.markdown(t["subtitle"])

# --- Geospatial Render ---
st.markdown(f"### {t['map_header']}")

# Build DataFrame of all 45 stations with simulated AQI values
station_data = []
for name, (lat, lon) in STATION_COORDINATES.items():
    pm25 = random.uniform(30, 400) # Mock current pm25
    cat = get_aqi_category_for_pm25(pm25)
    
    # Color mapping based on AQI category
    color = [0, 255, 0, 200]
    if cat == "Satisfactory": color = [156, 204, 101, 200]
    elif cat == "Moderate": color = [255, 235, 59, 200]
    elif cat == "Poor": color = [255, 152, 0, 200]
    elif cat == "Very Poor": color = [244, 67, 54, 200]
    elif cat == "Severe": color = [183, 28, 28, 200]
    
    station_data.append({
        "name": name,
        "lat": lat,
        "lon": lon,
        "pm25": pm25,
        "category": cat,
        "color": color
    })
    
df_map = pd.DataFrame(station_data)

# Pydeck render
view_state = pdk.ViewState(latitude=28.6139, longitude=77.2090, zoom=10, pitch=45)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position="[lon, lat]",
    get_color="color",
    get_radius=1500,
    pickable=True
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/dark-v10",
    initial_view_state=view_state,
    layers=[layer],
    tooltip={"text": "Station: {name}\nPM2.5: {pm25}\nStatus: {category}"}
))

col1, col2 = st.columns([1, 1])

# --- Forecast Horizon ---
with col1:
    st.markdown(f"### {t['forecast_header']}")
    # When a station is clicked/selected
    selected_station = st.selectbox("Select Station to view forecast:", df_map["name"].tolist())
    
    # Mock making a request to our FastAPI backend for the forecast
    # We will simulate the payload here for Streamlit UI standalone behavior
    st.info(f"Loading 24h predictive autoregressive forecast for {selected_station}...")
    
    # Simulated 24h curve
    current_pm = float(df_map[df_map["name"] == selected_station]["pm25"].iloc[0])
    forecast_curve = [current_pm]
    for _ in range(23):
        # random walk with momentum
        delta = random.uniform(-15, 15)
        forecast_curve.append(max(10, forecast_curve[-1] + delta))
        
    df_forecast = pd.DataFrame({
        "Hour": [f"+{i}h" for i in range(24)],
        "Forecasted PM2.5 (µg/m³)": forecast_curve
    })
    
    st.line_chart(df_forecast.set_index("Hour"))
    
    # Explainable AI Container
    with st.expander(t["xai_header"]):
        st.markdown("#### Feature Attribution (pseudo-SHAP)")
        st.write("Why is the prediction trending this way?")
        
        # Mock SHAP Values for Explainability
        shap_data = {
            "Feature": ["Low Wind Speed (WS)", "Regional Smog Inversion", "Local Thermal Anomaly", "Traffic NO2 Index"],
            "Impact %": [45, 25, 20, 10]
        }
        st.dataframe(pd.DataFrame(shap_data).set_index("Feature"))
        st.caption("High PM2.5 driven primarily by Low Wind Speed and Regional Smog Inversion.")

# --- Accessible Reporting Portal ---
with col2:
    st.markdown(f"### {t['report_header']}")
    
    with st.container():
        st.markdown("""
        <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; text-align: center;">
            <h1 style="font-size: 50px; margin: 0;">📸</h1>
            <p style="font-size: 20px;">Easy 1-Tap Incident Upload</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(t["photo_label"], type=["jpg", "png", "jpeg"])
        description = st.text_area(t["desc_label"])
        
        if st.button(t["report_btn"], use_container_width=True, type="primary"):
            if uploaded_file:
                # In production, this fires POST /api/report
                # We simulate the forensics trust score response here
                byte_len = len(uploaded_file.getvalue())
                mock_trust = min(100.0, 85.0 + (byte_len % 15))
                st.success(f"{t['success']} {mock_trust:.1f}%")
            else:
                st.warning("Please upload a photo first.")
