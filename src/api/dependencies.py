from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session_factory
from src.database.uow import SQLAlchemyUnitOfWork
from src.database.models import Driver
from src.services.location_manager import LocationManager
from src.services.order_service import OrderService
from src.services.routing import RoutingService
from src.services.auth_service import AuthService
from src.services.order_workflow import OrderWorkflowService
from src.config import settings

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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

from src.services.driver_service import DriverService

def get_driver_service(uow: SQLAlchemyUnitOfWork = Depends(get_uow)) -> DriverService:
    """Провайдер сервиса водителей."""
    return DriverService(uow)

def get_routing_service() -> RoutingService:
    """Провайдер сервиса маршрутизации."""
    return RoutingService()

def get_order_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    routing: RoutingService = Depends(get_routing_service)
) -> OrderService:
    """Провайдер сервиса заказов."""
    return OrderService(uow, routing)

def get_auth_service() -> AuthService:
    """Провайдер сервиса аутентификации."""
    return AuthService()

security = HTTPBearer()

async def get_current_driver(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
) -> Driver:
    """
    Извлекает текущего водителя из JWT токена.
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    telegram_id = payload.get("sub")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    async with uow:
        # Ищем по telegram_id (sub)
        driver = await uow.drivers.get_by_telegram_id(int(telegram_id))
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Driver not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not driver.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Driver is inactive"
            )
        return driver

def get_order_workflow_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
) -> OrderWorkflowService:
    """Провайдер сервиса управления жизненным циклом заказов."""
    return OrderWorkflowService(uow)
