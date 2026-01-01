from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import List, Optional

from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest, LocationUpdate
from src.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from src.services.order_service import OrderService
from src.services.driver_service import DriverService
from src.services.location_manager import LocationManager, DriverLocation
from src.api.dependencies import (
    get_order_service, 
    get_location_manager, 
    get_driver_service,
    get_geocoding_service,
    get_order_workflow_service,
    get_auth_service,
    get_current_driver
)
from src.services.order_workflow import OrderWorkflowService
from src.services.geocoding import GeocodingService
from src.schemas.geocoding import GeocodingResult
from src.schemas.auth import TelegramAuthRequest, TokenResponse
from src.database.models import OrderStatus, OrderPriority, Driver
from src.services.auth_service import AuthService
from src.core.logging import get_logger
from src.config import settings

# Import limiter from main app (will be set via app.state)
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["TMS API"])

# Локальный limiter для использования в декораторах
# Локальный limiter для использования в декораторах
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

# --- Authentication ---

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: TelegramAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Вход через Telegram WebApp.
    Валидирует initData и возвращает JWT токен.
    Если водитель новый - регистрирует его.
    """
    # 1. Валидация данных от Telegram
    user_data = auth_service.validate_init_data(data.init_data)
    telegram_id = user_data["id"]
    
    # 2. Поиск или регистрация водителя
    driver = await driver_service.get_by_telegram_id(telegram_id)
    if not driver:
        # Авто-регистрация
        driver_dto = DriverCreate(
            telegram_id=telegram_id,
            name=user_data.get("first_name", "Unknown Driver"),
            phone=None  # Телефон можно обновить позже
        )
        driver = await driver_service.register_driver(driver_dto)
        logger.info("driver_auto_registered", telegram_id=telegram_id, driver_id=driver.id)
    
    # 3. Генерация токена
    return auth_service.get_token_response(driver)

# --- Protected Routes ---

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """
    Создать новый заказ. 
    Автоматически привязывается к текущему водителю.
    """
    return await service.create_order(data, driver_id=current_driver.id)

@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Получить список заказов с опциональной фильтрацией по времени."""
    return await service.get_orders_list(start_date=start, end_date=end)

@router.patch("/orders/{order_id}/move", response_model=OrderResponse)
async def move_order(
    order_id: int,
    data: OrderMoveRequest,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Изменить время своего заказа."""
    # TODO: Проверить, принадлежит ли заказ водителю (если нужно)
    result = await service.move_order(order_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return result

@router.post("/orders/{order_id}/assign/{driver_id}", response_model=OrderResponse)
async def assign_order(
    order_id: int,
    driver_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Назначить водителя на заказ."""
    await service.assign_driver(order_id, driver_id)
    return await order_service.get_order(order_id)

@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Отменить заказ."""
    await service.cancel_order(order_id, reason)
    return await order_service.get_order(order_id)

@router.post("/orders/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Завершить заказ."""
    await service.complete_order(order_id)
    return await order_service.get_order(order_id)

@router.post("/orders/{order_id}/arrive", response_model=OrderResponse)
async def mark_arrived(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Отметить прибытие водителя."""
    await service.mark_arrived(order_id)
    return await order_service.get_order(order_id)

@router.post("/orders/{order_id}/start", response_model=OrderResponse)
async def start_trip(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Начать поездку."""
    await service.start_trip(order_id)
    return await order_service.get_order(order_id)

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Получить детали конкретного заказа."""
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/drivers/live", response_model=List[DriverLocation])
async def get_live_drivers(
    current_driver: Driver = Depends(get_current_driver),
    manager: LocationManager = Depends(get_location_manager)
):
    """Получить текущие координаты всех активных водителей (защищено)."""
    return await manager.get_active_drivers()

@router.post("/drivers/{driver_id}/location", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_LOCATION)
async def update_location(
    request: Request,
    driver_id: int,
    data: LocationUpdate,
    current_driver: Driver = Depends(get_current_driver),
    manager: LocationManager = Depends(get_location_manager)
):
    """
    Обновить свои координаты.
    """
    if current_driver.id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Вы можете обновлять только свою геопозицию"
        )
        
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
    current_driver: Driver = Depends(get_current_driver),
    service: DriverService = Depends(get_driver_service)
):
    """Получить список всех водителей (защищено)."""
    return await service.get_all_drivers()

@router.get("/drivers/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: DriverService = Depends(get_driver_service)
):
    """Информация о конкретном водителе (защищено)."""
    driver = await service.get_driver(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.patch("/drivers/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: int,
    data: DriverUpdate,
    current_driver: Driver = Depends(get_current_driver),
    service: DriverService = Depends(get_driver_service)
):
    """Обновить данные водителя (защищено)."""
    # Только сам водитель может себя обновлять (или админ)
    if current_driver.id != driver_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    driver = await service.update_driver(driver_id, data)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

# --- Geocoding ---

@router.get("/geocoding/search", response_model=List[GeocodingResult])
async def search_address(
    q: str,
    limit: int = 10,
    service: GeocodingService = Depends(get_geocoding_service)
):
    """Поиск адресов через Photon."""
    return await service.search(q, limit=limit)

@router.get("/geocoding/reverse", response_model=Optional[GeocodingResult])
async def reverse_geocode(
    lat: float,
    lon: float,
    service: GeocodingService = Depends(get_geocoding_service)
):
    """Обратный геокодинг (адрес по координатам)."""
    return await service.reverse(lat, lon)
