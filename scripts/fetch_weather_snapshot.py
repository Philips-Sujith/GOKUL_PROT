#!/usr/bin/env python3
"""
Ushna Kaappaan — Weather Snapshot Generator
Fetches current observations and 3-day hourly forecasts from Open-Meteo for all 83 South India districts.
Writes raw response payloads into weather_snapshot.json.
Designed to run via GitHub Actions to maintain an off-Render snapshot cache on the 'weather-data' branch.
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ushna.snapshot")

BASE_DIR = Path(__file__).resolve().parent.parent
DISTRICTS_FILE = BASE_DIR / "data" / "district_coordinates.json"
OUTPUT_FILE = BASE_DIR / "weather_snapshot.json"

OPEN_METEO_BASE_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")

# Open-Meteo exact variable lists matching backend implementations
CURRENT_VARS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,surface_pressure,"
    "wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation"
)
HOURLY_VARS = (
    "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,"
    "shortwave_radiation,direct_radiation,diffuse_radiation"
)

def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "UshnaKaappaan-WeatherSnapshot/1.0 (Open-Research-Prototype; Contact: admin@ushna.org)",
        "Accept": "application/json"
    })
    return session

def fetch_batch_with_retry(
    session: requests.Session,
    batch: list,
    max_attempts: int = 5,
    initial_backoff: float = 3.0
):
    lats = ",".join(str(d["latitude"]) for d in batch)
    lons = ",".join(str(d["longitude"]) for d in batch)

    params = {
        "latitude": lats,
        "longitude": lons,
        "current": CURRENT_VARS,
        "hourly": HOURLY_VARS,
        "forecast_days": 3,
        "timezone": "UTC"
    }

    for attempt in range(max_attempts):
        try:
            resp = session.get(OPEN_METEO_BASE_URL, params=params, timeout=30)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait_sec = float(retry_after) if retry_after else (initial_backoff * (2 ** attempt))
                except (ValueError, TypeError):
                    wait_sec = initial_backoff * (2 ** attempt)
                logger.warning(f"HTTP 429 received. Backing off for {wait_sec:.1f}s (attempt {attempt+1}/{max_attempts})...")
                time.sleep(wait_sec)
                continue

            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as exc:
            if attempt == max_attempts - 1:
                logger.error(f"Failed to fetch batch after {max_attempts} attempts: {exc}")
                return None
            wait_sec = initial_backoff * (2 ** attempt)
            logger.warning(f"Batch request warning: {exc}. Retrying in {wait_sec:.1f}s...")
            time.sleep(wait_sec)

    return None

def main():
    if not DISTRICTS_FILE.exists():
        logger.error(f"Districts file not found at: {DISTRICTS_FILE}")
        sys.exit(1)

    with open(DISTRICTS_FILE, "r", encoding="utf-8") as f:
        districts = json.load(f)

    total_districts = len(districts)
    logger.info(f"Loaded {total_districts} districts for snapshot fetch.")

    session = create_session()
    batch_size = 45
    fetched_records = {}

    for i in range(0, total_districts, batch_size):
        batch = districts[i:i + batch_size]
        logger.info(f"Fetching batch {i // batch_size + 1}/{(total_districts + batch_size - 1) // batch_size} ({len(batch)} districts)...")

        data = fetch_batch_with_retry(session, batch)
        if data is not None:
            if isinstance(data, list):
                for district, item in zip(batch, data):
                    fetched_records[district["id"]] = item
            elif isinstance(data, dict) and len(batch) == 1:
                fetched_records[batch[0]["id"]] = data
            else:
                logger.error(f"Unexpected response format from Open-Meteo: {type(data)}")
        else:
            logger.error(f"Batch {i // batch_size + 1} completely failed.")

        if i + batch_size < total_districts:
            time.sleep(2.0)  # Safe delay between batches

    success_count = len(fetched_records)
    success_ratio = success_count / total_districts if total_districts > 0 else 0.0
    logger.info(f"Successfully fetched {success_count}/{total_districts} districts ({success_ratio * 100:.1f}%).")

    # Safety check: Exit with non-zero code if fewer than 90% of districts were fetched
    # This prevents any corrupted or incomplete snapshot from overwriting valid data
    if success_ratio < 0.90:
        logger.error(f"Fetch threshold failed! Required >= 90%, but got {success_ratio * 100:.1f}%. Aborting.")
        sys.exit(1)

    now_utc = datetime.now(timezone.utc)
    snapshot_payload = {
        "fetched_at": now_utc.isoformat(),
        "total_districts": total_districts,
        "districts_count": success_count,
        "districts": fetched_records,
        # Aliases for direct endpoint lookups
        "current_weather": fetched_records,
        "forecasts": fetched_records
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, indent=2)

    logger.info(f"Weather snapshot successfully written to: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size} bytes).")

if __name__ == "__main__":
    main()
