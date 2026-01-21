from fastapi import APIRouter

from src.api.endpoints import health, stats

api_router = APIRouter()
api_router.include_router(health.router, prefix="") # Health endpoint at root level
api_router.include_router(stats.router, prefix="")
