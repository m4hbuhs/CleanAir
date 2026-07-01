"""
🗺️ Live Map — Interactive heatmap with Virtual Sensor Network visualization.
Displays AQI surface, plume dispersion, hotspot clusters, and citizen reports.
"""

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.set_page_config(page_title="Live Map | CleanAir", page_icon="🗺️", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #1b5e20 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(76, 175, 80, 0.3); box-shadow: 0 8px 32px rgba(27, 94, 32, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">🗺️ Live Pollution Map</h1>
    <p style="color: #a5d6a7; margin-top: 0.5rem;">
        Virtual Sensor Network heatmap with plume dispersion, hotspot clusters, and citizen reports.
    </p>
</div>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first to initialize the platform.")
    st.stop()

db = st.session_state.db

# ── Controls ──────────────────────────────
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])

with ctrl_col1:
    center_lat = st.number_input("Center Latitude", value=28.6139, format="%.4f", key="map_lat")
with ctrl_col2:
    center_lon = st.number_input("Center Longitude", value=77.2090, format="%.4f", key="map_lon")
with ctrl_col3:
    map_layer = st.selectbox(
        "Map Layer",
        ["All Layers", "Heatmap Only", "Reports Only", "Plume Only", "Hotspots Only"],
    )

# ── Fetch Live Data ──────────────────────────
with st.spinner("🌐 Fetching live environmental data..."):
    try:
        from backend.services.aqi_service import fetch_current_aqi
        from backend.services.weather_service import fetch_current_weather

        aqi_data = fetch_current_aqi(center_lat, center_lon)
        weather_data = fetch_current_weather(center_lat, center_lon)
    except Exception as e:
        st.warning(f"API fetch failed ({e}). Using fallback data.")
        aqi_data = {"us_aqi": 145, "pm10": 85, "pm2_5": 55, "carbon_monoxide": 800,
                    "nitrogen_dioxide": 35, "sulphur_dioxide": 12, "ozone": 50, "dust": 2.0}
        weather_data = {"temperature_2m": 34, "precipitation": 0, "wind_speed_10m": 6.0,
                       "wind_direction_10m": 220, "relative_humidity_2m": 55}

# ── Metrics Row ──────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
from backend.utils.aqi_categories import classify_aqi

aqi_val = aqi_data.get("us_aqi", 0)
cat = classify_aqi(aqi_val)

with m1:
    st.metric("Station AQI", f"{aqi_val:.0f}", help="Official station reading")
with m2:
    st.metric("PM2.5", f"{aqi_data.get('pm2_5', 0):.1f} µg/m³")
with m3:
    st.metric("Temperature", f"{weather_data.get('temperature_2m', 0):.1f}°C")
with m4:
    st.metric("Wind", f"{weather_data.get('wind_speed_10m', 0):.1f} km/h")
with m5:
    st.metric("Category", f"{cat.emoji} {cat.label}")

st.markdown("---")

# ── Generate Map Layers ──────────────────────
layers = []

# 1. Reports scatter layer
reports = db.get_all_reports()
if reports and map_layer in ["All Layers", "Reports Only"]:
    report_data = []
    for r in reports:
        color_map = {
            "Garbage Burning": [255, 87, 34, 200],
            "Smoke": [158, 158, 158, 200],
            "Fire": [244, 67, 54, 220],
            "Dust": [255, 193, 7, 180],
            "Construction Pollution": [121, 85, 72, 200],
            "Industrial Smoke": [96, 125, 139, 200],
            "Vehicle Exhaust": [69, 90, 100, 180],
        }
        color = color_map.get(r.pollution_type.value, [100, 100, 100, 150])
        report_data.append({
            "latitude": r.latitude,
            "longitude": r.longitude,
            "severity": r.severity.value,
            "type": r.pollution_type.value,
            "color": color,
            "radius": r.severity.value * 60,
            "description": r.description[:80],
        })

    if report_data:
        report_df = pd.DataFrame(report_data)
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=report_df,
            get_position=["longitude", "latitude"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.8,
            stroked=True,
            line_width_min_pixels=2,
            get_line_color=[255, 255, 255, 100],
        ))

# 2. Heatmap layer from Virtual Sensor surface
if map_layer in ["All Layers", "Heatmap Only"]:
    try:
        from backend.ml.feature_engineering import build_payload_from_apis
        payload = build_payload_from_apis(aqi_data, weather_data, st.session_state.pm2_5_history)

        engine = st.session_state.xgb_model
        if engine:
            prediction = engine.predict(payload)

            # Generate plume for heatmap
            from backend.services.plume_service import generate_plume_geometry
            X = payload.to_xgboost_features() if hasattr(payload, 'to_xgboost_features') else None

            if X is None:
                from backend.ml.feature_engineering import payload_to_feature_matrix
                X = payload_to_feature_matrix(payload)

            plume_df = generate_plume_geometry(
                lat=center_lat,
                lon=center_lon,
                wind_u=float(X["wind_u"].values[0]),
                wind_v=float(X["wind_v"].values[0]),
                aqi_weight=prediction.estimated_aqi,
            )

            layers.append(pdk.Layer(
                "HeatmapLayer",
                data=plume_df,
                get_position=["longitude", "latitude"],
                get_weight="weight",
                radius_pixels=45,
                intensity=1.5,
                threshold=0.05,
                aggregation=pdk.types.String("SUM"),
            ))
    except Exception as e:
        st.caption(f"⚠️ Heatmap generation: {e}")

# 3. Hotspot clusters
if reports and map_layer in ["All Layers", "Hotspots Only"]:
    from backend.services.hotspot_service import detect_hotspots
    from backend.models.schemas import CitizenReport, PollutionType, IncidentSeverity, ReportStatus

    hotspot_reports = []
    for r in reports:
        hotspot_reports.append(r)

    clusters = detect_hotspots(hotspot_reports)
    db.save_hotspots(clusters)

    if clusters:
        cluster_data = []
        for c in clusters:
            cluster_data.append({
                "latitude": c.center_latitude,
                "longitude": c.center_longitude,
                "radius": max(200, c.radius_km * 1000),
                "reports": c.report_count,
                "severity": c.avg_severity,
                "type": c.dominant_pollution_type,
                "color": [244, 67, 54, 100] if c.avg_severity >= 4 else [255, 152, 0, 100],
            })

        cluster_df = pd.DataFrame(cluster_data)
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=cluster_df,
            get_position=["longitude", "latitude"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.4,
            stroked=True,
            line_width_min_pixels=3,
            get_line_color=[255, 255, 255, 150],
        ))

# ── Render Map ──────────────────────────────
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/dark-v10",
    initial_view_state=pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=13,
        pitch=30,
        bearing=0,
    ),
    layers=layers,
    tooltip={
        "html": "<b>Type:</b> {type}<br/><b>Severity:</b> {severity}<br/><b>Info:</b> {description}",
        "style": {
            "backgroundColor": "#1a1f2e",
            "color": "#fafafa",
            "fontSize": "13px",
            "borderRadius": "8px",
            "padding": "8px",
        },
    },
))

# ── Map Legend ──────────────────────────────
st.markdown("---")
legend_col1, legend_col2, legend_col3 = st.columns(3)

with legend_col1:
    st.markdown("""
    **Report Markers:**
    - 🟠 Garbage Burning
    - ⚪ Smoke
    - 🔴 Fire
    - 🟡 Dust
    - 🟤 Construction
    - 🔵 Industrial
    """)

with legend_col2:
    st.markdown("""
    **Heatmap Intensity:**
    - 🟢 Low pollution
    - 🟡 Moderate
    - 🟠 High
    - 🔴 Very High
    - 🟣 Hazardous
    """)

with legend_col3:
    st.markdown("""
    **Clusters:**
    - 🔴 Critical hotspot (severity ≥ 4)
    - 🟠 Moderate hotspot (severity < 4)
    - Ring size = affected area radius
    """)

# ── Disclaimer ──────────────────────────────
st.markdown(
    """
    <div style="background: rgba(255, 152, 0, 0.1); border-left: 4px solid #FF9800;
         padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; font-size: 0.85rem; color: #FFB74D;">
        ⚠️ <strong>Virtual Sensor Network:</strong> Heatmap shows AI-estimated pollution levels,
        NOT official measurements. Based on nearest station data + citizen reports + weather.
        Confidence decreases with distance from monitoring stations.
    </div>
    """,
    unsafe_allow_html=True,
)
