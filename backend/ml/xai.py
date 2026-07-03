"""
Explainable AI (XAI) Engine using SHAP.

Explains XGBoost model predictions by determining which environmental 
features contributed most to the final AQI output.
"""

import os
import logging
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class XAIEngine:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.explainer = None
        self.is_initialized = False
        
        self._load_model()

    def _load_model(self):
        """Loads the XGBoost model and initializes the SHAP TreeExplainer."""
        if not os.path.exists(self.model_path):
            logger.warning("Model file not found for XAI at %s", self.model_path)
            return
            
        try:
            self.model = xgb.Booster()
            self.model.load_model(self.model_path)
            # Create a TreeExplainer for the XGBoost model
            self.explainer = shap.TreeExplainer(self.model)
            self.is_initialized = True
            logger.info("Successfully initialized SHAP TreeExplainer.")
        except Exception as e:
            logger.error("Failed to initialize SHAP Explainer: %s", e)

    def explain_prediction(self, feature_vector: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates SHAP values for a single prediction and returns the 
        top contributing features.
        
        Args:
            feature_vector: A 1-row DataFrame containing the model inputs.
            
        Returns:
            Dictionary containing base value, final prediction, and feature contributions.
        """
        if not self.is_initialized or self.explainer is None:
            return {"error": "XAI Engine not initialized"}
            
        try:
            # Calculate SHAP values
            # Output is typically a numpy array of shape (1, num_features)
            shap_values = self.explainer.shap_values(feature_vector)
            
            # The explainer might return a list if it's a multi-class model. 
            # Assuming regression for AQI.
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
                
            base_value = float(self.explainer.expected_value)
            
            # Extract features and their SHAP values
            contributions = []
            features = feature_vector.columns.tolist()
            shap_array = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            
            for i, feature in enumerate(features):
                contributions.append({
                    "feature": feature,
                    "value": float(feature_vector.iloc[0, i]),
                    "shap_value": float(shap_array[i]),
                    "impact": "increases_aqi" if shap_array[i] > 0 else "decreases_aqi",
                    "absolute_impact": float(abs(shap_array[i]))
                })
                
            # Sort by absolute impact to find most important drivers
            contributions = sorted(contributions, key=lambda x: x["absolute_impact"], reverse=True)
            
            # Calculate final prediction as base + sum(shap)
            final_prediction = base_value + sum(c["shap_value"] for c in contributions)
            
            return {
                "base_aqi": base_value,
                "predicted_aqi": final_prediction,
                "top_contributors": contributions[:5], # Top 5 drivers
                "all_contributions": contributions
            }
            
        except Exception as e:
            logger.error("Failed to calculate SHAP values: %s", e)
            return {"error": str(e)}

# Singleton initialization will happen later when model path is known.
