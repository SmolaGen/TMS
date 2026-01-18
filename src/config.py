"""
TMS Configuration

Конфигурация приложения через pydantic-settings.
"""

from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application Version
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tms:tms_secret@localhost:5432/tms_db"
    DEBUG: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Geocoding Service (Photon)
    PHOTON_URL: str = "http://localhost:2322/photon"

    # OSRM Routing Service
    OSRM_URL: str = "http://localhost:5000"

    # Routing Service Price Base
    PRICE_BASE: Decimal = Decimal("10.00")
    PRICE_PER_KM: Decimal = Decimal("1.00")

    # Sentry
    SENTRY_DSN: Optional[str] = None
    
    # Bot
    TELEGRAM_BOT_TOKEN: str = "placeholder"
    BOT_WEBHOOK_URL: str = "http://localhost:8000/webhook"
    TELEGRAM_INIT_DATA_EXPIRE_SECONDS: int = 86400

    # Security
    JWT_SECRET_KEY: str = "supersecret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30




# Создаём экземпляр настроек
settings = Settings()
