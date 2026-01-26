"""
Route Rebuild Service для автоматического перестроения маршрутов.

Сервис слушает события заказов и автоматически перестраивает маршруты
при изменении условий: новые заказы, отмены, изменения статусов.
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Route, RoutePoint, Order, Driver,
    RouteStatus, RouteOptimizationType, OrderStatus
)
from src.services.route_optimizer import RouteOptimizerService
from src.services.notification_service import NotificationService
from src.core.logging import get_logger

logger = get_logger(__name__)


class RebuildTrigger(str, Enum):
    """Типы триггеров для перестроения маршрута."""
    ORDER_ASSIGNED = "order_assigned"           # Заказ назначен водителю
    ORDER_CANCELLED = "order_cancelled"         # Заказ отменен
    ORDER_STATUS_CHANGED = "order_status_changed" # Статус заказа изменен
    MANUAL = "manual"                           # Ручной запрос
    TRAFFIC_UPDATE = "traffic_update"           # Обновление пробок


class RebuildResult(str, Enum):
    """Результат перестроения маршрута."""
    SUCCESS = "success"
    NO_ACTIVE_ROUTE = "no_active_route"
    NO_ORDERS_TO_OPTIMIZE = "no_orders_to_optimize"
    OPTIMIZATION_FAILED = "optimization_failed"
    DRIVER_NOT_FOUND = "driver_not_found"


@dataclass
class RebuildRequest:
    """Запрос на перестроение маршрута."""
    driver_id: int
    trigger: RebuildTrigger
    trigger_order_id: Optional[int] = None
    reason: Optional[str] = None


@dataclass
class RebuildResponse:
    """Результат перестроения маршрута."""
    result: RebuildResult
    route_id: Optional[int] = None
    total_distance_meters: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    points_count: int = 0
    message: str = ""
    rebuild_time_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "result": self.result.value,
            "route_id": self.route_id,
            "total_distance_meters": self.total_distance_meters,
            "total_duration_seconds": self.total_duration_seconds,
            "points_count": self.points_count,
            "message": self.message,
            "rebuild_time_seconds": self.rebuild_time_seconds
        }


class RouteRebuildService:
    """
    Сервис для автоматического перестроения маршрутов в реальном времени.

    Реагирует на события заказов и перестраивает маршруты водителей
    для оптимизации логистики.
    """

    def __init__(
        self,
        session: AsyncSession,
        optimizer_service: RouteOptimizerService,
        notification_service: Optional[NotificationService] = None
    ):
        """
        Инициализация сервиса.

        Args:
            session: Async сессия SQLAlchemy
            optimizer_service: Сервис оптимизации маршрутов
            notification_service: Опциональный сервис уведомлений
        """
        self.session = session
        self.optimizer_service = optimizer_service
        self.notification_service = notification_service

    async def on_order_assigned(self, order_id: int, driver_id: int) -> RebuildResponse:
        """
        Обработать назначение заказа водителю.

        Перестраивает маршрут водителя, добавляя новый заказ.
        """
        logger.info(
            "order_assigned_trigger",
            order_id=order_id,
            driver_id=driver_id,
            trigger=RebuildTrigger.ORDER_ASSIGNED.value
        )

        request = RebuildRequest(
            driver_id=driver_id,
            trigger=RebuildTrigger.ORDER_ASSIGNED,
            trigger_order_id=order_id,
            reason=f"Назначен новый заказ #{order_id}"
        )

        return await self.rebuild_route(request)

    async def on_order_cancelled(self, order: Order) -> RebuildResponse:
        """
        Обработать отмену заказа.

        Перестраивает маршрут водителя, удаляя отмененный заказ.
        """
        driver_id = order.driver_id
        if not driver_id:
            logger.debug("order_cancelled_no_driver", order_id=order.id)
            return RebuildResponse(
                result=RebuildResult.NO_ACTIVE_ROUTE,
                message="Заказ не был назначен водителю"
            )

        logger.info(
            "order_cancelled_trigger",
            order_id=order.id,
            driver_id=driver_id,
            trigger=RebuildTrigger.ORDER_CANCELLED.value
        )

        request = RebuildRequest(
            driver_id=driver_id,
            trigger=RebuildTrigger.ORDER_CANCELLED,
            trigger_order_id=order.id,
            reason=f"Заказ #{order.id} был отменен"
        )

        return await self.rebuild_route(request)

    async def on_order_status_changed(self, order: Order) -> RebuildResponse:
        """
        Обработать изменение статуса заказа.

        Перестраивает маршрут при изменении статуса, если это необходимо.
        Например, если водитель завершил одну точку, можно оптимизировать оставшиеся.
        """
        driver_id = order.driver_id
        if not driver_id:
            return RebuildResponse(
                result=RebuildResult.NO_ACTIVE_ROUTE,
                message="Заказ не назначен водителю"
            )

        # Перестраиваем только при определенных статусах
        rebuild_statuses = [
            OrderStatus.COMPLETED,
            OrderStatus.IN_PROGRESS,
            OrderStatus.EN_ROUTE_PICKUP
        ]

        if order.status not in rebuild_statuses:
            logger.debug(
                "order_status_changed_no_rebuild",
                order_id=order.id,
                status=order.status.value
            )
            return RebuildResponse(
                result=RebuildResult.SUCCESS,
                message="Перестроение не требуется для этого статуса"
            )

        logger.info(
            "order_status_changed_trigger",
            order_id=order.id,
            driver_id=driver_id,
            status=order.status.value,
            trigger=RebuildTrigger.ORDER_STATUS_CHANGED.value
        )

        request = RebuildRequest(
            driver_id=driver_id,
            trigger=RebuildTrigger.ORDER_STATUS_CHANGED,
            trigger_order_id=order.id,
            reason=f"Изменен статус заказа #{order.id} на {order.status.value}"
        )

        return await self.rebuild_route(request)

    async def rebuild_route(self, request: RebuildRequest) -> RebuildResponse:
        """
        Перестроить маршрут водителя.

        Алгоритм:
        1. Найти активный маршрут водителя
        2. Получить все активные заказы водителя
        3. Удалить старые RoutePoints
        4. Вызвать RouteOptimizerService для оптимизации
        5. Создать новые RoutePoints
        6. Обновить метрики маршрута
        7. Отправить уведомление водителю
        """
        start_time = datetime.utcnow()

        try:
            # 1. Проверить существование водителя
            driver = await self._get_driver(request.driver_id)
            if not driver:
                return RebuildResponse(
                    result=RebuildResult.DRIVER_NOT_FOUND,
                    message=f"Водитель {request.driver_id} не найден"
                )

            # 2. Найти или создать активный маршрут
            route = await self._get_or_create_active_route(request.driver_id)

            # 3. Получить все активные заказы водителя
            active_orders = await self._get_active_orders(request.driver_id)

            if not active_orders:
                logger.info(
                    "no_active_orders_for_rebuild",
                    driver_id=request.driver_id
                )
                # Если нет заказов, отметить маршрут как завершенный
                if route and route.status == RouteStatus.IN_PROGRESS:
                    route.status = RouteStatus.COMPLETED
                    route.completed_at = datetime.utcnow()
                    await self.session.commit()

                return RebuildResponse(
                    result=RebuildResult.NO_ORDERS_TO_OPTIMIZE,
                    route_id=route.id if route else None,
                    message="Нет активных заказов для оптимизации"
                )

            logger.info(
                "rebuilding_route",
                driver_id=request.driver_id,
                route_id=route.id,
                orders_count=len(active_orders),
                trigger=request.trigger.value
            )

            # 4. Удалить старые точки маршрута
            await self._clear_route_points(route.id)

            # 5. Оптимизировать маршрут
            optimized_route = await self._optimize_route(
                route=route,
                orders=active_orders
            )

            if not optimized_route:
                return RebuildResponse(
                    result=RebuildResult.OPTIMIZATION_FAILED,
                    route_id=route.id,
                    message="Не удалось оптимизировать маршрут"
                )

            # 6. Создать новые точки маршрута
            await self._create_route_points(
                route_id=route.id,
                optimized_points=optimized_route.points,
                estimated_arrivals=optimized_route.estimated_arrivals
            )

            # 7. Обновить метрики маршрута
            route.total_distance_meters = optimized_route.distance_meters
            route.total_duration_seconds = optimized_route.duration_seconds
            route.optimization_type = RouteOptimizationType.TIME

            # Если маршрут в статусе PLANNED и есть заказы в работе, перевести в IN_PROGRESS
            if route.status == RouteStatus.PLANNED:
                any_in_progress = any(
                    o.status in [OrderStatus.IN_PROGRESS, OrderStatus.EN_ROUTE_PICKUP]
                    for o in active_orders
                )
                if any_in_progress:
                    route.status = RouteStatus.IN_PROGRESS
                    route.started_at = datetime.utcnow()

            await self.session.commit()

            # 8. Отправить уведомление водителю
            await self._notify_driver_updated(
                driver_id=request.driver_id,
                route=route,
                points_count=len(optimized_route.points)
            )

            rebuild_time = (datetime.utcnow() - start_time).total_seconds()

            # Мониторинг performance: предупреждение если > 5 секунд
            if rebuild_time > 5.0:
                logger.warning(
                    "route_rebuild_slow",
                    driver_id=request.driver_id,
                    route_id=route.id,
                    rebuild_time_seconds=rebuild_time,
                    threshold_seconds=5.0,
                    message=f"Перестроение маршрута заняло {rebuild_time:.2f}с (порог: 5с)"
                )

            logger.info(
                "route_rebuild_success",
                driver_id=request.driver_id,
                route_id=route.id,
                distance_meters=optimized_route.distance_meters,
                duration_seconds=optimized_route.duration_seconds,
                points_count=len(optimized_route.points),
                rebuild_time_seconds=rebuild_time,
                trigger=request.trigger.value
            )

            return RebuildResponse(
                result=RebuildResult.SUCCESS,
                route_id=route.id,
                total_distance_meters=optimized_route.distance_meters,
                total_duration_seconds=optimized_route.duration_seconds,
                points_count=len(optimized_route.points),
                message=f"Маршрут успешно перестроен ({len(optimized_route.points)} точек)",
                rebuild_time_seconds=rebuild_time
            )

        except Exception as e:
            logger.error(
                "route_rebuild_error",
                driver_id=request.driver_id,
                trigger=request.trigger.value,
                error=str(e)
            )
            await self.session.rollback()

            rebuild_time = (datetime.utcnow() - start_time).total_seconds()

            return RebuildResponse(
                result=RebuildResult.OPTIMIZATION_FAILED,
                message=f"Ошибка при перестроении: {str(e)}",
                rebuild_time_seconds=rebuild_time
            )

    async def _get_driver(self, driver_id: int) -> Optional[Driver]:
        """Получить водителя по ID."""
        result = await self.session.execute(
            select(Driver).where(Driver.id == driver_id)
        )
        return result.scalar_one_or_none()

    async def _get_or_create_active_route(self, driver_id: int) -> Route:
        """
        Получить активный маршрут водителя или создать новый.

        Активный маршрут - это маршрут со статусом PLANNED или IN_PROGRESS.
        Если таких несколько, берется последний созданный.
        """
        # Ищем активный маршрут
        result = await self.session.execute(
            select(Route).where(
                and_(
                    Route.driver_id == driver_id,
                    Route.status.in_([RouteStatus.PLANNED, RouteStatus.IN_PROGRESS])
                )
            ).order_by(Route.created_at.desc())
        )
        route = result.scalar_one_or_none()

        if not route:
            # Создаем новый маршрут
            route = Route(
                driver_id=driver_id,
                status=RouteStatus.PLANNED,
                optimization_type=RouteOptimizationType.TIME
            )
            self.session.add(route)
            await self.session.flush()

            logger.info("created_new_route", driver_id=driver_id, route_id=route.id)

        return route

    async def _get_active_orders(self, driver_id: int) -> List[Order]:
        """
        Получить активные заказы водителя.

        Активные заказы - это заказы со статусом от ASSIGNED до IN_PROGRESS.
        """
        active_statuses = [
            OrderStatus.ASSIGNED,
            OrderStatus.EN_ROUTE_PICKUP,
            OrderStatus.DRIVER_ARRIVED,
            OrderStatus.IN_PROGRESS
        ]

        result = await self.session.execute(
            select(Order).where(
                and_(
                    Order.driver_id == driver_id,
                    Order.status.in_(active_statuses)
                )
            ).order_by(Order.time_range.lower.asc().nullslast())  # Сортировка по времени
        )
        return list(result.scalars().all())

    async def _clear_route_points(self, route_id: int) -> None:
        """Удалить все точки маршрута."""
        await self.session.execute(
            select(RoutePoint).where(RoutePoint.route_id == route_id)
        )
        # Удаляем через execute для скорости
        from sqlalchemy import delete
        await self.session.execute(
            delete(RoutePoint).where(RoutePoint.route_id == route_id)
        )

    async def _optimize_route(self, route: Route, orders: List[Order]):
        """
        Оптимизировать маршрут с помощью RouteOptimizerService.

        Args:
            route: Маршрут для оптимизации
            orders: Список заказов для включения в маршрут

        Returns:
            OptimizedRoute или None в случае ошибки
        """
        try:
            order_ids = [o.id for o in orders]

            # Определяем стартовую локацию
            # Если есть driver, можно использовать его последнюю позицию
            # Пока используем локацию первого заказа
            start_location = None
            if orders and orders[0].pickup_location:
                start_location = (
                    orders[0].pickup_location.x,
                    orders[0].pickup_location.y
                )

            # Вызываем оптимизатор
            optimized = await self.optimizer_service.optimize_route(
                driver_id=route.driver_id,
                order_ids=order_ids,
                start_location=start_location,
                optimize_for=RouteOptimizationType.TIME
            )

            return optimized

        except Exception as e:
            logger.error(
                "optimization_error",
                route_id=route.id,
                driver_id=route.driver_id,
                error=str(e)
            )
            return None

    async def _create_route_points(
        self,
        route_id: int,
        optimized_points: list,
        estimated_arrivals: list
    ) -> None:
        """
        Создать точки маршрута на основе оптимизированного маршрута.

        Args:
            route_id: ID маршрута
            optimized_points: Список OptimizationPoint из оптимизатора
            estimated_arrivals: Список предполагаемых времен прибытия
        """
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point

        for seq, point in enumerate(optimized_points, start=1):
            route_point = RoutePoint(
                route_id=route_id,
                sequence=seq,
                location=from_shape(Point(point.location[0], point.location[1]), srid=4326),
                address=point.address,
                order_id=point.order_id,
                stop_type=point.stop_type,
                estimated_arrival=estimated_arrivals[seq - 1] if seq - 1 < len(estimated_arrivals) else None,
                is_completed=False
            )
            self.session.add(route_point)

    async def _notify_driver_updated(
        self,
        driver_id: int,
        route: Route,
        points_count: int
    ) -> None:
        """
        Уведомить водителя об изменении маршрута.

        Args:
            driver_id: ID водителя
            route: Обновленный маршрут
            points_count: Количество точек в маршруте
        """
        if not self.notification_service:
            return

        try:
            distance_km = route.total_distance_meters / 1000 if route.total_distance_meters else 0
            duration_min = route.total_duration_seconds / 60 if route.total_duration_seconds else 0

            text = (
                f"<b>🔄 Маршрут обновлен</b>\n\n"
                f"Маршрут #{route.id}\n"
                f"📍 Точек: {points_count}\n"
                f"📏 Дистанция: {distance_km:.1f} км\n"
                f"⏱️ Время: {duration_min:.0f} мин\n\n"
                f"Нажмите /routes чтобы посмотреть детали"
            )

            await self.notification_service.send_message(driver_id, text)

        except Exception as e:
            logger.error(
                "failed_to_notify_driver",
                driver_id=driver_id,
                route_id=route.id,
                error=str(e)
            )
