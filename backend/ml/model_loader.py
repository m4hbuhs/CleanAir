import os
import json
import logging
from functools import lru_cache
import xgboost as xgb

logger = logging.getLogger(__name__)

@lru_cache(maxsize=32)
def get_model_pipeline(district_name: str):
    """Loads a 24-hour XGBoost pipeline from a JSON file into memory, cached."""
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    pipeline_path = os.path.join(models_dir, f"{district_name}_pipeline.json")
    
    if not os.path.exists(pipeline_path):
        return None

    try:
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
            
        logger.info(f"Loaded XGBoost pipeline for district: {district_name}")
        return {"models": models, "medians": medians}
    except Exception as e:
        logger.error(f"Failed to load pipeline {pipeline_path}: {e}")
        return None
