"""
Tests for 3-Day Human Thermal Stress Forecast Service and Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.forecast_service import forecast_service

client = TestClient(app)

def test_forecast_district_endpoint():
    response = client.get("/api/forecast/district/TN-03")
    assert response.status_code == 200
    data = response.json()
    assert "forecast" in data
    forecast = data["forecast"]
    assert forecast["district_id"] == "TN-03"
    assert "days" in forecast
    assert len(forecast["days"]) == 3
    
    # Check 3 days structure
    labels = [d["day_label"] for d in forecast["days"]]
    assert labels == ["Today", "Tomorrow", "Day 3"]
    
    for day in forecast["days"]:
        assert "peak_utci_c" in day
        assert "peak_time_ist" in day
        assert "category_info" in day
        assert "category" in day["category_info"]

def test_forecast_all_endpoint():
    response = client.get("/api/forecast/all?state=Tamil+Nadu")
    assert response.status_code == 200
    data = response.json()
    assert "forecasts" in data
    assert data["total_districts"] > 0
    first_f = data["forecasts"][0]
    assert "district_name" in first_f
    assert len(first_f["days"]) == 3
