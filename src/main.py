"""
TMS - Transport Management System

FastAPI приложение для управления транспортом.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database.connection import close_db, init_db
from src.core.logging import configure_logging, get_logger
from src.core.middleware import CorrelationIdMiddleware
from src.api.routes import router as api_router
from src.api.dependencies import get_redis
from src.workers.sync_worker import SyncLocationWorker
from src.services.location_manager import LocationManager

import asyncio

logger = get_logger(__name__)
configure_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("app_starting", env=settings.APP_ENV)
    
    # Инициализация Redis для воркера
    async for redis in get_redis():
        location_mgr = LocationManager(redis)
        worker = SyncLocationWorker(location_mgr)
        # Запускаем фоновый воркер
        asyncio.create_task(worker.run())
        break # Нам нужен только один клиент для старта задачи
    
    yield
    
    # Shutdown
    logger.info("app_stopping")
    await close_db()


app = FastAPI(
    title="TMS - Transport Management System",
    description="Отказоустойчивая система управления транспортом",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TMS - Transport Management System",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# TODO: Добавить роуты для:
# - /api/v1/drivers - CRUD для водителей
# - /api/v1/orders - CRUD для заказов
# - /api/v1/routing - Маршрутизация через OSRM
# - /api/v1/geocoding - Геокодинг через Photon
