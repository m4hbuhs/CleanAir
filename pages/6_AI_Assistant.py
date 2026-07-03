"""
💬 AI Assistant — Gemini-powered chatbot for citizens and officers.
Hyperlocal Location Intelligence Integrated.
"""

import streamlit as st
from backend.services.location_engine import location_engine

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

# ── Session State for Location Intelligence ────────────────
if "user_location" not in st.session_state:
    st.session_state.user_location = None
if "location_state" not in st.session_state:
    st.session_state.location_state = "unresolved" # unresolved, gps_prompt, manual_prompt, resolved
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

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

    # Get location-specific AQI if resolved
    aqi_info = "AQI data currently unavailable."
    loc = st.session_state.user_location
    if loc:
        try:
            from backend.services.virtual_sensor_engine import VirtualSensorEngine
            vs_engine = VirtualSensorEngine()
            reports = db.get_all_reports()
            vs_result = vs_engine.estimate_aqi(loc["lat"], loc["lon"], citizen_reports=reports)
            
            from backend.utils.aqi_categories import classify_aqi
            cat = classify_aqi(vs_result.estimated_aqi)
            
            # Predict 24h
            future_aqi = vs_result.hourly_forecast[-1].estimated_aqi if vs_result.hourly_forecast else vs_result.estimated_aqi
            
            # Attribution
            from backend.ml.attribution import attribution_engine
            from backend.services.data_fusion import build_unified_observation
            obs = build_unified_observation(loc["lat"], loc["lon"], reports)
            mock_shap = {"top_contributors": [{"feature": "pm10", "absolute_impact": 45.0}]}
            attr = attribution_engine.estimate_contributions(obs, mock_shap)
            
            aqi_info = (
                f"Hyperlocal AQI at {loc['locality']}: {vs_result.estimated_aqi:.0f} ({cat.label}).\n"
                f"Confidence: {vs_result.confidence.overall_pct}%.\n"
                f"Dominant Source: {attr['dominant_source']}.\n"
                f"Forecast (+24h): {future_aqi:.0f}.\n"
                f"Health Advisory: {cat.health_advisory}"
            )
            
            if loc.get("approximate"):
                aqi_info += "\n(Note: I estimate that you are in this region. This prediction is approximate. For neighborhood-level AQI, please enable GPS or enter your locality.)"
        except Exception as e:
            aqi_info = f"Error fetching hyperlocal data: {e}"

    context = f"""
    PLATFORM STATUS:
    - User Location: {loc['locality'] if loc else 'Unknown'}
    - Local AQI Data: {aqi_info}
    - Total Reports: {stats['total_reports']}
    - Active Hotspots: {stats['active_hotspots']}
    """
    return context


# ── Location Resolution State Machine ──────────────────────
def request_location_gps():
    st.session_state.location_state = "manual_prompt"
    # In a real app we'd trigger HTML5 Geolocation here. 
    # For now, we simulate user denying GPS and falling back to manual.
    st.session_state.chat_messages.append({"role": "assistant", "content": "GPS access denied. Please enter your locality, sector, colony, village, or nearby landmark (e.g., Rohini Sector 16, Saket)."})

def request_location_ip():
    loc = location_engine.geocode_ip()
    st.session_state.user_location = loc
    st.session_state.location_state = "resolved"
    st.session_state.chat_messages.append({"role": "assistant", "content": f"I estimate that you are in {loc['city']}. This prediction is approximate. For neighborhood-level AQI, please enable GPS or enter your locality."})
    process_pending_query()

def process_pending_query():
    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing hyperlocal data..."):
                if st.session_state.gemini_available:
                    from backend.services.gemini_service import chat_response
                    context = build_system_context()
                    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages[-10:]]
                    response = chat_response(query, history, context, st.session_state.gemini_client)
                else:
                    response = _get_fallback_response(query)
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

# ── Display Chat History ──────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Show GPS buttons if in gps_prompt state
if st.session_state.location_state == "gps_prompt":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📍 Allow GPS Access", use_container_width=True):
            # Simulate accepting GPS (Mock central Delhi)
            st.session_state.user_location = {"lat": 28.6139, "lon": 77.2090, "locality": "Central Delhi", "city": "Delhi", "approximate": False}
            st.session_state.location_state = "resolved"
            st.rerun()
    with col2:
        if st.button("⌨️ Enter Manually", use_container_width=True):
            request_location_gps()
            st.rerun()

# ── Chat Input ──────────────────────────
user_input = st.chat_input("Ask about air quality, health advice, or the platform...")

if user_input:
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # State Machine Logic
    if st.session_state.location_state == "manual_prompt":
        if user_input.strip() == "":
            request_location_ip()
        else:
            loc = location_engine.geocode_manual(user_input)
            st.session_state.user_location = loc
            st.session_state.location_state = "resolved"
            st.session_state.chat_messages.append({"role": "assistant", "content": f"Location resolved to {loc['locality']}. Analyzing..."})
            process_pending_query()
        st.rerun()

    elif st.session_state.location_state == "unresolved" and any(w in user_input.lower() for w in ["aqi", "air quality", "pollution"]):
        # Intercept environment queries
        st.session_state.pending_query = user_input
        st.session_state.location_state = "gps_prompt"
        msg = "To provide accurate neighborhood-level AQI predictions and nearby pollution hotspots, please allow access to your current location."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.rerun()

    else:
        # Normal chat
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if st.session_state.gemini_available:
                    from backend.services.gemini_service import chat_response
                    context = build_system_context()
                    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages[-10:]]
                    response = chat_response(user_input, history, context, st.session_state.gemini_client)
                else:
                    response = _get_fallback_response(user_input)

                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

# ── Sidebar Quick Actions ──────────────────────
with st.sidebar:
    if st.session_state.user_location:
        loc = st.session_state.user_location
        st.success(f"📍 **Active Location:** {loc['locality']}")
        if st.button("🗑️ Clear Location Cache", use_container_width=True):
            st.session_state.user_location = None
            st.session_state.location_state = "unresolved"
            st.session_state.pending_query = None
            st.rerun()
    else:
        st.info("📍 Location not set")

    st.markdown("### 💡 Quick Questions")
    quick_questions = [
        "What is the current AQI?",
        "Is it safe to go outside today?",
        "How do I report a pollution incident?"
    ]
    for q in quick_questions:
        if st.button(q, key=f"quick_{q[:20]}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": q})
            
            # Replicate state machine for quick buttons
            if st.session_state.location_state == "unresolved" and "aqi" in q.lower():
                st.session_state.pending_query = q
                st.session_state.location_state = "gps_prompt"
                msg = "To provide accurate neighborhood-level AQI predictions and nearby pollution hotspots, please allow access to your current location."
                st.session_state.chat_messages.append({"role": "assistant", "content": msg})
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_messages = [st.session_state.chat_messages[0]]
        st.rerun()

def _get_fallback_response(query: str) -> str:
    """Fallback responses when Gemini is unavailable."""
    query_lower = query.lower()
    
    if st.session_state.user_location:
        loc = st.session_state.user_location
        return f"🌍 The AQI in **{loc['locality']}** is currently being processed by the Virtual Sensor Network. Dominant sources appear to be traffic and localized dust. Forecasts show a stable trend over the next 24h."
    else:
        return "I need your location to provide accurate neighborhood-level AQI. Please ask for the AQI to trigger the location prompt!"
