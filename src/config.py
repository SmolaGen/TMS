"""
TMS Configuration

Конфигурация приложения через pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tms:tms_secret@localhost:5432/tms_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OSRM
    OSRM_URL: str = "http://localhost:5000"
    
    # Photon
    PHOTON_URL: str = "http://localhost:2322"
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-me"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "your-bot-token"
    TELEGRAM_WEBHOOK_URL: str = "https://myappnf.ru/bot/webhook"
    WEBAPP_URL: str = "https://myappnf.ru/webapp"

    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 86400  # 24 часа


settings = Settings()
