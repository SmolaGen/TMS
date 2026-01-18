from fastapi import APIRouter

from src.api.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="") # Health endpoint at root level
