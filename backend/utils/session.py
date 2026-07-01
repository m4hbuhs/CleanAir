import streamlit as st

def initialize_session():
    """
    Safely initialize all global session state variables needed across the app.
    Call this immediately after importing streamlit on every page.
    This is the single source of truth — Gemini, XGBoost, DB are all
    lazily initialized here so any page can be opened directly.
    """
    defaults = {
        # Gemini
        "gemini_available": False,
        "gemini_client": None,

        # XGBoost
        "xgb_model": None,

        # User
        "current_user": "usr_demo_01",
        "user_role": "citizen",

        # AQI rolling history (last 2 PM2.5 readings)
        "pm2_5_history": [45.0, 48.0],

        # Geolocation Default (Delhi)
        "report_lat": 28.6139,
        "report_lon": 77.2090,
        "exif_location": None,
        "searched_location": None,

        # Incident Analysis State
        "current_analysis": None,
        "report_text": "",

        # Database
        "db": None,

        # AI Assistant Chat
        "chat_messages": [
            {"role": "assistant", "content": "Hello! I am your CleanAir AI Assistant. How can I help you understand pollution data or environmental guidelines today?"}
        ],
        "chat_history": [],
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # ── Lazy-load Database ────────────────────────────────────────────────────
    if st.session_state.get("db") is None:
        try:
            from backend.database.firestore_client import InMemoryDB
            import json
            from pathlib import Path
            from backend.models.schemas import CitizenReport, PollutionType, IncidentSeverity, ReportStatus

            db = InMemoryDB()

            # Load sample reports from disk once
            sample_path = Path("data/sample_reports.json")
            if sample_path.exists():
                with open(sample_path, "r") as f:
                    samples = json.load(f)
                for s in samples:
                    report = CitizenReport(
                        report_id=s["report_id"],
                        user_id=s["user_id"],
                        latitude=s["latitude"],
                        longitude=s["longitude"],
                        pollution_type=PollutionType(s["pollution_type"]),
                        severity=IncidentSeverity(s["severity"]),
                        confidence=s["confidence"],
                        description=s["description"],
                        status=ReportStatus(s["status"]),
                        tokens_awarded=s["tokens_awarded"],
                    )
                    db.add_report(report)

                # Seed sample wallets
                user_tokens: dict = {}
                for s in samples:
                    uid = s["user_id"]
                    user_tokens.setdefault(uid, 0)
                    user_tokens[uid] += s["tokens_awarded"]
                for uid, tokens in user_tokens.items():
                    wallet = db.get_wallet(uid)
                    wallet.total_tokens = tokens
                    wallet.total_reports = sum(1 for s in samples if s["user_id"] == uid)
                    wallet.verified_reports = sum(
                        1 for s in samples
                        if s["user_id"] == uid and s["status"] in ("ai_verified", "officer_validated")
                    )
                    db.save_wallet(wallet)

            st.session_state["db"] = db

        except Exception as e:
            st.warning(f"⚠️ Database init failed: {e}")

    # ── Lazy-load Gemini ─────────────────────────────────────────────────────
    # Only try if not yet initialized (gemini_client is still None)
    if st.session_state.get("gemini_client") is None:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            from google import genai
            client = genai.Client()
            st.session_state["gemini_client"] = client
            st.session_state["gemini_available"] = True
        except Exception as e:
            st.warning(f"Gemini init failed: {e}")
            st.session_state["gemini_client"] = None
            st.session_state["gemini_available"] = False

    # ── Lazy-load XGBoost Model ──────────────────────────────────────────────
    if st.session_state.get("xgb_model") is None:
        try:
            from backend.ml.inference import get_inference_engine
            engine = get_inference_engine()
            engine.ensure_loaded()
            st.session_state["xgb_model"] = engine
        except Exception:
            st.session_state["xgb_model"] = None
