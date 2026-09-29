import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

class Settings:
    APP_NAME: str = "Ushna Kaappaan"
    FULL_TITLE: str = "Ushna Kaappaan — Localized Heat Stress & Early Warning System"
    TAGLINE: str = "From weather conditions to human heat risk."
    VERSION: str = "1.0.0"
    
    # Mode
    APP_MODE: str = os.getenv("APP_MODE", "LIVE").upper()
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ushna_kaappaan.db")
    
    # Open-Meteo
    OPEN_METEO_BASE_URL: str = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
    WEATHER_REFRESH_INTERVAL_HOURS: int = int(os.getenv("WEATHER_REFRESH_INTERVAL_HOURS", "2"))
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    TELEGRAM_AUTO_BROADCAST: bool = os.getenv("TELEGRAM_AUTO_BROADCAST", "false").lower() in ("true", "1", "yes")
    
    # Admin Credentials
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin@ushna2026")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "ushna-kaappaan-jwt-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "https://philips-sujith.github.io,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DISTRICTS_FILE: Path = DATA_DIR / "district_coordinates.json"
    GEOJSON_FILE: Path = DATA_DIR / "south_india_districts.geojson"
    UTCI_CATEGORIES_FILE: Path = DATA_DIR / "utci_categories.json"
    PROFILES_FILE: Path = DATA_DIR / "population_profiles.json"
    MODEL_ARTIFACTS_DIR: Path = BASE_DIR / "backend" / "artifacts" / "mortality_model"

settings = Settings()
