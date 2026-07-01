"""
🔍 Polluter Watch — Violation tracking for municipal officers.
Tracks repeated pollution violations at specific locations.
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Polluter Watch | CleanAir", page_icon="🔍", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #263238 0%, #37474f 50%, #263238 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(120, 144, 156, 0.3); box-shadow: 0 8px 32px rgba(38, 50, 56, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">🔍 Polluter Watch</h1>
    <p style="color: #b0bec5; margin-top: 0.5rem;">
        Track repeated pollution violations. Identify habitual offenders and enforce compliance.
        Restricted to Municipal Officers and Admins.
    </p>
</div>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first.")
    st.stop()

# ── Role Check ──────────────────────────────
if st.session_state.get("user_role") == "citizen":
    st.error("🔒 **Access Denied.** This section is restricted to Municipal Officers and Admins only.")
    st.markdown("""
    As a citizen, you can contribute by:
    - 📸 **Reporting incidents** on the Report page
    - 🏆 **Earning EcoTokens** for verified reports
    - 💬 **Asking the AI Assistant** for guidance
    """)
    st.stop()

db = st.session_state.db

# ── Violation Summary ──────────────────────────
violations = db.get_all_violations()

st.markdown("### 📊 Violation Overview")

v1, v2, v3, v4 = st.columns(4)
repeated = [v for v in violations if v.occurrence_count >= 2]

with v1:
    st.metric("Total Tracked Locations", len(violations))
with v2:
    st.metric("🔴 Repeat Offenders", len(repeated))
with v3:
    if violations:
        max_count = max(v.occurrence_count for v in violations)
        st.metric("Worst Offender Count", f"{max_count}x")
    else:
        st.metric("Worst Offender Count", "0")
with v4:
    types = set(v.violation_type for v in violations)
    st.metric("Violation Types", len(types))

st.markdown("---")

# ── Filter Controls ──────────────────────────
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    min_occurrences = st.slider("Minimum occurrences", 1, 10, 1)
with filter_col2:
    type_filter = st.multiselect(
        "Filter by violation type",
        options=list(set(v.violation_type for v in violations)) if violations else [],
        default=list(set(v.violation_type for v in violations)) if violations else [],
    )

# ── Violation Table ──────────────────────────
filtered = [
    v for v in violations
    if v.occurrence_count >= min_occurrences
    and (not type_filter or v.violation_type in type_filter)
]

if filtered:
    st.markdown("### 📋 Violation Records")

    viol_data = []
    for v in filtered:
        severity_indicator = "🔴" if v.occurrence_count >= 3 else "🟡" if v.occurrence_count >= 2 else "⚪"
        viol_data.append({
            "Status": severity_indicator,
            "Location": v.location_label,
            "Type": v.violation_type,
            "Occurrences": v.occurrence_count,
            "Last Reported": v.last_reported.strftime("%Y-%m-%d %H:%M"),
            "Report IDs": ", ".join(v.report_ids[:5]),
            "Coord": f"({v.latitude:.4f}, {v.longitude:.4f})",
        })

    st.dataframe(
        pd.DataFrame(viol_data),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Occurrences": st.column_config.ProgressColumn(
                "Occurrences",
                min_value=0,
                max_value=max(v.occurrence_count for v in filtered) if filtered else 10,
                format="%d",
            ),
        },
    )

    # ── Detailed Violation Cards ──────────────────
    st.markdown("---")
    st.markdown("### 📍 Violation Details")

    for v in filtered[:10]:
        severity_color = "#f44336" if v.occurrence_count >= 3 else "#FF9800"
        with st.expander(
            f"{'🔴' if v.occurrence_count >= 3 else '🟡'} {v.violation_type} — "
            f"{v.location_label} ({v.occurrence_count}x)"
        ):
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                st.markdown(f"**Type:** {v.violation_type}")
                st.markdown(f"**Occurrences:** {v.occurrence_count}")
            with dc2:
                st.markdown(f"**Last Reported:** {v.last_reported.strftime('%Y-%m-%d %H:%M')}")
                st.markdown(f"**Status:** {v.status}")
            with dc3:
                st.markdown(f"**Coordinates:** ({v.latitude:.4f}, {v.longitude:.4f})")
                st.markdown(f"**Linked Reports:** {len(v.report_ids)}")

            # Generate AI analysis if Gemini available
            if st.session_state.gemini_available:
                if st.button(f"🧠 AI Analysis", key=f"ai_viol_{v.location_label[:10]}"):
                    with st.spinner("Generating violation analysis..."):
                        try:
                            from backend.services.gemini_service import chat_response
                            analysis = chat_response(
                                f"Analyze this repeated pollution violation and recommend enforcement actions: "
                                f"Location: {v.location_label}, Type: {v.violation_type}, "
                                f"Occurrences: {v.occurrence_count}, Status: {v.status}",
                                context=f"This is a repeated {v.violation_type} violation at {v.location_label} "
                                       f"with {v.occurrence_count} occurrences.",
                                client=st.session_state.gemini_client,
                            )
                            st.markdown(analysis)
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

            # Action buttons
            act1, act2, act3 = st.columns(3)
            with act1:
                if st.button("📤 Issue Notice", key=f"notice_{v.location_label[:10]}"):
                    st.success(f"📤 Notice issued for {v.violation_type} at {v.location_label}")
            with act2:
                if st.button("👮 Deploy Team", key=f"deploy_{v.location_label[:10]}"):
                    st.success(f"👮 Enforcement team deployed to {v.location_label}")
            with act3:
                if st.button("✅ Mark Resolved", key=f"resolve_{v.location_label[:10]}"):
                    v.status = "resolved"
                    st.success(f"✅ Violation at {v.location_label} marked as resolved")
                    st.rerun()
else:
    if not violations:
        st.info("No violations tracked yet. Violations are automatically recorded when citizens report repeated pollution at the same location.")
    else:
        st.info("No violations match the current filter criteria.")

# ── Summary Statistics ──────────────────────
if violations:
    st.markdown("---")
    st.markdown("### 📊 Violation Type Breakdown")

    import plotly.express as px

    type_counts = {}
    for v in violations:
        type_counts[v.violation_type] = type_counts.get(v.violation_type, 0) + v.occurrence_count

    if type_counts:
        fig = px.bar(
            x=list(type_counts.keys()),
            y=list(type_counts.values()),
            labels={"x": "Violation Type", "y": "Total Occurrences"},
            color=list(type_counts.values()),
            color_continuous_scale=["#4CAF50", "#FF9800", "#f44336"],
            template="plotly_dark",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
