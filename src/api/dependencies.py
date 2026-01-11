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
from src.services.geocoding import GeocodingService
from src.services.order_workflow import OrderWorkflowService
from src.services.batch_assignment import BatchAssignmentService
from src.services.notification_service import NotificationService
from src.services.urgent_assignment import UrgentAssignmentService
from src.services.excel_import import ExcelImportService
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

async def get_urgent_assignment_service(
    location_manager: LocationManager = Depends(get_location_manager)
) -> UrgentAssignmentService:
    """Провайдер сервиса срочного назначения."""
    from src.database.connection import async_session_factory
    from sqlalchemy.ext.asyncio import AsyncSession
    
    session = AsyncSession(async_session_factory)
    try:
        yield UrgentAssignmentService(session, location_manager)
    finally:
        await session.close()

def get_routing_service() -> RoutingService:
    """Провайдер сервиса маршрутизации."""
    return RoutingService()

def get_order_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    routing: RoutingService = Depends(get_routing_service),
    urgent_service: UrgentAssignmentService = Depends(get_urgent_assignment_service),
    notification_service: NotificationService = Depends(get_notification_service)
) -> OrderService:
    """Провайдер сервиса заказов."""
    return OrderService(uow, routing, urgent_service, notification_service)

def get_excel_import_service(
    order_service: OrderService = Depends(get_order_service)
) -> ExcelImportService:
    """Провайдер сервиса импорта Excel."""
    return ExcelImportService(order_service)

def get_auth_service() -> AuthService:
    """Провайдер сервиса аутентификации."""
    return AuthService()

def get_geocoding_service() -> GeocodingService:
    """Провайдер сервиса геокодинга."""
    return GeocodingService()

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

async def get_notification_service(
    request: Request,
) -> NotificationService:
    """Провайдер сервиса уведомлений."""
    from src.database.connection import async_session_factory
    from sqlalchemy.ext.asyncio import AsyncSession
    
    bot = getattr(request.app.state, "bot", None)
    session = AsyncSession(async_session_factory)
    try:
        yield NotificationService(bot, session)
    finally:
        await session.close()

async def get_batch_assignment_service(
    order_service: OrderService = Depends(get_order_service),
    notification_service: NotificationService = Depends(get_notification_service)
) -> BatchAssignmentService:
    """Провайдер сервиса batch-распределения заказов."""
    from src.database.connection import async_session_factory
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(async_session_factory)
    try:
        yield BatchAssignmentService(session, order_service, notification_service)
    finally:
        await session.close()
