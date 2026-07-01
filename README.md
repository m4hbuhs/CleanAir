# 🍃 CleanAir & Clear Streets AI

**AI-Powered Hyperlocal Pollution Intelligence & Municipal Response Platform**

Built for the Google AI Hackathon 2026 | Powered by Gemini 2.5 Flash, XGBoost, Open-Meteo

---

## 🌟 What It Does

CleanAir creates a **Virtual Sensor Network** that estimates hyperlocal air quality at 500m resolution by fusing:

- 📡 **Official AQI station data** (Open-Meteo / CPCB)
- 📸 **Citizen reports** (photos, voice, text → classified by Gemini AI)
- 🌤️ **Weather conditions** (temperature, wind, precipitation)
- 🧠 **XGBoost ML model** trained on Delhi historical air quality data

> ⚠️ This system **does NOT claim to measure AQI directly from images**. It uses AI-assisted sensor fusion to estimate pollution at unmeasured locations, clearly distinguishing AI predictions from official readings.

---

## 🏗️ Architecture

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

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd hackathon

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the app
streamlit run 🍃_CleanAir.py
```

The app opens at `http://localhost:8501`

> ⚠️ **SECURITY WARNING:** Never commit your `.env` file or credential JSON files to version control. The `.gitignore` is pre-configured to ignore `.env`, `*.pem`, `*.key`, and service account files. Always use environment variables for secrets and never hardcode API keys in the source code.

---

## 📂 Project Structure

```
hackathon/
├── 🍃_CleanAir.py                    # Main Streamlit entry point
├── pages/
│   ├── 2_📸_Report_Incident.py       # Citizen upload (photo/voice/text)
│   ├── 3_🗺️_Live_Map.py             # Heatmap + plume + hotspots
│   ├── 4_📊_Municipal_Dashboard.py   # Command center for officers
│   ├── 5_🏆_EcoTokens.py            # Rewards + leaderboard
│   ├── 6_💬_AI_Assistant.py          # Gemini chatbot
│   └── 7_🔍_Polluter_Watch.py       # Violation tracking (officer-only)
├── backend/
│   ├── config.py                      # Centralized settings
│   ├── models/
│   │   └── schemas.py                 # Pydantic data models
│   ├── services/
│   │   ├── aqi_service.py             # Open-Meteo AQI ingestion
│   │   ├── weather_service.py         # Open-Meteo Weather ingestion
│   │   ├── vision_service.py          # Gemini multimodal classification
│   │   ├── speech_service.py          # Speech-to-Text (multilingual)
│   │   ├── gemini_service.py          # Reports, chatbot, analysis
│   │   ├── virtual_sensor.py          # Virtual Sensor Engine (core)
│   │   ├── hotspot_service.py         # DBSCAN clustering
│   │   ├── reward_service.py          # EcoToken engine
│   │   └── plume_service.py           # Gaussian plume model
│   ├── ml/
│   │   ├── inference.py               # XGBoost inference wrapper
│   │   └── feature_engineering.py     # Feature transforms
│   ├── database/
│   │   └── firestore_client.py        # In-memory DB (Firestore-ready)
│   └── utils/
│       ├── aqi_categories.py          # AQI classification
│       └── geo_utils.py               # Geospatial utilities
├── data/
│   └── sample_reports.json            # Sample citizen reports
├── cleanair_xgb_model.json            # Trained XGBoost model
├── air_quality_historical.csv         # Historical Delhi AQI data
├── weather.csv                        # Historical weather data
├── requirements.txt
├── .env.example
└── .streamlit/config.toml             # Streamlit theme
```

---

## 🔑 Key Features

| Feature | Technology | Description |
|---------|-----------|-------------|
| **Citizen Reporting** | Gemini 2.5 Flash | Photo/voice/text → AI classification of 7 pollution types |
| **Virtual Sensor Network** | XGBoost + Sensor Fusion | 500m-resolution AQI surface using station + citizen + weather data |
| **Hotspot Detection** | DBSCAN | Automatic clustering of pollution reports into actionable hotspots |
| **Plume Visualization** | Gaussian Model + Pydeck | Wind-driven pollution dispersion heatmap |
| **Municipal Dashboard** | Plotly + Gemini | KPI cards, trend charts, AI dispatch briefs |
| **EcoToken Rewards** | Custom Engine | Token wallet, leaderboard, badge system, reward redemption |
| **AI Chatbot** | Gemini 2.5 Flash | Context-aware assistant in Hindi, English, Marathi, and more |
| **Polluter Watch** | Violation Tracking | Repeat offender detection with enforcement workflows |
| **Speech-to-Text** | Google STT / Gemini | Multilingual voice complaint transcription |

---

## 🤖 Google APIs Used

| API | Purpose |
|-----|---------|
| **Gemini 2.5 Flash** | Multimodal classification, report generation, chatbot, complaint analysis |
| **Google Speech-to-Text** | Multilingual voice complaint transcription (8 Indian languages) |
| **Open-Meteo** | Free real-time AQI + weather data (no API key needed) |

---

## 📊 XGBoost Model Details

- **Task:** Next-day AQI prediction for Delhi
- **Features:** 14 engineered features (pollutants, weather, wind vectors, seasonal)
- **Training Data:** Delhi historical AQI (2022–2026) from Open-Meteo
- **Format:** JSON (`cleanair_xgb_model.json`) for fast loading and portability

### Model Input Features

| Feature | Description |
|---------|-------------|
| us_aqi | Current US AQI reading |
| pm10, pm2_5 | Particulate matter concentrations |
| pm2_5_roll3 | 3-day rolling average PM2.5 |
| carbon_monoxide | CO concentration |
| nitrogen_dioxide | NO₂ concentration |
| sulphur_dioxide | SO₂ concentration |
| ozone | O₃ concentration |
| dust | Dust concentration |
| tavg | Average temperature |
| prcp | Precipitation |
| wind_u, wind_v | Decomposed wind vector |
| month | Current month (seasonal feature) |

---

## ⚠️ Important Disclaimers

1. **AI-Estimated AQI:** All hyperlocal AQI values are estimates from the Virtual Sensor Network, NOT official government readings.
2. **Confidence Scores:** Every prediction includes a confidence score. Lower confidence near edges of the sensor network.
3. **Does NOT Replace Monitoring:** This system assists but does not replace official CPCB monitoring stations.
4. **Vision Classification:** Images are classified by AI for pollution type detection, NOT for direct AQI measurement.

---

## 🛠️ Development

```bash
# Run tests
python -m pytest tests/ -v

# Format code
black backend/ pages/

# Type checking
mypy backend/
```

---

## 📜 License

MIT License — Built for Google AI Hackathon 2026

---

## 👨‍💻 Team

Built with ❤️ for cleaner air and clearer streets.
