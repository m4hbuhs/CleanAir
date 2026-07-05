import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import xgboost as xgb
import firebase_admin
from firebase_admin import credentials
import json
import os
from glob import glob

from backend.api.router import router as api_router
from backend.api.twilio_webhook import router as twilio_router
from backend.api.accessibility import router as accessibility_router

logger = logging.getLogger(__name__)

def load_xgboost_pipeline(pipeline_path: str):
    """Loads a 24-hour XGBoost pipeline from a JSON file into memory."""
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)
        
    medians = pipeline_data.get('medians', {})
    estimators_json = pipeline_data.get('estimators_json', [])
    
    models = []
    for est_dict in estimators_json:
        model = xgb.XGBRegressor()
        # Load directly from bytearray to avoid temp files on disk
        model.load_model(bytearray(json.dumps(est_dict), 'utf-8'))
        models.append(model)
        
    return {"models": models, "medians": medians}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all district models from backend/ml/models into memory ONCE
    app.state.models = {}
    
    models_dir = os.path.join(os.path.dirname(__file__), "ml", "models")
    if os.path.exists(models_dir):
        pipeline_files = glob(os.path.join(models_dir, "*_pipeline.json"))
        for p_file in pipeline_files:
            district_name = os.path.basename(p_file).replace("_pipeline.json", "")
            try:
                app.state.models[district_name] = load_xgboost_pipeline(p_file)
                logger.info(f"Loaded XGBoost pipeline for district: {district_name}")
            except Exception as e:
                logger.error(f"Failed to load pipeline {p_file}: {e}")
    else:
        logger.warning(f"backend/ml/models directory not found at {models_dir}")
        
    try:
        if not firebase_admin._apps:
            # This automatically uses the GOOGLE_APPLICATION_CREDENTIALS env var
            firebase_admin.initialize_app()
        logger.info("Firebase Admin initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")

    yield
    
    # Cleanup on shutdown
    app.state.models.clear()

app = FastAPI(title="Hyperlocal Command Center API", lifespan=lifespan)

# 1. Enable Global CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(twilio_router, prefix="/api/v1")
app.include_router(accessibility_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
