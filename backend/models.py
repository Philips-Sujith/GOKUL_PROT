from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class District(Base):
    __tablename__ = "districts"
    
    id = Column(String(32), primary_key=True, index=True) # e.g. TN-01
    name = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True) # Tamil Nadu, Kerala, Karnataka
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)
    
    weather_observations = relationship("WeatherObservation", back_populates="district", cascade="all, delete-orphan")
    thermal_results = relationship("ThermalResult", back_populates="district", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="district", cascade="all, delete-orphan")

class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(String(32), ForeignKey("districts.id"), nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, default=utc_now, index=True)
    timestamp_ist = Column(String(50), nullable=False)
    temperature_c = Column(Float, nullable=False)
    relative_humidity = Column(Float, nullable=False)
    wind_speed_mps = Column(Float, nullable=False)
    wind_direction_deg = Column(Float, default=0.0)
    surface_pressure_hpa = Column(Float, default=1013.25)
    shortwave_radiation_wm2 = Column(Float, default=0.0)
    direct_radiation_wm2 = Column(Float, default=0.0)
    diffuse_radiation_wm2 = Column(Float, default=0.0)
    source = Column(String(50), default="Open-Meteo")
    data_quality = Column(String(20), default="VALID") # VALID, STALE, INVALID, UNAVAILABLE
    mode = Column(String(20), default="LIVE") # LIVE or DEMO
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    district = relationship("District", back_populates="weather_observations")

class ThermalResult(Base):
    __tablename__ = "thermal_results"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(String(32), ForeignKey("districts.id"), nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, default=utc_now, index=True)
    timestamp_ist = Column(String(50), nullable=False)
    mrt_c = Column(Float, nullable=False) # Mean Radiant Temperature in Celsius
    utci_c = Column(Float, nullable=False) # UTCI in Celsius
    utci_category = Column(String(50), nullable=False) # e.g. "Extreme heat stress"
    severity_rank = Column(Integer, default=1) # 0 to 5
    data_quality = Column(String(20), default="VALID")
    mode = Column(String(20), default="LIVE")
    created_at = Column(DateTime, default=utc_now)
    
    district = relationship("District", back_populates="thermal_results")

class MortalityPrediction(Base):
    __tablename__ = "mortality_predictions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    state = Column(String(50), nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, default=utc_now, index=True)
    timestamp_ist = Column(String(50), nullable=False)
    predicted_rate_per_100k = Column(Float, nullable=False)
    risk_context = Column(String(50), nullable=False) # Baseline, Elevated, High, Severe
    model_name = Column(String(100), default="Ushna Kaappaan Mortality Model v1.0")
    model_version = Column(String(50), default="v1.0.0-synthetic-prototype")
    data_type = Column(String(50), default="SYNTHETIC")
    feature_values = Column(JSON, nullable=True)
    mode = Column(String(20), default="LIVE")
    created_at = Column(DateTime, default=utc_now)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_uid = Column(String(64), unique=True, index=True)
    district_id = Column(String(32), ForeignKey("districts.id"), nullable=False, index=True)
    state = Column(String(50), nullable=False)
    utci_c = Column(Float, nullable=False)
    utci_category = Column(String(50), nullable=False)
    operational_severity = Column(String(20), nullable=False) # LOW, MODERATE, HIGH, SEVERE, EXTREME
    recipient_roles = Column(JSON, nullable=False) # list of roles
    advisory_text = Column(Text, nullable=False)
    status = Column(String(20), default="ACTIVE") # ACTIVE, RESOLVED, SUPPRESSED
    mode = Column(String(20), default="LIVE")
    created_at = Column(DateTime, default=utc_now, index=True)
    
    district = relationship("District", back_populates="alerts")
    deliveries = relationship("TelegramDelivery", back_populates="alert", cascade="all, delete-orphan")

class TelegramDelivery(Base):
    __tablename__ = "telegram_deliveries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    recipient_role = Column(String(50), nullable=False)
    chat_id = Column(String(100), nullable=False)
    message_body = Column(Text, nullable=False)
    transport_mode = Column(String(20), default="REAL") # REAL or MOCK
    delivery_status = Column(String(20), default="SENT") # SENT, FAILED, SIMULATED
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=utc_now, index=True)
    
    alert = relationship("Alert", back_populates="deliveries")

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), default="System Administrator")
    role = Column(String(50), default="SUPERADMIN")
    created_at = Column(DateTime, default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp_utc = Column(DateTime, default=utc_now, index=True)
