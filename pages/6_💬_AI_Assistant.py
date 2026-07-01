"""
💬 AI Assistant — Gemini-powered chatbot for citizens and officers.
Context-aware: knows current AQI, active hotspots, and recent reports.
"""

import streamlit as st

st.set_page_config(page_title="AI Assistant | CleanAir", page_icon="💬", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #4a148c 0%, #6a1b9a 50%, #4a148c 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(171, 71, 188, 0.3); box-shadow: 0 8px 32px rgba(74, 20, 140, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">💬 AI Assistant</h1>
    <p style="color: #ce93d8; margin-top: 0.5rem;">
        Ask about air quality, health advice, pollution reports, or get help navigating the platform.
        Powered by Gemini 2.5 Flash.
    </p>
</div>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first.")
    st.stop()

# ── Initialize Chat History ──────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "🍃 Hello! I'm the CleanAir AI Assistant. I can help you with:\n\n"
                      "- 🌍 **Current air quality** in your area\n"
                      "- 🏥 **Health advice** based on AQI levels\n"
                      "- 📸 **How to report** pollution incidents\n"
                      "- 🏆 **EcoToken rewards** and redemption\n"
                      "- 🗺️ **Hotspot information** and trends\n\n"
                      "Ask me anything! I can respond in Hindi, English, Marathi, and more.",
        }
    ]

# ── Build Context ──────────────────────────
def build_system_context() -> str:
    """Build current system context for the chatbot."""
    db = st.session_state.db
    stats = db.get_stats()

    # Try to get live AQI
    try:
        from backend.services.aqi_service import fetch_current_aqi
        aqi_data = fetch_current_aqi(28.6139, 77.2090)
        current_aqi = aqi_data.get("us_aqi", "N/A")
    except Exception:
        current_aqi = "unavailable"

    from backend.utils.aqi_categories import classify_aqi
    if isinstance(current_aqi, (int, float)):
        cat = classify_aqi(current_aqi)
        aqi_info = f"AQI: {current_aqi:.0f} ({cat.label}). {cat.health_advisory}"
    else:
        aqi_info = "AQI data currently unavailable."

    context = f"""
    PLATFORM STATUS:
    - Delhi Current AQI: {aqi_info}
    - Total Reports: {stats['total_reports']}
    - Today's Reports: {stats['today_reports']}
    - Active Hotspots: {stats['active_hotspots']}
    - Pending Reports: {stats['pending_reports']}
    - Total Users: {stats['total_users']}
    - User Role: {st.session_state.get('user_role', 'citizen')}
    """

    # Add recent reports
    reports = db.get_all_reports()[:5]
    if reports:
        context += "\nRECENT REPORTS:\n"
        for r in reports:
            context += f"- {r.pollution_type.value} at ({r.latitude:.3f}, {r.longitude:.3f}), severity {r.severity.value}/5\n"

    return context


# ── Display Chat History ──────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat Input ──────────────────────────
user_input = st.chat_input("Ask about air quality, health advice, or the platform...")

if user_input:
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if st.session_state.gemini_available:
                from backend.services.gemini_service import chat_response

                context = build_system_context()
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_messages[-10:]
                ]

                response = chat_response(
                    user_message=user_input,
                    conversation_history=history,
                    context=context,
                    client=st.session_state.gemini_client,
                )
            else:
                # Fallback responses for demo
                response = _get_fallback_response(user_input)

            st.markdown(response)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response}
            )

# ── Sidebar Quick Actions ──────────────────────
with st.sidebar:
    st.markdown("### 💡 Quick Questions")
    quick_questions = [
        "What is the current AQI in Delhi?",
        "Is it safe to go outside today?",
        "How do I report a pollution incident?",
        "What are EcoTokens?",
        "दिल्ली की हवा की गुणवत्ता कैसी है?",
        "What causes high PM2.5 levels?",
    ]
    for q in quick_questions:
        if st.button(q, key=f"quick_{q[:20]}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": q})
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_messages = [st.session_state.chat_messages[0]]
        st.rerun()


def _get_fallback_response(query: str) -> str:
    """Fallback responses when Gemini is unavailable."""
    query_lower = query.lower()

    if any(w in query_lower for w in ["aqi", "air quality", "pollution level", "हवा"]):
        return (
            "🌍 Delhi's current AQI is typically in the **Moderate to Unhealthy** range "
            "(100-200+ AQI). For real-time data, check the Live Map page.\n\n"
            "**Health Advice:**\n"
            "- If AQI > 150: Limit outdoor activity, especially for children and elderly\n"
            "- If AQI > 200: Wear N95 masks outdoors\n"
            "- If AQI > 300: Stay indoors, use air purifiers\n\n"
            "⚠️ These are AI-estimated values, not official CPCB readings."
        )
    elif any(w in query_lower for w in ["report", "submit", "upload", "complaint"]):
        return (
            "📸 **How to Report a Pollution Incident:**\n\n"
            "1. Go to the **Report Incident** page\n"
            "2. Upload a photo, record audio, or type a description\n"
            "3. Our AI (Gemini) will classify the pollution type and severity\n"
            "4. Confirm the location and submit\n"
            "5. Earn **EcoTokens** for your contribution!\n\n"
            "Your report helps improve air quality monitoring for your neighborhood."
        )
    elif any(w in query_lower for w in ["token", "reward", "earn", "redeem"]):
        return (
            "🏆 **EcoToken Rewards:**\n\n"
            "- **10 tokens** for every report submission\n"
            "- **+25 bonus** when a municipal officer verifies your report\n"
            "- **+15 bonus** for high-severity incidents\n"
            "- **+10 bonus** for photos with high AI confidence\n\n"
            "Redeem tokens for metro cards, shopping vouchers, and certificates "
            "on the EcoTokens page!"
        )
    else:
        return (
            "I'm the CleanAir AI Assistant. I can help with:\n"
            "- 🌍 Air quality information\n"
            "- 🏥 Health advice\n"
            "- 📸 Reporting instructions\n"
            "- 🏆 EcoToken rewards\n\n"
            "Currently running in demo mode. Connect the Gemini API for full functionality."
        )
