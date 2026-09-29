"""
Ushna Kaappaan — Background Scheduler & Processing Pipeline
Orchestrates the 2-hour weather ingestion, thermofeel UTCI calculation,
mortality inference, and early-warning alert evaluation cycle.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import District, WeatherObservation, ThermalResult, MortalityPrediction, AuditLog
from backend.services.weather_provider import default_weather_provider, utc_to_ist_str
from backend.services.thermal_stress_service import ThermalStressService
from backend.services.mortality_service import mortality_service
from backend.services.alert_engine import alert_engine

logger = logging.getLogger("ushna.scheduler")

class PipelineScheduler:
    def __init__(self):
        self.last_run_utc: datetime = None
        self.last_run_ist: str = "Never"
        self.last_successful_run_utc: datetime = None
        self.last_successful_run_ist: str = "Never"
        self.live_districts_count: int = 0
        self.last_status: str = "INITIALIZING"
        self.last_summary: Dict[str, Any] = {}
        self.is_running: bool = False

    def initialize_districts(self, db: Session):
        """Seed 83 districts into the database from JSON if empty."""
        count = db.query(District).count()
        if count >= 83:
            logger.info(f"Database already contains {count} districts.")
            return

        with open(settings.DISTRICTS_FILE, "r") as f:
            districts_data = json.load(f)

        for d in districts_data:
            existing = db.query(District).filter(District.id == d["id"]).first()
            if not existing:
                district = District(
                    id=d["id"],
                    name=d["name"],
                    state=d["state"],
                    latitude=d["latitude"],
                    longitude=d["longitude"],
                    elevation=d.get("elevation", 0.0)
                )
                db.add(district)

        db.commit()
        logger.info(f"Initialized {len(districts_data)} districts in database.")

    def run_full_pipeline(self, mode: str = "LIVE") -> Dict[str, Any]:
        """
        Executes the full end-to-end processing pipeline for all 83 districts.
        """
        if self.is_running:
            return {"status": "SKIPPED", "reason": "Pipeline already running"}

        self.is_running = True
        dt_start = datetime.now(timezone.utc)
        db = SessionLocal()

        try:
            self.initialize_districts(db)
            districts = db.query(District).all()
            districts_dict_list = [
                {
                    "id": d.id,
                    "name": d.name,
                    "state": d.state,
                    "latitude": d.latitude,
                    "longitude": d.longitude,
                    "elevation": d.elevation
                } for d in districts
            ]

            logger.info(f"Starting {mode} pipeline for {len(districts_dict_list)} districts...")

            # 1. Fetch Weather
            weather_map = default_weather_provider.fetch_all_districts_weather(districts_dict_list)

            # 2. Process Scientific Thermal Pipeline & Persist
            processed_count = 0
            failed_count = 0
            thermal_records = []
            alerts_triggered = []
            state_weather_buckets = {"Tamil Nadu": [], "Kerala": [], "Karnataka": []}

            for d in districts:
                obs_data = weather_map.get(d.id)
                has_valid_fetch = obs_data and obs_data.get("data_quality") == "VALID" and obs_data.get("temperature_c") is not None

                if not has_valid_fetch:
                    failed_count += 1
                    # District fetch failed -> check for previous valid observation to preserve
                    last_obs = db.query(WeatherObservation).filter(
                        WeatherObservation.district_id == d.id,
                        WeatherObservation.data_quality == "VALID"
                    ).order_by(WeatherObservation.created_at.desc()).first()

                    if last_obs:
                        # Do NOT overwrite previously stored good readings with defaults!
                        # The existing valid DB records remain authoritative.
                        if d.state in state_weather_buckets:
                            state_weather_buckets[d.state].append({
                                "temperature_c": last_obs.temperature_c,
                                "relative_humidity": last_obs.relative_humidity,
                                "wind_speed_mps": last_obs.wind_speed_mps,
                                "data_quality": "STALE"
                            })
                        continue
                    else:
                        # No prior valid data and fetch failed:
                        # Do NOT compute UTCI or thermal category from fallback defaults!
                        logger.warning(f"No live or cached weather for district {d.name} ({d.id}). Skipping UTCI calculation.")
                        continue

                # Save Valid Weather Observation
                weather_obs = WeatherObservation(
                    district_id=d.id,
                    timestamp_utc=obs_data["timestamp_utc"],
                    timestamp_ist=obs_data["timestamp_ist"],
                    temperature_c=obs_data["temperature_c"],
                    relative_humidity=obs_data["relative_humidity"],
                    wind_speed_mps=obs_data["wind_speed_mps"],
                    wind_direction_deg=obs_data.get("wind_direction_deg", 0.0),
                    surface_pressure_hpa=obs_data.get("surface_pressure_hpa", 1013.25),
                    shortwave_radiation_wm2=obs_data.get("shortwave_radiation_wm2", 0.0),
                    direct_radiation_wm2=obs_data.get("direct_radiation_wm2", 0.0),
                    diffuse_radiation_wm2=obs_data.get("diffuse_radiation_wm2", 0.0),
                    source=obs_data.get("source", "Open-Meteo"),
                    data_quality=obs_data.get("data_quality", "VALID"),
                    mode=mode,
                    raw_payload=obs_data.get("raw_payload")
                )
                db.add(weather_obs)

                # Execute ECMWF Thermofeel Thermal Calculation on real data
                thermal_res = ThermalStressService.process_district_thermal_stress(
                    lat=d.latitude,
                    lon=d.longitude,
                    dt_utc=dt_start,
                    temp_c=obs_data["temperature_c"],
                    rh_percent=obs_data["relative_humidity"],
                    wind_speed_mps=obs_data["wind_speed_mps"],
                    shortwave_radiation_wm2=obs_data.get("shortwave_radiation_wm2", 0.0),
                    direct_radiation_wm2=obs_data.get("direct_radiation_wm2", 0.0),
                    diffuse_radiation_wm2=obs_data.get("diffuse_radiation_wm2", 0.0)
                )

                thermal_rec = ThermalResult(
                    district_id=d.id,
                    timestamp_utc=dt_start,
                    timestamp_ist=utc_to_ist_str(dt_start),
                    mrt_c=thermal_res["mrt_c"],
                    utci_c=thermal_res["utci_c"],
                    utci_category=thermal_res["category_info"]["category"],
                    severity_rank=thermal_res["category_info"]["severity_rank"],
                    data_quality="VALID",
                    mode=mode
                )
                db.add(thermal_rec)
                thermal_records.append(thermal_rec)
                processed_count += 1

                if d.state in state_weather_buckets:
                    state_weather_buckets[d.state].append(obs_data)

                # 3. Evaluate District Alert
                alert_res = alert_engine.evaluate_district_alert(
                    db_session=db,
                    district=d,
                    utci_c=thermal_res["utci_c"],
                    utci_category=thermal_res["category_info"]["category"],
                    mode=mode
                )
                if alert_res:
                    alerts_triggered.append(alert_res)

            # 4. State-level Mortality Predictions (only if we have real state observations)
            mortality_results = []
            for state_name, w_list in state_weather_buckets.items():
                if w_list:
                    m_pred = mortality_service.predict_state_mortality(state_name, w_list, mode=mode)
                    if m_pred.get("status") != "UNAVAILABLE":
                        db_pred = MortalityPrediction(
                            state=state_name,
                            timestamp_utc=dt_start,
                            timestamp_ist=m_pred["timestamp_ist"],
                            predicted_rate_per_100k=m_pred["predicted_mortality_rate_per_100000"],
                            risk_context=m_pred["risk_context"],
                            model_name=m_pred["model_name"],
                            model_version=m_pred["model_version"],
                            data_type="SYNTHETIC",
                            mode=mode
                        )
                        db.add(db_pred)
                        mortality_results.append(m_pred)

            # Audit Log
            audit = AuditLog(
                actor="SystemScheduler",
                action="REFRESH_WEATHER_AND_THERMAL_PIPELINE",
                details={
                    "mode": mode,
                    "districts_total": len(districts),
                    "processed_count": processed_count,
                    "failed_count": failed_count,
                    "alerts_generated": len(alerts_triggered)
                }
            )
            db.add(audit)
            db.commit()

            dt_end = datetime.now(timezone.utc)
            duration_sec = round((dt_end - dt_start).total_seconds(), 2)

            self.last_run_utc = dt_start
            self.last_run_ist = utc_to_ist_str(dt_start)
            if processed_count > 0:
                self.last_successful_run_utc = dt_start
                self.last_successful_run_ist = self.last_run_ist
                self.live_districts_count = processed_count

            self.last_status = "SUCCESS" if processed_count > 0 else ("PARTIAL" if failed_count < len(districts) else "NO_LIVE_DATA")
            self.last_summary = {
                "timestamp_utc": dt_start.isoformat(),
                "timestamp_ist": self.last_run_ist,
                "last_successful_ingestion_ist": self.last_successful_run_ist,
                "districts_with_live_data_count": self.live_districts_count,
                "districts_processed": processed_count,
                "districts_failed": failed_count,
                "alerts_triggered": len(alerts_triggered),
                "duration_seconds": duration_sec,
                "mortality_predictions": mortality_results
            }

            logger.info(f"Pipeline finished in {duration_sec}s. Live: {processed_count}, Failed: {failed_count}, Alerts: {len(alerts_triggered)}")
            return self.last_summary

        except Exception as e:
            db.rollback()
            logger.error(f"Pipeline execution failure: {e}", exc_info=True)
            self.last_status = f"FAILED: {str(e)}"
            return {"status": "FAILED", "error": str(e)}
        finally:
            self.is_running = False
            db.close()

scheduler_instance = PipelineScheduler()
