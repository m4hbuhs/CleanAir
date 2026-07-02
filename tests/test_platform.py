"""
Test suite for CleanAir & Clear Streets AI platform.
Covers ML inference, feature engineering, hotspot detection, AQI classification,
geo utilities, reward engine, and data schemas.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pydantic import ValidationError


# ─────────────────────────────────────────────
# Test: AQI Categories
# ─────────────────────────────────────────────

class TestAQICategories:
    def test_classify_good(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(30)
        assert cat.label == "Good"
        assert cat.color == "#00E400"
        assert cat.risk_level == "Low"

    def test_classify_moderate(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(75)
        assert cat.label == "Moderate"

    def test_classify_unhealthy(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(180)
        assert cat.label == "Unhealthy"
        assert cat.risk_level == "Very High"

    def test_classify_hazardous(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(450)
        assert cat.label == "Hazardous"
        assert cat.risk_level == "Emergency"

    def test_classify_beyond_500(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(600)
        assert cat.label == "Hazardous"

    def test_classify_negative(self):
        from backend.utils.aqi_categories import classify_aqi
        cat = classify_aqi(-10)
        assert cat.label == "Good"

    def test_risk_score(self):
        from backend.utils.aqi_categories import get_aqi_risk_score
        assert get_aqi_risk_score(0) == 0.0
        assert get_aqi_risk_score(250) == 0.5
        assert get_aqi_risk_score(500) == 1.0
        assert get_aqi_risk_score(600) == 1.0

    def test_confidence_label(self):
        from backend.utils.aqi_categories import get_confidence_label
        assert get_confidence_label(0.95) == "Very High"
        assert get_confidence_label(0.80) == "High"
        assert get_confidence_label(0.65) == "Moderate"
        assert get_confidence_label(0.45) == "Low"
        assert get_confidence_label(0.20) == "Very Low"


# ─────────────────────────────────────────────
# Test: Geo Utilities
# ─────────────────────────────────────────────

class TestGeoUtils:
    def test_haversine_same_point(self):
        from backend.utils.geo_utils import haversine_km
        assert haversine_km(28.6, 77.2, 28.6, 77.2) == 0.0

    def test_haversine_known_distance(self):
        from backend.utils.geo_utils import haversine_km
        # Delhi to Noida ≈ 20 km
        dist = haversine_km(28.6139, 77.2090, 28.5355, 77.3910)
        assert 15 < dist < 25

    def test_grid_generation_has_points(self):
        from backend.utils.geo_utils import generate_grid
        points = generate_grid(28.6139, 77.2090, radius_km=2.0, resolution_meters=500)
        assert len(points) > 10

    def test_grid_generation_within_radius(self):
        from backend.utils.geo_utils import generate_grid, haversine_km
        points = generate_grid(28.6139, 77.2090, radius_km=2.0, resolution_meters=500)
        for p in points:
            dist = haversine_km(28.6139, 77.2090, p.latitude, p.longitude)
            assert dist <= 2.1  # Small margin for floating point

    def test_bounding_box(self):
        from backend.utils.geo_utils import bounding_box
        min_lat, min_lon, max_lat, max_lon = bounding_box(28.6, 77.2, 5.0)
        assert min_lat < 28.6 < max_lat
        assert min_lon < 77.2 < max_lon


# ─────────────────────────────────────────────
# Test: Pydantic Schemas
# ─────────────────────────────────────────────

class TestSchemas:
    def test_valid_payload(self):
        from backend.models.schemas import LiveInferencePayload
        payload = LiveInferencePayload(
            us_aqi=120, pm10=80, pm2_5=55, carbon_monoxide=900,
            nitrogen_dioxide=40, sulphur_dioxide=15, ozone=60, dust=2.5,
            pm2_5_yesterday_1=50, pm2_5_yesterday_2=48,
            tavg=31, prcp=0, wspd=6.2, wdir=240,
        )
        assert payload.us_aqi == 120.0
        assert payload.pm2_5 == 55.0

    def test_invalid_wind_direction(self):
        from backend.models.schemas import LiveInferencePayload
        with pytest.raises(ValidationError):
            LiveInferencePayload(
                us_aqi=100, pm10=50, pm2_5=30, carbon_monoxide=500,
                nitrogen_dioxide=25, sulphur_dioxide=10, ozone=45, dust=1.0,
                pm2_5_yesterday_1=28, pm2_5_yesterday_2=29,
                tavg=28, prcp=0, wspd=5.0, wdir=550,  # Invalid: > 360
            )

    def test_negative_pm25_rejected(self):
        from backend.models.schemas import LiveInferencePayload
        with pytest.raises(ValidationError):
            LiveInferencePayload(
                us_aqi=100, pm10=50, pm2_5=-10, carbon_monoxide=500,
                nitrogen_dioxide=25, sulphur_dioxide=10, ozone=45, dust=1.0,
                pm2_5_yesterday_1=28, pm2_5_yesterday_2=29,
                tavg=28, prcp=0, wspd=5.0, wdir=180,
            )

    def test_citizen_report_defaults(self):
        from backend.models.schemas import CitizenReport
        report = CitizenReport(latitude=28.6, longitude=77.2)
        assert report.status.value == "pending"
        assert report.tokens_awarded == 0


# ─────────────────────────────────────────────
# Test: Feature Engineering
# ─────────────────────────────────────────────

class TestFeatureEngineering:
    def _make_payload(self):
        from backend.models.schemas import LiveInferencePayload
        return LiveInferencePayload(
            us_aqi=120, pm10=80, pm2_5=55, carbon_monoxide=900,
            nitrogen_dioxide=40, sulphur_dioxide=15, ozone=60, dust=2.5,
            pm2_5_yesterday_1=50, pm2_5_yesterday_2=48,
            tavg=31, prcp=0, wspd=6.2, wdir=240,
        )

    def test_feature_matrix_shape(self):
        from backend.ml.feature_engineering import payload_to_feature_matrix
        payload = self._make_payload()
        X = payload_to_feature_matrix(payload)
        assert X.shape == (1, 14)

    def test_feature_order(self):
        from backend.ml.feature_engineering import payload_to_feature_matrix, ORDERED_FEATURES
        payload = self._make_payload()
        X = payload_to_feature_matrix(payload)
        assert list(X.columns) == ORDERED_FEATURES

    def test_rolling_average(self):
        from backend.ml.feature_engineering import payload_to_feature_matrix
        payload = self._make_payload()
        X = payload_to_feature_matrix(payload)
        expected_roll = (55 + 50 + 48) / 3
        assert abs(X["pm2_5_roll3"].values[0] - expected_roll) < 0.01

    def test_wind_decomposition(self):
        from backend.ml.feature_engineering import payload_to_feature_matrix
        payload = self._make_payload()
        X = payload_to_feature_matrix(payload)
        wind_u = X["wind_u"].values[0]
        wind_v = X["wind_v"].values[0]
        # Reconstructed speed should match original
        reconstructed_speed = np.sqrt(wind_u**2 + wind_v**2)
        assert abs(reconstructed_speed - 6.2) < 0.01


# ─────────────────────────────────────────────
# Test: XGBoost Inference
# ─────────────────────────────────────────────

class TestXGBoostInference:
    def test_model_loads(self):
        from backend.ml.inference import get_inference_engine
        engine = get_inference_engine()
        engine.ensure_loaded()
        assert engine._loaded is True

    def test_prediction_returns_result(self):
        from backend.ml.inference import get_inference_engine
        from backend.models.schemas import LiveInferencePayload
        engine = get_inference_engine()
        payload = LiveInferencePayload(
            us_aqi=120, pm10=80, pm2_5=55, carbon_monoxide=900,
            nitrogen_dioxide=40, sulphur_dioxide=15, ozone=60, dust=2.5,
            pm2_5_yesterday_1=50, pm2_5_yesterday_2=48,
            tavg=31, prcp=0, wspd=6.2, wdir=240,
        )
        result = engine.predict(payload)
        assert result.estimated_aqi > 0
        assert 0 < result.confidence <= 1.0
        assert result.risk_level in ["Low", "Moderate", "High", "Very High", "Severe", "Emergency"]
        assert result.is_official is False
        assert len(result.disclaimer) > 0

    def test_vision_multiplier_effect(self):
        from backend.ml.inference import get_inference_engine
        from backend.models.schemas import LiveInferencePayload
        engine = get_inference_engine()
        payload = LiveInferencePayload(
            us_aqi=120, pm10=80, pm2_5=55, carbon_monoxide=900,
            nitrogen_dioxide=40, sulphur_dioxide=15, ozone=60, dust=2.5,
            pm2_5_yesterday_1=50, pm2_5_yesterday_2=48,
            tavg=31, prcp=0, wspd=6.2, wdir=240,
        )
        base = engine.predict(payload, vision_severity_multiplier=1.0)
        boosted = engine.predict(payload, vision_severity_multiplier=1.3)
        assert boosted.estimated_aqi > base.estimated_aqi


# ─────────────────────────────────────────────
# Test: Hotspot Detection
# ─────────────────────────────────────────────

class TestHotspotDetection:
    def test_no_reports(self):
        from backend.services.hotspot_service import detect_hotspots
        clusters = detect_hotspots([])
        assert clusters == []

    def test_single_report(self):
        from backend.services.hotspot_service import detect_hotspots
        from backend.models.schemas import CitizenReport, IncidentSeverity
        reports = [CitizenReport(latitude=28.6, longitude=77.2, severity=IncidentSeverity(3))]
        clusters = detect_hotspots(reports)
        assert clusters == []

    def test_cluster_formation(self):
        from backend.services.hotspot_service import detect_hotspots
        from backend.models.schemas import CitizenReport, PollutionType, IncidentSeverity
        reports = [
            CitizenReport(latitude=28.620, longitude=77.210, pollution_type=PollutionType.GARBAGE_BURNING, severity=IncidentSeverity(4)),
            CitizenReport(latitude=28.621, longitude=77.211, pollution_type=PollutionType.GARBAGE_BURNING, severity=IncidentSeverity(4)),
            CitizenReport(latitude=28.622, longitude=77.212, pollution_type=PollutionType.GARBAGE_BURNING, severity=IncidentSeverity(3)),
        ]
        clusters = detect_hotspots(reports)
        assert len(clusters) >= 1
        assert clusters[0].report_count >= 3
        assert clusters[0].dominant_pollution_type == "Garbage Burning"


# ─────────────────────────────────────────────
# Test: Reward Engine
# ─────────────────────────────────────────────

class TestRewardEngine:
    def test_base_tokens(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenReport, IncidentSeverity
        engine = RewardEngine()
        report = CitizenReport(latitude=28.6, longitude=77.2, severity=IncidentSeverity(2))
        tokens = engine.calculate_tokens(report)
        assert tokens == 10  # Base tokens

    def test_high_severity_bonus(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenReport, IncidentSeverity
        engine = RewardEngine()
        report = CitizenReport(latitude=28.6, longitude=77.2, severity=IncidentSeverity(4))
        tokens = engine.calculate_tokens(report)
        assert tokens == 25  # Base 10 + high severity 15

    def test_fake_upload_zero_tokens(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenReport, VisionClassification, IncidentSeverity
        engine = RewardEngine()
        from backend.models.schemas import VisionClassification, PollutionType, IncidentSeverity, CitizenReport
        engine = RewardEngine()
        report = CitizenReport(latitude=28.6, longitude=77.2, severity=IncidentSeverity(4))
        classification = VisionClassification(
            is_fake_upload=True,
            pollution_type=PollutionType.UNKNOWN,
            severity=IncidentSeverity.MINIMAL,
            confidence=0.0,
            severity_multiplier=1.0,
            description="Fake"
        )
        tokens = engine.calculate_tokens(report, classification)
        assert tokens == 0

    def test_wallet_award(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenWallet
        engine = RewardEngine()
        wallet = CitizenWallet(user_id="test_user")
        wallet = engine.award_tokens(wallet, 50, "Test award")
        assert wallet.total_tokens == 50
        assert wallet.total_reports == 1
        assert len(wallet.transactions) == 1
        assert "first_report" in wallet.badges

    def test_leaderboard_sorting(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenWallet
        engine = RewardEngine()
        wallets = [
            CitizenWallet(user_id="a", total_tokens=100),
            CitizenWallet(user_id="b", total_tokens=300),
            CitizenWallet(user_id="c", total_tokens=200),
        ]
        lb = engine.get_leaderboard(wallets)
        assert lb[0].user_id == "b"
        assert lb[0].rank == 1
        assert lb[1].user_id == "c"
        assert lb[2].user_id == "a"

    def test_redeem_insufficient(self):
        from backend.services.reward_service import RewardEngine
        from backend.models.schemas import CitizenWallet
        engine = RewardEngine()
        wallet = CitizenWallet(user_id="broke", total_tokens=5)
        success, msg = engine.redeem_reward(wallet, "metro_pass_1")
        assert success is False
        assert "Insufficient" in msg


# ─────────────────────────────────────────────
# Test: Database (InMemoryDB)
# ─────────────────────────────────────────────

class TestInMemoryDB:
    def test_add_and_get_report(self):
        from backend.database.firestore_client import InMemoryDB
        from backend.models.schemas import CitizenReport
        db = InMemoryDB()
        report = CitizenReport(latitude=28.6, longitude=77.2, description="test")
        saved = db.add_report(report)
        assert saved.report_id != ""
        retrieved = db.get_report(saved.report_id)
        assert retrieved.description == "test"

    def test_wallet_creation(self):
        from backend.database.firestore_client import InMemoryDB
        db = InMemoryDB()
        wallet = db.get_wallet("new_user")
        assert wallet.user_id == "new_user"
        assert wallet.total_tokens == 0

    def test_stats(self):
        from backend.database.firestore_client import InMemoryDB
        from backend.models.schemas import CitizenReport
        db = InMemoryDB()
        db.add_report(CitizenReport(latitude=28.6, longitude=77.2))
        db.add_report(CitizenReport(latitude=28.7, longitude=77.3))
        stats = db.get_stats()
        assert stats["total_reports"] == 2


# ─────────────────────────────────────────────
# Test: Plume Model
# ─────────────────────────────────────────────

class TestPlumeModel:
    def test_plume_generates_points(self):
        from backend.services.plume_service import generate_plume_geometry
        df = generate_plume_geometry(28.6, 77.2, wind_u=3.0, wind_v=2.0, aqi_weight=150)
        assert len(df) > 50
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "weight" in df.columns

    def test_plume_zero_wind(self):
        from backend.services.plume_service import generate_plume_geometry
        df = generate_plume_geometry(28.6, 77.2, wind_u=0.0, wind_v=0.0, aqi_weight=150)
        assert len(df) > 0  # Should still generate radial spread

# ─────────────────────────────────────────────
# Test: Virtual Sensor Network Components
# ─────────────────────────────────────────────

class TestGeminiPollutionFeatures:
    def test_to_numerical_scores_default(self):
        from backend.models.schemas import GeminiPollutionFeatures
        features = GeminiPollutionFeatures(pollution_type="Unknown", severity="Low", confidence=0.8)
        scores = features.to_numerical_scores()
        assert scores["severity_score"] == 0.2
        assert scores["dust_score"] == 0.0
        assert scores["smoke_score"] == 0.0
        assert scores["construction_score"] == 0.0

    def test_to_numerical_scores_high(self):
        from backend.models.schemas import GeminiPollutionFeatures
        features = GeminiPollutionFeatures(
            pollution_type="Construction Dust", 
            severity="High", 
            confidence=0.9,
            construction_detected=True,
            dust_detected=True
        )
        scores = features.to_numerical_scores()
        assert scores["severity_score"] == 0.8
        assert scores["dust_score"] == 1.0
        assert scores["construction_score"] == 1.0


class TestConfidenceScoring:
    def test_high_confidence(self):
        from backend.ml.confidence import compute_confidence
        conf = compute_confidence(
            distance_to_station_km=1.0, 
            citizen_report_count=5, 
            gemini_confidence=0.9, 
            data_freshness_minutes=5, 
            missing_feature_count=0
        )
        assert conf.overall_pct > 80
        assert conf.confidence_label == "High"

    def test_low_confidence(self):
        from backend.ml.confidence import compute_confidence
        conf = compute_confidence(
            distance_to_station_km=15.0, 
            citizen_report_count=0, 
            gemini_confidence=None, 
            data_freshness_minutes=120, 
            missing_feature_count=4
        )
        assert conf.overall_pct < 50
        assert conf.confidence_label == "Low"


class TestAlertEngine:
    def test_evaluate_alerts_trigger(self):
        from backend.services.alert_engine import evaluate_alerts
        from backend.models.schemas import CitizenReport, IncidentSeverity, PollutionType
        
        # 3 reports to cross the threshold
        reports = [
            CitizenReport(latitude=28.6, longitude=77.2, severity=IncidentSeverity.HIGH, pollution_type=PollutionType.CONSTRUCTION)
            for _ in range(4)
        ]
        alerts = evaluate_alerts(
            estimated_aqi=160, 
            confidence_pct=75, 
            citizen_reports=reports, 
            latitude=28.6, 
            longitude=77.2
        )
        assert len(alerts) > 0
        assert alerts[0].estimated_aqi == 160
        assert "Construction" in alerts[0].pollution_type

    def test_evaluate_alerts_no_trigger(self):
        from backend.services.alert_engine import evaluate_alerts
        alerts = evaluate_alerts(
            estimated_aqi=100, 
            confidence_pct=80, 
            citizen_reports=[], 
            latitude=28.6, 
            longitude=77.2
        )
        assert len(alerts) == 0


class TestSatelliteService:
    def test_mock_satellite_provider(self):
        from backend.services.satellite_service import fetch_satellite_features
        features = fetch_satellite_features(28.6, 77.2)
        assert features is not None
        assert features.aerosol_optical_depth >= 0


class TestVirtualSensorEngine:
    def test_estimate_aqi_fallback(self):
        from backend.services.virtual_sensor_engine import VirtualSensorEngine
        engine = VirtualSensorEngine()
        # With no DB/API mocks, it should still return a result
        result = engine.estimate_aqi(28.6, 77.2)
        assert result.estimated_aqi > 0
        assert result.confidence is not None


class TestHourlyForecast:
    def test_hourly_forecast(self):
        from backend.services.virtual_sensor_engine import VirtualSensorEngine
        engine = VirtualSensorEngine()
        result = engine.estimate_aqi(28.6, 77.2)
        assert len(result.hourly_forecast) > 0
        assert result.hourly_forecast[0].hour_offset == 0  # Starts at hour 0 (current)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
