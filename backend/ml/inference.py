"""
XGBoost inference engine for AQI prediction.
Wraps model loading, prediction, and confidence estimation.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import xgboost as xgb

from backend.config import get_settings, MODEL_DIR
from backend.models.schemas import LiveInferencePayload, PredictionResult
from backend.ml.feature_engineering import payload_to_feature_matrix
from backend.utils.aqi_categories import classify_aqi, get_confidence_label

logger = logging.getLogger(__name__)


class XGBoostInferenceEngine:
    """
    Production-grade inference wrapper for the CleanAir XGBoost model.

    Handles:
    - Model loading from JSON format (faster, more portable than .pkl)
    - Single-sample and batch prediction
    - Confidence estimation via prediction variance heuristic
    - Structured output with AQI classification
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = xgb.XGBRegressor()
        self._model_path = model_path or str(
            MODEL_DIR / get_settings().xgboost_model_path
        )
        self._loaded = False

    def load(self) -> None:
        """Load the trained model from disk."""
        path = Path(self._model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"XGBoost model not found at {path}. "
                f"Ensure 'cleanair_xgb_model.json' is in the project root."
            )
        self._model.load_model(str(path))
        self._loaded = True
        logger.info("XGBoost model loaded from %s", path)

    def ensure_loaded(self) -> None:
        """Lazy-load model on first prediction call."""
        if not self._loaded:
            self.load()

    def predict_raw(self, payload: LiveInferencePayload) -> float:
        """
        Run raw XGBoost prediction. Returns predicted AQI as float.
        """
        self.ensure_loaded()
        X = payload_to_feature_matrix(payload)
        prediction = float(self._model.predict(X)[0])
        return max(0.0, prediction)  # AQI cannot be negative

    def predict(
        self,
        payload: LiveInferencePayload,
        vision_severity_multiplier: float = 1.0,
    ) -> PredictionResult:
        """
        Full inference pipeline producing a structured PredictionResult.

        Args:
            payload: Validated telemetry payload
            vision_severity_multiplier: 1.0–1.5 boost from vision detection

        Returns:
            PredictionResult with estimated AQI, risk level, confidence,
            category classification, and health advisory.
        """
        self.ensure_loaded()

        X = payload_to_feature_matrix(payload)
        base_prediction = float(self._model.predict(X)[0])
        base_prediction = max(0.0, base_prediction)

        # Apply vision-based severity escalation
        multiplier = max(1.0, min(1.5, vision_severity_multiplier))
        adjusted_prediction = base_prediction * multiplier

        # Confidence estimation heuristic:
        # Higher confidence when:
        #   - Input AQI is close to prediction (model agrees with station)
        #   - Weather features are within typical Delhi ranges
        #   - No extreme extrapolation
        input_aqi = payload.us_aqi
        delta = abs(adjusted_prediction - input_aqi)
        # Confidence degrades as prediction diverges from station reading
        # Base confidence of 0.92 (model R² from training), reduced by divergence
        base_confidence = 0.92
        divergence_penalty = min(0.4, delta / 500.0)
        confidence = round(max(0.3, base_confidence - divergence_penalty), 2)

        # Classify the prediction
        category = classify_aqi(adjusted_prediction)

        return PredictionResult(
            estimated_aqi=round(adjusted_prediction, 1),
            risk_level=category.risk_level,
            confidence=confidence,
            pm2_5_predicted=round(payload.pm2_5 * (adjusted_prediction / max(input_aqi, 1.0)), 1),
            category_label=category.label,
            category_color=category.color,
            health_advisory=category.health_advisory,
            is_official=False,
        )


# ── Module-level singleton ──────────────────
_engine: Optional[XGBoostInferenceEngine] = None


def get_inference_engine() -> XGBoostInferenceEngine:
    """Returns a cached singleton inference engine."""
    global _engine
    if _engine is None:
        _engine = XGBoostInferenceEngine()
    return _engine
