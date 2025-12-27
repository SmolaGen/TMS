from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from typing import List

from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest, LocationUpdate
from src.services.order_service import OrderService
from src.services.location_manager import LocationManager, DriverLocation
from src.api.dependencies import get_order_service, get_location_manager
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["TMS API"])

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
async def update_location(
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
