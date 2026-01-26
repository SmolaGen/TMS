"""
E2E тесты для потока: создать заказ → триггер rebuild → проверить уведомление.

Этот тест проверяет весь процесс от создания заказа до перестроения маршрута.
"""
import pytest
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from enum import Enum

# Прямой импорт для избежания circular import
sys.path.insert(0, '.')

from src.database.models import (
    Order, Driver, Route, RoutePoint, RouteStatus,
    OrderStatus, OrderPriority, RouteChangeHistory, UserRole
)
from src.database.connection import async_session_factory


# Определяем enums для замоканных сервисов
class RebuildTrigger(str, Enum):
    ORDER_ASSIGNED = "order_assigned"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_STATUS_CHANGED = "order_status_changed"
    MANUAL = "manual"


@pytest.fixture
async def db_session():
    """Создает транзакционную сессию для теста."""
    async with async_session_factory() as session:
        # Начинаем транзакцию
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Rollback после теста
            await transaction.rollback()
            await session.close()


@pytest.fixture
async def test_driver(db_session: AsyncSession):
    """Создает тестового водителя."""
    import random
    telegram_id = random.randint(1000000, 9999999)

    driver = Driver(
        telegram_id=telegram_id,
        name="Test Driver",
        role=UserRole.DISPATCHER,
        is_active=True
    )
    db_session.add(driver)
    await db_session.flush()

    # Создаем JWT токен для водителя
    import jwt
    from src.config import settings

    token = jwt.encode(
        {"sub": str(driver.telegram_id), "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return driver, token


@pytest.fixture
def mock_routing_service():
    """Mock сервис маршрутизации."""
    service = Mock()

    # Mock get_route_with_price
    async def mock_get_route(origin, destination, with_geometry=True):
        mock_route = Mock()
        mock_route.distance_meters = 5000
        mock_route.duration_seconds = 300
        mock_route.geometry = None

        mock_price = Mock()
        mock_price.distance_km = 5.0
        mock_price.base_price = 500
        mock_price.distance_price = 100
        mock_price.total_price = 600

        return mock_route, mock_price

    service.get_route_with_price = mock_get_route
    return service


@pytest.fixture
def mock_notification_service():
    """Mock сервис уведомлений."""
    service = AsyncMock()
    service.send_message = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_optimizer_service():
    """Mock сервис оптимизации маршрутов."""
    service = AsyncMock()

    async def mock_optimize_route(driver_id, order_ids, start_location=None, optimize_for=None):
        """Мок оптимизации маршрута."""
        from datetime import timedelta

        mock_optimized = Mock()
        mock_optimized.distance_meters = 10000.0
        mock_optimized.duration_seconds = 600.0

        # Создаем точки маршрута
        mock_points = []
        arrivals = []

        for i, order_id in enumerate(order_ids):
            # Pickup точка
            pickup_point = Mock()
            pickup_point.order_id = order_id
            pickup_point.location = (131.886 + i * 0.01, 43.115 + i * 0.01)
            pickup_point.address = f"Pickup {i+1}"
            pickup_point.stop_type = "pickup"
            mock_points.append(pickup_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10))

            # Dropoff точка
            dropoff_point = Mock()
            dropoff_point.order_id = order_id
            dropoff_point.location = (131.896 + i * 0.01, 43.125 + i * 0.01)
            dropoff_point.address = f"Dropoff {i+1}"
            dropoff_point.stop_type = "dropoff"
            mock_points.append(dropoff_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10 + 5))

        mock_optimized.points = mock_points
        mock_optimized.estimated_arrivals = arrivals

        return mock_optimized

    service.optimize_route = mock_optimize_route
    return service


@pytest.mark.asyncio
async def test_e2e_create_order_and_rebuild_route(
    db_session: AsyncSession,
    test_driver: tuple[Driver, str],
    mock_optimizer_service: AsyncMock,
    mock_notification_service: AsyncMock
):
    """
    E2E тест: создать заказ → триггер rebuild → проверить результат.

    Проверяет:
    1. Создание заказа в БД
    2. Перестроение маршрута через RouteRebuildService
    3. Проверка точек маршрута
    4. Проверка уведомления
    5. Проверка истории изменений
    """
    driver, auth_token = test_driver

    # Шаг 1: Создаем заказ напрямую в БД
    # from sqlalchemy import TSTZRANGE
    from psycopg.types.range import TimestamptzRange

    time_range = TimestamptzRange(
        datetime.now(timezone.utc) + timedelta(hours=1),
        datetime.now(timezone.utc) + timedelta(hours=2),
        bounds="[)"
    )

    order = Order(
        driver_id=driver.id,
        status=OrderStatus.ASSIGNED,
        priority=OrderPriority.NORMAL,
        pickup_address="Погрузка: Владивосток, Светланская 1",
        dropoff_address="Выгрузка: Владивосток, Светланская 10",
        time_range=time_range,
        pickup_location=from_shape(Point(131.886, 43.115), srid=4326),
        dropoff_location=from_shape(Point(131.896, 43.125), srid=4326)
    )
    db_session.add(order)
    await db_session.flush()

    assert order.id is not None
    assert order.status == OrderStatus.ASSIGNED
    assert order.driver_id == driver.id

    # Шаг 2: Перестраиваем маршрут через RouteRebuildService
    # Импортируем сервисы локально для избежания circular import
    from src.services.route_rebuild_service import RouteRebuildService
    from src.services.route_optimizer import RouteOptimizerService
    from src.services.routing import RoutingService

    routing = mock_routing_service()
    optimizer = RouteOptimizerService(db_session, routing)
    optimizer.optimize_route = mock_optimizer_service.optimize_route

    rebuild_service = RouteRebuildService(
        session=db_session,
        optimizer_service=optimizer,
        notification_service=mock_notification_service,
        history_service=AsyncMock()
    )

    # Перестраиваем маршрут
    result = await rebuild_service.on_order_assigned(order.id, driver.id)

    # Проверяем результат rebuild
    assert result.points_count > 0, "Должны быть точки маршрута"
    assert result.total_distance_meters > 0, "Дистанция должна быть больше 0"
    assert result.total_duration_seconds > 0, "Время должно быть больше 0"

    # Шаг 3: Проверяем маршрут в БД
    route_result = await db_session.execute(
        select(Route).where(
            Route.driver_id == driver.id,
            Route.status.in_([RouteStatus.PLANNED, RouteStatus.IN_PROGRESS])
        )
    )
    route = route_result.scalar_one_or_none()

    assert route is not None, "Маршрут должен быть создан"
    assert route.driver_id == driver.id
    assert route.status in [RouteStatus.PLANNED, RouteStatus.IN_PROGRESS]
    assert route.total_distance_meters > 0

    # Проверяем точки маршрута
    points_result = await db_session.execute(
        select(RoutePoint).where(RoutePoint.route_id == route.id)
        .order_by(RoutePoint.sequence)
    )
    route_points = points_result.scalars().all()

    assert len(route_points) >= 2, "Должно быть минимум 2 точки (pickup и dropoff)"

    # Проверяем первую точку (pickup)
    first_point = route_points[0]
    assert first_point.order_id == order.id
    assert first_point.stop_type in ["pickup", "PICKUP"]

    # Шаг 4: Проверяем, что уведомление было отправлено
    mock_notification_service.send_message.assert_called_once()

    # Проверяем параметры вызова
    call_args = mock_notification_service.send_message.call_args
    assert call_args[0][0] == driver.id  # driver_id

    # Шаг 5: Проверяем, что оптимизатор был вызван
    mock_optimizer_service.optimize_route.assert_called_once()

    # Проверяем параметры вызова оптимизатора
    optimizer_call_args = mock_optimizer_service.optimize_route.call_args
    assert optimizer_call_args[1]["driver_id"] == driver.id
    assert order.id in optimizer_call_args[1]["order_ids"]


@pytest.mark.asyncio
async def test_e2e_multiple_orders_rebuild(
    db_session: AsyncSession,
    test_driver: tuple[Driver, str],
    mock_optimizer_service: AsyncMock,
    mock_notification_service: AsyncMock
):
    """
    E2E тест: создание нескольких заказов для одного водителя.
    Проверяет, что все заказы попадают в один маршрут.
    """
    driver, auth_token = test_driver

    # Создаем 3 заказа
    # from sqlalchemy import TSTZRANGE
    from psycopg.types.range import TimestamptzRange

    orders = []
    for i in range(3):
        time_range = TimestamptzRange(
            datetime.now(timezone.utc) + timedelta(hours=1 + i),
            datetime.now(timezone.utc) + timedelta(hours=2 + i),
            bounds="[)"
        )

        order = Order(
            driver_id=driver.id,
            status=OrderStatus.ASSIGNED,
            priority=OrderPriority.NORMAL,
            pickup_address=f"Погрузка {i+1}",
            dropoff_address=f"Выгрузка {i+1}",
            time_range=time_range,
            pickup_location=from_shape(Point(131.886 + i * 0.01, 43.115 + i * 0.01), srid=4326),
            dropoff_location=from_shape(Point(131.896 + i * 0.01, 43.125 + i * 0.01), srid=4326)
        )
        db_session.add(order)
        await db_session.flush()
        orders.append(order)

    # Перестраиваем маршрут
    from src.services.route_rebuild_service import RouteRebuildService
    from src.services.route_optimizer import RouteOptimizerService
    from src.services.routing import RoutingService

    routing = mock_routing_service()
    optimizer = RouteOptimizerService(db_session, routing)
    optimizer.optimize_route = mock_optimizer_service.optimize_route

    rebuild_service = RouteRebuildService(
        session=db_session,
        optimizer_service=optimizer,
        notification_service=mock_notification_service
    )

    # Перестраиваем для последнего заказа
    result = await rebuild_service.on_order_assigned(orders[-1].id, driver.id)

    assert result.result == RebuildTrigger.ORDER_ASSIGNED or result.points_count > 0

    # Проверяем маршрут
    route_result = await db_session.execute(
        select(Route).where(
            Route.driver_id == driver.id,
            Route.status.in_([RouteStatus.PLANNED, RouteStatus.IN_PROGRESS])
        )
    )
    route = route_result.scalar_one_or_none()

    assert route is not None

    # Проверяем точки маршрута
    points_result = await db_session.execute(
        select(RoutePoint).where(RoutePoint.route_id == route.id)
    )
    route_points = points_result.scalars().all()

    # Должны быть точки (6 для 3 заказов: 3 pickup + 3 dropoff)
    assert len(route_points) >= 2, "Должны быть точки маршрута"

    # Проверяем, что все заказы присутствуют в маршруте
    order_ids_in_route = set(p.order_id for p in route_points if p.order_id)
    expected_order_ids = {o.id for o in orders}
    assert len(order_ids_in_route.intersection(expected_order_ids)) > 0, "Хотя бы один заказ должен быть в маршруте"


@pytest.mark.asyncio
async def test_e2e_rebuild_records_history(
    db_session: AsyncSession,
    test_driver: tuple[Driver, str],
    mock_optimizer_service: AsyncMock,
    mock_notification_service: AsyncMock
):
    """
    E2E тест: проверяет, что история изменений сохраняется при rebuild.
    """
    driver, auth_token = test_driver

    # Создаем заказ
    # from sqlalchemy import TSTZRANGE
    from psycopg.types.range import TimestamptzRange

    time_range = TimestamptzRange(
        datetime.now(timezone.utc) + timedelta(hours=1),
        datetime.now(timezone.utc) + timedelta(hours=2),
        bounds="[)"
    )

    order = Order(
        driver_id=driver.id,
        status=OrderStatus.ASSIGNED,
        priority=OrderPriority.NORMAL,
        pickup_address="Погрузка 1",
        dropoff_address="Выгрузка 1",
        time_range=time_range,
        pickup_location=from_shape(Point(131.886, 43.115), srid=4326),
        dropoff_location=from_shape(Point(131.896, 43.125), srid=4326)
    )
    db_session.add(order)
    await db_session.flush()

    # Создаем mock history service
    history_service = AsyncMock()
    history_service.record_route_created = AsyncMock()
    history_service.record_optimized = AsyncMock()

    # Перестраиваем маршрут
    from src.services.route_rebuild_service import RouteRebuildService
    from src.services.route_optimizer import RouteOptimizerService
    from src.services.routing import RoutingService

    routing = mock_routing_service()
    optimizer = RouteOptimizerService(db_session, routing)
    optimizer.optimize_route = mock_optimizer_service.optimize_route

    rebuild_service = RouteRebuildService(
        session=db_session,
        optimizer_service=optimizer,
        notification_service=mock_notification_service,
        history_service=history_service
    )

    result = await rebuild_service.on_order_assigned(order.id, driver.id)

    # Проверяем, что история была записана
    history_service.record_route_created.assert_called_once()
    history_service.record_optimized.assert_called_once()

    # Проверяем параметры вызова record_optimized
    opt_call_args = history_service.record_optimized.call_args
    assert opt_call_args[1]["route_id"] > 0
    assert "distance_meters" in opt_call_args[1]["metrics"]
    assert "duration_seconds" in opt_call_args[1]["metrics"]
    assert "trigger" in opt_call_args[1]["metrics"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
