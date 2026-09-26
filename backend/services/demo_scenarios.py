"""
Ushna Kaappaan — Controlled Demo Scenarios
Provides parameterized environmental inputs that pass through the genuine
ECMWF thermofeel calculation pipeline without hardcoding outcomes.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
import random

from backend.services.thermal_stress_service import ThermalStressService
from backend.services.weather_provider import utc_to_ist_str

DEMO_SCENARIOS = {
    "NORMAL": {
        "name": "Normal Baseline",
        "description": "Pleasant tropical day with comfortable ambient temperatures and low radiation.",
        "base_temp": 27.5,
        "temp_variation": 2.0,
        "base_rh": 55.0,
        "base_wind": 3.8,
        "base_sw_rad": 280.0,
        "base_direct_rad": 150.0,
        "base_diffuse_rad": 130.0
    },
    "MODERATE_HEAT": {
        "name": "Moderate Heat",
        "description": "Standard warm summer afternoon with noticeable solar loading and moderate humidity.",
        "base_temp": 32.5,
        "temp_variation": 1.8,
        "base_rh": 60.0,
        "base_wind": 2.8,
        "base_sw_rad": 550.0,
        "base_direct_rad": 350.0,
        "base_diffuse_rad": 200.0
    },
    "HIGH_HEAT_STRESS": {
        "name": "High Heat Stress",
        "description": "Pre-heatwave conditions with elevated air temperatures and significant thermal radiation.",
        "base_temp": 36.8,
        "temp_variation": 1.5,
        "base_rh": 58.0,
        "base_wind": 2.2,
        "base_sw_rad": 750.0,
        "base_direct_rad": 550.0,
        "base_diffuse_rad": 200.0
    },
    "SEVERE_HEAT_STRESS": {
        "name": "Severe Heatwave",
        "description": "Severe heatwave event with blistering sunshine and heavy metabolic heat burden.",
        "base_temp": 39.8,
        "temp_variation": 1.5,
        "base_rh": 54.0,
        "base_wind": 1.8,
        "base_sw_rad": 880.0,
        "base_direct_rad": 680.0,
        "base_diffuse_rad": 200.0
    },
    "EXTREME_HEAT_STRESS": {
        "name": "Extreme Heat Crisis",
        "description": "Catastrophic heat emergency combining searing air temperatures, stagnant wind, and high humidity.",
        "base_temp": 43.5,
        "temp_variation": 1.5,
        "base_rh": 62.0,
        "base_wind": 1.2,
        "base_sw_rad": 960.0,
        "base_direct_rad": 780.0,
        "base_diffuse_rad": 180.0
    }
}

class DemoScenarioEngine:
    @staticmethod
    def generate_district_scenario_data(scenario_key: str, district: Dict[str, Any]) -> Dict[str, Any]:
        scenario = DEMO_SCENARIOS.get(scenario_key, DEMO_SCENARIOS["NORMAL"])
        dt_utc = datetime.now(timezone.utc)
        
        # Micro-variation based on district latitude/elevation to simulate realistic spatial gradients
        lat_factor = (district["latitude"] - 10.0) * 0.15
        elev_factor = (district.get("elevation", 100.0) / 500.0) * -0.8
        
        temp_c = scenario["base_temp"] + lat_factor + elev_factor + random.uniform(-0.5, 0.5)
        rh = max(20.0, min(95.0, scenario["base_rh"] + random.uniform(-3.0, 3.0)))
        wind = max(0.5, scenario["base_wind"] + random.uniform(-0.3, 0.3))
        sw_rad = max(0.0, scenario["base_sw_rad"] + random.uniform(-20.0, 20.0))
        direct_rad = max(0.0, scenario["base_direct_rad"] + random.uniform(-15.0, 15.0))
        diffuse_rad = max(0.0, scenario["base_diffuse_rad"] + random.uniform(-10.0, 10.0))

        # Run REAL SCIENTIFIC THERMAL PIPELINE
        thermal_res = ThermalStressService.process_district_thermal_stress(
            lat=district["latitude"],
            lon=district["longitude"],
            dt_utc=dt_utc,
            temp_c=temp_c,
            rh_percent=rh,
            wind_speed_mps=wind,
            shortwave_radiation_wm2=sw_rad,
            direct_radiation_wm2=direct_rad,
            diffuse_radiation_wm2=diffuse_rad
        )

        return {
            "district_id": district["id"],
            "district_name": district["name"],
            "state": district["state"],
            "scenario": scenario_key,
            "scenario_name": scenario["name"],
            "timestamp_utc": dt_utc.isoformat(),
            "timestamp_ist": utc_to_ist_str(dt_utc),
            "weather": {
                "temperature_c": round(temp_c, 1),
                "relative_humidity": round(rh, 1),
                "wind_speed_mps": round(wind, 1),
                "shortwave_radiation_wm2": round(sw_rad, 1),
                "direct_radiation_wm2": round(direct_rad, 1),
                "diffuse_radiation_wm2": round(diffuse_rad, 1)
            },
            "thermal": thermal_res,
            "mode": "DEMO"
        }

demo_engine = DemoScenarioEngine()
