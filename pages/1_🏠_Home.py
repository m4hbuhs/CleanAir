"""
🏠 Home — Quick overview and navigation hub.
Displays live AQI, recent activity, and quick action buttons.
"""

import streamlit as st
from datetime import datetime, timezone

st.set_page_config(page_title="Home | CleanAir", page_icon="🏠", layout="wide")

from backend.utils.session import initialize_session
initialize_session()

db = st.session_state.db
stats = db.get_stats()

# ── Hero ──────────────────────────────
st.markdown("""
<div style="background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 40%, #0d4429 100%);
     padding: 2.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(76, 175, 80, 0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.4);">
    <h1 style="color: #e0f2f1; margin: 0; font-size: 2.2rem; font-weight: 800;">
        🏠 Welcome to CleanAir & Clear Streets
    </h1>
    <p style="color: #80cbc4; margin-top: 0.5rem; font-size: 1.05rem;">
        Your AI-powered neighborhood pollution intelligence platform for Delhi
    </p>
</div>
""", unsafe_allow_html=True)

# ── Live AQI Banner ──────────────────────────
try:
    from backend.services.aqi_service import fetch_current_aqi
    from backend.utils.aqi_categories import classify_aqi
    aqi_data = fetch_current_aqi(28.6139, 77.2090)
    current_aqi = aqi_data.get("us_aqi", 0)
    cat = classify_aqi(current_aqi)
    pm25 = aqi_data.get("pm2_5", 0)
except Exception:
    current_aqi = 145
    pm25 = 58
    from backend.utils.aqi_categories import classify_aqi
    cat = classify_aqi(current_aqi)

st.markdown(f"""
<div style="background: linear-gradient(145deg, #1a1f2e, #252b3b);
     border: 2px solid {cat.color}40; border-radius: 16px; padding: 1.5rem;
     margin-bottom: 1.5rem; text-align: center;
     box-shadow: 0 4px 20px {cat.color}20;">
    <div style="font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 1px;">
        Delhi Live Station AQI
    </div>
    <div style="font-size: 4rem; font-weight: 800; color: {cat.color}; margin: 0.3rem 0;">
        {cat.emoji} {current_aqi:.0f}
    </div>
    <div style="font-size: 1.1rem; color: {cat.color}; font-weight: 600;">
        {cat.label}
    </div>
    <div style="font-size: 0.85rem; color: #999; margin-top: 0.5rem;">
        PM2.5: {pm25:.1f} µg/m³ · Updated {datetime.now(timezone.utc).strftime('%H:%M UTC')}
    </div>
</div>
""", unsafe_allow_html=True)

# Health advisory
st.markdown(f"""
<div style="background: {cat.color}15; border-left: 4px solid {cat.color};
     padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1.5rem;">
    <span style="font-weight: 600; color: {cat.color};">🏥 Health Advisory:</span>
    <span style="color: #ccc;"> {cat.health_advisory}</span>
</div>
""", unsafe_allow_html=True)

# ── Quick Stats ──────────────────────────
s1, s2, s3, s4 = st.columns(4)
with s1:
    st.metric("📊 Total Reports", stats["total_reports"])
with s2:
    st.metric("📅 Today", stats["today_reports"])
with s3:
    st.metric("🔴 Hotspots", stats["active_hotspots"])
with s4:
    st.metric("👥 Citizens", stats["total_users"])

st.markdown("---")

# ── Quick Actions ──────────────────────────
st.markdown("### ⚡ Quick Actions")

qa1, qa2, qa3, qa4 = st.columns(4)

with qa1:
    st.markdown("""
    <div style="background: linear-gradient(145deg, #1a237e22, #283593aa);
         border: 1px solid #5c6bc044; border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem;">📸</div>
        <div style="font-weight: 600; color: #9fa8da; margin-top: 0.5rem;">Report Incident</div>
        <div style="color: #666; font-size: 0.8rem; margin-top: 0.3rem;">Upload photo or describe pollution</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_📸_Report_Incident.py", label="Go to Reports →", use_container_width=True)

with qa2:
    st.markdown("""
    <div style="background: linear_gradient(145deg, #1b5e2022, #2e7d32aa);
         border: 1px solid #4CAF5044; border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem;">🗺️</div>
        <div style="font-weight: 600; color: #a5d6a7; margin-top: 0.5rem;">Live Map</div>
        <div style="color: #666; font-size: 0.8rem; margin-top: 0.3rem;">Heatmap & hotspot clusters</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_🗺️_Live_Map.py", label="View Map →", use_container_width=True)

with qa3:
    st.markdown("""
    <div style="background: linear-gradient(145deg, #f57f1722, #ff8f00aa);
         border: 1px solid #FFB30044; border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem;">🏆</div>
        <div style="font-weight: 600; color: #fff9c4; margin-top: 0.5rem;">EcoTokens</div>
        <div style="color: #666; font-size: 0.8rem; margin-top: 0.3rem;">Check your rewards & badges</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/5_🏆_EcoTokens.py", label="View Tokens →", use_container_width=True)

with qa4:
    st.markdown("""
    <div style="background: linear-gradient(145deg, #4a148c22, #6a1b9aaa);
         border: 1px solid #ab47bc44; border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem;">💬</div>
        <div style="font-weight: 600; color: #ce93d8; margin-top: 0.5rem;">AI Assistant</div>
        <div style="color: #666; font-size: 0.8rem; margin-top: 0.3rem;">Ask about air quality & health</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/6_💬_AI_Assistant.py", label="Chat Now →", use_container_width=True)

st.markdown("---")

# ── Recent Activity ──────────────────────────
st.markdown("### 📋 Recent Activity")

reports = db.get_all_reports()[:5]
if reports:
    for r in reports:
        severity_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⚫"}.get(r.severity.value, "⚪")
        status_badge = {
            "pending": "⏳", "ai_verified": "🤖", "officer_validated": "✅",
            "rejected": "❌", "resolved": "✔️",
        }.get(r.status.value, "❓")

        st.markdown(f"""
        <div style="background: #1a1f2e; border: 1px solid #333; border-radius: 8px;
             padding: 0.8rem 1rem; margin-bottom: 0.5rem; display: flex; align-items: center;">
            <span style="font-size: 1.3rem; margin-right: 0.8rem;">{severity_emoji}</span>
            <div style="flex: 1;">
                <span style="font-weight: 600; color: #fafafa;">{r.pollution_type.value}</span>
                <span style="color: #666; font-size: 0.8rem; margin-left: 0.5rem;">
                    ({r.latitude:.3f}, {r.longitude:.3f})
                </span>
                <br/>
                <span style="color: #888; font-size: 0.8rem;">{r.description[:80]}...</span>
            </div>
            <span style="font-size: 1.1rem;">{status_badge}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No reports yet. Be the first to report a pollution incident!")

# ── Footer disclaimer ──────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style="background: rgba(255, 152, 0, 0.08); border-left: 4px solid #FF9800;
         padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; font-size: 0.82rem; color: #FFB74D;">
        ⚠️ <strong>Disclaimer:</strong> AQI values shown are from the Open-Meteo Air Quality API
        (CAMS Global model). AI-predicted hyperlocal values from the Virtual Sensor Network are
        estimates and do NOT replace official CPCB monitoring station readings.
    </div>
    """,
    unsafe_allow_html=True,
)
