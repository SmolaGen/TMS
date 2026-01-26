from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
from typing import List, Optional

from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest, LocationUpdate
from src.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from src.services.order_service import OrderService
from src.services.driver_service import DriverService
from src.services.location_manager import LocationManager, DriverLocation
from src.services.excel_import import ExcelImportService
from src.api.dependencies import (
    get_order_service, 
    get_location_manager, 
    get_driver_service,
    get_geocoding_service,
    get_order_workflow_service,
    get_auth_service,
    get_current_driver,
    get_batch_assignment_service,
    get_excel_import_service
)
from fastapi import File, UploadFile
from src.services.order_workflow import OrderWorkflowService
from src.services.geocoding import GeocodingService
from src.schemas.geocoding import GeocodingResult
from src.schemas.auth import TelegramAuthRequest, TokenResponse
from src.database.models import OrderStatus, OrderPriority, Driver
from src.services.auth_service import AuthService
from src.services.batch_assignment import BatchAssignmentService
from src.schemas.batch_assignment import (
    BatchAssignmentRequest,
    BatchAssignmentResult,
    BatchPreviewResponse,
    UnassignedOrdersResponse,
    DriverScheduleResponse
)
from src.schemas.stats import DetailedStatsResponse
from src.core.logging import get_logger
from src.config import settings
from src.api.contractors import router as contractor_router
from src.api.endpoints.drivers import router as driver_endpoints_router
from src.api.endpoints.notifications import router as notifications_router

# Import limiter from main app (will be set via app.state)
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["TMS API"])
router.include_router(contractor_router)
router.include_router(driver_endpoints_router)
router.include_router(notifications_router)

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
        driver = await driver_service.create_driver_from_telegram(
            telegram_id=telegram_id,
            name=user_data.get("first_name", "Unknown Driver"),
            username=user_data.get("username")
        )
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
    Диспетчеры и админы могут назначать на любого водителя.
    Водители могут создавать заказы только для себя.
    """
    from src.database.models import UserRole
    
    # Диспетчеры и админы могут назначать на любого водителя
    if current_driver.role in (UserRole.ADMIN, UserRole.DISPATCHER):
        # Используем driver_id из запроса (может быть None для неназначенных)
        target_driver_id = data.driver_id
    else:
        # Водители создают заказы только для себя
        target_driver_id = current_driver.id
    
    return await service.create_order(data, driver_id=target_driver_id)

@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    include_geometry: bool = False,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Получить список заказов с опциональной фильтрацией по времени."""
    return await service.get_orders_list(start_date=start, end_date=end, include_geometry=include_geometry)

@router.post("/orders/import/excel")
async def import_orders_excel(
    file: UploadFile = File(...),
    excel_service: ExcelImportService = Depends(get_excel_import_service)
):
    """
    Импорт заказов из Excel.
    Геокодинг выполняется автоматически для каждого заказа.
    """
    try:
        orders_data = await excel_service.parse_excel(file)
        result = await excel_service.import_orders(orders_data)
        return result
    except Exception as e:
        logger.exception("excel_import_failed")
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {str(e)}")

@router.patch("/orders/{order_id}/move", response_model=OrderResponse)
async def move_order(
    order_id: int,
    data: OrderMoveRequest,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Изменить время заказа. Водители могут перемещать только свои заказы."""
    from src.database.models import UserRole
    
    # Проверка прав доступа
    order = await service.get_order(order_id)
    
    # Водители могут перемещать только свои заказы
    if current_driver.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        if order.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете перемещать только свои заказы"
            )
    
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
    from statemachine.exceptions import TransitionNotAllowed
    try:
        await service.cancel_order(order_id, reason)
        return await order_service.get_order(order_id)
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/orders/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Завершить заказ."""
    from statemachine.exceptions import TransitionNotAllowed
    try:
        await service.complete_order(order_id)
        return await order_service.get_order(order_id)
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/orders/{order_id}/depart", response_model=OrderResponse)
async def mark_departed(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Отметить выезд водителя к клиенту."""
    from statemachine.exceptions import TransitionNotAllowed
    try:
        await service.mark_departed(order_id)
        return await order_service.get_order(order_id)
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/orders/{order_id}/arrive", response_model=OrderResponse)
async def mark_arrived(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Отметить прибытие водителя."""
    from statemachine.exceptions import TransitionNotAllowed
    try:
        await service.mark_arrived(order_id)
        return await order_service.get_order(order_id)
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/orders/{order_id}/start", response_model=OrderResponse)
async def start_trip(
    order_id: int,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderWorkflowService = Depends(get_order_workflow_service),
    order_service: OrderService = Depends(get_order_service)
):
    """Начать поездку."""
    from statemachine.exceptions import TransitionNotAllowed
    try:
        await service.start_trip(order_id)
        return await order_service.get_order(order_id)
    except TransitionNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/orders/active", response_model=List[OrderResponse])
async def get_active_orders(
    start_date: datetime,
    end_date: datetime,
    current_driver: Driver = Depends(get_current_driver),
    service: OrderService = Depends(get_order_service)
):
    """Получить активные заказы за период."""
    return await service.get_orders_list(start_date=start_date, end_date=end_date)

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
    service: DriverService = Depends(get_driver_service),
    manager: LocationManager = Depends(get_location_manager)
):
    """
    Получить список всех водителей (защищено).
    Включает is_online статус на основе активности в Redis (геолокация < 5 минут).
    """
    drivers = await service.get_all_drivers()
    online_driver_ids = await manager.get_active_driver_ids()
    online_set = set(online_driver_ids)

    for driver in drivers:
        driver.is_online = driver.id in online_set

    return drivers

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

from src.schemas.driver import DriverStatsResponse

@router.get("/drivers/{driver_id}/stats", response_model=DriverStatsResponse)
async def get_driver_stats(
    driver_id: int,
    days: int = 30,  # Количество дней для статистики
    current_driver: Driver = Depends(get_current_driver),
    service: DriverService = Depends(get_driver_service)
):
    """Получить статистику водителя за период."""
    stats = await service.get_driver_stats(driver_id, days)
    if not stats:
        raise HTTPException(status_code=404, detail="Driver not found")
    return stats

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


# --- Routing ---

from src.schemas.routing import RouteResponse
from src.services.routing import RoutingService, RouteNotFoundError, OSRMUnavailableError
from src.api.dependencies import get_routing_service

@router.get("/routing/route", response_model=RouteResponse)
async def get_route(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    with_geometry: bool = True,
    service: RoutingService = Depends(get_routing_service)
):
    """
    Получить маршрут между двумя точками.
    
    Возвращает: расстояние, время, стоимость и polyline геометрию.
    """
    try:
        route, price = await service.get_route_with_price(
            origin=(origin_lon, origin_lat),  # OSRM ожидает (lon, lat)
            destination=(destination_lon, destination_lat),
            with_geometry=with_geometry
        )
        
        return RouteResponse(
            distance_meters=route.distance_meters,
            distance_km=float(price.distance_km),
            duration_seconds=route.duration_seconds,
            duration_minutes=round(route.duration_seconds / 60, 1),
            geometry=route.geometry,
            base_price=price.base_price,
            distance_price=price.distance_price,
            total_price=price.total_price
        )
    except RouteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Маршрут не найден между указанными точками"
        )
    except OSRMUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис маршрутизации временно недоступен"
        )


# --- Batch Assignment ---

@router.post("/orders/batch-assign", response_model=BatchAssignmentResult)
async def batch_assign_orders(
    request: BatchAssignmentRequest,
    current_driver: Driver = Depends(get_current_driver),
    service: BatchAssignmentService = Depends(get_batch_assignment_service)
):
    """
    Запустить автоматическое batch-распределение заказов на указанную дату.

    Доступно только диспетчерам и администраторам.
    """
    from src.database.models import UserRole

    # Проверка прав доступа
    if current_driver.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )

    try:
        result = await service.assign_orders_batch(request)
        return result
    except Exception as e:
        logger.error(f"Batch assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при распределении заказов"
        )


@router.get("/orders/batch-preview/{target_date}", response_model=BatchPreviewResponse)
async def preview_batch_assignment(
    target_date: date,
    priority_filter: Optional[OrderPriority] = None,
    driver_ids: Optional[str] = None,  # comma-separated
    max_orders_per_driver: int = 10,
    current_driver: Driver = Depends(get_current_driver),
    service: BatchAssignmentService = Depends(get_batch_assignment_service)
):
    """
    Предпросмотр распределения заказов без фактического назначения.

    Доступно только диспетчерам и администраторам.
    """
    from src.database.models import UserRole

    # Проверка прав доступа
    if current_driver.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )

    try:
        # Парсинг driver_ids из строки
        parsed_driver_ids = None
        if driver_ids:
            try:
                parsed_driver_ids = [int(x.strip()) for x in driver_ids.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный формат driver_ids"
                )

        request = BatchAssignmentRequest(
            target_date=target_date,
            priority_filter=priority_filter,
            driver_ids=parsed_driver_ids,
            max_orders_per_driver=max_orders_per_driver
        )

        result = await service.preview_assignments(request)
        return BatchPreviewResponse(result=result)
    except Exception as e:
        logger.error(f"Batch preview failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при предпросмотре распределения"
        )


@router.get("/orders/unassigned/{target_date}", response_model=UnassignedOrdersResponse)
async def get_unassigned_orders(
    target_date: date,
    current_driver: Driver = Depends(get_current_driver),
    order_service: OrderService = Depends(get_order_service)
):
    """
    Получить список нераспределенных заказов на указанную дату.

    Доступно диспетчерам и администраторам.
    """
    from src.database.models import UserRole
    from datetime import datetime, time

    # Проверка прав доступа
    if current_driver.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )

    try:
        # Получить заказы через OrderRepository
        from src.database.repository import OrderRepository
        from src.database.connection import async_session_factory
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(async_session_factory) as session:
            repo = OrderRepository(session)
            orders = await repo.get_unassigned_orders_on_date(target_date)

            # Преобразовать в словарь для ответа
            orders_data = []
            for order in orders:
                orders_data.append({
                    "id": order.id,
                    "pickup_address": order.pickup_address,
                    "dropoff_address": order.dropoff_address,
                    "priority": order.priority.value,
                    "time_start": order.time_range.lower.isoformat() if order.time_range else None,
                    "time_end": order.time_range.upper.isoformat() if order.time_range else None,
                    "distance_meters": order.distance_meters,
                    "duration_seconds": order.duration_seconds
                })

            return UnassignedOrdersResponse(
                orders=orders_data,
                total_count=len(orders_data),
                target_date=target_date
            )
    except Exception as e:
        logger.error(f"Failed to get unassigned orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка заказов"
        )


@router.get("/drivers/{driver_id}/schedule/{target_date}", response_model=DriverScheduleResponse)
async def get_driver_schedule(
    driver_id: int,
    target_date: date,
    current_driver: Driver = Depends(get_current_driver),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Получить расписание водителя на указанную дату.

    Доступно диспетчерам, администраторам и самому водителю.
    """
    from src.database.models import UserRole

    # Проверка прав доступа
    if current_driver.role not in (UserRole.ADMIN, UserRole.DISPATCHER) and current_driver.id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра расписания"
        )

    try:
        # Получить информацию о водителе
        driver = await driver_service.get_driver(driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Водитель не найден")

        # Получить заказы водителя на дату
        from src.database.repository import OrderRepository
        from src.database.connection import async_session_factory
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(async_session_factory) as session:
            repo = OrderRepository(session)
            orders = await repo.get_driver_orders_on_date(driver_id, target_date)

            # Преобразовать заказы в элементы расписания
            schedule_items = []
            for order in orders:
                schedule_items.append({
                    "order_id": order.id,
                    "time_start": order.time_range.lower.isoformat() if order.time_range else None,
                    "time_end": order.time_range.upper.isoformat() if order.time_range else None,
                    "pickup_address": order.pickup_address,
                    "dropoff_address": order.dropoff_address,
                    "status": order.status.value,
                    "priority": order.priority.value
                })

            return DriverScheduleResponse(
                driver_id=driver_id,
                driver_name=driver.name,
                target_date=target_date,
                schedule=schedule_items,
                total_orders=len(schedule_items),
                available_slots=max(0, 10 - len(schedule_items))  # Примерное количество слотов
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get driver schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении расписания водителя"
        )


# --- Statistics ---

@router.get("/stats/detailed", response_model=DetailedStatsResponse)
async def get_detailed_stats(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    current_driver: Driver = Depends(get_current_driver),
    order_service: OrderService = Depends(get_order_service),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Получить детализированную статистику за период.
    
    По умолчанию возвращает статистику за последние 7 дней.
    """
    from datetime import timedelta
    from collections import defaultdict
    from src.database.models import DriverStatus
    
    # Определяем период
    if not end:
        end = datetime.now()
    if not start:
        start = end - timedelta(days=7)
    
    try:
        # Получаем заказы за период
        orders = await order_service.get_orders_list(start_date=start, end_date=end)
        
        # Статистика по статусам
        by_status = defaultdict(int)
        for order in orders:
            by_status[order.status.value] += 1
        
        # Статистика по приоритетам
        by_priority = defaultdict(int)
        for order in orders:
            by_priority[order.priority.value] += 1
        
        # Статистика по часам
        by_hour = defaultdict(int)
        for order in orders:
            if order.time_start:
                hour = order.time_start.hour
                by_hour[hour] += 1
        hourly_stats = [{"hour": h, "count": by_hour.get(h, 0)} for h in range(24)]
        
        # Статистика по дням
        by_day = defaultdict(lambda: {"count": 0, "revenue": 0.0})
        for order in orders:
            if order.time_start:
                date_str = order.time_start.strftime("%d.%m")
                by_day[date_str]["count"] += 1
                by_day[date_str]["revenue"] += float(order.price or 0)
        
        daily_stats = [{"date": d, "count": v["count"], "revenue": v["revenue"]} for d, v in sorted(by_day.items())]
        
        # Общая выручка
        total_revenue = sum(float(o.price or 0) for o in orders)
        avg_revenue = total_revenue / len(orders) if orders else 0
        
        # Водители
        all_drivers = await driver_service.get_all_drivers()
        active_drivers = [d for d in all_drivers if d.status == DriverStatus.AVAILABLE or d.status == DriverStatus.BUSY]
        
        # Топ водителей (по количеству выполненных заказов)
        driver_orders = defaultdict(lambda: {"completed": 0, "revenue": 0.0, "name": ""})
        for order in orders:
            if order.driver_id and order.status.value == "completed":
                driver_orders[order.driver_id]["completed"] += 1
                driver_orders[order.driver_id]["revenue"] += float(order.price or 0)
                driver_orders[order.driver_id]["name"] = order.driver_name or f"Driver #{order.driver_id}"
        
        top_drivers = sorted(
            [
                {
                    "driver_id": did,
                    "name": data["name"],
                    "completed_orders": data["completed"],
                    "total_revenue": data["revenue"],
                    "average_rating": None
                }
                for did, data in driver_orders.items()
            ],
            key=lambda x: x["completed_orders"],
            reverse=True
        )[:5]
        
        # Статистика маршрутов
        total_distance = sum(float(o.distance_meters or 0) for o in orders) / 1000  # в км
        avg_distance = total_distance / len(orders) if orders else 0
        
        longest_order = max(orders, key=lambda o: o.distance_meters or 0, default=None)
        longest_route = {
            "distance": float(longest_order.distance_meters or 0) / 1000 if longest_order else 0,
            "order_id": longest_order.id if longest_order else 0
        }
        
        return DetailedStatsResponse(
            period={
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            orders={
                "total": len(orders),
                "byStatus": dict(by_status),
                "byPriority": dict(by_priority),
                "byHour": hourly_stats,
                "byDay": daily_stats,
                "averageRevenue": avg_revenue,
                "totalRevenue": total_revenue
            },
            drivers={
                "total": len(all_drivers),
                "active": len(active_drivers),
                "topDrivers": top_drivers
            },
            routes={
                "totalDistance": total_distance,
                "averageDistance": avg_distance,
                "longestRoute": longest_route
            }
        )
    except Exception as e:
        logger.error(f"Failed to get detailed stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )


@router.get("/stats/overview")
async def get_stats_overview(
    current_driver: Driver = Depends(get_current_driver),
    order_service: OrderService = Depends(get_order_service),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Получить краткую статистику для Dashboard KPI.
    Возвращает активные заказы, свободных водителей, завершенные сегодня, алерты.
    """
    from datetime import timedelta
    from src.database.models import DriverStatus, OrderStatus
    
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Получаем все заказы за сегодня
        orders = await order_service.get_orders_list(start_date=today_start, end_date=today_end)
        
        # Активные заказы (не completed, не cancelled)
        active_statuses = [OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.EN_ROUTE_PICKUP, 
                          OrderStatus.DRIVER_ARRIVED, OrderStatus.IN_PROGRESS]
        active_orders = len([o for o in orders if o.status in active_statuses])
        
        # Завершенные сегодня
        completed_today = len([o for o in orders if o.status == OrderStatus.COMPLETED])
        
        # Водители
        all_drivers = await driver_service.get_all_drivers()
        free_drivers = len([d for d in all_drivers if d.status == DriverStatus.AVAILABLE])
        
        # Алерты — заказы без водителя более 10 минут
        alerts = []
        now = datetime.now()
        for order in orders:
            if order.status == OrderStatus.PENDING and order.created_at:
                age_minutes = (now - order.created_at).total_seconds() / 60
                if age_minutes > 10:
                    alerts.append({
                        "id": str(order.id),
                        "type": "warning",
                        "title": f"Заказ #{order.id} без водителя",
                        "description": f"Ожидает назначения более {int(age_minutes)} минут",
                        "timestamp": order.created_at.isoformat(),
                        "orderId": order.id
                    })
        
        return {
            "stats": {
                "activeOrders": active_orders,
                "freeDrivers": free_drivers,
                "completedToday": completed_today,
                "averageRating": 4.8,  # TODO: добавить реальный расчет
                "averageWaitTime": 5   # TODO: добавить реальный расчет
            },
            "alerts": alerts[:10]  # Максимум 10 алертов
        }
    except Exception as e:
        logger.error(f"Failed to get stats overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении обзора статистики"
        )
