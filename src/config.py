"""
TMS Configuration

Конфигурация приложения через pydantic-settings.
"""

from decimal import Decimal
from pydantic import field_validator
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
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/dbname"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OSRM
    OSRM_URL: str = "http://localhost:5000"
    OSRM_TIMEOUT: float = 10.0
    
    # Pricing
    PRICE_BASE: Decimal = Decimal("300")
    PRICE_PER_KM: Decimal = Decimal("25")
    
    # Photon
    PHOTON_URL: str = "http://localhost:2322"

    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
    TELEGRAM_INIT_DATA_EXPIRE_SECONDS: int = 86400  # 24 часа
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "CHANGE_ME_IN_ENV"
    TELEGRAM_WEBHOOK_URL: str = "https://myappnf.ru/bot/webhook"
    WEBAPP_URL: str = "https://myappnf.ru/webapp"
    ADMIN_USERNAME: str = "alsmolentsev"
    ADMIN_TELEGRAM_ID: int = 7711619136

    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 86400  # 24 часа

    # Security
    APP_DOMAIN: str = "myappnf.ru"
    CORS_ORIGINS: str = "https://myappnf.ru,https://www.myappnf.ru,https://tg-scan.ru,https://newface25.ru,http://localhost:5173"
    
    # Rate Limiting (SlowAPI)
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_LOCATION: str = "30/minute"  # Защита high-throughput GPS endpoint

    # Notifications
    NOTIFICATIONS_ENABLED: bool = True
    ENABLE_TELEGRAM_NOTIFICATIONS: bool = True
    ENABLE_WEBHOOK_NOTIFICATIONS: bool = True
    NOTIFICATION_RETRY_COUNT: int = 3
    NOTIFICATION_RETRY_DELAY: int = 5  # seconds

    # Health Checks
    HEALTH_CHECK_TIMEOUT: float = 5.0  # seconds
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_CHECK_RETRIES: int = 3

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # seconds
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 120  # seconds


settings = Settings()
