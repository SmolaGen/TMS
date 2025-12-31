"""
Order Service

Сервис для работы с заказами. 
Управляет жизненным циклом заказа, интегрирует маршрутизацию и машину состояний.
"""

from datetime import timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.core.logging import get_logger

# PostgreSQL error code for exclusion constraint violation
EXCLUSION_VIOLATION = "23P01"

from src.database.models import Order, OrderStatus
from src.database.uow import AbstractUnitOfWork
from src.schemas.order import OrderCreate, OrderMoveRequest, OrderResponse
from src.services.order_workflow import OrderWorkflowService
from src.services.routing import (
    RoutingService,
    RoutingServiceError,
    RouteNotFoundError,
    OSRMUnavailableError,
)

logger = get_logger(__name__)


class OrderService:
    """
    Сервис для работы с заказами.
    Управляет жизненным циклом заказа и временными ограничениями.
    
    Интегрирует:
    - RoutingService для расчёта маршрутов и цен
    - OrderWorkflowService (State Machine) для управления статусами
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        routing_service: Optional[RoutingService] = None
    ):
        """
        Args:
            uow: Unit of Work для транзакций
            routing_service: Сервис маршрутизации (инжектируется)
        """
        self.uow = uow
        self.routing_service = routing_service or RoutingService()
        self.workflow = OrderWorkflowService(uow)

    async def create_order(self, data: OrderCreate) -> OrderResponse:
        """
        Создает заказ с автоматическим расчётом маршрута и цены.
        
        Процесс:
        1. Получаем маршрут через OSRM (дистанция, время)
        2. Рассчитываем цену через RoutingService
        3. Формируем time_range: [time_start, time_start + duration)
        4. Сохраняем заказ со всеми данными
        5. При наличии driver_id — назначаем водителя через workflow
        
        Args:
            data: Данные для создания заказа
            
        Returns:
            Созданный заказ
            
        Raises:
            HTTPException(400): Маршрут не найден
            HTTPException(503): OSRM недоступен
            HTTPException(409): Конфликт расписания водителя
        """
        # === 1. Получаем маршрут ===
        pickup = (data.pickup_lon, data.pickup_lat)
        dropoff = (data.dropoff_lon, data.dropoff_lat)
        
        try:
            route_result = await self.routing_service.get_route(pickup, dropoff)
        except RouteNotFoundError as e:
            logger.warning("route_not_found", pickup=pickup, dropoff=dropoff, error=str(e))
            raise HTTPException(
                status_code=400,
                detail=f"Маршрут между точками не найден: {e}"
            )
        except OSRMUnavailableError as e:
            logger.error("osrm_unavailable", error=str(e))
            raise HTTPException(
                status_code=503,
                detail="Сервис маршрутизации временно недоступен"
            )
        except RoutingServiceError as e:
            logger.error("routing_error", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка расчёта маршрута: {e}"
            )
        
        # === 2. Рассчитываем цену ===
        price_result = self.routing_service.calculate_price(route_result.distance_meters)
        
        # === 3. Формируем time_range ===
        # Если пользователь указал time_start и time_end — используем их
        # Иначе можно было бы рассчитать: time_end = time_start + duration
        # Но в текущей схеме time_start и time_end обязательны в OrderCreate
        time_start = data.time_start
        time_end = data.time_end
        
        # Альтернатива: автоматический расчёт end_time на основе duration
        # time_end = time_start + timedelta(seconds=route_result.duration_seconds)
        
        # === 4. Сохраняем заказ ===
        try:
            async with self.uow:
                order = Order(
                    status=OrderStatus.PENDING,
                    priority=data.priority,
                    pickup_location=f"SRID=4326;POINT({data.pickup_lon} {data.pickup_lat})",
                    dropoff_location=f"SRID=4326;POINT({data.dropoff_lon} {data.dropoff_lat})",
                    distance_meters=route_result.distance_meters,
                    duration_seconds=route_result.duration_seconds,
                    price=price_result.total_price,
                    comment=data.comment
                )
                self.uow.orders.add(order)
                await self.uow.commit()  # Получаем ID

                # Устанавливаем time_range через raw SQL (tstzrange)
                await self.uow.session.execute(
                    text("""
                        UPDATE orders 
                        SET time_range = tstzrange(:start, :end, '[)')
                        WHERE id = :id
                    """),
                    {"start": time_start, "end": time_end, "id": order.id}
                )
                await self.uow.commit()

                logger.info(
                    "order_created",
                    order_id=order.id,
                    distance_km=float(price_result.distance_km),
                    price=float(price_result.total_price),
                    duration_min=round(route_result.duration_seconds / 60, 1)
                )

        except IntegrityError as e:
            await self.uow.rollback()
            # Проверяем код ошибки PostgreSQL для exclusion violation
            if hasattr(e.orig, 'pgcode') and e.orig.pgcode == EXCLUSION_VIOLATION:
                logger.warning("driver_schedule_conflict", driver_id=data.driver_id)
                raise HTTPException(
                    status_code=409,
                    detail="Конфликт расписания водителя: указанный временной интервал занят"
                )
            raise

        # === 5. Назначаем водителя через workflow ===
        if data.driver_id:
            try:
                await self.workflow.assign_driver(order.id, data.driver_id)
            except IntegrityError as e:
                # Conflict при назначении водителя
                if hasattr(e.orig, 'pgcode') and e.orig.pgcode == EXCLUSION_VIOLATION:
                    raise HTTPException(
                        status_code=409,
                        detail="Конфликт расписания водителя: указанный временной интервал занят"
                    )
                raise

        # Возвращаем обновленный объект
        return await self.get_order(order.id)

    async def assign_driver(self, order_id: int, driver_id: int) -> OrderResponse:
        """
        Назначает водителя на заказ через State Machine.
        
        Raises:
            HTTPException(409): Конфликт расписания водителя
        """
        try:
            await self.workflow.assign_driver(order_id, driver_id)
        except IntegrityError as e:
            if hasattr(e.orig, 'pgcode') and e.orig.pgcode == EXCLUSION_VIOLATION:
                raise HTTPException(
                    status_code=409,
                    detail="Конфликт расписания водителя: указанный временной интервал занят"
                )
            raise
        return await self.get_order(order_id)

    async def mark_arrived(self, order_id: int) -> OrderResponse:
        """Отмечает прибытие водителя через State Machine."""
        await self.workflow.mark_arrived(order_id)
        return await self.get_order(order_id)

    async def start_trip(self, order_id: int) -> OrderResponse:
        """Начинает поездку через State Machine."""
        await self.workflow.start_trip(order_id)
        return await self.get_order(order_id)

    async def complete_order(self, order_id: int) -> OrderResponse:
        """Завершает заказ через State Machine."""
        await self.workflow.complete_order(order_id)
        return await self.get_order(order_id)

    async def cancel_order(self, order_id: int, reason: Optional[str] = None) -> OrderResponse:
        """Отменяет заказ через State Machine."""
        await self.workflow.cancel_order(order_id, reason)
        return await self.get_order(order_id)

    async def move_order(self, order_id: int, data: OrderMoveRequest) -> Optional[OrderResponse]:
        """
        Обновляет время заказа (Drag-and-Drop на Gantt-диаграмме).
        
        Raises:
            HTTPException(409): Конфликт расписания водителя
        """
        try:
            async with self.uow:
                order = await self.uow.orders.get(order_id)
                if not order:
                    return None

                await self.uow.session.execute(
                    text("""
                        UPDATE orders 
                        SET time_range = tstzrange(:start, :end, '[)')
                        WHERE id = :id
                    """),
                    {"start": data.new_time_start, "end": data.new_time_end, "id": order_id}
                )
                await self.uow.commit()

                logger.info(
                    "order_moved",
                    order_id=order_id,
                    new_start=data.new_time_start.isoformat(),
                    new_end=data.new_time_end.isoformat()
                )
                
                await self.uow.session.refresh(order)
                return self._to_response(order)

        except IntegrityError as e:
            await self.uow.rollback()
            if hasattr(e.orig, 'pgcode') and e.orig.pgcode == EXCLUSION_VIOLATION:
                raise HTTPException(
                    status_code=409,
                    detail="Конфликт расписания водителя: указанный временной интервал занят"
                )
            raise

    async def get_order(self, order_id: int) -> Optional[OrderResponse]:
        """Получает заказ по ID."""
        async with self.uow:
            order = await self.uow.orders.get(order_id)
            return self._to_response(order) if order else None

    async def get_orders_by_status(self, status: OrderStatus) -> List[OrderResponse]:
        """Получает заказы по статусу."""
        async with self.uow:
            orders = await self.uow.orders.get_by_status(status)
            return [self._to_response(order) for order in orders]

    async def get_driver_orders(self, driver_id: int) -> List[OrderResponse]:
        """Получает заказы водителя."""
        async with self.uow:
            orders = await self.uow.orders.get_by_driver(driver_id)
            return [self._to_response(order) for order in orders]

    def _to_response(self, order: Order) -> OrderResponse:
        """
        Маппинг модели Order в схему OrderResponse.
        
        Извлекает time_start и time_end из tstzrange.
        """
        # Извлечение границ из tstzrange
        time_start = None
        time_end = None
        
        if order.time_range is not None:
            # psycopg2 Range object
            if hasattr(order.time_range, 'lower'):
                time_start = order.time_range.lower
                time_end = order.time_range.upper

        return OrderResponse(
            id=order.id,
            driver_id=order.driver_id,
            status=order.status,
            priority=order.priority,
            time_start=time_start,
            time_end=time_end,
            distance_meters=order.distance_meters,
            duration_seconds=order.duration_seconds,
            price=float(order.price) if order.price else None,
            comment=order.comment,
            created_at=order.created_at,
            updated_at=order.updated_at,
            arrived_at=order.arrived_at,
            started_at=order.started_at,
            end_time=order.end_time,
            cancelled_at=order.cancelled_at,
            cancellation_reason=order.cancellation_reason
        )
