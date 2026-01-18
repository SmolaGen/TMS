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

    # Routing Service
    PRICE_BASE: Decimal = Decimal("100.00") # Added missing setting

# Instantiate settings to be imported by other modules
settings = Settings()
