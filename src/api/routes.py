"""
API Routes - Главный роутер для всех API эндпоинтов.
"""
from fastapi import APIRouter

from src.api.endpoints.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

# Health check endpoint
api_router.include_router(health_router, tags=["Health"])
