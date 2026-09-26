"""
Validation Tests for State-Level Mortality Inference Service & Model Artifacts
Phase 8, 9, 14 / Requirements Checklist 15-23, 34, 35, 43
"""

import pytest
import os
from backend.services.mortality_service import mortality_service, STATE_BASELINES

def test_model_artifacts_exist():
    assert mortality_service.model_path.exists(), "Mortality model pipeline joblib artifact missing"
    assert mortality_service.feature_config_path.exists(), "Feature config JSON missing"
    assert mortality_service.metrics_path.exists(), "Validation metrics JSON missing"
    assert mortality_service.is_loaded, "Mortality model pipeline failed to load into service"

def test_leakage_exclusion():
    feature_cols = mortality_service.feature_config.get("feature_columns", [])
    excluded = mortality_service.feature_config.get("excluded_columns", [])
    
    # Must NOT include target or outcome-derived death totals
    assert "heat_related_mortality_rate_per_100000" not in feature_cols
    assert "heatstroke_deaths" not in feature_cols
    assert "heat_related_deaths_total" not in feature_cols
    assert "expected_heat_related_deaths" not in feature_cols
    assert "mortality_anomaly" not in feature_cols

def test_state_level_inference():
    for state in ["Tamil Nadu", "Kerala", "Karnataka"]:
        res = mortality_service.predict_state_mortality(state, [], mode="LIVE")
        assert res["state"] == state
        assert res["predicted_mortality_rate_per_100000"] >= 0.0
        assert "risk_context" in res
        assert "model_version" in res
        assert "synthetic_disclaimer" in res
        assert "STATE_LEVEL_ONLY" in res["spatial_scope"]

def test_invalid_state_rejection():
    with pytest.raises(ValueError):
        mortality_service.build_state_feature_vector("Delhi", [])

def test_mortality_model_deterministic_consistency():
    """
    Requirements Checklist Section 12:
    Fixed input vector evaluated multiple times must produce identical deterministic outputs.
    """
    fixed_weather = [
        {"temperature_c": 36.5, "relative_humidity": 65.0, "wind_speed_mps": 2.1, "data_quality": "VALID"},
        {"temperature_c": 37.0, "relative_humidity": 62.0, "wind_speed_mps": 2.3, "data_quality": "VALID"}
    ]
    
    # Run inference 10 times with identical input
    predictions = []
    for _ in range(10):
        res = mortality_service.predict_state_mortality("Tamil Nadu", fixed_weather, mode="LIVE")
        predictions.append(res["predicted_mortality_rate_per_100000"])
        
    # All 10 predictions must be strictly equal
    assert len(set(predictions)) == 1, f"Non-deterministic predictions detected: {predictions}"
    assert predictions[0] > 0.0

def test_mortality_model_input_perturbation_sensitivity():
    """
    Requirements Checklist Section 12:
    Controlled changes in thermal stress variables must traceably shift predictions.
    """
    # 1. Baseline temperate weather
    cool_weather = [
        {"temperature_c": 28.0, "relative_humidity": 50.0, "wind_speed_mps": 3.0, "data_quality": "VALID"}
    ]
    res_cool = mortality_service.predict_state_mortality("Tamil Nadu", cool_weather)

    # 2. Severe heatwave weather
    hot_weather = [
        {"temperature_c": 41.0, "relative_humidity": 70.0, "wind_speed_mps": 1.0, "data_quality": "VALID"}
    ]
    res_hot = mortality_service.predict_state_mortality("Tamil Nadu", hot_weather)

    # Hot condition should yield a higher predicted mortality rate than cool baseline
    rate_cool = res_cool["predicted_mortality_rate_per_100000"]
    rate_hot = res_hot["predicted_mortality_rate_per_100000"]
    
    assert rate_hot > rate_cool, f"Expected hot rate ({rate_hot}) > cool rate ({rate_cool})"
    print(f"Verified Traceability: Cool baseline rate={rate_cool:.6f}, Severe heatwave rate={rate_hot:.6f}")
