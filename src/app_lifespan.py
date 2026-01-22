
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.config import settings
from src.core.logging import get_logger, configure_logging
from src.telegram_bot_module import setup_telegram_bot, shutdown_telegram_bot_module
from src.database.connection import close_db
from src.workers.scheduler import TMSProjectScheduler

# Sentry SDK
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("app_starting", env=settings.APP_ENV)

    # Initialize Sentry (only in production)
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn and settings.APP_ENV == "production":
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,
            environment=settings.APP_ENV,
        )
        logger.info("sentry_initialized")

    logger.info("lifespan_redis_ready")

    # Bot logic moved to setup_telegram_bot which is called from create_app or lifespan
    # But lifespan here seems to duplicate it or try to start scheduler without bot

    # Initialize Bot and Scheduler
    await setup_telegram_bot(app)

    yield

    # Shutdown
    logger.info("app_stopping")
    await shutdown_telegram_bot_module(app)
    await close_db()
