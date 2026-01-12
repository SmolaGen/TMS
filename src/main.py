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
from src.api.routes import router as api_router
from aiogram.types import Update
from src.workers.scheduler import TMSProjectScheduler

# Prometheus metrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Sentry SDK
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

logger = get_logger(__name__)
configure_logging(settings.LOG_LEVEL)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'tms_requests_total',
    'Total request count',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'tms_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
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
            traces_sample_rate=0.1,  # 10% трейсов
            environment=settings.APP_ENV,
        )
        logger.info("sentry_initialized")
    
    # Инициализация Redis (для LocationManager в API)
    # NOTE: ingest_worker запускается как отдельный процесс (не в lifespan)
    # Это обеспечивает масштабируемость и отказоустойчивость
    logger.info("lifespan_redis_ready")


    # Инициализация Бота (graceful fallback если токен невалидный)
    try:
        bot, dp = await create_bot()
        app.state.bot = bot
        app.state.dp = dp

        # Установка webhook (только в prod/staging, при наличии URL)
        if settings.TELEGRAM_WEBHOOK_URL and "your-bot-token" not in settings.TELEGRAM_BOT_TOKEN:
            await setup_webhook(bot)
            logger.info("bot_webhook_set", url=settings.TELEGRAM_WEBHOOK_URL)
        
        # Запуск планировщика
        if bot:
            scheduler = TMSProjectScheduler(bot)
            await scheduler.start()
            app.state.scheduler = scheduler
    except Exception as e:
        logger.warning("bot_init_failed", error=str(e))
        app.state.bot = None
        app.state.dp = None
    
    yield
    
    # Shutdown
    logger.info("app_stopping")
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        await app.state.scheduler.shutdown()
    await close_db()
    # await init_db()  # Используем alembic вместо автоматического создания


app = FastAPI(
    title="TMS - Transport Management System",
    description="Отказоустойчивая система управления транспортом",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate Limiting (SlowAPI with Redis backend)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    headers_enabled=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware (production: ограничено конкретными доменами)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID and Logging context
app.add_middleware(CorrelationIdMiddleware)

# API Routes
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tms-backend"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/bot/webhook")
async def bot_webhook(update: dict):
    """Эндпоинт для получения обновлений от Telegram."""
    bot = app.state.bot
    dp = app.state.dp
    
    telegram_update = Update.model_validate(update, context={"bot": bot})
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для real-time обновлений."""
    # Проверка Origin для безопасности (CORS для WebSocket)
    origin = websocket.headers.get("origin")
    allowed_origins = settings.CORS_ORIGINS.split(",")
    
    if origin and origin not in allowed_origins:
        logger.warning("websocket_rejected_origin", origin=origin)
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    
    await websocket.accept()
    logger.info("websocket_connected", origin=origin)
    
    # Отправляем приветственное сообщение
    try:
        await websocket.send_json({
            "type": "HELLO",
            "payload": {"message": "Connected to TMS WS"}
        })
    except Exception as e:
        logger.error("websocket_hello_failed", error=str(e))
    
    try:
        while True:
            # Пока просто держим соединение живым
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TMS - Transport Management System",
        "docs": "/docs",
        "redoc": "/redoc",
    }

