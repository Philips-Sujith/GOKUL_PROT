"""
Ushna Kaappaan — Weather Data Provider Layer
Abstract provider interface and Open-Meteo REST implementation.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import requests
import logging

from backend.config import settings

logger = logging.getLogger("ushna.weather")

def utc_to_ist_str(dt_utc: datetime) -> str:
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt_utc.astimezone(ist_tz)
    return dt_ist.strftime("%Y-%m-%d %I:%M %p IST")

class WeatherDataProvider(ABC):
    @abstractmethod
    def fetch_district_weather(self, district: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch weather observation for a single district."""
        pass

    @abstractmethod
    def fetch_all_districts_weather(self, districts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Fetch weather observations for a list of districts. Returns mapping of district_id -> observation."""
        pass

class OpenMeteoWeatherProvider(WeatherDataProvider):
    def __init__(self, base_url: str = settings.OPEN_METEO_BASE_URL, timeout_sec: int = 15):
        self.base_url = base_url
        self.timeout_sec = timeout_sec
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "UshnaKaappaan-HeatEarlyWarning/1.0 (Open-Research-Prototype; Contact: admin@ushna.org)",
            "Accept": "application/json"
        })

    def _parse_current_payload(self, district_id: str, data: Dict[str, Any], dt_utc: datetime) -> Dict[str, Any]:
        current = data.get("current", {})
        
        # Wind speed from Open-Meteo is km/h by default -> convert to m/s
        wind_kmh = float(current.get("wind_speed_10m", 0.0))
        wind_mps = round(wind_kmh / 3.6, 2)
        
        temp_c = float(current.get("temperature_2m", 0.0))
        rh_percent = float(current.get("relative_humidity_2m", 50.0))
        surface_pressure = float(current.get("surface_pressure", 1013.25))
        wind_dir = float(current.get("wind_direction_10m", 0.0))
        
        sw_rad = float(current.get("shortwave_radiation", 0.0))
        direct_rad = float(current.get("direct_radiation", 0.0))
        diffuse_rad = float(current.get("diffuse_radiation", 0.0))
        
        return {
            "district_id": district_id,
            "timestamp_utc": dt_utc,
            "timestamp_ist": utc_to_ist_str(dt_utc),
            "temperature_c": temp_c,
            "relative_humidity": rh_percent,
            "wind_speed_mps": wind_mps,
            "wind_direction_deg": wind_dir,
            "surface_pressure_hpa": surface_pressure,
            "shortwave_radiation_wm2": sw_rad,
            "direct_radiation_wm2": direct_rad,
            "diffuse_radiation_wm2": diffuse_rad,
            "source": "Open-Meteo",
            "data_quality": "VALID",
            "raw_payload": current
        }

    def fetch_district_weather(self, district: Dict[str, Any]) -> Dict[str, Any]:
        dt_utc = datetime.now(timezone.utc)
        params = {
            "latitude": district["latitude"],
            "longitude": district["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,surface_pressure,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation",
            "timezone": "UTC"
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout_sec)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_current_payload(district["id"], data, dt_utc)
        except Exception as e:
            logger.error(f"Error fetching weather for district {district.get('name')}: {e}")
            return {
                "district_id": district["id"],
                "timestamp_utc": dt_utc,
                "timestamp_ist": utc_to_ist_str(dt_utc),
                "temperature_c": 0.0,
                "relative_humidity": 0.0,
                "wind_speed_mps": 0.0,
                "wind_direction_deg": 0.0,
                "surface_pressure_hpa": 1013.25,
                "shortwave_radiation_wm2": 0.0,
                "direct_radiation_wm2": 0.0,
                "diffuse_radiation_wm2": 0.0,
                "source": "Open-Meteo",
                "data_quality": "UNAVAILABLE",
                "error": str(e)
            }

    def fetch_all_districts_weather(self, districts: List[Dict[str, Any]], batch_size: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        Batch-fetches weather for all districts with session pooling and rate limiting.
        """
        import time
        results = {}
        dt_utc = datetime.now(timezone.utc)
        
        for i in range(0, len(districts), batch_size):
            batch = districts[i:i+batch_size]
            lats = ",".join(str(d["latitude"]) for d in batch)
            lons = ",".join(str(d["longitude"]) for d in batch)
            
            params = {
                "latitude": lats,
                "longitude": lons,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,surface_pressure,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation",
                "timezone": "UTC"
            }
            
            try:
                resp = self.session.get(self.base_url, params=params, timeout=self.timeout_sec)
                resp.raise_for_status()
                data = resp.json()
                
                if isinstance(data, list):
                    for district, item in zip(batch, data):
                        results[district["id"]] = self._parse_current_payload(district["id"], item, dt_utc)
                elif isinstance(data, dict) and len(batch) == 1:
                    results[batch[0]["id"]] = self._parse_current_payload(batch[0]["id"], data, dt_utc)
                else:
                    for district in batch:
                        results[district["id"]] = self.fetch_district_weather(district)
                        
            except Exception as e:
                logger.error(f"Batch fetch error for batch {i//batch_size + 1}: {e}")
                for district in batch:
                    results[district["id"]] = self.fetch_district_weather(district)
                    
            time.sleep(0.15) # gentle pacing between batches
                    
        return results

# Default provider singleton
default_weather_provider: WeatherDataProvider = OpenMeteoWeatherProvider()
