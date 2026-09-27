"""
Ushna Kaappaan — 3-Day Human Thermal Stress Forecast Service
Implements physically based 3-day thermal forecast using Open-Meteo hourly weather forecast
and ECMWF thermofeel MRT and UTCI calculation pipeline.
"""

import math
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import requests

from backend.config import settings
from backend.services.thermal_stress_service import ThermalStressService, UTCI_CATEGORIES
from backend.services.weather_provider import utc_to_ist_str

logger = logging.getLogger("ushna.forecast")

IST_TZ = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST_TZ)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class ForecastService:
    def __init__(self, base_url: str = settings.OPEN_METEO_BASE_URL, timeout_sec: int = 20, cache_ttl_seconds: int = 3600):
        self.base_url = base_url
        self.timeout_sec = timeout_sec
        self.cache_ttl_seconds = cache_ttl_seconds
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
            "User-Agent": "UshnaKaappaan-HeatEarlyWarning/1.0 (3-Day-Forecast; Contact: admin@ushna.org)",
            "Accept": "application/json"
        })
        self._forecast_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Dict[str, float] = {}

    def _format_day_forecast(self, day_label: str, target_date_str: str, day_hours: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Given a list of calculated hourly points for an IST day, finds the peak UTCI point."""
        if not day_hours:
            return {
                "day_label": day_label,
                "date": target_date_str,
                "peak_utci_c": 0.0,
                "peak_time_ist": "N/A",
                "category_info": ThermalStressService.classify_utci(0.0),
                "peak_mrt_c": 0.0,
                "peak_temperature_c": 0.0,
                "peak_relative_humidity": 0.0,
                "data_quality": "UNAVAILABLE"
            }

        peak_point = max(day_hours, key=lambda x: x["utci_c"])
        peak_dt_ist = peak_point["dt_ist"]
        peak_time_str = peak_dt_ist.strftime("%H:%M IST")

        return {
            "day_label": day_label,
            "date": target_date_str,
            "peak_utci_c": round(peak_point["utci_c"], 1),
            "peak_time_ist": peak_time_str,
            "category_info": peak_point["category_info"],
            "peak_mrt_c": round(peak_point["mrt_c"], 1),
            "peak_temperature_c": round(peak_point["temperature_c"], 1),
            "peak_relative_humidity": round(peak_point["relative_humidity"], 1),
            "hourly_summary": [
                {
                    "time_ist": h["dt_ist"].strftime("%H:%M"),
                    "utci_c": round(h["utci_c"], 1),
                    "temp_c": round(h["temperature_c"], 1),
                    "category": h["category_info"]["category"]
                }
                for h in day_hours
            ],
            "data_quality": "VALID"
        }

    def _generate_outlook_summary(self, days: List[Dict[str, Any]]) -> str:
        """Generates a concise public advisory summary comparing the 3 days."""
        if len(days) < 2:
            return "Thermal stress forecast active."

        today_utci = days[0]["peak_utci_c"]
        tom_utci = days[1]["peak_utci_c"]
        day3_utci = days[2]["peak_utci_c"] if len(days) > 2 else tom_utci

        max_day = max(days, key=lambda d: d["peak_utci_c"])
        max_label = max_day["day_label"]

        if tom_utci > today_utci + 1.5:
            return f"Conditions may become noticeably more stressful tomorrow ({tom_utci}°C peak)."
        elif tom_utci < today_utci - 1.5:
            return f"Thermal stress expected to ease slightly tomorrow ({tom_utci}°C peak)."
        elif max_day["peak_utci_c"] >= 38.0:
            return f"Persistent strong heat stress expected; highest peak on {max_label} ({max_day['peak_utci_c']}°C)."
        else:
            return f"Thermal conditions remain steady; peak stress around {days[0]['peak_time_ist']}."

    def _process_hourly_data(self, district: Dict[str, Any], hourly_data: Dict[str, Any], is_demo: bool = False, demo_offset: float = 0.0) -> Dict[str, Any]:
        """Runs the thermofeel physics pipeline for all hourly forecast points and groups into 3 days."""
        times = hourly_data.get("time", [])
        temps = hourly_data.get("temperature_2m", [])
        rhs = hourly_data.get("relative_humidity_2m", [])
        winds = hourly_data.get("wind_speed_10m", [])
        sw_rads = hourly_data.get("shortwave_radiation", [])
        dir_rads = hourly_data.get("direct_radiation", [])
        diff_rads = hourly_data.get("diffuse_radiation", [])

        lat = float(district["latitude"])
        lon = float(district["longitude"])

        now_ist = get_ist_now()
        today_date = now_ist.date()
        tomorrow_date = today_date + timedelta(days=1)
        day3_date = today_date + timedelta(days=2)

        day_buckets: Dict[str, List[Dict[str, Any]]] = {
            today_date.isoformat(): [],
            tomorrow_date.isoformat(): [],
            day3_date.isoformat(): []
        }

        for i in range(len(times)):
            time_str = times[i]
            # Parse ISO UTC timestamp
            try:
                if time_str.endswith("Z"):
                    dt_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                elif "+" in time_str or "-" in time_str[10:]:
                    dt_utc = datetime.fromisoformat(time_str)
                else:
                    dt_utc = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            except Exception:
                continue

            dt_ist = dt_utc.astimezone(IST_TZ)
            date_key = dt_ist.date().isoformat()

            if date_key not in day_buckets:
                continue

            temp_c = float(temps[i]) if i < len(temps) and temps[i] is not None else 32.0
            rh_pct = float(rhs[i]) if i < len(rhs) and rhs[i] is not None else 50.0
            wind_kmh = float(winds[i]) if i < len(winds) and winds[i] is not None else 7.2
            wind_mps = wind_kmh / 3.6
            sw_rad = float(sw_rads[i]) if i < len(sw_rads) and sw_rads[i] is not None else 0.0
            dir_rad = float(dir_rads[i]) if i < len(dir_rads) and dir_rads[i] is not None else 0.0
            diff_rad = float(diff_rads[i]) if i < len(diff_rads) and diff_rads[i] is not None else 0.0

            if is_demo and demo_offset != 0.0:
                temp_c += demo_offset
                sw_rad = max(0.0, sw_rad * (1.0 + demo_offset * 0.05))

            # Run physical thermofeel calculation
            thermal_res = ThermalStressService.process_district_thermal_stress(
                lat=lat,
                lon=lon,
                dt_utc=dt_utc,
                temp_c=temp_c,
                rh_percent=rh_pct,
                wind_speed_mps=wind_mps,
                shortwave_radiation_wm2=sw_rad,
                direct_radiation_wm2=dir_rad,
                diffuse_radiation_wm2=diff_rad
            )

            day_buckets[date_key].append({
                "dt_utc": dt_utc,
                "dt_ist": dt_ist,
                "temperature_c": temp_c,
                "relative_humidity": rh_pct,
                "wind_speed_mps": wind_mps,
                "mrt_c": thermal_res["mrt_c"],
                "utci_c": thermal_res["utci_c"],
                "category_info": thermal_res["category_info"]
            })

        days_forecast = [
            self._format_day_forecast("Today", today_date.isoformat(), day_buckets[today_date.isoformat()]),
            self._format_day_forecast("Tomorrow", tomorrow_date.isoformat(), day_buckets[tomorrow_date.isoformat()]),
            self._format_day_forecast("Day 3", day3_date.isoformat(), day_buckets[day3_date.isoformat()])
        ]

        outlook = self._generate_outlook_summary(days_forecast)
        generated_at_ist = now_ist.strftime("%Y-%m-%d %I:%M %p IST")

        return {
            "district_id": district["id"],
            "district_name": district["name"],
            "state": district["state"],
            "latitude": lat,
            "longitude": lon,
            "forecast_generated_at": generated_at_ist,
            "source": "Open-Meteo Forecast + ECMWF thermofeel (Brode et al. 2012 / Di Napoli et al. 2020)",
            "data_quality": "VALID",
            "outlook_summary": outlook,
            "days": days_forecast
        }

    def fetch_district_forecast(self, district: Dict[str, Any], is_demo: bool = False, demo_scenario: str = "HIGH_HEAT_STRESS") -> Dict[str, Any]:
        """Fetches 3-day forecast for a single district with caching."""
        district_id = district["id"]
        cache_key = f"{district_id}_{'DEMO_' + demo_scenario if is_demo else 'LIVE'}"

        now_sec = time.time()
        if cache_key in self._forecast_cache and (now_sec - self._cache_timestamp.get(cache_key, 0)) < self.cache_ttl_seconds:
            return self._forecast_cache[cache_key]

        demo_offset = 0.0
        if is_demo:
            if demo_scenario == "EXTREME_HEATWAVE":
                demo_offset = 5.0
            elif demo_scenario == "HIGH_HEAT_STRESS":
                demo_offset = 2.5
            elif demo_scenario == "MILD_DAY":
                demo_offset = -4.0

        params = {
            "latitude": district["latitude"],
            "longitude": district["longitude"],
            "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,shortwave_radiation,direct_radiation,diffuse_radiation",
            "forecast_days": 3,
            "timezone": "UTC"
        }

        try:
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout_sec)
            resp.raise_for_status()
            data = resp.json()
            hourly = data.get("hourly", {})
            forecast_res = self._process_hourly_data(district, hourly, is_demo=is_demo, demo_offset=demo_offset)

            self._forecast_cache[cache_key] = forecast_res
            self._cache_timestamp[cache_key] = now_sec
            return forecast_res

        except Exception as e:
            logger.error(f"Error fetching 3-day forecast for district {district.get('name')}: {e}")
            if cache_key in self._forecast_cache:
                cached = dict(self._forecast_cache[cache_key])
                cached["data_quality"] = "STALE"
                return cached

            now_ist = get_ist_now()
            today_date = now_ist.date()
            return {
                "district_id": district["id"],
                "district_name": district["name"],
                "state": district["state"],
                "latitude": district["latitude"],
                "longitude": district["longitude"],
                "forecast_generated_at": now_ist.strftime("%Y-%m-%d %I:%M %p IST"),
                "source": "Open-Meteo Forecast + ECMWF thermofeel",
                "data_quality": "UNAVAILABLE",
                "error": str(e),
                "outlook_summary": "Forecast data temporarily unavailable.",
                "days": [
                    {
                        "day_label": label,
                        "date": (today_date + timedelta(days=idx)).isoformat(),
                        "peak_utci_c": 0.0,
                        "peak_time_ist": "N/A",
                        "category_info": ThermalStressService.classify_utci(0.0),
                        "peak_mrt_c": 0.0,
                        "peak_temperature_c": 0.0,
                        "peak_relative_humidity": 0.0,
                        "data_quality": "UNAVAILABLE"
                    }
                    for idx, label in enumerate(["Today", "Tomorrow", "Day 3"])
                ]
            }

    def fetch_all_forecasts(self, districts: List[Dict[str, Any]], is_demo: bool = False, demo_scenario: str = "HIGH_HEAT_STRESS", batch_size: int = 5) -> Dict[str, Dict[str, Any]]:
        """Batch-fetches 3-day forecasts for all 83 districts."""
        results = {}
        now_sec = time.time()

        districts_to_fetch = []
        for d in districts:
            cache_key = f"{d['id']}_{'DEMO_' + demo_scenario if is_demo else 'LIVE'}"
            if cache_key in self._forecast_cache and (now_sec - self._cache_timestamp.get(cache_key, 0)) < self.cache_ttl_seconds:
                results[d["id"]] = self._forecast_cache[cache_key]
            else:
                districts_to_fetch.append(d)

        demo_offset = 0.0
        if is_demo:
            if demo_scenario == "EXTREME_HEATWAVE":
                demo_offset = 5.0
            elif demo_scenario == "HIGH_HEAT_STRESS":
                demo_offset = 2.5
            elif demo_scenario == "MILD_DAY":
                demo_offset = -4.0

        for i in range(0, len(districts_to_fetch), batch_size):
            batch = districts_to_fetch[i:i+batch_size]
            lats = ",".join(str(d["latitude"]) for d in batch)
            lons = ",".join(str(d["longitude"]) for d in batch)

            params = {
                "latitude": lats,
                "longitude": lons,
                "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,shortwave_radiation,direct_radiation,diffuse_radiation",
                "forecast_days": 3,
                "timezone": "UTC"
            }

            try:
                resp = self.session.get(self.base_url, params=params, timeout=self.timeout_sec)
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, list):
                    for district, item in zip(batch, data):
                        hourly = item.get("hourly", {})
                        f_res = self._process_hourly_data(district, hourly, is_demo=is_demo, demo_offset=demo_offset)
                        cache_key = f"{district['id']}_{'DEMO_' + demo_scenario if is_demo else 'LIVE'}"
                        self._forecast_cache[cache_key] = f_res
                        self._cache_timestamp[cache_key] = now_sec
                        results[district["id"]] = f_res
                elif isinstance(data, dict) and len(batch) == 1:
                    hourly = data.get("hourly", {})
                    f_res = self._process_hourly_data(batch[0], hourly, is_demo=is_demo, demo_offset=demo_offset)
                    cache_key = f"{batch[0]['id']}_{'DEMO_' + demo_scenario if is_demo else 'LIVE'}"
                    self._forecast_cache[cache_key] = f_res
                    self._cache_timestamp[cache_key] = now_sec
                    results[batch[0]["id"]] = f_res
                else:
                    for district in batch:
                        results[district["id"]] = self.fetch_district_forecast(district, is_demo=is_demo, demo_scenario=demo_scenario)

            except Exception as e:
                logger.error(f"Batch forecast fetch error for batch {i//batch_size + 1}: {e}")
                for district in batch:
                    results[district["id"]] = self.fetch_district_forecast(district, is_demo=is_demo, demo_scenario=demo_scenario)

            time.sleep(0.15)

        return results

# Singleton instance
forecast_service = ForecastService()
