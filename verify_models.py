import xgboost as xgb
import pandas as pd
import numpy as np
import json
from pathlib import Path
import tempfile
import os

def main():
    model_path = Path("final_json_models/central_pipeline.json")
    print(f"Loading pipeline from {model_path}")
    
    with open(model_path, 'r') as f:
        pipeline_data = json.load(f)
        
    estimators_json = pipeline_data.get('estimators_json', [])
    print(f"Found {len(estimators_json)} estimators in the pipeline.")
    
    models = []
    # Load all 24 models
    for i, est_dict in enumerate(estimators_json):
        model = xgb.XGBRegressor()
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, 'w') as tmp:
            json.dump(est_dict, tmp)
        
        model.load_model(temp_path)
        os.remove(temp_path)
        models.append(model)
        
    print("\n--- Model Feature Inspection ---")
    
    for i, m in enumerate(models):
        try:
            dummy = np.zeros((1, 100))
            m.predict(dummy)
        except ValueError as e:
            error_msg = str(e)
            expected = error_msg.split("expected: ")[1].split(",")[0]
            if i < 3 or i > 21:
                print(f"Model {i+1} expects {expected} features.")
            elif i == 3:
                print("...")
            
    print("\n--- Cascaded Mock Prediction ---")
    current_input = np.zeros((1, 36))
    print(f"Initial Input Shape: {current_input.shape}")
    
    predictions = []
    for i, m in enumerate(models):
        pred = m.predict(current_input)
        predictions.append(pred[0])
        # Append the prediction as a new feature for the next model
        current_input = np.hstack([current_input, pred.reshape(-1, 1)])
        
    predictions = np.array(predictions)
    
    print(f"Final Input Shape after 24 hours: {current_input.shape}")
    print("\n--- Prediction Output ---")
    print(f"Type: {type(predictions)}")
    print(f"Shape: {predictions.shape}")
    print(f"Output contents: {predictions}")

if __name__ == "__main__":
    main()
