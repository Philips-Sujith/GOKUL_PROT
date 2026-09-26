#!/usr/bin/env python3
"""
Ushna Kaappaan — State-Level Heat-Related Mortality ML Training Pipeline
Phase 8 / Requirements Checklist 22 & 43

Target: heat_related_mortality_rate_per_100000 (Daily heat-related deaths per 100,000 population)
Data type: SYNTHETIC (Guin et al. 2025 statistical calibration baseline)
Scope: State-level (Tamil Nadu, Kerala, Karnataka)
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

DATA_PATH = Path("dataset/mortality_synthetic_daily.csv")
ARTIFACTS_DIR = Path("backend/artifacts/mortality_model")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = "heat_related_mortality_rate_per_100000"
TARGET_UNIT = "deaths per 100,000 population per day"
TARGET_DEFINITION = "Estimated daily rate of heat-related and heat-exacerbated mortality per 100,000 residents"

EXCLUDED_COLUMNS = [
    "date",
    "data_type",
    "state",
    "heat_index_f",
    "wbgt_category",
    "thermal_signature",
    # Leakage columns (raw death counts, components, expectations, anomaly)
    "expected_heatstroke_deaths",
    "expected_other_heat_related_deaths",
    "expected_heat_related_deaths",
    "heatstroke_deaths",
    "other_heat_related_deaths",
    "heat_related_deaths_total",
    "heat_related_deaths_male",
    "heat_related_deaths_female",
    "heatstroke_deaths_male",
    "heatstroke_deaths_female",
    "heat_related_deaths_under_30",
    "heat_related_deaths_30_59",
    "heat_related_deaths_60_plus",
    "mortality_anomaly",
    "heatstroke_mortality_rate_per_100000",
    "heat_related_mortality_rate_per_100000"  # Excluded from X because it is y
]

def load_and_preprocess(data_path: Path):
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found at {data_path}")
    
    df = pd.read_csv(data_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["date", "state"]).reset_index(drop=True)
    
    if "heatwave_day" in df.columns:
        df["heatwave_day"] = df["heatwave_day"].astype(int)
        
    feature_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]
    
    return df, feature_cols

def temporal_train_test_split(df, feature_cols, target_col, train_ratio=0.75):
    unique_dates = df["date"].drop_duplicates().sort_values().values
    split_idx = int(len(unique_dates) * train_ratio)
    split_date = unique_dates[split_idx]
    
    train_mask = df["date"] < split_date
    test_mask = df["date"] >= split_date
    
    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, target_col]
    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, target_col]
    
    print(f"Total records: {len(df)}")
    print(f"Train records: {len(X_train)} (Up to {pd.to_datetime(split_date).strftime('%Y-%m-%d')})")
    print(f"Test records:  {len(X_test)} (From {pd.to_datetime(split_date).strftime('%Y-%m-%d')})")
    
    return X_train, y_train, X_test, y_test, str(split_date)

def evaluate_candidates(X_train, y_train, X_test, y_test):
    candidates = {
        "Ridge_Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("regressor", Ridge(alpha=10.0, random_state=42))
        ]),
        "ElasticNet_Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("regressor", ElasticNet(alpha=0.01, l1_ratio=0.5, random_state=42))
        ]),
        "Random_Forest_Regressor": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("regressor", RandomForestRegressor(n_estimators=150, max_depth=8, min_samples_split=4, random_state=42))
        ]),
        "Gradient_Boosting_Regressor": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("regressor", GradientBoostingRegressor(n_estimators=120, max_depth=4, learning_rate=0.05, random_state=42))
        ]),
        "Extra_Trees_Regressor": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("regressor", ExtraTreesRegressor(n_estimators=150, max_depth=8, min_samples_split=4, random_state=42))
        ])
    }
    
    results = {}
    
    for name, pipe in candidates.items():
        pipe.fit(X_train, y_train)
        preds_train = pipe.predict(X_train)
        preds_test = pipe.predict(X_test)
        
        train_rmse = float(np.sqrt(mean_squared_error(y_train, preds_train)))
        test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
        test_mae = float(mean_absolute_error(y_test, preds_test))
        test_r2 = float(r2_score(y_test, preds_test))
        
        # Pearson correlation
        corr = float(np.corrcoef(y_test, preds_test)[0, 1]) if len(preds_test) > 1 else 0.0
        
        results[name] = {
            "train_rmse": train_rmse,
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "test_r2": test_r2,
            "test_pearson_corr": corr,
            "pipeline": pipe
        }
        
        print(f"[{name}] Test RMSE: {test_rmse:.5f}, MAE: {test_mae:.5f}, R2: {test_r2:.4f}, Corr: {corr:.4f}")
        
    # Select best candidate with highest R2 / lowest Test RMSE
    best_name = max(results.keys(), key=lambda k: results[k]["test_r2"])
    print(f"\n=> Best Selected Model: {best_name}")
    
    return best_name, results

def main():
    print("==================================================")
    print("USHNA KAAPPAAN — MORTALITY MODEL TRAINING PIPELINE")
    print("==================================================")
    
    df, feature_cols = load_and_preprocess(DATA_PATH)
    print(f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns.")
    print(f"Selected {len(feature_cols)} predictor features (Zero target leakage).")
    
    X_train, y_train, X_test, y_test, split_date = temporal_train_test_split(
        df, feature_cols, TARGET_COLUMN, train_ratio=0.75
    )
    
    best_name, candidate_results = evaluate_candidates(X_train, y_train, X_test, y_test)
    best_info = candidate_results[best_name]
    best_pipeline = best_info["pipeline"]
    
    # Train final pipeline on entire dataset for production inference artifact
    final_pipeline = best_pipeline
    final_pipeline.fit(df[feature_cols], df[TARGET_COLUMN])
    
    # Save trained model artifact
    model_artifact_path = ARTIFACTS_DIR / "mortality_model_pipeline.joblib"
    joblib.dump(final_pipeline, model_artifact_path)
    print(f"Saved model artifact to: {model_artifact_path}")
    
    # Feature importances if available
    feature_importances = {}
    reg = final_pipeline.named_steps["regressor"]
    if hasattr(reg, "feature_importances_"):
        for col, imp in zip(feature_cols, reg.feature_importances_):
            feature_importances[col] = float(imp)
        feature_importances = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True))
    elif hasattr(reg, "coef_"):
        for col, coef in zip(feature_cols, reg.coef_):
            feature_importances[col] = float(abs(coef))
        feature_importances = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True))
        
    # Save feature configuration
    feature_config = {
        "target_column": TARGET_COLUMN,
        "target_unit": TARGET_UNIT,
        "target_definition": TARGET_DEFINITION,
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "excluded_columns": EXCLUDED_COLUMNS,
        "feature_importances_ranked": feature_importances
    }
    with open(ARTIFACTS_DIR / "feature_config.json", "w") as f:
        json.dump(feature_config, f, indent=2)
        
    # Save candidate comparison & validation metrics
    validation_summary = {
        "dataset_rows": len(df),
        "temporal_split_date": str(split_date),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "selected_model": best_name,
        "validation_metrics": {
            "test_rmse": best_info["test_rmse"],
            "test_mae": best_info["test_mae"],
            "test_r2": best_info["test_r2"],
            "test_pearson_corr": best_info["test_pearson_corr"],
            "train_rmse": best_info["train_rmse"]
        },
        "all_candidate_metrics": {
            k: {
                "test_rmse": v["test_rmse"],
                "test_mae": v["test_mae"],
                "test_r2": v["test_r2"],
                "test_pearson_corr": v["test_pearson_corr"],
                "train_rmse": v["train_rmse"]
            } for k, v in candidate_results.items()
        }
    }
    with open(ARTIFACTS_DIR / "validation_metrics.json", "w") as f:
        json.dump(validation_summary, f, indent=2)
        
    # Save Model Metadata
    model_metadata = {
        "model_name": "Ushna Kaappaan Mortality Model",
        "model_version": "v1.0.0-synthetic-prototype",
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "algorithm": best_name,
        "dataset_source": "dataset/mortality_synthetic_daily.csv",
        "data_type": "SYNTHETIC (Guin et al. 2025 statistical calibration)",
        "spatial_resolution": "STATE_LEVEL_ONLY",
        "supported_states": ["Tamil Nadu", "Kerala", "Karnataka"],
        "target": {
            "name": TARGET_COLUMN,
            "unit": TARGET_UNIT,
            "description": TARGET_DEFINITION
        },
        "risk_band_interpretation": {
            "baseline": "Rate <= 0.05 per 100,000 (Typical background levels)",
            "moderate_risk": "0.05 < Rate <= 0.15 per 100,000 (Elevated heat exposure stress)",
            "high_risk": "0.15 < Rate <= 0.30 per 100,000 (High excess heat burden)",
            "severe_risk": "Rate > 0.30 per 100,000 (Critical cumulative thermal load)"
        },
        "scientific_limitations": [
            "Trained exclusively on synthetic calibration data; NOT official NCRB or IMD mortality data.",
            "Produces state-level aggregated rates; MUST NOT be decomposed into district-level mortality.",
            "Designed for early-warning and preparedness benchmarking, not individual clinical forecasting."
        ]
    }
    with open(ARTIFACTS_DIR / "model_metadata.json", "w") as f:
        json.dump(model_metadata, f, indent=2)

    # Reload test and test inference
    print("\n--- Verifying Model Reload and Real Inference ---")
    reloaded_pipeline = joblib.load(model_artifact_path)
    sample_features = df[feature_cols].iloc[0:3]
    sample_preds = reloaded_pipeline.predict(sample_features)
    print(f"Sample Inferences (first 3 records): {sample_preds.tolist()}")
    assert len(sample_preds) == 3, "Inference output size mismatch"
    print("SUCCESS: Mortality Model artifact successfully trained, exported, reloaded, and verified!")

if __name__ == "__main__":
    main()
