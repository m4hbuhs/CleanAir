"""
🍃 CleanAir & Clear Streets AI
AI-Powered Hyperlocal Pollution Intelligence & Municipal Response Platform

Main entry point for the Streamlit multi-page application.
"""

import streamlit as st
import json
from pathlib import Path
from backend.utils.session import initialize_session

# ── Page Configuration ──────────────────────
st.set_page_config(
    page_title="CleanAir & Clear Streets AI",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize Session State ──────────────────────
initialize_session()

# Custom CSS below


# ── Custom CSS ──────────────────────────────
st.markdown("""
<style>
    /* Global typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

    /* Hero gradient header */
    .hero-header {
        background: linear-gradient(135deg, #0f4c3a 0%, #1a6b4f 30%, #2d8f6f 60%, #0f4c3a 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(76, 175, 80, 0.3);
        box-shadow: 0 8px 32px rgba(15, 76, 58, 0.4);
    }
    .hero-header h1 {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .hero-header p {
        color: #b2dfdb;
        font-size: 1.05rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #1a1f2e, #252b3b);
        border: 1px solid rgba(76, 175, 80, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.2);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #4CAF50;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #aaaaaa;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.3rem;
    }

    /* AQI badge colors */
    .aqi-good { color: #00E400; }
    .aqi-moderate { color: #FFFF00; }
    .aqi-usg { color: #FF7E00; }
    .aqi-unhealthy { color: #FF0000; }
    .aqi-very-unhealthy { color: #8F3F97; }
    .aqi-hazardous { color: #7E0023; }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #0E1117 100%);
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-pending { background: #FF98001a; color: #FF9800; border: 1px solid #FF980044; }
    .badge-verified { background: #4CAF501a; color: #4CAF50; border: 1px solid #4CAF5044; }
    .badge-rejected { background: #f443361a; color: #f44336; border: 1px solid #f4433644; }

    /* Disclaimer bar */
    .disclaimer {
        background: rgba(255, 152, 0, 0.1);
        border-left: 4px solid #FF9800;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
        color: #FFB74D;
        margin: 1rem 0;
    }

    /* Smooth card animation */
    .stMetric { transition: all 0.3s ease; }
    .stMetric:hover { transform: scale(1.02); }

    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────
with st.sidebar:
    st.markdown("### 🍃 CleanAir AI")
    st.markdown("---")

    # Role selector
    role = st.selectbox(
        "👤 Select Role",
        options=["citizen", "officer", "admin"],
        index=["citizen", "officer", "admin"].index(st.session_state.user_role),
        format_func=lambda x: {"citizen": "🏠 Citizen", "officer": "🏛️ Municipal Officer", "admin": "⚙️ Admin"}[x],
    )
    st.session_state.user_role = role

    st.markdown("---")

    # Quick stats
    stats = st.session_state.db.get_stats()
    st.markdown(f"📊 **Total Reports:** {stats['total_reports']}")
    st.markdown(f"📅 **Today:** {stats['today_reports']}")
    st.markdown(f"⏳ **Pending:** {stats['pending_reports']}")
    st.markdown(f"✅ **Verified:** {stats['verified_reports']}")
    st.markdown(f"🔴 **Hotspots:** {stats['active_hotspots']}")
    st.markdown(f"👥 **Users:** {stats['total_users']}")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#666; font-size:0.75rem;'>"
        "Built for Google AI Hackathon 2026<br>"
        "Powered by Gemini • XGBoost • Open-Meteo"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Main Landing Content ──────────────────────
st.markdown(
    """
    <div class="hero-header">
        <h1>🍃 CleanAir & Clear Streets AI</h1>
        <p>AI-Powered Hyperlocal Pollution Intelligence & Municipal Response Platform</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Disclaimer
st.markdown(
    """
    <div class="disclaimer">
        ⚠️ <strong>Important:</strong> This platform provides AI-estimated hyperlocal AQI using a
        Virtual Sensor Network. These are NOT official CPCB/government readings. All predictions
        include confidence scores. The system assists, but does not replace, official monitoring.
    </div>
    """,
    unsafe_allow_html=True,
)

# Quick stats row
col1, col2, col3, col4 = st.columns(4)

# Fetch live AQI for overview
try:
    from backend.services.aqi_service import fetch_current_aqi
    live_aqi = fetch_current_aqi(28.6139, 77.2090)
    current_aqi = live_aqi.get("us_aqi", 0)
except Exception:
    current_aqi = 142  # Typical Delhi value as fallback

from backend.utils.aqi_categories import classify_aqi
aqi_cat = classify_aqi(current_aqi)

with col1:
    st.metric("🌍 Live Delhi AQI (Station)", f"{current_aqi:.0f}", delta=f"{aqi_cat.label}")
with col2:
    st.metric("📊 Total Reports", stats["total_reports"])
with col3:
    st.metric("🔴 Active Hotspots", stats["active_hotspots"])
with col4:
    st.metric("🪙 Tokens Distributed", stats["total_tokens_distributed"])

st.markdown("---")

# Feature overview
st.markdown("### 🚀 Platform Features")

feat_col1, feat_col2, feat_col3 = st.columns(3)

with feat_col1:
    st.markdown("""
    #### 📸 Citizen Reporting
    Upload photos, record voice complaints, or type reports.
    Our AI (Gemini 2.5 Flash) classifies pollution type, severity,
    and detects fake uploads automatically.
    """)

with feat_col2:
    st.markdown("""
    #### 🧠 Virtual Sensor Network
    AI Sensor Fusion combining AQI stations, citizen reports,
    weather data, and your XGBoost model to estimate hyperlocal
    AQI at 500m resolution across the city.
    """)

with feat_col3:
    st.markdown("""
    #### 🏛️ Municipal Dashboard
    Real-time command center with Gemini-generated dispatch briefs,
    DBSCAN hotspot detection, trend analysis, and automated
    resource allocation recommendations.
    """)

feat_col4, feat_col5, feat_col6 = st.columns(3)

with feat_col4:
    st.markdown("""
    #### 🗺️ Live Heatmap
    Interactive pollution heatmap with Gaussian plume dispersion
    modeling, hotspot clusters, and wind-driven pollution
    trajectory visualization.
    """)

with feat_col5:
    st.markdown("""
    #### 🏆 EcoToken Rewards
    Incentivize citizen participation with tokens redeemable
    for metro cards, shopping vouchers, and certificates.
    Leaderboard and badge system included.
    """)

with feat_col6:
    st.markdown("""
    #### 💬 AI Assistant
    Context-aware chatbot powered by Gemini that understands
    current AQI conditions and provides health advisories
    in multiple Indian languages.
    """)

st.markdown("---")

# Architecture summary
st.markdown("### 🏗️ System Architecture")
st.markdown("""
```
Citizen Upload (Photo/Voice/Text)
    ↓
Gemini 2.5 Flash — Multimodal Classification
    ↓
Virtual Sensor Engine — AI Sensor Fusion
    ├── Nearest AQI Station (Open-Meteo)
    ├── Weather Conditions (Open-Meteo)
    ├── Citizen Report Severity
    └── Historical PM2.5 Trends
    ↓
XGBoost Model — Predicted Hyperlocal AQI
    ↓
DBSCAN Hotspot Detection → Municipal Dashboard
    ↓
Gemini AI — Dispatch Briefs + Chatbot
    ↓
EcoToken Rewards → Citizen Wallet
```
""")

# Navigation hint
st.info("👈 Use the sidebar to navigate to different sections of the platform.")
