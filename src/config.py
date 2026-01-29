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

    @field_validator('SECRET_KEY', 'JWT_SECRET_KEY', 'TELEGRAM_BOT_TOKEN')
    @classmethod
    def validate_not_placeholder(cls, v: str, info) -> str:
        """Ensure secrets are not placeholder values."""

        # CRITICAL: Reject compromised secrets from git history
        # These values were exposed in previous commits and must never be used
        COMPROMISED_SECRETS = {
            # Old JWT secret key (exposed in git history before security fix)
            '6064f7b6b3e7f6d1a9e8b7c6d5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a',
            # Old Telegram bot token (exposed in git history before security fix)
            '8237141688:AAGcLKDClo_RUxXRdO7CeGjNw_zwzITHf4w',
        }

        if v in COMPROMISED_SECRETS:
            raise ValueError(
                f'{info.field_name} is a COMPROMISED secret from git history. '
                f'This value was exposed in previous commits and MUST NOT be used. '
                f'Anyone with repository access can extract this value. '
                f'Generate a new secret immediately using: '
                f'python -c "import secrets; print(secrets.token_hex(32))"'
            )

        placeholder_values = {
            'CHANGE_ME_IN_ENV',
            'CHANGE_ME',
            'your-secret-key-change-me',
            'your-jwt-secret-key-here',
            'your-telegram-bot-token-here',
            'your-bot-token-from-botfather',
        }

        if v in placeholder_values:
            raise ValueError(
                f'{info.field_name} cannot use placeholder value "{v}". '
                f'You must set a real secret in your .env file. '
                f'See .env.example for setup instructions.'
            )

        # Check for CHANGEME_ prefix pattern (from .env.example)
        if v.upper().startswith('CHANGEME'):
            raise ValueError(
                f'{info.field_name} cannot start with "CHANGEME" - this is a placeholder from .env.example. '
                f'You must generate a real secret. '
                f'Use: python -c "import secrets; print(secrets.token_hex(32))"'
            )

        # Enforce minimum length for security
        if len(v) < 32:
            raise ValueError(
                f'{info.field_name} must be at least 32 characters long for security. '
                f'Current length: {len(v)}. Generate a secure secret using: '
                f'python -c "import secrets; print(secrets.token_hex(32))"'
            )

        return v

    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL doesn't contain placeholder or compromised passwords."""

        # Check for placeholder password
        if 'password@' in v or ':password@' in v:
            raise ValueError(
                'DATABASE_URL contains placeholder password. '
                'Set a real database password in your .env file.'
            )

        # CRITICAL: Check for compromised password from git history
        if 'tms_secret' in v.lower():
            raise ValueError(
                'DATABASE_URL contains COMPROMISED password "tms_secret" from git history. '
                'This password was exposed in previous commits and MUST be changed. '
                'Generate a new password and update both the database and .env file. '
                'See SECURITY_FIX.md for rotation instructions.'
            )

        return v

settings = Settings()
