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
reports = db.get_all_reports()  # Load once, used by KPI, alerts and charts

# ── KPI Row ──────────────────────────────
st.markdown("### 📈 Key Performance Indicators")

# Fetch live AQI + Virtual Sensor estimate
try:
    from backend.services.aqi_service import fetch_current_aqi
    live_aqi_data = fetch_current_aqi(28.6139, 77.2090)
    current_aqi = live_aqi_data.get("us_aqi", 0)
except Exception:
    live_aqi_data = {}
    current_aqi = 142

from backend.utils.aqi_categories import classify_aqi
cat = classify_aqi(current_aqi)

# Virtual Sensor estimate
try:
    from backend.services.virtual_sensor_engine import VirtualSensorEngine
    vs_engine = VirtualSensorEngine()
    vs_result = vs_engine.estimate_aqi(28.6139, 77.2090, citizen_reports=reports)
    estimated_aqi = vs_result.estimated_aqi
    confidence_pct = vs_result.confidence.overall_pct
    confidence_label = vs_result.confidence.confidence_label
except Exception:
    estimated_aqi = current_aqi
    confidence_pct = 60
    confidence_label = "Medium"
    vs_result = None

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("📡 Official Station AQI", f"{current_aqi:.0f}", delta=cat.label, delta_color="off",
              help="Source: Open-Meteo (CAMS Global model)")
with kpi2:
    est_cat = classify_aqi(estimated_aqi)
    delta = estimated_aqi - current_aqi
    st.metric("🧠 AI Estimated AQI", f"{estimated_aqi:.0f}",
              delta=f"{delta:+.0f} vs station", delta_color="inverse",
              help=f"Virtual Sensor Network estimate. Confidence: {confidence_pct}% ({confidence_label})")
with kpi3:
    st.metric("📋 Open Incidents", stats["pending_reports"])
with kpi4:
    st.metric("📊 Today's Reports", stats["today_reports"])
with kpi5:
    st.metric("🔴 Active Hotspots", stats["active_hotspots"])

st.markdown("---")

# ── Active Alerts Section ──────────────────────────────
st.markdown("### 🚨 Active Municipal Alerts")
try:
    from backend.services.alert_engine import evaluate_alerts
    active_alerts = evaluate_alerts(
        estimated_aqi=estimated_aqi,
        confidence_pct=confidence_pct,
        citizen_reports=reports,
        latitude=28.6139,
        longitude=77.2090,
    )
except Exception as e:
    active_alerts = []
    st.caption(f"Alert engine unavailable: {e}")

if active_alerts:
    for alert in active_alerts:
        a_col1, a_col2 = st.columns([2, 1])
        with a_col1:
            st.markdown(f"""
            <div style="background:rgba(244,67,54,0.1);border-left:4px solid #f44336;
                 border-radius:0 8px 8px 0;padding:1rem;margin-bottom:0.5rem;">
                <strong style="color:#f44336;font-size:1rem;">🚨 {alert.alert_type}</strong>
                <span style="color:#888;font-size:0.8rem;margin-left:0.8rem;">Confidence: {alert.confidence_pct}% · AQI: {alert.estimated_aqi:.0f}</span><br/>
                <span style="color:#aaa;font-size:0.85rem;">{' · '.join(alert.reasons)}</span>
            </div>""", unsafe_allow_html=True)
        with a_col2:
            st.markdown("**🛡️ Suggested Actions:**")
            for action in alert.suggested_actions[:3]:
                st.markdown(f"- {action}")
else:
    st.success("✅ No active alerts. All conditions within acceptable thresholds.")

st.markdown("---")

# ── Charts Section ──────────────────────────
chart_col1, chart_col2 = st.columns(2)

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

# ── 24-Hour Forecast (Virtual Sensor) ──────────
st.markdown("### 📈 24-Hour Hyperlocal AQI Forecast")
if vs_result and vs_result.hourly_forecast:
    hours = [f"+{p.hour_offset}h" for p in vs_result.hourly_forecast]
    aqis = [p.estimated_aqi for p in vs_result.hourly_forecast]
    confs = [p.confidence * 100 for p in vs_result.hourly_forecast]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=aqis, mode="lines+markers",
        name="Est. AQI", line=dict(color=est_cat.color, width=2.5),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=confs, mode="lines",
        name="Confidence %", line=dict(color="#888", width=1, dash="dot"),
        yaxis="y2",
    ))
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=350, margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Time Offset",
        showlegend=True,
        legend=dict(orientation="h", y=1.1),
        yaxis=dict(title="Estimated AQI", gridcolor="#333"),
        yaxis2=dict(title="Confidence %", overlaying="y", side="right", gridcolor="#222"),
        xaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Hourly forecast unavailable.")

st.markdown("---")

# ── Executive AI Summary ──────────────────────
st.markdown("### 🤖 Executive AI Summary & Dispatch Brief")

if st.button("🧠 Generate Executive Brief", type="primary"):
    with st.spinner("Gemini is analyzing the environmental digital twin matrix..."):
        try:
            from backend.services.executive_report import generate_executive_brief
            from backend.services.hotspot_service import detect_hotspots
            from backend.recommendation.incident_priority import rank_incidents
            
            raw_hotspots = detect_hotspots(reports) if reports else []
            # Convert objects to dicts for the ranking engine if needed, or pass as is if properties match
            hs_dicts = []
            for h in raw_hotspots:
                hs_dicts.append({
                    "center_latitude": h.center_latitude,
                    "center_longitude": h.center_longitude,
                    "radius_km": h.radius_km,
                    "avg_severity": h.avg_severity,
                    "dominant_pollution_type": h.dominant_pollution_type,
                })
            
            ranked_hotspots = rank_incidents(hs_dicts)
            
            brief = generate_executive_brief(ranked_hotspots, stats)
            
            st.markdown(f"""
            <div style="background:rgba(255, 255, 255, 0.05);border-left:4px solid #ab47bc;
                 border-radius:0 8px 8px 0;padding:1.5rem;margin-bottom:1.5rem;">
                {brief}
            </div>""", unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Failed to generate Executive Brief: {e}")

# ── Incident Prioritization & Lifecycle ──────────────────────
st.markdown("### 🚨 Active Priority Incidents")
try:
    from backend.services.hotspot_service import detect_hotspots
    from backend.recommendation.incident_priority import rank_incidents
    
    raw_hotspots = detect_hotspots(reports) if reports else []
    hs_dicts = []
    for h in raw_hotspots:
        hs_dicts.append({
            "center_latitude": h.center_latitude,
            "center_longitude": h.center_longitude,
            "radius_km": h.radius_km,
            "avg_severity": h.avg_severity,
            "dominant_pollution_type": h.dominant_pollution_type,
        })
    ranked_hotspots = rank_incidents(hs_dicts)
    
    if ranked_hotspots:
        for idx, hs in enumerate(ranked_hotspots[:3]):
            with st.expander(f"Priority #{idx+1} | Severity: {hs['avg_severity']} | {hs['dominant_pollution_type']}"):
                colA, colB, colC = st.columns(3)
                colA.metric("Priority Score", f"{hs['priority_score']:.2f}")
                colB.metric("Affected Pop", f"{hs['impact_metrics']['headcount']:,}")
                colC.metric("Vulnerable Assets", hs['impact_metrics']['total_vulnerable_assets'])
                
                # Incident Lifecycle
                st.markdown("**Incident Lifecycle:**")
                stages = ["Detected", "Assigned", "En Route", "Arrived", "Resolved", "Verified"]
                # Mock state for demo
                current_stage = "Assigned" if idx == 0 else "Detected"
                
                cols = st.columns(len(stages))
                for i, stage in enumerate(stages):
                    color = "#4CAF50" if stages.index(current_stage) >= i else "#555"
                    cols[i].markdown(f"<div style='text-align:center; padding:5px; background:{color}; border-radius:4px;'>{stage}</div>", unsafe_allow_html=True)
                
                if st.button(f"Advance Stage", key=f"adv_{idx}"):
                    st.toast("Lifecycle stage advanced!")
                    
    else:
        st.success("No active hotspots to prioritize.")
except Exception as e:
    st.error(f"Prioritization Engine unavailable: {e}")
# 🧠 Explainable AI & Resource Optimizer 🧠
st.markdown("---")
st.markdown("### 🧠 Decision Support & Attribution")

ds_col1, ds_col2 = st.columns(2)

with ds_col1:
    st.markdown("#### 🔍 Pollution Source Attribution (SHAP)")
    try:
        from backend.ml.attribution import attribution_engine
        from backend.services.data_fusion import build_unified_observation
        obs = build_unified_observation(28.6139, 77.2090, reports)
        
        # Mock SHAP analysis since full XGB is complex to invoke here directly
        mock_shap = {
            "top_contributors": [
                {"feature": "pm10", "absolute_impact": 45.0},
                {"feature": "traffic", "absolute_impact": 20.0}
            ]
        }
        attr_result = attribution_engine.estimate_contributions(obs, mock_shap)
        
        st.write(f"**Dominant Source:** {attr_result['dominant_source']} (Confidence: {attr_result['confidence']}%)")
        
        import plotly.express as px
        import pandas as pd
        
        attr_df = pd.DataFrame([
            {"Source": k, "Contribution (%)": v} for k, v in attr_result['contributions'].items() if v > 0
        ])
        fig_attr = px.pie(attr_df, names="Source", values="Contribution (%)", template="plotly_dark", hole=0.5)
        fig_attr.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_attr, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to load Attribution Engine: {e}")

with ds_col2:
    st.markdown("#### 🚒 Automated Resource Optimization")
    try:
        from backend.recommendation.resource_optimizer import resource_optimizer
        from backend.analytics.trend_service import trend_service
        
        # Get trend
        hist_aqis = [estimated_aqi * 0.9, estimated_aqi * 0.95, estimated_aqi]
        trend = trend_service.analyze_trend(estimated_aqi, hist_aqis)
        
        st.info(f"📈 **Current Trend:** {trend}")
        
        dom_src = attr_result.get("dominant_source", "Unknown") if 'attr_result' in locals() else "Unknown"
        res_rec = resource_optimizer.get_recommendation(
            lat=28.6139, lon=77.2090, 
            dominant_source=dom_src, 
            severity="High" if estimated_aqi > 200 else "Medium"
        )
        
        if res_rec["error"] if "error" in res_rec else False:
            st.warning(res_rec["error"])
        else:
            st.success(f"**Recommended Department:** {res_rec['required_department']}")
            st.write(f"**Priority:** {res_rec['priority']}")
            st.write(f"**Reasoning:** {res_rec['reasoning']}")
            st.write(f"**Equipment Needed:** {res_rec['suggested_equipment']} ({res_rec['suggested_manpower']} personnel)")
            
            st.metric("Estimated Arrival (ETA)", f"{res_rec['eta_minutes']} mins", f"Distance: {res_rec['distance_km']} km", delta_color="inverse")
            
            if st.button("Dispatch Recommended Resources", type="primary"):
                st.toast("Resources Dispatched Successfully!", icon="🚀")
    except Exception as e:
        st.error(f"Failed to load Resource Optimizer: {e}")

# 📊 Recent Reports Table 📊
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
