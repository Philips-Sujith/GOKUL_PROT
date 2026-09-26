"""
Ushna Kaappaan — Operational Alert Engine
Evaluates district thermal results, maps to operational severity levels,
routes to role-based recipient channels, and handles cooldown deduplication.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid
import logging

from backend.models import Alert, District, ThermalResult
from backend.services.telegram_service import telegram_service
from backend.services.weather_provider import utc_to_ist_str

logger = logging.getLogger("ushna.alert_engine")

class AlertEngine:
    # Cooldown window in hours for duplicate alerts on the same district & severity
    COOLDOWN_HOURS = 4

    @staticmethod
    def map_operational_severity(utci_c: float) -> Tuple_Severity:
        """
        Translates continuous UTCI into application-level operational severity and recipient role list.
        """
        if utci_c >= 46.0:
            return (
                "EXTREME",
                ["Municipality Authorities", "Public Health Centres", "Worker Union Leaders", "General Public"],
                "SUGGESTED PRECAUTIONARY ACTION: Recommend temporary suspension of high-exposure outdoor labour during peak hours. Open air-cooled public rest centres, ready emergency heatstroke response wards, and deploy mobile water distribution to vulnerable settlements."
            )
        elif utci_c >= 42.0:
            return (
                "SEVERE",
                ["Municipality Authorities", "Public Health Centres", "Worker Union Leaders"],
                "SUGGESTED PRECAUTIONARY ACTION: Reschedule outdoor construction and municipal sanitation shifts to non-peak morning hours (before 11:00 AM). Ready health centres with oral rehydration salts and cooling packs. Provide frequent shaded rest breaks."
            )
        elif utci_c >= 38.0:
            return (
                "HIGH",
                ["Municipality Authorities", "Public Health Centres"],
                "RECOMMENDED CIVIC PRECAUTION: Issue public hydration advisories across local civic channels. Distribute ORS packets at urban health posts and transit hubs. Inspect shaded water points in public areas."
            )
        elif utci_c >= 32.0:
            return (
                "MODERATE",
                ["Public Health Advisory"],
                "CAUTIONARY ADVISORY: Advise citizens and outdoor workers to hydrate frequently and avoid direct sun during peak solar hours (12:00 PM - 3:30 PM)."
            )
        else:
            return (
                "LOW",
                ["Dashboard Monitoring"],
                "NORMAL BASELINE: Standard continuous monitoring. Regular activities may proceed."
            )

    @classmethod
    def should_trigger_notification(cls, operational_severity: str) -> bool:
        """Only dispatch external Telegram notifications for HIGH, SEVERE, and EXTREME alerts."""
        return operational_severity in ["HIGH", "SEVERE", "EXTREME"]

    @classmethod
    def evaluate_district_alert(
        cls,
        db_session,
        district: District,
        utci_c: float,
        utci_category: str,
        mode: str = "LIVE"
    ) -> Optional[Dict[str, Any]]:
        severity, roles, advisory = cls.map_operational_severity(utci_c)
        dt_utc = datetime.now(timezone.utc)
        timestamp_ist = utc_to_ist_str(dt_utc)

        # Check cooldown deduplication
        cutoff = dt_utc - timedelta(hours=cls.COOLDOWN_HOURS)
        recent_alert = db_session.query(Alert).filter(
            Alert.district_id == district.id,
            Alert.operational_severity == severity,
            Alert.created_at >= cutoff,
            Alert.mode == mode
        ).first()

        if recent_alert:
            logger.debug(f"Alert suppressed by cooldown for district {district.name} ({severity})")
            return None

        # Create new Alert record
        alert_uid = f"ALT-{district.id}-{uuid.uuid4().hex[:8].upper()}"
        alert_record = Alert(
            alert_uid=alert_uid,
            district_id=district.id,
            state=district.state,
            utci_c=utci_c,
            utci_category=utci_category,
            operational_severity=severity,
            recipient_roles=roles,
            advisory_text=advisory,
            status="ACTIVE",
            mode=mode,
            created_at=dt_utc
        )
        db_session.add(alert_record)
        db_session.commit()
        db_session.refresh(alert_record)

        # Trigger notification if eligible
        delivery_results = []
        if cls.should_trigger_notification(severity):
            for role in roles:
                del_res = telegram_service.send_notification(
                    db_session=db_session,
                    alert_id=alert_record.id,
                    district_name=district.name,
                    state=district.state,
                    utci_c=utci_c,
                    utci_category=utci_category,
                    operational_severity=severity,
                    advisory_text=advisory,
                    timestamp_ist=timestamp_ist,
                    recipient_role=role,
                    mode=mode
                )
                delivery_results.append(del_res)

        return {
            "alert_id": alert_record.id,
            "alert_uid": alert_record.alert_uid,
            "district_id": district.id,
            "district_name": district.name,
            "state": district.state,
            "utci_c": utci_c,
            "utci_category": utci_category,
            "operational_severity": severity,
            "recipient_roles": roles,
            "advisory_text": advisory,
            "deliveries": delivery_results,
            "created_at": dt_utc.isoformat()
        }

    @classmethod
    def manual_escalation(
        cls,
        db_session,
        district: District,
        escalation_severity: str,
        custom_advisory: str,
        target_roles: List[str],
        admin_actor: str,
        mode: str = "LIVE"
    ) -> Dict[str, Any]:
        dt_utc = datetime.now(timezone.utc)
        timestamp_ist = utc_to_ist_str(dt_utc)
        
        # Latest thermal result
        latest_thermal = db_session.query(ThermalResult).filter(
            ThermalResult.district_id == district.id,
            ThermalResult.mode == mode
        ).order_by(ThermalResult.created_at.desc()).first()
        
        utci_c = latest_thermal.utci_c if latest_thermal else 38.0
        utci_category = latest_thermal.utci_category if latest_thermal else "Strong heat stress"

        alert_uid = f"ESC-{district.id}-{uuid.uuid4().hex[:8].upper()}"
        alert_record = Alert(
            alert_uid=alert_uid,
            district_id=district.id,
            state=district.state,
            utci_c=utci_c,
            utci_category=utci_category,
            operational_severity=escalation_severity,
            recipient_roles=target_roles,
            advisory_text=custom_advisory,
            status="ACTIVE",
            mode=mode,
            created_at=dt_utc
        )
        db_session.add(alert_record)
        db_session.commit()
        db_session.refresh(alert_record)

        # Dispatch escalation notifications
        deliveries = []
        for role in target_roles:
            del_res = telegram_service.send_notification(
                db_session=db_session,
                alert_id=alert_record.id,
                district_name=district.name,
                state=district.state,
                utci_c=utci_c,
                utci_category=utci_category,
                operational_severity=f"{escalation_severity} (MANUAL ESCALATION by {admin_actor})",
                advisory_text=custom_advisory,
                timestamp_ist=timestamp_ist,
                recipient_role=role,
                mode=mode
            )
            deliveries.append(del_res)

        return {
            "alert_id": alert_record.id,
            "alert_uid": alert_record.alert_uid,
            "status": "ESCALATED",
            "deliveries": deliveries
        }

Tuple_Severity = Any
alert_engine = AlertEngine()
