from typing import List, Optional
from sqlalchemy import text
from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, OrderStatus
from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest
from src.core.logging import get_logger

logger = get_logger(__name__)

class OrderService:
    """
    Сервис для работы с заказами. 
    Управляет жизненным циклом заказа и временными ограничениями.
    """
    
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def create_order(self, data: OrderCreate) -> OrderResponse:
        """
        Создает заказ. 
        Временной интервал записывается в tstzrange через raw SQL, 
        так как SQLAlchemy 2.0 не имеет полной нативной поддержки для формирования tstzrange в коде.
        """
        async with self.uow:
            order = Order(
                driver_id=data.driver_id,
                status=OrderStatus.PENDING if not data.driver_id else OrderStatus.ASSIGNED,
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
            
            # Возвращаем обновленный объект
            await self.uow.session.refresh(order)
            return self._to_response(order)

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
        # TODO: В будущем можно добавить кастомный тип в SQLAlchemy для автоматической обработки tstzrange
        return OrderResponse(
            id=order.id,
            driver_id=order.driver_id,
            status=order.status,
            priority=order.priority,
            comment=order.comment,
            created_at=order.created_at,
            updated_at=order.updated_at,
            # Временные поля будут заполнены через refresh после UPDATE или можно вытащить отдельно
            # Для упрощения сейчас они могут быть None если не делать доп. селект
        )
