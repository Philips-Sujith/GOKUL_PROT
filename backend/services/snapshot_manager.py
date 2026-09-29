"""
Ushna Kaappaan — Weather Snapshot Fallback Service
Manages downloading, caching, and serving pre-fetched weather snapshots from GitHub.
Provides in-memory caching for 10 minutes and stale detection (> 12 hours).
"""

import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import requests

from backend.config import settings
from backend.services.weather_provider import utc_to_ist_str

logger = logging.getLogger("ushna.snapshot_manager")

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class SnapshotManager:
    def __init__(self, cache_ttl_seconds: int = 600):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_snapshot: Optional[Dict[str, Any]] = None
        self._cache_timestamp: float = 0.0
        self._last_source: str = "None"
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "UshnaKaappaan-BackendSnapshot/1.0 (Contact: admin@ushna.org)",
            "Accept": "application/json"
        })

    def _parse_snapshot_data(self, data: Dict[str, Any], source_label: str) -> Dict[str, Any]:
        fetched_at_str = data.get("fetched_at")
        age_hours = 0.0
        is_stale = False
        fetched_ist_str = "N/A"

        if fetched_at_str:
            try:
                if fetched_at_str.endswith("Z"):
                    dt_utc = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
                else:
                    dt_utc = datetime.fromisoformat(fetched_at_str)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                age_hours = max(0.0, (now_utc - dt_utc).total_seconds() / 3600.0)
                is_stale = (age_hours > 12.0)
                dt_ist = dt_utc.astimezone(IST_TZ)
                fetched_ist_str = dt_ist.strftime("%I:%M %p IST")
            except Exception as e:
                logger.warning(f"Error parsing snapshot fetched_at '{fetched_at_str}': {e}")

        # Standardize dictionary lookup
        districts_map = data.get("districts") or data.get("current_weather") or {}

        return {
            "raw": data,
            "districts": districts_map,
            "fetched_at_str": fetched_at_str,
            "fetched_ist_str": fetched_ist_str,
            "age_hours": round(age_hours, 2),
            "is_stale": is_stale,
            "source": source_label,
            "districts_count": len(districts_map)
        }

    def get_snapshot(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest weather snapshot.
        Caches in-memory for 10 minutes (600 seconds).
        Tries remote URL first, then falls back to local file if available.
        """
        now = time.time()
        if not force_refresh and self._cached_snapshot is not None:
            if (now - self._cache_timestamp) < self.cache_ttl_seconds:
                return self._cached_snapshot

        # 1. Try remote GitHub URL
        url = getattr(settings, "WEATHER_SNAPSHOT_URL", "").strip()
        if url:
            try:
                logger.info(f"Downloading weather snapshot from {url}...")
                resp = self._session.get(url, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = self._parse_snapshot_data(data, source_label=url)
                    self._cached_snapshot = parsed
                    self._cache_timestamp = now
                    self._last_source = url
                    logger.info(f"Loaded weather snapshot from remote: {parsed['districts_count']} districts (age: {parsed['age_hours']}h).")
                    return parsed
                else:
                    logger.warning(f"Remote snapshot returned HTTP {resp.status_code}.")
            except Exception as e:
                logger.warning(f"Failed to fetch remote weather snapshot from {url}: {e}")

        # 2. Try local fallback file (useful before remote branch is published or for local development)
        local_file = getattr(settings, "WEATHER_SNAPSHOT_LOCAL_FILE", settings.BASE_DIR / "weather_snapshot.json")
        if local_file and Path(local_file).exists():
            try:
                with open(local_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                parsed = self._parse_snapshot_data(data, source_label=f"Local ({local_file.name})")
                self._cached_snapshot = parsed
                self._cache_timestamp = now
                self._last_source = str(local_file)
                logger.info(f"Loaded weather snapshot from local file: {parsed['districts_count']} districts (age: {parsed['age_hours']}h).")
                return parsed
            except Exception as e:
                logger.warning(f"Failed to load local weather snapshot from {local_file}: {e}")

        # 3. If remote and local both failed, but we still have an older cache in memory, keep using it
        if self._cached_snapshot is not None:
            logger.warning("Using existing in-memory snapshot cache despite refresh failure.")
            return self._cached_snapshot

        logger.error("No weather snapshot available (both remote URL and local file failed).")
        return None

    def get_district_raw(self, district_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self.get_snapshot()
        if not snapshot:
            return None
        return snapshot["districts"].get(district_id)

    def get_quality_label(self) -> str:
        snapshot = self.get_snapshot()
        if not snapshot:
            return "UNAVAILABLE"
        time_part = snapshot["fetched_ist_str"]
        if snapshot["is_stale"]:
            return f"SNAPSHOT (STALE, {time_part})"
        return f"SNAPSHOT ({time_part})"

    @property
    def status_info(self) -> Dict[str, Any]:
        snapshot = self.get_snapshot()
        if not snapshot:
            return {
                "status": "UNAVAILABLE",
                "configured_url": getattr(settings, "WEATHER_SNAPSHOT_URL", ""),
                "source": "None",
                "age_hours": None,
                "is_stale": False,
                "fetched_at_ist": "N/A",
                "districts_count": 0
            }

        return {
            "status": "STALE" if snapshot["is_stale"] else "ACTIVE",
            "configured_url": getattr(settings, "WEATHER_SNAPSHOT_URL", ""),
            "source": snapshot["source"],
            "age_hours": snapshot["age_hours"],
            "is_stale": snapshot["is_stale"],
            "fetched_at_utc": snapshot.get("fetched_at_str", "N/A"),
            "fetched_at_ist": snapshot["fetched_ist_str"],
            "districts_count": snapshot["districts_count"]
        }

# Global singleton instance
snapshot_manager = SnapshotManager()
