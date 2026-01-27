"""
Route Optimizer Service для multi-stop маршрутов с TSP алгоритмом.

Реализует оптимизацию маршрутов с несколькими точками остановки,
используя алгоритм решения задачи коммивояжёра (TSP).
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import itertools

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.database.models import (
    Route, RoutePoint, Order, Driver,
    RouteStatus, RouteOptimizationType, RouteStopType
)
# Прямой импорт для избежания circular import через __init__.py
from src.core.logging import get_logger

logger = get_logger(__name__)


class RouteOptimizerError(Exception):
    """Базовое исключение сервиса оптимизации маршрутов."""
    pass


class OrdersNotFoundError(RouteOptimizerError):
    """Заказы не найдены."""
    pass


class DriverNotFoundError(RouteOptimizerError):
    """Водитель не найден."""
    pass


class NoValidRouteError(RouteOptimizerError):
    """Не удалось построить маршрут."""
    pass


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


class RouteOptimizerService:
    """
    Сервис для оптимизации multi-stop маршрутов.

    Использует жадный алгоритм nearest neighbour для решения TSP
    с возможностью оптимизации по времени или расстоянию.
    """

    def __init__(
        self,
        session: AsyncSession,
        routing_service = None
    ):
        """
        Инициализация сервиса.

        Args:
            session: Async сессия SQLAlchemy
            routing_service: Сервис маршрутизации (если None, создаётся новый)
        """
        self.session = session
        if routing_service is None:
            # Локальный импорт для избежания circular import
            import src.services.routing as routing_module
            routing_service = routing_module.RoutingService()
        self.routing_service = routing_service

    async def optimize_route(
        self,
        driver_id: int,
        order_ids: List[int],
        start_location: Optional[Tuple[float, float]] = None,
        optimize_for: RouteOptimizationType = RouteOptimizationType.TIME
    ) -> Route:
        """
        Оптимизировать multi-stop маршрут для водителя.

        Args:
            driver_id: ID водителя
            order_ids: Список ID заказов для включения в маршрут
            start_location: Начальная точка (lon, lat). Если None, используется последнее положение водителя
            optimize_for: Критерий оптимизации (time/distance)

        Returns:
            Созданная модель Route с точками маршрута

        Raises:
            DriverNotFoundError: Водитель не найден
            OrdersNotFoundError: Один или несколько заказов не найдены
            NoValidRouteError: Не удалось построить маршрут
            RouteOptimizerError: Другая ошибка оптимизации
        """
        logger.info(
            "route_optimization_start",
            driver_id=driver_id,
            order_count=len(order_ids),
            optimize_for=optimize_for.value
        )

        # 1. Валидация водителя
        driver = await self._get_driver(driver_id)
        if not driver:
            raise DriverNotFoundError(f"Driver with id {driver_id} not found")

        # 2. Получаем заказы
        orders = await self._get_orders(order_ids)
        if len(orders) != len(order_ids):
            found_ids = [o.id for o in orders]
            missing_ids = set(order_ids) - set(found_ids)
            raise OrdersNotFoundError(f"Orders not found: {missing_ids}")

        # 3. Определяем начальную точку
        if start_location is None:
            # Используем pickup_location первого заказа или текущую позицию водителя
            start_location = self._get_start_location_from_orders(orders)

        # 4. Подготавливаем точки для оптимизации
        optimization_points = self._prepare_optimization_points(orders)

        # 5. Запускаем TSP оптимизацию
        optimized = await self._solve_tsp(
            start_location=start_location,
            points=optimization_points,
            optimize_for=optimize_for
        )

        # 6. Создаём маршрут в БД
        route = await self._create_route(
            driver_id=driver_id,
            optimized=optimized,
            optimization_type=optimize_for
        )

        logger.info(
            "route_optimization_complete",
            route_id=route.id,
            driver_id=driver_id,
            points_count=len(optimized.points),
            total_distance_meters=optimized.distance_meters,
            total_duration_seconds=optimized.duration_seconds
        )

        return route

    async def _get_driver(self, driver_id: int) -> Optional[Driver]:
        """Получить водителя по ID."""
        result = await self.session.execute(
            select(Driver).where(Driver.id == driver_id)
        )
        return result.scalar_one_or_none()

    async def _get_orders(self, order_ids: List[int]) -> List[Order]:
        """Получить заказы по списку ID."""
        result = await self.session.execute(
            select(Order).where(Order.id.in_(order_ids))
        )
        return list(result.scalars().all())

    def _get_start_location_from_orders(self, orders: List[Order]) -> Tuple[float, float]:
        """
        Получить начальную точку из заказов.

        Использует pickup_location первого заказа в списке.
        """
        if not orders:
            raise ValueError("No orders provided")

        first_order = orders[0]
        if first_order.pickup_location:
            # Локальный импорт для избежания circular import
            import src.services.routing as routing_module
            RoutingService = routing_module.RoutingService
            return RoutingService.parse_geometry_point(first_order.pickup_location)
        else:
            # Fallback: координаты Владивостока (центр города)
            logger.warning("no_pickup_location_fallback", order_id=first_order.id)
            return (131.886, 43.115)  # (lon, lat)

    def _prepare_optimization_points(self, orders: List[Order]) -> List[OptimizationPoint]:
        """
        Подготовить точки для оптимизации из заказов.

        Для каждого заказа создаём точки pickup и dropoff.
        """
        points = []
        # Локальный импорт для избежания circular import
        import src.services.routing as routing_module
        RoutingService = routing_module.RoutingService

        for order in orders:
            # Pickup точка
            if order.pickup_location:
                pickup_coords = RoutingService.parse_geometry_point(order.pickup_location)
                points.append(OptimizationPoint(
                    order_id=order.id,
                    location=pickup_coords,
                    address=order.pickup_address,
                    stop_type=RouteStopType.PICKUP
                ))

            # Dropoff точка
            if order.dropoff_location:
                dropoff_coords = RoutingService.parse_geometry_point(order.dropoff_location)
                points.append(OptimizationPoint(
                    order_id=order.id,
                    location=dropoff_coords,
                    address=order.dropoff_address,
                    stop_type=RouteStopType.DROPOFF
                ))

        return points

    async def _solve_tsp(
        self,
        start_location: Tuple[float, float],
        points: List[OptimizationPoint],
        optimize_for: RouteOptimizationType
    ) -> OptimizedRoute:
        """
        Решить TSP используя жадный алгоритм nearest neighbour.

        Args:
            start_location: Начальная точка (lon, lat)
            points: Список точек для посещения
            optimize_for: Критерий оптимизации

        Returns:
            OptimizedRoute с оптимальным порядком точек
        """
        if not points:
            raise NoValidRouteError("No points to optimize")

        unvisited = points.copy()
        route_points: List[OptimizationPoint] = []
        total_distance = 0.0
        total_duration = 0.0
        estimated_arrivals: List[Optional[datetime]] = []
        current_time = datetime.utcnow()
        current_location = start_location

        # Локальный импорт для избежания circular import
        import src.services.routing as routing_module
        RoutingService = routing_module.RoutingService
        RoutingServiceError = routing_module.RoutingServiceError

        # Nearest neighbour алгоритм
        while unvisited:
            nearest_point = None
            nearest_distance = float('inf')
            nearest_duration = float('inf')
            nearest_point_distance = float('inf')

            # Находим ближайшую точку
            for point in unvisited:
                try:
                    route_result = await self.routing_service.get_route(
                        origin=current_location,
                        destination=point.location,
                        with_geometry=False
                    )

                    # Выбор метрики для оптимизации
                    metric_value = (
                        route_result.duration_seconds
                        if optimize_for == RouteOptimizationType.TIME
                        else route_result.distance_meters
                    )

                    if metric_value < nearest_distance:
                        # Нашли более близкую точку по выбранной метрике
                        nearest_distance = metric_value
                        nearest_duration = route_result.duration_seconds
                        # Сохраняем полную дистанцию и время для суммирования
                        nearest_point_distance = route_result.distance_meters
                        nearest_point = point

                except RoutingServiceError as e:
                    logger.warning(
                        "route_calculation_failed",
                        point_id=point.order_id,
                        error=str(e)
                    )
                    continue

            if nearest_point is None:
                logger.warning("no_reachable_points", remaining=len(unvisited))
                break

            # Добавляем точку в маршрут
            unvisited.remove(nearest_point)
            route_points.append(nearest_point)
            # Суммируем реальную дистанцию и время
            total_distance += nearest_point_distance
            total_duration += nearest_duration

            # Рассчитываем время прибытия
            current_time += timedelta(seconds=nearest_duration)
            estimated_arrivals.append(current_time)
            current_location = nearest_point.location

        if not route_points:
            raise NoValidRouteError("Could not build route - no reachable points")

        return OptimizedRoute(
            distance_meters=total_distance,
            duration_seconds=total_duration,
            points=route_points,
            estimated_arrivals=estimated_arrivals
        )

    async def _create_route(
        self,
        driver_id: int,
        optimized: OptimizedRoute,
        optimization_type: RouteOptimizationType
    ) -> Route:
        """
        Создать маршрут и точки в БД.

        Args:
            driver_id: ID водителя
            optimized: Оптимизированный маршрут
            optimization_type: Тип оптимизации

        Returns:
            Созданная модель Route
        """
        # Создаём маршрут
        route = Route(
            driver_id=driver_id,
            status=RouteStatus.PLANNED,
            optimization_type=optimization_type,
            total_distance_meters=optimized.distance_meters,
            total_duration_seconds=optimized.duration_seconds
        )

        self.session.add(route)
        await self.session.flush()  # Получаем route.id

        # Создаём точки маршрута
        route_points = []
        for sequence, point in enumerate(optimized.points, start=1):
            estimated_arrival = (
                optimized.estimated_arrivals[sequence - 1]
                if sequence <= len(optimized.estimated_arrivals)
                else None
            )

            # Создаём Point геометрию
            point_geom = from_shape(Point(point.location), srid=4326)

            route_point = RoutePoint(
                route_id=route.id,
                sequence=sequence,
                location=point_geom,
                address=point.address,
                order_id=point.order_id,
                stop_type=point.stop_type,
                estimated_arrival=estimated_arrival
            )
            route_points.append(route_point)

        self.session.add_all(route_points)
        await self.session.commit()

        # Загружаем связи
        await self.session.refresh(route)
        return route
