"""
📊 Municipal Dashboard — Command center for municipal officers.
KPI cards, trend charts, Gemini dispatch briefs, and resource allocation.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Municipal Dashboard | CleanAir", page_icon="📊", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #b71c1c 0%, #c62828 50%, #b71c1c 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(239, 83, 80, 0.3); box-shadow: 0 8px 32px rgba(183, 28, 28, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">📊 Municipal Command Center</h1>
    <p style="color: #ef9a9a; margin-top: 0.5rem;">
        Real-time operational dashboard for municipal officers. AI-generated dispatch briefs,
        hotspot analysis, and resource allocation recommendations.
    </p>
</div>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first.")
    st.stop()

# ── Role Check ──────────────────────────────
if st.session_state.get("user_role") == "citizen":
    st.warning("🔒 This dashboard is restricted to Municipal Officers and Admins. Switch your role in the sidebar.")
    st.stop()

db = st.session_state.db
stats = db.get_stats()

# ── KPI Row ──────────────────────────────
st.markdown("### 📈 Key Performance Indicators")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

# Fetch live AQI
try:
    from backend.services.aqi_service import fetch_current_aqi
    live_aqi = fetch_current_aqi(28.6139, 77.2090)
    current_aqi = live_aqi.get("us_aqi", 0)
except Exception:
    current_aqi = 142

from backend.utils.aqi_categories import classify_aqi
cat = classify_aqi(current_aqi)

with kpi1:
    st.metric("🌍 Current AQI", f"{current_aqi:.0f}", delta=cat.label, delta_color="off")
with kpi2:
    # XGBoost prediction
    predicted_aqi = current_aqi * 1.08  # Approximate
    if st.session_state.xgb_model:
        try:
            from backend.services.weather_service import fetch_current_weather
            from backend.ml.feature_engineering import build_payload_from_apis
            weather_data = fetch_current_weather(28.6139, 77.2090)
            payload = build_payload_from_apis(live_aqi, weather_data, st.session_state.pm2_5_history)
            pred = st.session_state.xgb_model.predict(payload)
            predicted_aqi = pred.estimated_aqi
        except Exception:
            pass
    st.metric("🧠 Predicted AQI (24h)", f"{predicted_aqi:.0f}")
with kpi3:
    st.metric("📋 Open Incidents", stats["pending_reports"])
with kpi4:
    st.metric("📊 Today's Reports", stats["today_reports"])
with kpi5:
    st.metric("🔴 Active Hotspots", stats["active_hotspots"])

st.markdown("---")

# ── Charts Section ──────────────────────────
chart_col1, chart_col2 = st.columns(2)

reports = db.get_all_reports()

with chart_col1:
    st.markdown("### 📊 Reports by Pollution Type")
    if reports:
        type_counts = {}
        for r in reports:
            t = r.pollution_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        type_df = pd.DataFrame(
            [{"Type": k, "Count": v} for k, v in type_counts.items()]
        )
        fig = px.bar(
            type_df, x="Type", y="Count",
            color="Count",
            color_continuous_scale=["#4CAF50", "#FF9800", "#f44336"],
            template="plotly_dark",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No reports yet.")

with chart_col2:
    st.markdown("### 📈 Severity Distribution")
    if reports:
        sev_counts = {}
        sev_labels = {1: "Minimal", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}
        for r in reports:
            s = sev_labels.get(r.severity.value, "Unknown")
            sev_counts[s] = sev_counts.get(s, 0) + 1

        sev_df = pd.DataFrame(
            [{"Severity": k, "Count": v} for k, v in sev_counts.items()]
        )
        fig = px.pie(
            sev_df, names="Severity", values="Count",
            color="Severity",
            color_discrete_map={
                "Minimal": "#4CAF50", "Low": "#8BC34A", "Moderate": "#FF9800",
                "High": "#f44336", "Critical": "#7E0023",
            },
            template="plotly_dark",
            hole=0.4,
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No reports yet.")

# ── AQI Trend (from historical data) ──────────
st.markdown("### 📉 Historical AQI Trend (Delhi)")
try:
    hist_df = pd.read_csv("air_quality_historical.csv")
    hist_df["date"] = pd.to_datetime(hist_df["date"])
    hist_df = hist_df.dropna(subset=["us_aqi"])
    hist_df = hist_df.tail(90)  # Last 90 days

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["date"], y=hist_df["us_aqi"],
        mode="lines",
        name="US AQI",
        line=dict(color="#4CAF50", width=2),
        fill="tozeroy",
        fillcolor="rgba(76, 175, 80, 0.1)",
    ))

    # Add threshold lines
    for thresh, color, label in [
        (50, "#00E400", "Good"), (100, "#FFFF00", "Moderate"),
        (150, "#FF7E00", "USG"), (200, "#FF0000", "Unhealthy"),
    ]:
        fig.add_hline(y=thresh, line_dash="dot", line_color=color, opacity=0.3,
                     annotation_text=label, annotation_position="right")

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=350,
        xaxis_title="Date",
        yaxis_title="US AQI",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.caption(f"Historical data unavailable: {e}")

st.markdown("---")

# ── AI Dispatch Brief ──────────────────────
st.markdown("### 🤖 AI-Generated Dispatch Brief")

if st.button("🧠 Generate AI Dispatch Report", type="primary"):
    with st.spinner("Gemini is analyzing current conditions..."):
        if st.session_state.gemini_available and st.session_state.xgb_model:
            try:
                from backend.services.gemini_service import generate_municipal_dispatch
                from backend.models.schemas import PredictionResult

                pred = PredictionResult(
                    estimated_aqi=predicted_aqi,
                    risk_level=classify_aqi(predicted_aqi).risk_level,
                    confidence=0.88,
                    category_label=classify_aqi(predicted_aqi).label,
                    category_color=classify_aqi(predicted_aqi).color,
                    health_advisory=classify_aqi(predicted_aqi).health_advisory,
                )

                dispatch = generate_municipal_dispatch(
                    prediction=pred,
                    weather_summary=f"Temp: {weather_data.get('temperature_2m', 'N/A')}°C, "
                                   f"Wind: {weather_data.get('wind_speed_10m', 'N/A')} km/h",
                    client=st.session_state.gemini_client,
                )

                st.markdown(f"**📋 Incident Summary:** {dispatch.incident_summary}")
                st.markdown(f"**🔍 Cause Analysis:** {dispatch.cause_analysis}")
                st.markdown(f"**⚠️ Severity:** {dispatch.severity_assessment}")

                st.markdown("**📌 Recommended Actions:**")
                for i, action in enumerate(dispatch.recommended_actions, 1):
                    st.markdown(f"  {i}. {action}")

                st.markdown("**🚛 Resource Deployment:**")
                for resource in dispatch.resource_deployment:
                    st.markdown(f"  - {resource}")

                st.success(f"📈 **Estimated Improvement:** {dispatch.estimated_improvement}")

            except Exception as e:
                st.error(f"Dispatch generation failed: {e}")
        else:
            st.info("Gemini API not available. Showing template dispatch.")
            st.markdown(f"""
            **📋 Incident Summary:** Air quality in central Delhi has reached {predicted_aqi:.0f} AQI,
            classified as {classify_aqi(predicted_aqi).label}. Multiple citizen reports indicate active
            pollution sources in the area.

            **📌 Recommended Actions:**
            1. Deploy mobile monitoring unit to hotspot areas
            2. Issue public health advisory via SMS
            3. Activate water sprinkler systems on major roads

            **🚛 Resource Deployment:**
            - 2 water mist cannons
            - 3 sanitation teams
            - 1 mobile AQI monitoring van
            """)

# ── Recent Reports Table ──────────────────────
st.markdown("---")
st.markdown("### 📋 Recent Incident Reports")

if reports:
    report_table = []
    for r in reports[:20]:
        status_badge = {
            "pending": "⏳ Pending",
            "ai_verified": "🤖 AI Verified",
            "officer_validated": "✅ Officer Validated",
            "rejected": "❌ Rejected",
            "resolved": "✔️ Resolved",
        }
        report_table.append({
            "ID": r.report_id,
            "Type": r.pollution_type.value,
            "Severity": f"{'🔴' * r.severity.value}",
            "Status": status_badge.get(r.status.value, r.status.value),
            "Confidence": f"{r.confidence:.0%}",
            "Location": f"({r.latitude:.3f}, {r.longitude:.3f})",
            "Description": r.description[:60] + "...",
        })

    st.dataframe(pd.DataFrame(report_table), use_container_width=True, hide_index=True)

    # ── Validate Reports ──────────────────────
    st.markdown("### ✅ Validate Pending Reports")
    pending = [r for r in reports if r.status.value == "pending"]
    if pending:
        for r in pending[:5]:
            with st.expander(f"📋 {r.report_id} — {r.pollution_type.value} (Severity: {r.severity.value}/5)"):
                st.markdown(f"**Description:** {r.description}")
                st.markdown(f"**Location:** ({r.latitude:.4f}, {r.longitude:.4f})")
                st.markdown(f"**AI Confidence:** {r.confidence:.0%}")

                val_col1, val_col2 = st.columns(2)
                with val_col1:
                    if st.button(f"✅ Validate", key=f"val_{r.report_id}"):
                        db.update_report_status(r.report_id, "officer_validated")
                        # Bonus tokens
                        from backend.services.reward_service import RewardEngine
                        engine = RewardEngine()
                        wallet = db.get_wallet(r.user_id)
                        wallet.verified_reports += 1
                        wallet = engine.award_tokens(wallet, 25, "Officer validation bonus", r.report_id)
                        db.save_wallet(wallet)
                        st.success(f"Report {r.report_id} validated! +25 bonus tokens to {r.user_id}")
                        st.rerun()
                with val_col2:
                    if st.button(f"❌ Reject", key=f"rej_{r.report_id}"):
                        db.update_report_status(r.report_id, "rejected")
                        st.warning(f"Report {r.report_id} rejected.")
                        st.rerun()
    else:
        st.success("No pending reports! All reports have been reviewed.")
else:
    st.info("No reports submitted yet.")
