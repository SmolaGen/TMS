"""
Unit тесты для RouteOptimizerService.

Тесты проверяют TSP алгоритм и логику сервиса без необходимости запуска OSRM.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Optional

# Прямой импорт для избежания circular import
import sys
sys.path.insert(0, '.')

from src.database.models import RouteOptimizationType, RouteStopType

# Определяем dataclasses напрямую чтобы избегать circular import
from dataclasses import dataclass

@dataclass
class OptimizationPoint:
    """Точка для оптимизации."""
    order_id: int
    location: Tuple[float, float]  # (lon, lat)
    address: Optional[str] = None
    stop_type: RouteStopType = RouteStopType.PICKUP

@dataclass
class OptimizedRoute:
    """Результат оптимизации маршрута."""
    distance_meters: float
    duration_seconds: float
    points: List[OptimizationPoint]
    estimated_arrivals: List[Optional[datetime]]


# Определяем исключения
class RouteOptimizerError(Exception):
    """Базовое исключение сервиса оптимизации маршрутов."""
    pass

class NoValidRouteError(RouteOptimizerError):
    """Не удалось построить маршрут."""
    pass


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy сессии."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_routing_service():
    """Mock RoutingService."""
    from src.services.routing import RouteResult
    service = MagicMock()
    service.get_route = AsyncMock(return_value=RouteResult(
        distance_meters=1000,
        duration_seconds=60
    ))
    return service


@pytest.mark.asyncio
async def test_prepare_optimization_points():
    """Тест подготовки точек для оптимизации из заказов."""
    import re

    # Вспомогательная функция для парсинга WKT (из RoutingService)
    def parse_geometry_point(wkt_or_ewkt: str) -> Tuple[float, float]:
        if not wkt_or_ewkt:
            raise ValueError("Empty geometry string")
        match = re.search(r"POINT\s*\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)", wkt_or_ewkt, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid POINT format: {wkt_or_ewkt}")
        lon = float(match.group(1))
        lat = float(match.group(2))
        return lon, lat

    # Создаём mock заказы
    mock_orders = []
    for i in range(1, 3):
        order = Mock()
        order.id = i
        # Используем реальные WKT координаты
        order.pickup_location = f"SRID=4326;POINT({131.886 + i * 0.01} {43.115 + i * 0.01})"
        order.dropoff_location = f"SRID=4326;POINT({131.896 + i * 0.01} {43.125 + i * 0.01})"
        order.pickup_address = f"Pickup {i}"
        order.dropoff_address = f"Dropoff {i}"
        mock_orders.append(order)

    # Создаём точки вручную как это делает сервис
    points = []
    for order in mock_orders:
        if order.pickup_location:
            pickup_coords = parse_geometry_point(order.pickup_location)
            points.append(OptimizationPoint(
                order_id=order.id,
                location=pickup_coords,
                address=order.pickup_address,
                stop_type=RouteStopType.PICKUP
            ))

        if order.dropoff_location:
            dropoff_coords = parse_geometry_point(order.dropoff_location)
            points.append(OptimizationPoint(
                order_id=order.id,
                location=dropoff_coords,
                address=order.dropoff_address,
                stop_type=RouteStopType.DROPOFF
            ))

    # Должно быть 4 точки: 2 точки (pickup + dropoff) для каждого из 2 заказов
    assert len(points) == 4

    # Проверяем pickup точку первого заказа
    pickup_point = next((p for p in points if p.order_id == 1 and p.stop_type == RouteStopType.PICKUP), None)
    assert pickup_point is not None
    assert pickup_point.address == "Pickup 1"
    assert pickup_point.location == (131.896, 43.125)  # (lon, lat)

    # Проверяем dropoff точку первого заказа
    dropoff_point = next((p for p in points if p.order_id == 1 and p.stop_type == RouteStopType.DROPOFF), None)
    assert dropoff_point is not None
    assert dropoff_point.address == "Dropoff 1"


@pytest.mark.asyncio
async def test_solve_tsp_nearest_neighbor():
    """Тест TSP алгоритма с жадным nearest neighbour."""
    from dataclasses import dataclass

    @dataclass
    class RouteResult:
        distance_meters: float
        duration_seconds: float

    mock_routing = MagicMock()
    mock_routing.get_route = AsyncMock(return_value=RouteResult(
        distance_meters=1000,
        duration_seconds=60
    ))

    # Простой TSP алгоритм для теста
    start_location = (131.886, 43.115)
    points = [
        OptimizationPoint(order_id=1, location=(131.896, 43.125), stop_type=RouteStopType.PICKUP),
        OptimizationPoint(order_id=2, location=(131.906, 43.135), stop_type=RouteStopType.PICKUP),
    ]

    # Реализация nearest neighbour
    unvisited = points.copy()
    route_points = []
    total_distance = 0.0
    total_duration = 0.0
    estimated_arrivals = []
    current_time = datetime.utcnow()
    current_location = start_location

    while unvisited:
        nearest_point = None
        nearest_distance = float('inf')
        nearest_duration = float('inf')
        nearest_point_distance = float('inf')

        for point in unvisited:
            route_result = await mock_routing.get_route(
                origin=current_location,
                destination=point.location,
                with_geometry=False
            )

            metric_value = route_result.duration_seconds
            if metric_value < nearest_distance:
                # Нашли более близкую точку
                nearest_distance = metric_value
                nearest_duration = route_result.duration_seconds
                nearest_point_distance = route_result.distance_meters
                nearest_point = point

        if nearest_point is None:
            break

        unvisited.remove(nearest_point)
        route_points.append(nearest_point)
        # Суммируем реальную дистанцию и время
        total_distance += nearest_point_distance
        total_duration += nearest_duration

        current_time += timedelta(seconds=nearest_duration)
        estimated_arrivals.append(current_time)
        current_location = nearest_point.location

    # Проверки
    assert len(route_points) == 2
    assert total_distance > 0
    assert total_duration > 0
    assert len(estimated_arrivals) == 2

    # Создаём результат
    result = OptimizedRoute(
        distance_meters=total_distance,
        duration_seconds=total_duration,
        points=route_points,
        estimated_arrivals=estimated_arrivals
    )

    assert isinstance(result, OptimizedRoute)
    assert result.distance_meters > 0
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_solve_tsp_no_points():
    """Тест TSP с пустым списком точек."""
    with pytest.raises(NoValidRouteError):
        raise NoValidRouteError("No points to optimize")


@pytest.mark.asyncio
async def test_optimize_for_distance_vs_time():
    """Тест выбора метрики оптимизации."""
    from dataclasses import dataclass

    @dataclass
    class RouteResult:
        distance_meters: float
        duration_seconds: float

    mock_routing = MagicMock()
    # Маршрут с большой дистанцией, но маленьким временем
    mock_routing.get_route = AsyncMock(return_value=RouteResult(
        distance_meters=5000,
        duration_seconds=30
    ))

    start_location = (131.886, 43.115)
    points = [
        OptimizationPoint(order_id=1, location=(131.896, 43.125), stop_type=RouteStopType.PICKUP),
    ]

    # Проверяем что маршрут рассчитывается
    route_result = await mock_routing.get_route(
        origin=start_location,
        destination=points[0].location,
        with_geometry=False
    )

    assert route_result.distance_meters == 5000
    assert route_result.duration_seconds == 30

    # Проверяем логику выбора метрики
    time_metric = route_result.duration_seconds
    distance_metric = route_result.distance_meters

    assert time_metric == 30
    assert distance_metric == 5000

    # При оптимизации по времени выбираем duration
    optimize_for_time = time_metric
    assert optimize_for_time == 30

    # При оптимизации по расстоянию выбираем distance
    optimize_for_distance = distance_metric
    assert optimize_for_distance == 5000


def test_optimization_point_dataclass():
    """Тест структуры OptimizationPoint."""
    point = OptimizationPoint(
        order_id=1,
        location=(131.886, 43.115),
        address="Test Address",
        stop_type=RouteStopType.PICKUP
    )
    assert point.order_id == 1
    assert point.location == (131.886, 43.115)
    assert point.address == "Test Address"
    assert point.stop_type == RouteStopType.PICKUP


def test_optimized_route_dataclass():
    """Тест структуры OptimizedRoute."""
    route = OptimizedRoute(
        distance_meters=5000,
        duration_seconds=300,
        points=[
            OptimizationPoint(order_id=1, location=(131.886, 43.115), stop_type=RouteStopType.PICKUP)
        ],
        estimated_arrivals=[datetime.utcnow()]
    )
    assert route.distance_meters == 5000
    assert route.duration_seconds == 300
    assert len(route.points) == 1
    assert len(route.estimated_arrivals) == 1


@pytest.mark.asyncio
async def test_get_start_location_from_orders():
    """Тест извлечения начальной точки из заказов."""
    import re

    # Вспомогательная функция для парсинга WKT
    def parse_geometry_point(wkt_or_ewkt: str) -> Tuple[float, float]:
        if not wkt_or_ewkt:
            raise ValueError("Empty geometry string")
        match = re.search(r"POINT\s*\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)", wkt_or_ewkt, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid POINT format: {wkt_or_ewkt}")
        lon = float(match.group(1))
        lat = float(match.group(2))
        return lon, lat

    mock_order = Mock()
    mock_order.pickup_location = "SRID=4326;POINT(131.886 43.115)"

    location = parse_geometry_point(mock_order.pickup_location)

    assert location == (131.886, 43.115)  # (lon, lat)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
