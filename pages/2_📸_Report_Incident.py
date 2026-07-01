"""
📸 Report Incident — Citizen pollution reporting page.
Supports photo upload, voice recording, and text complaints.
Uses Gemini for classification and XGBoost for AQI impact prediction.
"""

import streamlit as st
import uuid
from PIL import Image
from datetime import datetime, timezone

st.set_page_config(page_title="Report Incident | CleanAir", page_icon="📸", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #1a237e 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(92, 107, 192, 0.3); box-shadow: 0 8px 32px rgba(26, 35, 126, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">📸 Report a Pollution Incident</h1>
    <p style="color: #9fa8da; margin-top: 0.5rem;">
        Where did this happen? Upload a photo or describe the problem. Our AI will classify
        the pollution type and predict its impact on local air quality.
    </p>
</div>
""", unsafe_allow_html=True)

from backend.utils.session import initialize_session
initialize_session()

db = st.session_state.get("db")

# ── Step 1: Location ──────────────────────────────
st.markdown("### 📍 Step 1: Incident Location")
st.write("Type the address or landmark where you noticed the pollution. If you upload a photo with GPS enabled, we will auto-detect it!")

col_search, col_btn = st.columns([3, 1])
with col_search:
    address_query = st.text_input("Address / Landmark", placeholder="e.g., Connaught Place, Delhi", label_visibility="collapsed")
with col_btn:
    if st.button("Search Location", use_container_width=True):
        from backend.utils.geo_utils import geocode_address
        with st.spinner("Finding coordinates..."):
            lat, lon = geocode_address(address_query)
            
            # AI Fallback: If address fails, use Gemini to clean typos/spaces and try again!
            if not lat and st.session_state.get("gemini_available", False):
                try:
                    response = st.session_state.get("gemini_client").models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Format this address for a geocoding API. Fix spelling, add spaces (e.g. 'newdelhi' -> 'New Delhi'). Output ONLY the address: {address_query}"
                    )
                    clean_address = response.text.strip()
                    if clean_address and clean_address != address_query:
                        lat, lon = geocode_address(clean_address)
                        if lat and lon:
                            st.toast(f"🤖 AI corrected your typo to: '{clean_address}'")
                except Exception:
                    pass

            if lat and lon:
                st.session_state.report_lat = lat
                st.session_state.report_lon = lon
                st.session_state.exif_location = None # Clear EXIF if they do a manual search after
                st.success(f"Location found!")
            else:
                st.error("Location not found. Try a different search.")

st.markdown(f"**Current Selected Coordinates:** Latitude `{st.session_state.report_lat:.4f}` | Longitude `{st.session_state.report_lon:.4f}`")
st.markdown("---")

# ── Step 2: Evidence ──────────────────────────────
st.markdown("### 📁 Step 2: Provide Evidence")
tab_photo, tab_voice, tab_text = st.tabs(["📸 Photo Upload", "🎤 Voice Complaint", "📝 Text Report"])

analyze_triggered = False
evidence_type = None

with tab_photo:
    col_upload, col_preview = st.columns([1, 1])

    with col_upload:
        uploaded_image = st.file_uploader(
            "Upload a photo of the pollution incident",
            type=["jpg", "jpeg", "png", "webp"],
            key="photo_upload",
        )
        photo_text_context = st.text_area(
            "Optional: Describe what you see",
            placeholder="e.g., Heavy smoke coming from garbage dump near sector 15...",
            key="photo_text",
        )

    with col_preview:
        if uploaded_image:
            img = Image.open(uploaded_image)
            st.image(img, caption="📸 Uploaded Evidence", use_container_width=True)

    if uploaded_image and st.button("🔍 Analyze Photo & Predict AQI", key="analyze_photo", type="primary"):
        analyze_triggered = True
        evidence_type = "photo"

with tab_voice:
    st.markdown("Upload an audio recording of your complaint. Supports Hindi, English, Marathi, Gujarati, Tamil.")

    from backend.services.speech_service import get_supported_languages
    langs = get_supported_languages()
    selected_lang = st.selectbox(
        "Select your language",
        options=[l["code"] for l in langs],
        format_func=lambda x: next(l["name"] for l in langs if l["code"] == x),
        index=0,
    )

    audio_file = st.file_uploader(
        "Upload audio recording",
        type=["wav", "mp3", "ogg", "flac", "m4a"],
        key="audio_upload",
    )

    if audio_file and st.button("🎯 Analyze Audio & Predict AQI", key="analyze_voice", type="primary"):
        analyze_triggered = True
        evidence_type = "voice"

with tab_text:
    text_complaint = st.text_area(
        "Describe the pollution incident in detail",
        placeholder="e.g., There is heavy smoke coming from the garbage dump near sector 15. Children in the area are having breathing problems...",
        height=150,
        key="text_complaint",
    )

    if text_complaint and st.button("📤 Analyze Text & Predict AQI", key="analyze_text", type="primary"):
        analyze_triggered = True
        evidence_type = "text"

# ── Processing & Analysis ──────────────────────
if analyze_triggered:
    with st.spinner("🧠 AI is analyzing the evidence..."):
        if evidence_type == "photo":
            img = Image.open(uploaded_image)
            
            # Extract EXIF location
            try:
                from backend.utils.geo_utils import extract_exif_location
                exif_lat, exif_lon = extract_exif_location(img)
                if exif_lat is not None and exif_lon is not None:
                    st.session_state.report_lat = exif_lat
                    st.session_state.report_lon = exif_lon
                    st.toast("📍 Location auto-updated from photo GPS metadata!", icon="📍")
            except Exception:
                pass

            if st.session_state.get("gemini_available", False):
                from backend.services.vision_service import classify_pollution_image
                res = classify_pollution_image(img, photo_text_context, st.session_state.gemini_client)
            else:
                from backend.models.schemas import VisionClassification
                res = VisionClassification(
                    pollution_type="Garbage Burning", severity=4, confidence=0.85,
                    severity_multiplier=1.3, description="Demo mode simulated.", is_fake_upload=False,
                )
            st.session_state.current_analysis = res
            st.session_state.report_text = photo_text_context or res.description

        elif evidence_type == "voice":
            from backend.services.speech_service import transcribe_audio
            audio_bytes = audio_file.read()
            transcription = transcribe_audio(audio_bytes, selected_lang)
            st.toast(f"Transcription: {transcription}")
            
            if st.session_state.gemini_available and transcription:
                from backend.services.vision_service import classify_text_only
                res = classify_text_only(transcription, st.session_state.gemini_client)
            else:
                from backend.models.schemas import VisionClassification
                res = VisionClassification(
                    pollution_type="Smoke", severity=3, confidence=0.72,
                    severity_multiplier=1.15, description=transcription[:200],
                )
            st.session_state.current_analysis = res
            st.session_state.report_text = transcription

        elif evidence_type == "text":
            if st.session_state.get("gemini_available", False):
                from backend.services.vision_service import classify_text_only
                res = classify_text_only(text_complaint, st.session_state.gemini_client)
            else:
                from backend.models.schemas import VisionClassification
                res = VisionClassification(
                    pollution_type="Garbage Burning", severity=3, confidence=0.70,
                    severity_multiplier=1.15, description=text_complaint[:200],
                )
            st.session_state.current_analysis = res
            st.session_state.report_text = text_complaint

        # ── Smart Auto-Geocoding ──────────────────────
        # If the AI extracted a location from the text, use it automatically!
        if getattr(res, "location_mentioned", None):
            from backend.utils.geo_utils import geocode_address
            lat, lon = geocode_address(res.location_mentioned)
            if lat and lon:
                st.session_state.report_lat = lat
                st.session_state.report_lon = lon
                st.toast(f"📍 Location '{res.location_mentioned}' auto-detected from your text!", icon="🧠")

# ── Results & AQI Impact ──────────────────────
res = st.session_state.current_analysis
if res:
    st.markdown("---")
    st.markdown("### 🔬 Step 3: AI Results & Predicted Impact")

    if res.is_fake_upload:
        st.error("🚫 **Fake Upload Detected!** This evidence does not appear to show a pollution incident.")
    else:
        # AI Classification
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1: st.metric("Pollution Type", res.pollution_type)
        with rc2: 
            emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⚫"}.get(res.severity, "⚪")
            st.metric("Severity", f"{emoji} {res.severity}/5")
        with rc3: st.metric("AI Confidence", f"{res.confidence:.0%}")
        with rc4: st.metric("AQI Boost Factor", f"×{res.severity_multiplier:.2f}")

        if res.description:
            st.info(f"📋 **AI Analysis:** {res.description}")

        st.markdown("#### 🎯 Predicted AQI Impact at Location")
        try:
            from backend.services.aqi_service import fetch_current_aqi
            from backend.services.weather_service import fetch_current_weather
            from backend.ml.feature_engineering import build_payload_from_apis

            lat, lon = st.session_state.report_lat, st.session_state.report_lon
            aqi_data = fetch_current_aqi(lat, lon)
            weather_data = fetch_current_weather(lat, lon)
            payload = build_payload_from_apis(aqi_data, weather_data, st.session_state.get("pm2_5_history", []))

            engine = st.session_state.get("xgb_model")
            if engine:
                prediction = engine.predict(payload, res.severity_multiplier)

                pc1, pc2, pc3 = st.columns(3)
                with pc1:
                    st.metric("Official Station AQI", f"{aqi_data['us_aqi']:.0f}")
                with pc2:
                    from backend.utils.aqi_categories import classify_aqi
                    cat = classify_aqi(prediction.estimated_aqi)
                    st.metric(
                        "🧠 AI-Predicted Hyperlocal AQI",
                        f"{prediction.estimated_aqi:.0f}",
                        delta=f"{prediction.estimated_aqi - aqi_data['us_aqi']:+.0f} from station",
                        delta_color="inverse",
                    )
                with pc3:
                    st.metric("Prediction Confidence", f"{prediction.confidence:.0%}")

                st.markdown(f"<div class='disclaimer'>⚠️ {prediction.disclaimer}</div>", unsafe_allow_html=True)
                st.warning(f"🏥 **Health Advisory ({cat.label}):** {cat.health_advisory}")

        except Exception as e:
            st.warning(f"Could not generate AQI prediction: {e}")

        # ── Submit Report ──────────────────────
        st.markdown("---")
        if st.button("✅ Submit Verified Report & Earn EcoTokens", type="primary", use_container_width=True):
            from backend.models.schemas import CitizenReport, PollutionType, IncidentSeverity

            try: ptype = PollutionType(res.pollution_type)
            except ValueError: ptype = PollutionType.UNKNOWN

            try: sev = IncidentSeverity(res.severity)
            except ValueError: sev = IncidentSeverity.MODERATE

            report = CitizenReport(
                report_id=str(uuid.uuid4())[:8],
                user_id=st.session_state.get("current_user", "usr_demo_01"),
                latitude=st.session_state.report_lat,
                longitude=st.session_state.report_lon,
                pollution_type=ptype,
                severity=sev,
                confidence=res.confidence,
                description=st.session_state.report_text[:500],
                status="ai_verified" if res.confidence >= 0.7 else "pending",
            )

            db.add_report(report)

            # Award tokens
            from backend.services.reward_service import RewardEngine
            reward_engine = RewardEngine()
            tokens = reward_engine.calculate_tokens(report, res)
            wallet = db.get_wallet(st.session_state.get("current_user", "usr_demo_01"))
            wallet = reward_engine.award_tokens(wallet, tokens, f"Report: {report.report_id}", report.report_id)
            db.save_wallet(wallet)

            # Track violations
            db.record_violation(report)

            report.tokens_awarded = tokens

            st.balloons()
            st.success(f"✅ **Report Submitted Successfully!** Earned 🪙 {tokens} EcoTokens. Resetting form...")
            
            import time
            time.sleep(2.5)
            
            # Reset the form
            st.session_state.current_analysis = None
            st.session_state.report_text = ""
            st.rerun()
