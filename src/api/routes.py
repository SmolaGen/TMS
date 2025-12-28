from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from typing import List

from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest, LocationUpdate
from src.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from src.services.order_service import OrderService
from src.services.driver_service import DriverService
from src.services.location_manager import LocationManager, DriverLocation
from src.api.dependencies import get_order_service, get_location_manager, get_driver_service
from src.core.logging import get_logger
from src.config import settings

# Import limiter from main app (will be set via app.state)
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["TMS API"])

# Локальный limiter для использования в декораторах
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    """
    Создать новый заказ. 
    Проверяет пересечение времени для водителя на уровне БД (Exclusion Constraint).
    """
    try:
        return await service.create_order(data)
    except IntegrityError as e:
        # 23P01 - Код ошибки PostgreSQL для Exclusion Constraint
        if hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23P01':
            logger.warning("order_overlap_detected", driver_id=data.driver_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "time_overlap", "message": "Driver is busy at this time"}
            )
        raise

@router.patch("/orders/{order_id}/move", response_model=OrderResponse)
async def move_order(
    order_id: int,
    data: OrderMoveRequest,
    service: OrderService = Depends(get_order_service)
):
    """Изменить время заказа (например, Drag-and-Drop в UI)."""
    try:
        result = await service.move_order(order_id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Order not found")
        return result
    except IntegrityError as e:
        if hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23P01':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "time_overlap", "message": "Driver is busy at this time"}
            )
        raise

@router.get("/drivers/live", response_model=List[DriverLocation])
async def get_live_drivers(
    manager: LocationManager = Depends(get_location_manager)
):
    """Получить текущие координаты всех активных водителей (из Redis)."""
    return await manager.get_active_drivers()

@router.post("/drivers/{driver_id}/location", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_LOCATION)
async def update_location(
    request: Request,  # Required by SlowAPI
    driver_id: int,
    data: LocationUpdate,
    manager: LocationManager = Depends(get_location_manager)
):
    """
    Обновить координаты водителя. 
    Пишет только в Redis буфер. БД обновляется позже воркером.
    """
    await manager.update_driver_location(
        driver_id=driver_id,
        latitude=data.latitude,
        longitude=data.longitude,
        status=data.status or "available",
        timestamp=data.timestamp
    )
    return None


# --- Driver Management ---

@router.post("/drivers", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def register_driver(
    data: DriverCreate,
    service: DriverService = Depends(get_driver_service)
):
    """Регистрация нового водителя."""
    try:
        return await service.register_driver(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/drivers", response_model=List[DriverResponse])
async def list_drivers(
    service: DriverService = Depends(get_driver_service)
):
    """Получить список всех водителей."""
    return await service.get_all_drivers()

@router.get("/drivers/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: int,
    service: DriverService = Depends(get_driver_service)
):
    """Информация о конкретном водителе."""
    driver = await service.get_driver(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.patch("/drivers/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: int,
    data: DriverUpdate,
    service: DriverService = Depends(get_driver_service)
):
    """Обновить данные водителя (включая статус и активность)."""
    driver = await service.update_driver(driver_id, data)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver
