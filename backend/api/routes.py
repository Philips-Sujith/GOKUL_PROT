"""
Ushna Kaappaan — REST API Router
Defines all public and administrative API endpoints.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.config import settings
from backend.database import get_db
from backend.models import District, WeatherObservation, ThermalResult, MortalityPrediction, Alert, TelegramDelivery, AdminUser, AuditLog
from backend.services.thermal_stress_service import UTCI_CATEGORIES, ThermalStressService
from backend.services.weather_provider import default_weather_provider, utc_to_ist_str
from backend.services.mortality_service import mortality_service
from backend.services.alert_engine import alert_engine
from backend.services.telegram_service import telegram_service
from backend.services.demo_scenarios import demo_engine, DEMO_SCENARIOS
from backend.services.scheduler import scheduler_instance
from backend.services.forecast_service import forecast_service

logger = logging.getLogger("ushna.api")
router = APIRouter(prefix="/api")

# Load population profiles
with open(settings.PROFILES_FILE, "r") as f:
    POPULATION_PROFILES = json.load(f)

# Global runtime mode state
runtime_state = {
    "mode": settings.APP_MODE, # LIVE or DEMO
    "demo_scenario": "HIGH_HEAT_STRESS",
    "demo_cache": {}
}

# --- Request / Response Models ---
class ModeUpdateRequest(BaseModel):
    mode: str # LIVE or DEMO
    demo_scenario: Optional[str] = "HIGH_HEAT_STRESS"

class LoginRequest(BaseModel):
    username: str
    password: str

class ManualEscalationRequest(BaseModel):
    district_id: str
    operational_severity: str
    custom_advisory: str
    target_roles: List[str]

class ReportRequest(BaseModel):
    district_id: Optional[str] = None
    state: Optional[str] = None

# --- Helper functions ---
def get_current_mode() -> str:
    return runtime_state["mode"]

def get_latest_district_data(db: Session, district_id: str, mode: str):
    d = db.query(District).filter(District.id == district_id).first()
    if not d:
        return None
        
    if mode == "DEMO":
        scenario = runtime_state.get("demo_scenario", "HIGH_HEAT_STRESS")
        cache_key = f"{district_id}_{scenario}"
        if cache_key not in runtime_state["demo_cache"]:
            district_dict = {
                "id": d.id, "name": d.name, "state": d.state,
                "latitude": d.latitude, "longitude": d.longitude, "elevation": d.elevation
            }
            demo_data = demo_engine.generate_district_scenario_data(scenario, district_dict)
            runtime_state["demo_cache"][cache_key] = demo_data
            
        data = runtime_state["demo_cache"][cache_key]
        return {
            "id": d.id,
            "name": d.name,
            "state": d.state,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "elevation": d.elevation,
            "weather": data["weather"],
            "thermal": data["thermal"],
            "timestamp_ist": data["timestamp_ist"],
            "mode": "DEMO",
            "scenario": data["scenario_name"]
        }
    else:
        # LIVE mode: fetch latest from DB
        latest_weather = db.query(WeatherObservation).filter(
            WeatherObservation.district_id == d.id,
            WeatherObservation.mode == "LIVE"
        ).order_by(desc(WeatherObservation.created_at)).first()
        
        latest_thermal = db.query(ThermalResult).filter(
            ThermalResult.district_id == d.id,
            ThermalResult.mode == "LIVE"
        ).order_by(desc(ThermalResult.created_at)).first()
        
        has_real_weather = latest_weather is not None and latest_weather.data_quality != "UNAVAILABLE" and latest_weather.temperature_c is not None
        has_real_thermal = latest_thermal is not None and latest_thermal.data_quality != "UNAVAILABLE" and latest_thermal.utci_c is not None
        
        if has_real_weather:
            weather_dict = {
                "temperature_c": latest_weather.temperature_c,
                "relative_humidity": latest_weather.relative_humidity,
                "wind_speed_mps": latest_weather.wind_speed_mps,
                "wind_direction_deg": latest_weather.wind_direction_deg,
                "surface_pressure_hpa": latest_weather.surface_pressure_hpa,
                "shortwave_radiation_wm2": latest_weather.shortwave_radiation_wm2,
                "direct_radiation_wm2": latest_weather.direct_radiation_wm2,
                "diffuse_radiation_wm2": latest_weather.diffuse_radiation_wm2,
                "data_quality": latest_weather.data_quality
            }
        else:
            weather_dict = {
                "temperature_c": None,
                "relative_humidity": None,
                "wind_speed_mps": None,
                "wind_direction_deg": None,
                "surface_pressure_hpa": None,
                "shortwave_radiation_wm2": None,
                "direct_radiation_wm2": None,
                "diffuse_radiation_wm2": None,
                "data_quality": "UNAVAILABLE"
            }
        
        if has_real_thermal:
            cat_info = ThermalStressService.classify_utci(latest_thermal.utci_c)
            thermal_dict = {
                "mrt_c": latest_thermal.mrt_c,
                "utci_c": latest_thermal.utci_c,
                "category_info": cat_info,
                "data_quality": latest_thermal.data_quality
            }
        else:
            thermal_dict = {
                "mrt_c": None,
                "utci_c": None,
                "category_info": {
                    "category": "No live data",
                    "min_utci": 0.0,
                    "max_utci": 0.0,
                    "severity_rank": 0,
                    "color": "#94a3b8",
                    "badge_bg": "#f1f5f9",
                    "badge_text": "#475569",
                    "badge_border": "#cbd5e1",
                    "description": "Live weather station feed currently unavailable."
                },
                "data_quality": "UNAVAILABLE"
            }
        
        return {
            "id": d.id,
            "name": d.name,
            "state": d.state,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "elevation": d.elevation,
            "weather": weather_dict,
            "thermal": thermal_dict,
            "timestamp_ist": latest_weather.timestamp_ist if latest_weather else utc_to_ist_str(datetime.now(timezone.utc)),
            "mode": "LIVE"
        }

# --- Endpoints ---

@router.get("/system/status")
def get_system_status(db: Session = Depends(get_db)):
    """Returns current system health, modes, update timestamps, and notification configurations."""
    mode = get_current_mode()
    districts_count = db.query(District).count()
    active_alerts_count = db.query(Alert).filter(Alert.status == "ACTIVE", Alert.mode == mode).count()
    
    # Calculate live districts with valid observation in database
    live_districts_count = db.query(WeatherObservation.district_id).filter(
        WeatherObservation.data_quality == "VALID",
        WeatherObservation.mode == mode
    ).distinct().count()
    
    return {
        "app_name": settings.APP_NAME,
        "full_title": settings.FULL_TITLE,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "mode": mode,
        "demo_scenario": runtime_state.get("demo_scenario") if mode == "DEMO" else None,
        "available_demo_scenarios": list(DEMO_SCENARIOS.keys()),
        "districts_count": districts_count,
        "districts_with_live_data_count": live_districts_count,
        "active_alerts_count": active_alerts_count,
        "last_pipeline_run_ist": scheduler_instance.last_run_ist,
        "last_successful_ingestion_ist": scheduler_instance.last_successful_run_ist,
        "pipeline_status": scheduler_instance.last_status,
        "weather_provider": "Open-Meteo REST (Non-commercial open tier)",
        "thermal_engine": "ECMWF thermofeel (Di Napoli et al. 2020 & Brode et al. 2012)",
        "mortality_model": {
            "status": "LOADED" if mortality_service.is_loaded else "UNAVAILABLE",
            "version": mortality_service.model_metadata.get("model_version", "v1.0.0-synthetic-prototype"),
            "data_type": "SYNTHETIC (Guin et al. 2025 calibration)"
        },
        "telegram_integration": {
            "is_configured": telegram_service.is_configured,
            "transport_mode": "REAL" if telegram_service.is_configured else "MOCK/TEST (Simulated)",
            "bot_status": "ONLINE (Connected)" if telegram_service.is_configured else "MOCK_MODE (No credentials in .env)"
        }
    }

@router.post("/system/mode")
def set_system_mode(req: ModeUpdateRequest):
    """Switch application mode between LIVE and DEMO scenarios."""
    req_mode = req.mode.upper()
    if req_mode not in ["LIVE", "DEMO"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be LIVE or DEMO.")
        
    runtime_state["mode"] = req_mode
    if req.demo_scenario and req.demo_scenario in DEMO_SCENARIOS:
        runtime_state["demo_scenario"] = req.demo_scenario
        runtime_state["demo_cache"] = {} # clear demo cache to recalculate with selected scenario
        
    return {
        "message": f"Application switched to {req_mode} mode.",
        "mode": req_mode,
        "demo_scenario": runtime_state.get("demo_scenario") if req_mode == "DEMO" else None
    }

@router.post("/system/refresh")
def trigger_refresh_pipeline():
    """Manually triggers the weather and thermal computing cycle."""
    mode = get_current_mode()
    res = scheduler_instance.run_full_pipeline(mode=mode)
    return {
        "message": "Processing cycle executed.",
        "result": res
    }

@router.get("/districts")
def list_districts(state: Optional[str] = None, db: Session = Depends(get_db)):
    """Returns all 83 districts with current thermal status and coordinates."""
    mode = get_current_mode()
    query = db.query(District)
    if state:
        query = query.filter(District.state == state)
    districts = query.all()
    
    results = []
    for d in districts:
        data = get_latest_district_data(db, d.id, mode)
        if data:
            results.append(data)
            
    return {
        "total_districts": len(results),
        "mode": mode,
        "districts": results
    }

@router.get("/districts/{district_id}")
def get_district_details(district_id: str, db: Session = Depends(get_db)):
    """Returns comprehensive details for a specific district."""
    mode = get_current_mode()
    data = get_latest_district_data(db, district_id, mode)
    if not data:
        raise HTTPException(status_code=404, detail="District not found.")
        
    # Get 24-hour history from DB (if LIVE mode)
    history = []
    if mode == "LIVE":
        past_results = db.query(ThermalResult).filter(
            ThermalResult.district_id == district_id,
            ThermalResult.mode == "LIVE"
        ).order_by(desc(ThermalResult.created_at)).limit(12).all()
        
        for r in reversed(past_results):
            history.append({
                "timestamp_ist": r.timestamp_ist,
                "utci_c": r.utci_c,
                "mrt_c": r.mrt_c,
                "category": r.utci_category
            })
            
    return {
        "district": data,
        "history_trend": history,
        "mode": mode
    }

@router.get("/forecast/district/{district_id}")
def get_district_forecast(district_id: str, db: Session = Depends(get_db)):
    """
    Returns 3-day human thermal stress forecast for a specific district.
    Runs ECMWF thermofeel MRT & UTCI calculation over Open-Meteo 3-day hourly forecast.
    """
    mode = get_current_mode()
    d = db.query(District).filter(District.id == district_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="District not found.")
        
    district_dict = {
        "id": d.id, "name": d.name, "state": d.state,
        "latitude": d.latitude, "longitude": d.longitude, "elevation": d.elevation
    }
    
    is_demo = (mode == "DEMO")
    demo_scenario = runtime_state.get("demo_scenario", "HIGH_HEAT_STRESS")
    
    forecast_data = forecast_service.fetch_district_forecast(
        district=district_dict,
        is_demo=is_demo,
        demo_scenario=demo_scenario
    )
    
    return {
        "mode": mode,
        "forecast": forecast_data
    }

@router.get("/forecast/all")
def get_all_districts_forecast(state: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns 3-day human thermal stress forecast summaries for all 83 districts.
    """
    mode = get_current_mode()
    query = db.query(District)
    if state:
        query = query.filter(District.state == state)
    districts = query.all()
    
    district_dicts = [
        {
            "id": d.id, "name": d.name, "state": d.state,
            "latitude": d.latitude, "longitude": d.longitude, "elevation": d.elevation
        }
        for d in districts
    ]
    
    is_demo = (mode == "DEMO")
    demo_scenario = runtime_state.get("demo_scenario", "HIGH_HEAT_STRESS")
    
    forecasts = forecast_service.fetch_all_forecasts(
        districts=district_dicts,
        is_demo=is_demo,
        demo_scenario=demo_scenario
    )
    
    # Format list for admin and public consume
    forecast_list = []
    for d in districts:
        if d.id in forecasts:
            f_item = forecasts[d.id]
            forecast_list.append({
                "district_id": d.id,
                "district_name": d.name,
                "state": d.state,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "forecast_generated_at": f_item.get("forecast_generated_at"),
                "data_quality": f_item.get("data_quality", "VALID"),
                "outlook_summary": f_item.get("outlook_summary"),
                "days": f_item.get("days", [])
            })
            
    return {
        "total_districts": len(forecast_list),
        "mode": mode,
        "forecasts": forecast_list
    }

@router.get("/thermal/latest")
def get_thermal_overview(db: Session = Depends(get_db)):
    """Returns South India aggregated thermal statistics, high-risk counts, and category distributions."""
    mode = get_current_mode()
    districts = db.query(District).all()
    
    district_summaries = []
    category_counts = {cat["category"]: 0 for cat in UTCI_CATEGORIES}
    state_breakdown = {"Tamil Nadu": [], "Kerala": [], "Karnataka": []}
    
    max_utci = -999.0
    hottest_district = None
    
    for d in districts:
        data = get_latest_district_data(db, d.id, mode)
        if data:
            cat_name = data["thermal"]["category_info"]["category"]
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
            
            utci = data["thermal"]["utci_c"]
            if utci > max_utci:
                max_utci = utci
                hottest_district = data["name"]
                
            district_summaries.append({
                "id": d.id,
                "name": d.name,
                "state": d.state,
                "utci_c": utci,
                "mrt_c": data["thermal"]["mrt_c"],
                "category": cat_name,
                "color": data["thermal"]["category_info"]["color"],
                "latitude": d.latitude,
                "longitude": d.longitude
            })
            
            if d.state in state_breakdown:
                state_breakdown[d.state].append(utci)

    state_averages = {}
    for st, vals in state_breakdown.items():
        state_averages[st] = round(sum(vals) / len(vals), 2) if vals else 0.0

    high_risk_count = (
        category_counts.get("Extreme heat stress", 0) +
        category_counts.get("Very strong heat stress", 0) +
        category_counts.get("Strong heat stress", 0)
    )

    return {
        "mode": mode,
        "total_districts": len(districts),
        "high_risk_districts_count": high_risk_count,
        "max_utci_c": max_utci if hottest_district else 0.0,
        "hottest_district": hottest_district,
        "category_distribution": category_counts,
        "state_averages_utci": state_averages,
        "districts_thermal": district_summaries,
        "utci_reference_categories": UTCI_CATEGORIES
    }

@router.get("/population-profiles")
def list_population_profiles():
    """Returns all 9 tailored population and occupational profiles."""
    return {
        "profiles": POPULATION_PROFILES
    }

@router.get("/health-impact/{district_id}")
def get_health_impact_advisory(district_id: str, profile: str = "general_public", db: Session = Depends(get_db)):
    """
    Returns population profile-specific health advisory and precautions for the district's current UTCI.
    NOTE: Profile modulates the advisory and precautions, NEVER the scientific UTCI or weather values.
    """
    mode = get_current_mode()
    data = get_latest_district_data(db, district_id, mode)
    if not data:
        raise HTTPException(status_code=404, detail="District not found.")
        
    selected_prof = next((p for p in POPULATION_PROFILES if p["id"] == profile), POPULATION_PROFILES[0])
    utci_cat = data["thermal"]["category_info"]["category"]
    advisory_info = selected_prof["advisories_by_category"].get(utci_cat, {
        "summary": "Standard thermal health advisory.",
        "precautions": ["Stay hydrated."],
        "symptoms_watch": ["None"]
    })
    
    return {
        "district_id": data["id"],
        "district_name": data["name"],
        "state": data["state"],
        "utci_c": data["thermal"]["utci_c"],
        "utci_category": utci_cat,
        "profile": {
            "id": selected_prof["id"],
            "name": selected_prof["name"],
            "icon": selected_prof["icon"],
            "description": selected_prof["description"],
            "vulnerability_weight": selected_prof["vulnerability_weight"]
        },
        "health_advisory": advisory_info,
        "disclaimer": "General heat health guidance only. Does not constitute medical diagnosis or individual clinical prescription."
    }

@router.get("/mortality/overview")
def get_mortality_overview(db: Session = Depends(get_db)):
    """
    Returns State-Level mortality estimates for Tamil Nadu, Kerala, Karnataka from the trained ML model.
    CRITICAL: Does NOT provide district-level mortality. Explicitly labels synthetic baseline dataset.
    """
    mode = get_current_mode()
    states = ["Tamil Nadu", "Kerala", "Karnataka"]
    state_results = []
    
    for st in states:
        # Collect state district weather observations
        districts = db.query(District).filter(District.state == st).all()
        w_list = []
        for d in districts:
            data = get_latest_district_data(db, d.id, mode)
            if data:
                w_list.append(data["weather"])
                
        pred = mortality_service.predict_state_mortality(st, w_list, mode=mode)
        state_results.append(pred)
        
    return {
        "mode": mode,
        "spatial_resolution": "STATE_LEVEL_ONLY",
        "district_prediction_policy": "STRICTLY_DISALLOWED (State-level epidemiological aggregation only)",
        "model_metadata": mortality_service.model_metadata,
        "validation_metrics": mortality_service.validation_metrics.get("validation_metrics", {}),
        "state_estimates": state_results,
        "synthetic_data_disclaimer": "The underlying calibration dataset is synthetic (Guin et al. 2025 statistical baseline). These figures represent prototype research estimates for public health planning, NOT official government fatality counts."
    }

@router.get("/alerts")
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Returns active and recent operational alerts and Telegram delivery logs."""
    mode = get_current_mode()
    alerts = db.query(Alert).filter(Alert.mode == mode).order_by(desc(Alert.created_at)).limit(limit).all()
    deliveries = db.query(TelegramDelivery).order_by(desc(TelegramDelivery.sent_at)).limit(limit).all()
    
    alert_list = []
    for a in alerts:
        district_name = a.district.name if a.district else "Unknown"
        alert_list.append({
            "id": a.id,
            "alert_uid": a.alert_uid,
            "district_id": a.district_id,
            "district_name": district_name,
            "state": a.state,
            "utci_c": a.utci_c,
            "utci_category": a.utci_category,
            "operational_severity": a.operational_severity,
            "recipient_roles": a.recipient_roles,
            "advisory_text": a.advisory_text,
            "status": a.status,
            "mode": a.mode,
            "created_at": a.created_at.isoformat()
        })
        
    delivery_list = []
    for d in deliveries:
        delivery_list.append({
            "id": d.id,
            "alert_id": d.alert_id,
            "recipient_role": d.recipient_role,
            "chat_id": d.chat_id,
            "message_body": d.message_body,
            "transport_mode": d.transport_mode,
            "delivery_status": d.delivery_status,
            "error_message": d.error_message,
            "sent_at": d.sent_at.isoformat()
        })
        
    return {
        "mode": mode,
        "total_active_alerts": len([a for a in alert_list if a["status"] == "ACTIVE"]),
        "alerts": alert_list,
        "telegram_deliveries": delivery_list
    }

@router.post("/admin/login")
def admin_login(req: LoginRequest):
    """Admin authentication using environment credentials and JWT_SECRET signed token."""
    if req.username == settings.ADMIN_USERNAME and req.password == settings.ADMIN_PASSWORD:
        import hmac
        import hashlib
        token_payload = f"{req.username}:{int(datetime.now(timezone.utc).timestamp())}"
        signed_token = hmac.new(settings.JWT_SECRET.encode("utf-8"), token_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "status": "SUCCESS",
            "token": signed_token,
            "user": {
                "username": req.username,
                "role": "SUPERADMIN",
                "full_name": "State Heat Control Administrator"
            }
        }
    raise HTTPException(status_code=401, detail="Invalid administrator credentials.")

@router.post("/admin/escalations/send")
def send_manual_escalation(req: ManualEscalationRequest, db: Session = Depends(get_db)):
    """Admin manual escalation and precautionary Telegram broadcast."""
    d = db.query(District).filter(District.id == req.district_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="District not found.")
        
    mode = get_current_mode()
    res = alert_engine.manual_escalation(
        db_session=db,
        district=d,
        escalation_severity=req.operational_severity,
        custom_advisory=req.custom_advisory,
        target_roles=req.target_roles,
        admin_actor="AdminPortalUser",
        mode=mode
    )
    
    return {
        "status": "SUCCESS",
        "message": f"Escalation successfully dispatched for {d.name}, {d.state}.",
        "result": res
    }

@router.post("/admin/reports/generate")
def generate_admin_report(req: ReportRequest, db: Session = Depends(get_db)):
    """Generates a comprehensive official heat-stress and operational advisory report."""
    mode = get_current_mode()
    dt_utc = datetime.now(timezone.utc)
    
    # District or State report
    if req.district_id:
        d_data = get_latest_district_data(db, req.district_id, mode)
        if not d_data:
            raise HTTPException(status_code=404, detail="District not found.")
            
        return {
            "report_title": f"Heat Stress & Early Warning Assessment Report — {d_data['name']}",
            "report_id": f"REP-UK-{d_data['id']}-{int(dt_utc.timestamp())}",
            "generated_at_ist": utc_to_ist_str(dt_utc),
            "mode": mode,
            "district_profile": d_data,
            "recommended_actions": alert_engine.map_operational_severity(d_data["thermal"]["utci_c"])[2],
            "signatory": "State Disaster Management Heat Taskforce"
        }
    else:
        # Full South India State Report
        overview = get_thermal_overview(db)
        mort = get_mortality_overview(db)
        return {
            "report_title": "South India Regional Heat Stress & Human Thermal Risk Synthesis Report",
            "report_id": f"REP-SOUTH-INDIA-{int(dt_utc.timestamp())}",
            "generated_at_ist": utc_to_ist_str(dt_utc),
            "mode": mode,
            "coverage": "Tamil Nadu (38 districts), Kerala (14 districts), Karnataka (31 districts) = 83 Districts",
            "regional_thermal_summary": overview,
            "state_mortality_burdens": mort["state_estimates"],
            "system_disclaimer": "Prepared via Ushna Kaappaan Automated Localized Heat Early Warning System."
        }
