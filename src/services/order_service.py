from typing import List, Optional
from sqlalchemy import text
from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, OrderStatus
from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest
from src.services.order_workflow import OrderWorkflowService
from src.core.logging import get_logger

logger = get_logger(__name__)

class OrderService:
    """
    Сервис для работы с заказами. 
    Управляет жизненным циклом заказа и временными ограничениями.
    """
    
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow
        self.workflow = OrderWorkflowService(uow)

    async def create_order(self, data: OrderCreate) -> OrderResponse:
        """
        Создает заказ. 
        """
        async with self.uow:
            order = Order(
                status=OrderStatus.PENDING,
                priority=data.priority,
                pickup_location=f"SRID=4326;POINT({data.pickup_lon} {data.pickup_lat})",
                dropoff_location=f"SRID=4326;POINT({data.dropoff_lon} {data.dropoff_lat})",
                comment=data.comment
            )
            self.uow.orders.add(order)
            await self.uow.commit() # Получаем ID

            # Устанавливаем time_range
            await self.uow.session.execute(
                text("""
                    UPDATE orders 
                    SET time_range = tstzrange(:start, :end, '[)')
                    WHERE id = :id
                """),
                {"start": data.time_start, "end": data.time_end, "id": order.id}
            )
            await self.uow.commit()
            
            # Если водитель указан, используем workflow для назначения (и смены статуса на ASSIGNED)
            if data.driver_id:
                async with self.uow: # Re-open or use current if possible? Better to use workflow's transaction logic
                     await self.workflow.assign_driver(order.id, data.driver_id)

            # Возвращаем обновленный объект
            await self.uow.session.refresh(order)
            return self._to_response(order)

    async def assign_driver(self, order_id: int, driver_id: int) -> OrderResponse:
        await self.workflow.assign_driver(order_id, driver_id)
        return await self.get_order(order_id)

    async def mark_arrived(self, order_id: int) -> OrderResponse:
        await self.workflow.mark_arrived(order_id)
        return await self.get_order(order_id)

    async def start_trip(self, order_id: int) -> OrderResponse:
        await self.workflow.start_trip(order_id)
        return await self.get_order(order_id)

    async def complete_order(self, order_id: int) -> OrderResponse:
        await self.workflow.complete_order(order_id)
        return await self.get_order(order_id)

    async def cancel_order(self, order_id: int, reason: Optional[str] = None) -> OrderResponse:
        await self.workflow.cancel_order(order_id, reason)
        return await self.get_order(order_id)

    async def move_order(self, order_id: int, data: OrderMoveRequest) -> Optional[OrderResponse]:
        """Обновляет время заказа (Drag-and-Drop)."""
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
            
            await self.uow.session.refresh(order)
            return self._to_response(order)

    async def get_order(self, order_id: int) -> Optional[OrderResponse]:
        async with self.uow:
            order = await self.uow.orders.get(order_id)
            return self._to_response(order) if order else None

    def _to_response(self, order: Order) -> OrderResponse:
        """Вспомогательный метод для маппинга модели в схему."""
        return OrderResponse(
            id=order.id,
            driver_id=order.driver_id,
            status=order.status,
            priority=order.priority,
            comment=order.comment,
            created_at=order.created_at,
            updated_at=order.updated_at,
            arrived_at=order.arrived_at,
            started_at=order.started_at,
            end_time=order.end_time,
            cancelled_at=order.cancelled_at,
            cancellation_reason=order.cancellation_reason
        )
