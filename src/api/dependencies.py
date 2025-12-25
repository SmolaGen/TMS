from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session_factory
from src.database.uow import SQLAlchemyUnitOfWork
from src.services.location_manager import LocationManager
from src.services.order_service import OrderService
from src.config import settings

import redis.asyncio as aioredis

async def get_redis() -> Redis:
    """Провайдер клиента Redis."""
    client = aioredis.from_url(settings.REDIS_URL)
    try:
        yield client
    finally:
        await client.close()

def get_uow() -> SQLAlchemyUnitOfWork:
    """Провайдер Unit of Work."""
    return SQLAlchemyUnitOfWork(async_session_factory)

def get_location_manager(redis: Redis = Depends(get_redis)) -> LocationManager:
    """Провайдер сервиса геолокации."""
    return LocationManager(redis)

def get_order_service(uow: SQLAlchemyUnitOfWork = Depends(get_uow)) -> OrderService:
    """Провайдер сервиса заказов."""
    return OrderService(uow)
