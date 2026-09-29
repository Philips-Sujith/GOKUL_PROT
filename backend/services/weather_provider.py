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

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OpenMeteoWeatherProvider(WeatherDataProvider):
    def __init__(self, base_url: str = settings.OPEN_METEO_BASE_URL, timeout_sec: int = 15):
        self.base_url = base_url
        self.timeout_sec = timeout_sec
        self.session = requests.Session()
        
        # Configure automatic exponential backoff for transient 503/429/5xx gateway hiccups
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
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

    def _get_with_backoff(self, params: Dict[str, Any], max_retries: int = 3, initial_backoff: float = 2.0) -> Any:
        import time
        for attempt in range(max_retries):
            try:
                resp = self.session.get(self.base_url, params=params, timeout=self.timeout_sec)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    try:
                        wait_time = float(retry_after) if retry_after else (initial_backoff * (2 ** attempt))
                    except (ValueError, TypeError):
                        wait_time = initial_backoff * (2 ** attempt)
                    logger.warning(
                        f"Open-Meteo 429 Too Many Requests received. Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})."
                    )
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = initial_backoff * (2 ** attempt)
                logger.warning(f"Weather request error: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
        return None

    def fetch_district_weather(self, district: Dict[str, Any]) -> Dict[str, Any]:
        dt_utc = datetime.now(timezone.utc)
        params = {
            "latitude": district["latitude"],
            "longitude": district["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,surface_pressure,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation",
            "timezone": "UTC"
        }
        try:
            data = self._get_with_backoff(params, max_retries=3, initial_backoff=2.0)
            if data is not None:
                return self._parse_current_payload(district["id"], data, dt_utc)
            raise ValueError("No data returned from Open-Meteo")
        except Exception as e:
            logger.warning(f"Weather fetch notice for district {district.get('name')}: {e}")
            return {
                "district_id": district["id"],
                "timestamp_utc": dt_utc,
                "timestamp_ist": utc_to_ist_str(dt_utc),
                "temperature_c": None,
                "relative_humidity": None,
                "wind_speed_mps": None,
                "wind_direction_deg": None,
                "surface_pressure_hpa": None,
                "shortwave_radiation_wm2": None,
                "direct_radiation_wm2": None,
                "diffuse_radiation_wm2": None,
                "source": "Open-Meteo",
                "data_quality": "UNAVAILABLE",
                "error": str(e)
            }

    def fetch_all_districts_weather(self, districts: List[Dict[str, Any]], batch_size: int = 45) -> Dict[str, Dict[str, Any]]:
        """
        Batch-fetches weather for all districts with session pooling, larger batch coordinate requests,
        exponential backoff on 429, and gentle inter-batch pacing.
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
                data = self._get_with_backoff(params, max_retries=3, initial_backoff=2.0)
                
                if isinstance(data, list):
                    for district, item in zip(batch, data):
                        results[district["id"]] = self._parse_current_payload(district["id"], item, dt_utc)
                elif isinstance(data, dict) and len(batch) == 1:
                    results[batch[0]["id"]] = self._parse_current_payload(batch[0]["id"], data, dt_utc)
                else:
                    raise ValueError(f"Unexpected response structure for batch: {type(data)}")
                        
            except Exception as e:
                logger.warning(f"Batch fetch notice for batch {i//batch_size + 1}: {e}")
                # Do NOT trigger a barrage of individual single-district requests!
                for district in batch:
                    results[district["id"]] = {
                        "district_id": district["id"],
                        "timestamp_utc": dt_utc,
                        "timestamp_ist": utc_to_ist_str(dt_utc),
                        "temperature_c": None,
                        "relative_humidity": None,
                        "wind_speed_mps": None,
                        "wind_direction_deg": None,
                        "surface_pressure_hpa": None,
                        "shortwave_radiation_wm2": None,
                        "direct_radiation_wm2": None,
                        "diffuse_radiation_wm2": None,
                        "source": "Open-Meteo",
                        "data_quality": "UNAVAILABLE",
                        "error": str(e)
                    }
                    
            if i + batch_size < len(districts):
                time.sleep(1.0) # gentle pacing between multi-district batches
                    
        return results

# Default provider singleton
default_weather_provider: WeatherDataProvider = OpenMeteoWeatherProvider()
