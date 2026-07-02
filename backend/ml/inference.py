"""
XGBoost inference engine for AQI prediction.
Wraps model loading, prediction, confidence estimation, and hourly forecasting.
"""

import logging
from pathlib import Path
from typing import Optional, List

import numpy as np
import xgboost as xgb

from backend.config import get_settings, MODEL_DIR
from backend.models.schemas import (
    LiveInferencePayload,
    PredictionResult,
    HourlyForecastPoint,
)
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
    - Recursive 24-hour hourly forecasting
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

    def predict_hourly_forecast(
        self,
        current_payload: LiveInferencePayload,
        hourly_weather_forecast: List[dict],
        vision_severity_multiplier: float = 1.0,
    ) -> List[HourlyForecastPoint]:
        """
        Generate a 24-hour AQI forecast using recursive single-step
        prediction with hourly weather forecast data.

        Strategy: each future hour uses the previous hour's predicted
        AQI as the input AQI, combined with the weather forecast for
        that hour. Confidence decays over time.

        Args:
            current_payload: The current-hour telemetry payload.
            hourly_weather_forecast: List of dicts, one per future hour,
                with keys: temperature_2m, precipitation, wind_speed_10m,
                wind_direction_10m.
            vision_severity_multiplier: Severity multiplier from Gemini.

        Returns:
            List of HourlyForecastPoint for hours 0 through N.
        """
        self.ensure_loaded()

        # Hour 0: current prediction
        current_result = self.predict(current_payload, vision_severity_multiplier)
        forecast: List[HourlyForecastPoint] = [
            HourlyForecastPoint(
                hour_offset=0,
                estimated_aqi=current_result.estimated_aqi,
                confidence=current_result.confidence,
                weather_summary="Current conditions",
            )
        ]

        # Carry forward values for recursive prediction
        prev_aqi = current_result.estimated_aqi
        prev_pm25 = current_payload.pm2_5
        prev_pm25_1 = current_payload.pm2_5_yesterday_1
        base_confidence = current_result.confidence

        for i, weather in enumerate(hourly_weather_forecast, start=1):
            try:
                # Scale PM2.5 proportionally to AQI change
                scale_ratio = prev_aqi / max(current_payload.us_aqi, 1.0)
                estimated_pm25 = current_payload.pm2_5 * scale_ratio

                future_payload = LiveInferencePayload(
                    us_aqi=prev_aqi,
                    pm10=current_payload.pm10 * scale_ratio,
                    pm2_5=estimated_pm25,
                    carbon_monoxide=current_payload.carbon_monoxide,
                    nitrogen_dioxide=current_payload.nitrogen_dioxide,
                    sulphur_dioxide=current_payload.sulphur_dioxide,
                    ozone=current_payload.ozone,
                    dust=current_payload.dust,
                    pm2_5_yesterday_1=prev_pm25,
                    pm2_5_yesterday_2=prev_pm25_1,
                    tavg=float(weather.get("temperature_2m", current_payload.tavg)),
                    prcp=float(weather.get("precipitation", 0.0)),
                    wspd=float(weather.get("wind_speed_10m", current_payload.wspd)),
                    wdir=max(0.0, min(360.0, float(
                        weather.get("wind_direction_10m", current_payload.wdir)
                    ))),
                )

                raw_pred = self.predict_raw(future_payload)
                multiplier = max(1.0, min(1.5, vision_severity_multiplier))
                adjusted = raw_pred * multiplier

                # Confidence decays by ~2% per forecast hour
                hour_confidence = round(max(0.2, base_confidence - i * 0.02), 2)

                wind_spd = weather.get("wind_speed_10m", "?")
                temp = weather.get("temperature_2m", "?")
                weather_desc = f"Temp: {temp}°C, Wind: {wind_spd} km/h"

                forecast.append(HourlyForecastPoint(
                    hour_offset=i,
                    estimated_aqi=round(adjusted, 1),
                    confidence=hour_confidence,
                    weather_summary=weather_desc,
                ))

                # Carry forward
                prev_pm25_1 = prev_pm25
                prev_pm25 = estimated_pm25
                prev_aqi = adjusted

            except Exception as e:
                logger.warning("Forecast step %d failed: %s", i, e)
                # Fill remaining with last known value
                forecast.append(HourlyForecastPoint(
                    hour_offset=i,
                    estimated_aqi=round(prev_aqi, 1),
                    confidence=0.2,
                    weather_summary="Forecast unavailable",
                ))

        return forecast


# ── Module-level singleton ──────────────────
_engine: Optional[XGBoostInferenceEngine] = None


def get_inference_engine() -> XGBoostInferenceEngine:
    """Returns a cached singleton inference engine."""
    global _engine
    if _engine is None:
        _engine = XGBoostInferenceEngine()
    return _engine
