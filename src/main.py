"""
TMS - Transport Management System

FastAPI приложение для управления транспортом.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.database.connection import close_db
from src.bot.main import create_bot, setup_webhook
from src.core.logging import get_logger, configure_logging
from src.core.middleware import CorrelationIdMiddleware
from src.api.routes import api_router  # Import the api_router
from aiogram.types import Update
from src.workers.scheduler import TMSProjectScheduler

# Prometheus metrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Sentry SDK
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Sentry initialization
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
            ),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    logger.info("Sentry initialized.")

# Initialize SlowAPI Limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    """
    logger.info("Application startup...")
    # Initialize scheduler
    app.state.scheduler = TMSProjectScheduler()
    app.state.scheduler.start()
    logger.info("Scheduler started.")

    yield

    logger.info("Application shutdown...")
    # Shutdown scheduler
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown()
        logger.info("Scheduler shut down.")
    await close_db()
    logger.info("Database connection closed.")


app = FastAPI(
    title="TMS API",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add Correlation ID Middleware
app.add_middleware(CorrelationIdMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routes
app.include_router(api_router)


@app.get("/metrics")
async def metrics():
    """
    Endpoint to expose Prometheus metrics.
    """
    return Response(content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.post("/webhook")
async def bot_webhook(update: Update):
    """
    Endpoint for Telegram bot webhooks.
    """
    bot = create_bot()
    await bot.update_queue.put(update)
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    """
    Startup event handler.
    """
    if settings.BOT_WEBHOOK_URL:
        await setup_webhook(settings.BOT_WEBHOOK_URL)
        logger.info(f"Telegram bot webhook set to {settings.BOT_WEBHOOK_URL}")
    else:
        logger.warning("BOT_WEBHOOK_URL is not set. Telegram bot webhook will not be configured.")


# WebSocket endpoint for real-time updates (example)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        logger.info("Client disconnected from websocket")
