"""
Unit & Integration Tests for Operational AlertEngine & Telegram Transport
Phase 11, 12, 14 / Requirements Checklist 24, 25, 26, 34, 35
"""

import pytest
from backend.services.alert_engine import alert_engine
from backend.services.telegram_service import telegram_service

def test_operational_severity_mapping():
    sev_ext, roles_ext, adv_ext = alert_engine.map_operational_severity(47.5)
    assert sev_ext == "EXTREME"
    assert "General Public" in roles_ext

    sev_sev, roles_sev, _ = alert_engine.map_operational_severity(43.5)
    assert sev_sev == "SEVERE"
    assert "Worker Union Leaders" in roles_sev

    sev_high, roles_high, _ = alert_engine.map_operational_severity(39.0)
    assert sev_high == "HIGH"
    assert "Public Health Centres" in roles_high

    sev_mod, roles_mod, _ = alert_engine.map_operational_severity(34.0)
    assert sev_mod == "MODERATE"

    sev_low, roles_low, _ = alert_engine.map_operational_severity(25.0)
    assert sev_low == "LOW"

def test_telegram_message_formatting():
    msg = telegram_service.format_alert_message(
        district_name="Chennai",
        state="Tamil Nadu",
        utci_c=42.5,
        utci_category="Very strong heat stress",
        operational_severity="SEVERE",
        advisory_text="Halt afternoon open-air labour.",
        timestamp_ist="2026-09-25 12:00 PM IST",
        recipient_role="Worker Union Leaders",
        mode="LIVE"
    )
    assert "USHNA KAAPPAAN" in msg
    assert "Chennai" in msg
    assert "42.5°C" in msg
    assert "Worker Union Leaders" in msg

def test_mock_telegram_transport():
    # If no token configured, must route to mock/simulated transport
    res = telegram_service.send_notification(
        db_session=None,
        alert_id=1,
        district_name="Madurai",
        state="Tamil Nadu",
        utci_c=44.0,
        utci_category="Very strong heat stress",
        operational_severity="SEVERE",
        advisory_text="Deploy hydration stations.",
        timestamp_ist="2026-09-25 01:00 PM IST",
        recipient_role="Municipality Authorities",
        mode="LIVE"
    )
    assert res["delivery_status"] in ["SENT", "MOCK / TEST - NOT ACTUALLY SENT", "SIMULATED"]
    assert res["recipient_role"] == "Municipality Authorities"
