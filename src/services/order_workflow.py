from datetime import datetime
from typing import Optional
from statemachine import StateMachine, State
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Order, OrderStatus, DriverStatus
from src.database.uow import AbstractUnitOfWork
from src.core.logging import get_logger

logger = get_logger(__name__)

class OrderStateMachine(StateMachine):
    """
    Машина состояний для заказа.
    Управляет переходами и обновлением полей в модели Order.
    """
    # === STATES ===
    pending = State("Pending", value=OrderStatus.PENDING, initial=True)
    assigned = State("Assigned", value=OrderStatus.ASSIGNED)
    driver_arrived = State("Driver Arrived", value=OrderStatus.DRIVER_ARRIVED)
    in_progress = State("In Progress", value=OrderStatus.IN_PROGRESS)
    completed = State("Completed", value=OrderStatus.COMPLETED, final=True)
    cancelled = State("Cancelled", value=OrderStatus.CANCELLED, final=True)

    # === TRANSITIONS ===
    assign = pending.to(assigned)
    unassign = assigned.to(pending)
    arrive = assigned.to(driver_arrived)
    start_trip = driver_arrived.to(in_progress)
    complete = in_progress.to(completed)
    
    cancel = (
        pending.to(cancelled) |
        assigned.to(cancelled) |
        driver_arrived.to(cancelled) |
        in_progress.to(cancelled)
    )

    def __init__(self, order: Order):
        self.order = order
        # Инициализируем SM текущим статусом заказа. 
        # В python-statemachine 2.x это может вызвать on_enter_{state}
        super().__init__(start_value=order.status)

    # === CALLBACKS ===

    def before_assign(self, driver_id: int):
        """Вызывается только при переходе 'assign'"""
        self.order.driver_id = driver_id
        logger.info("order_assign_transition", order_id=self.order.id, driver_id=driver_id)

    def on_enter_assigned(self):
        self.order.status = OrderStatus.ASSIGNED
        logger.info("order_entered_assigned", order_id=self.order.id)

    def on_enter_pending(self):
        self.order.status = OrderStatus.PENDING
        self.order.driver_id = None
        logger.info("order_unassigned", order_id=self.order.id)

    def on_enter_driver_arrived(self):
        self.order.status = OrderStatus.DRIVER_ARRIVED
        self.order.arrived_at = datetime.utcnow()
        logger.info("driver_arrived", order_id=self.order.id)

    def on_enter_in_progress(self):
        self.order.status = OrderStatus.IN_PROGRESS
        self.order.started_at = datetime.utcnow()
        logger.info("order_started", order_id=self.order.id)

    def on_enter_completed(self):
        self.order.status = OrderStatus.COMPLETED
        self.order.end_time = datetime.utcnow()
        if self.order.driver:
            self.order.driver.status = DriverStatus.AVAILABLE
        logger.info("order_completed", order_id=self.order.id)

    def on_enter_cancelled(self, reason: Optional[str] = None):
        self.order.status = OrderStatus.CANCELLED
        self.order.cancelled_at = datetime.utcnow()
        self.order.cancellation_reason = reason
        if self.order.driver:
            self.order.driver.status = DriverStatus.AVAILABLE
        logger.info("order_cancelled", order_id=self.order.id, reason=reason)


class OrderWorkflowService:
    """
    Сервис для выполнения бизнес-операций над заказами через State Machine.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def _get_order_and_sm(self, order_id: int) -> tuple[Order, OrderStateMachine]:
        order = await self.uow.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order, OrderStateMachine(order)

    async def assign_driver(self, order_id: int, driver_id: int):
        async with self.uow:
            order, sm = await self._get_order_and_sm(order_id)
            driver = await self.uow.drivers.get(driver_id)
            if not driver:
                raise ValueError(f"Driver {driver_id} not found")
            
            sm.assign(driver_id=driver_id)
            driver.status = DriverStatus.BUSY
            await self.uow.commit()

    async def mark_arrived(self, order_id: int):
        async with self.uow:
            order, sm = await self._get_order_and_sm(order_id)
            sm.arrive()
            await self.uow.commit()

    async def start_trip(self, order_id: int):
        async with self.uow:
            order, sm = await self._get_order_and_sm(order_id)
            sm.start_trip()
            await self.uow.commit()

    async def complete_order(self, order_id: int):
        async with self.uow:
            order, sm = await self._get_order_and_sm(order_id)
            sm.complete()
            await self.uow.commit()

    async def cancel_order(self, order_id: int, reason: Optional[str] = None):
        async with self.uow:
            order, sm = await self._get_order_and_sm(order_id)
            sm.cancel(reason=reason)
            await self.uow.commit()
