"""
TMS - Transport Management System

FastAPI приложение для управления транспортом.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database.connection import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    if settings.DEBUG:
        # В debug режиме можно инициализировать БД напрямую
        # В продакшене используйте Alembic
        pass
    
    yield
    
    # Shutdown
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
