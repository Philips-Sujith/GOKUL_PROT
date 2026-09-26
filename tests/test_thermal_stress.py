"""
Unit & Scientific Validation Tests for ThermalStressService
Phase 4 & 14 / Requirements Checklist 8, 9, 10, 34, 35
"""

import pytest
from datetime import datetime, timezone
from backend.services.thermal_stress_service import ThermalStressService

def test_solar_zenith_angle():
    dt_noon = datetime(2026, 6, 21, 6, 30, tzinfo=timezone.utc) # ~12:00 PM IST in Chennai (lat 13.08, lon 80.27)
    cos_sza, sza_deg = ThermalStressService.calculate_solar_zenith_angle(13.0827, 80.2707, dt_noon)
    assert 0.0 <= cos_sza <= 1.0
    assert 0.0 <= sza_deg <= 90.0

def test_vapour_pressure():
    # At 30°C and 50% RH: saturation VP ~ 42.4 hPa, actual VP ~ 21.2 hPa
    vp = ThermalStressService.calculate_vapour_pressure_hpa(30.0, 50.0)
    assert 20.0 <= vp <= 23.0

def test_mrt_and_utci_calculation():
    dt_now = datetime.now(timezone.utc)
    # Warm tropical afternoon conditions
    res = ThermalStressService.process_district_thermal_stress(
        lat=13.0827,
        lon=80.2707,
        dt_utc=dt_now,
        temp_c=36.0,
        rh_percent=55.0,
        wind_speed_mps=2.5,
        shortwave_radiation_wm2=750.0,
        direct_radiation_wm2=550.0,
        diffuse_radiation_wm2=200.0
    )
    
    assert res["data_quality"] == "VALID"
    assert res["mrt_c"] > 36.0 # MRT should be higher than air temp in direct sunshine
    assert res["utci_c"] > 35.0 # UTCI should reflect strong / very strong thermal stress
    assert "category" in res["category_info"]
    assert res["category_info"]["severity_rank"] >= 3

def test_utci_authoritative_categories():
    assert ThermalStressService.classify_utci(48.0)["category"] == "Extreme heat stress"
    assert ThermalStressService.classify_utci(41.0)["category"] == "Very strong heat stress"
    assert ThermalStressService.classify_utci(35.0)["category"] == "Strong heat stress"
    assert ThermalStressService.classify_utci(28.0)["category"] == "Moderate heat stress"
    assert ThermalStressService.classify_utci(22.0)["category"] == "No thermal stress"
    assert ThermalStressService.classify_utci(5.0)["category"] == "Slight cold stress"

def test_invalid_weather_handling():
    res = ThermalStressService.process_district_thermal_stress(
        lat=13.0827,
        lon=80.2707,
        dt_utc=datetime.now(timezone.utc),
        temp_c=120.0, # Unphysical temperature
        rh_percent=50.0,
        wind_speed_mps=2.0
    )
    assert res["data_quality"] == "INVALID"
    assert "validation_error" in res
