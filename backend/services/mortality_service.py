"""
Ushna Kaappaan — State-Level Heat-Related Mortality Inference Service
Phase 9 / Requirements Checklist 15-23, 43
"""

import math
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from backend.config import settings
from backend.services.weather_provider import utc_to_ist_str

logger = logging.getLogger("ushna.mortality")

# State baseline profiles (from dataset calibration metadata)
STATE_BASELINES = {
    "Tamil Nadu": {
        "population": 77000000,
        "elderly_population_percent": 13.0,
        "working_age_population_percent": 40.0,
        "under_30_population_percent": 47.0,
        "outdoor_worker_fraction": 0.36,
        "urban_population_percent": 55.0,
        "healthcare_access_index": 0.78,
        "heat_action_plan_index": 0.60,
        "cooling_access_index": 0.55,
        "public_health_response_index": 0.55
    },
    "Kerala": {
        "population": 35800000,
        "elderly_population_percent": 17.0,
        "working_age_population_percent": 45.0,
        "under_30_population_percent": 38.0,
        "outdoor_worker_fraction": 0.28,
        "urban_population_percent": 50.0,
        "healthcare_access_index": 0.85,
        "heat_action_plan_index": 0.65,
        "cooling_access_index": 0.55,
        "public_health_response_index": 0.60
    },
    "Karnataka": {
        "population": 68000000,
        "elderly_population_percent": 11.5,
        "working_age_population_percent": 38.5,
        "under_30_population_percent": 50.0,
        "outdoor_worker_fraction": 0.45,
        "urban_population_percent": 42.0,
        "healthcare_access_index": 0.70,
        "heat_action_plan_index": 0.55,
        "cooling_access_index": 0.50,
        "public_health_response_index": 0.50
    }
}

class MortalityInferenceService:
    def __init__(self):
        self.artifacts_dir = settings.MODEL_ARTIFACTS_DIR
        self.model_path = self.artifacts_dir / "mortality_model_pipeline.joblib"
        self.feature_config_path = self.artifacts_dir / "feature_config.json"
        self.metadata_path = self.artifacts_dir / "model_metadata.json"
        self.metrics_path = self.artifacts_dir / "validation_metrics.json"
        
        self.pipeline = None
        self.feature_config = {}
        self.model_metadata = {}
        self.validation_metrics = {}
        self.is_loaded = False
        
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            if self.model_path.exists():
                self.pipeline = joblib.load(self.model_path)
                logger.info(f"Loaded trained mortality model pipeline from {self.model_path}")
            else:
                logger.warning(f"Mortality model artifact not found at {self.model_path}")
                
            if self.feature_config_path.exists():
                with open(self.feature_config_path, "r") as f:
                    self.feature_config = json.load(f)
                    
            if self.metadata_path.exists():
                with open(self.metadata_path, "r") as f:
                    self.model_metadata = json.load(f)
                    
            if self.metrics_path.exists():
                with open(self.metrics_path, "r") as f:
                    self.validation_metrics = json.load(f)
                    
            if self.pipeline is not None and "feature_columns" in self.feature_config:
                self.is_loaded = True
        except Exception as e:
            logger.error(f"Error loading mortality model artifacts: {e}")
            self.is_loaded = False

    def build_state_feature_vector(self, state: str, district_weather_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Builds a single-row DataFrame matching the exact trained FEATURE_COLUMNS for the state.
        """
        if state not in STATE_BASELINES:
            raise ValueError(f"State '{state}' not supported. Supported states: {list(STATE_BASELINES.keys())}")
            
        base = STATE_BASELINES[state]
        
        # Aggregate weather across state districts
        if district_weather_list:
            temps = [w["temperature_c"] for w in district_weather_list if w.get("data_quality") == "VALID"]
            rhs = [w["relative_humidity"] for w in district_weather_list if w.get("data_quality") == "VALID"]
            winds = [w["wind_speed_mps"] for w in district_weather_list if w.get("data_quality") == "VALID"]
        else:
            temps, rhs, winds = [33.0], [60.0], [2.5]
            
        mean_t = float(np.mean(temps)) if temps else 33.0
        max_t = float(np.max(temps)) if temps else 36.0
        min_t = float(np.min(temps)) if temps else 26.0
        mean_rh = float(np.mean(rhs)) if rhs else 60.0
        mean_wind = float(np.mean(winds)) if winds else 2.5
        
        # Calculate derived physics
        # Dew point
        a, b = 17.27, 237.7
        alpha = ((a * mean_t) / (b + mean_t)) + math.log(max(0.01, mean_rh / 100.0))
        dew_point_c = (b * alpha) / (a - alpha)
        
        # Heat index (Celsius)
        # Simplified Rothfusz polynomial in Celsius
        tf = (max_t * 9/5) + 32
        hi_f = -42.379 + 2.04901523*tf + 10.14333127*mean_rh - 0.22475541*tf*mean_rh - 6.83783e-3*(tf**2) - 5.481717e-2*(mean_rh**2) + 1.22874e-3*(tf**2)*mean_rh + 8.5282e-4*tf*(mean_rh**2) - 1.99e-6*(tf**2)*(mean_rh**2)
        heat_index_c = (hi_f - 32) * 5/9
        
        # WBGT approximation
        wbgt_c = 0.7 * dew_point_c + 0.2 * (max_t + 2.0) + 0.1 * max_t
        
        # Nighttime heat stress & anomalies
        nighttime_min_t = min_t + 1.2
        nighttime_heat_stress = max(0.0, min(1.0, (nighttime_min_t - 24.0) / 6.0))
        humidity_burden = max(0.0, min(1.0, (dew_point_c - 18.0) / 8.0))
        
        temp_anom = max_t - 34.0
        humid_anom = mean_rh - 65.0
        
        heatwave_flag = 1 if (max_t >= 37.0 and temp_anom >= 2.0) else 0
        consec_hot = 3 if heatwave_flag else 1
        consec_heat = 2 if wbgt_c >= 30.0 else 0
        hours_above_35 = max(0, int((max_t - 33.0) * 2.5))
        heat_dur = max(0, int((wbgt_c - 28.0) * 2.0))
        
        # Indices
        outdoor_exp_idx = (base["outdoor_worker_fraction"] / 0.6) * 0.9
        urban_heat_idx = 0.8 * (base["urban_population_percent"] / 100.0) + 0.12 * max(0.0, min(1.0, (max_t - 32.0) / 8.0))
        pop_exp_idx = 0.5 * (base["population"] / 80000000) + 0.3 * (base["urban_population_percent"] / 100.0) + 0.2 * outdoor_exp_idx
        vul_idx = 0.35 * (base["elderly_population_percent"] / 20.0) + 0.25 * (base["outdoor_worker_fraction"] / 0.6) + 0.25 * (1.0 - base["healthcare_access_index"]) + 0.15 * (1.0 - base["cooling_access_index"])
        
        heat_exp_idx = max(0.0, (max_t - 30.0) * 0.25 + (wbgt_c - 26.0) * 0.35)
        
        row_dict = {
            "population": base["population"],
            "elderly_population_percent": base["elderly_population_percent"],
            "working_age_population_percent": base["working_age_population_percent"],
            "under_30_population_percent": base["under_30_population_percent"],
            "outdoor_worker_fraction": base["outdoor_worker_fraction"],
            "urban_population_percent": base["urban_population_percent"],
            "maximum_temperature_c": max_t,
            "minimum_temperature_c": min_t,
            "mean_temperature_c": mean_t,
            "relative_humidity_percent": mean_rh,
            "wind_speed_mps": mean_wind,
            "dew_point_c": dew_point_c,
            "heat_index_c": heat_index_c,
            "wbgt_c": wbgt_c,
            "hours_above_heat_threshold": hours_above_35,
            "nighttime_min_temperature_c": nighttime_min_t,
            "heatwave_day": heatwave_flag,
            "consecutive_hot_days": consec_hot,
            "temperature_anomaly_c": temp_anom,
            "humidity_anomaly_percent": humid_anom,
            "heat_duration_hours": heat_dur,
            "consecutive_heat_days": consec_heat,
            "nighttime_heat_stress": nighttime_heat_stress,
            "humidity_burden": humidity_burden,
            "outdoor_exposure_index": outdoor_exp_idx,
            "urban_heat_index": urban_heat_idx,
            "population_exposure_index": pop_exp_idx,
            "vulnerability_index": vul_idx,
            "public_health_response_index": base["public_health_response_index"],
            "healthcare_access_index": base["healthcare_access_index"],
            "heat_action_plan_index": base["heat_action_plan_index"],
            "cooling_access_index": base["cooling_access_index"],
            "heat_exposure_index": heat_exp_idx,
            "heat_exposure_lag_1": heat_exp_idx * 0.95,
            "heat_exposure_lag_2": heat_exp_idx * 0.90,
            "heat_exposure_lag_3": heat_exp_idx * 0.85,
            "heat_exposure_lag_7": heat_exp_idx * 0.70,
            "cumulative_heat_load_3day": heat_exp_idx * 2.8,
            "cumulative_heat_load_7day": heat_exp_idx * 6.2
        }
        
        feature_cols = self.feature_config.get("feature_columns", list(row_dict.keys()))
        df = pd.DataFrame([row_dict])[feature_cols]
        return df

    def predict_state_mortality(self, state: str, district_weather_list: List[Dict[str, Any]], mode: str = "LIVE") -> Dict[str, Any]:
        """
        Executes real inference on the trained model pipeline. Returns state-level continuous mortality estimate.
        """
        if not self.is_loaded:
            self._load_artifacts()
            if not self.is_loaded:
                return {
                    "state": state,
                    "status": "UNAVAILABLE",
                    "error": "Mortality model artifact not loaded"
                }
                
        df_features = self.build_state_feature_vector(state, district_weather_list)
        
        # Real inference from trained Ridge regression pipeline
        raw_pred = float(self.pipeline.predict(df_features)[0])
        pred_rate_per_100k = max(0.0, raw_pred)
        
        # Prototype application risk categorization (matching model_metadata.json risk_band_interpretation)
        if pred_rate_per_100k > 0.30:
            risk_context = "Severe Cumulative Heat Risk"
            badge_color = "red"
        elif pred_rate_per_100k > 0.15:
            risk_context = "High Heat-Related Mortality Risk"
            badge_color = "orange"
        elif pred_rate_per_100k > 0.05:
            risk_context = "Elevated Mortality Risk Context"
            badge_color = "amber"
        else:
            risk_context = "Baseline Background Level"
            badge_color = "green"
            
        dt_utc = datetime.now(timezone.utc)
        per_capita_daily = pred_rate_per_100k / 100000.0
        
        return {
            "state": state,
            "timestamp_utc": dt_utc.isoformat(),
            "timestamp_ist": utc_to_ist_str(dt_utc),
            "predicted_mortality_rate_per_100000": round(pred_rate_per_100k, 6),
            "predicted_rate_display": f"{pred_rate_per_100k:.4f} per 100,000 (daily)",
            "predicted_per_capita_daily": f"{per_capita_daily:.8e}",
            "unit": "deaths per 100,000 population per day",
            "risk_context": risk_context,
            "badge_color": badge_color,
            "model_name": self.model_metadata.get("model_name", "Ushna Kaappaan Mortality Model"),
            "model_version": self.model_metadata.get("model_version", "v1.0.0-synthetic-prototype"),
            "algorithm": self.model_metadata.get("algorithm", "Ridge_Regression"),
            "data_type": "SYNTHETIC (Guin et al. 2025 statistical calibration)",
            "spatial_scope": "STATE_LEVEL_ONLY (District-level prediction strictly disallowed)",
            "mode": mode,
            "validation_summary": self.validation_metrics.get("validation_metrics", {}),
            "synthetic_disclaimer": "PROTOTYPE ESTIMATE ONLY: Trained on synthetic calibration data (Guin et al. 2025 statistical baseline). For academic benchmarking only. Not official NCRB/IMD casualty statistics. Must not be used for clinical or administrative casualty forecasting."
        }

# Singleton
mortality_service = MortalityInferenceService()
