"""
Integration Tests for Ushna Kaappaan FastAPI Endpoints
Phase 14 / Requirements Checklist 31, 34, 35
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_system_status():
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app_name"] == "Ushna Kaappaan"
    assert data["districts_count"] == 83
    assert data["mode"] in ["LIVE", "DEMO"]
    assert "mortality_model" in data

def test_districts_list():
    resp = client.get("/api/districts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_districts"] == 83
    assert len(data["districts"]) == 83

def test_district_state_filter():
    resp_tn = client.get("/api/districts?state=Tamil%20Nadu")
    assert resp_tn.status_code == 200
    assert resp_tn.json()["total_districts"] == 38

    resp_kl = client.get("/api/districts?state=Kerala")
    assert resp_kl.status_code == 200
    assert resp_kl.json()["total_districts"] == 14

    resp_ka = client.get("/api/districts?state=Karnataka")
    assert resp_ka.status_code == 200
    assert resp_ka.json()["total_districts"] == 31

def test_district_details():
    resp = client.get("/api/districts/TN-03")
    assert resp.status_code == 200
    data = resp.json()
    assert data["district"]["id"] == "TN-03"
    assert data["district"]["name"] == "Chennai"
    assert "thermal" in data["district"]
    assert "weather" in data["district"]

def test_health_impact_profile():
    resp = client.get("/api/health-impact/TN-03?profile=outdoor_worker")
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile"]["id"] == "outdoor_worker"
    assert "precautions" in data["health_advisory"]
    assert "symptoms_watch" in data["health_advisory"]

def test_mortality_overview():
    resp = client.get("/api/mortality/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["spatial_resolution"] == "STATE_LEVEL_ONLY"
    assert len(data["state_estimates"]) == 3
    assert "synthetic_data_disclaimer" in data

def test_mode_switching_and_demo():
    resp = client.post("/api/system/mode", json={"mode": "DEMO", "demo_scenario": "EXTREME_HEAT_STRESS"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "DEMO"

    # Reset back to LIVE
    resp_live = client.post("/api/system/mode", json={"mode": "LIVE"})
    assert resp_live.status_code == 200
    assert resp_live.json()["mode"] == "LIVE"

def test_admin_login_and_security():
    # Invalid login
    resp_invalid = client.post("/api/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp_invalid.status_code == 401

    # Valid login
    resp_valid = client.post("/api/admin/login", json={"username": "admin", "password": "admin@ushna2026"})
    assert resp_valid.status_code == 200
    assert resp_valid.json()["status"] == "SUCCESS"
