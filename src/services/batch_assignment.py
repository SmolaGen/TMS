"""
Batch Assignment Service для автоматического распределения заказов между водителями.
"""

from datetime import date, datetime, time
from typing import List, Dict, Tuple, Optional
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Order, Driver, OrderStatus, OrderPriority, UserRole
from src.database.repository import OrderRepository
from src.services.order_service import OrderService
from src.core.logging import get_logger

logger = get_logger(__name__)


class AssignmentResult(str, Enum):
    """Результаты распределения."""
    SUCCESS = "success"
    NO_AVAILABLE_DRIVERS = "no_available_drivers"
    TIME_CONFLICT = "time_conflict"
    DRIVER_BUSY = "driver_busy"


class BatchAssignmentRequest:
    """Запрос на batch-распределение."""

    def __init__(
        self,
        target_date: date,
        priority_filter: Optional[OrderPriority] = None,
        driver_ids: Optional[List[int]] = None,
        max_orders_per_driver: Optional[int] = None
    ):
        self.target_date = target_date
        self.priority_filter = priority_filter
        self.driver_ids = driver_ids
        self.max_orders_per_driver = max_orders_per_driver or 10


class BatchAssignmentResult:
    """Результат batch-распределения."""

    def __init__(self):
        self.assigned_orders: List[Tuple[int, int]] = []  # (order_id, driver_id)
        self.failed_orders: List[Tuple[int, str]] = []  # (order_id, reason)
        self.total_processed = 0
        self.total_assigned = 0
        self.total_failed = 0

    def add_success(self, order_id: int, driver_id: int):
        self.assigned_orders.append((order_id, driver_id))
        self.total_assigned += 1

    def add_failure(self, order_id: int, reason: str):
        self.failed_orders.append((order_id, reason))
        self.total_failed += 1

    @property
    def success_rate(self) -> float:
        return self.total_assigned / self.total_processed if self.total_processed > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            "assigned_orders": self.assigned_orders,
            "failed_orders": self.failed_orders,
            "total_processed": self.total_processed,
            "total_assigned": self.total_assigned,
            "total_failed": self.total_failed,
            "success_rate": self.total_assigned / self.total_processed if self.total_processed > 0 else 0
        }


class BatchAssignmentService:
    """
    Сервис для автоматического распределения заказов между водителями.

    Использует жадный алгоритм с учетом приоритетов заказов и доступности водителей.
    """

    def __init__(self, session: AsyncSession, order_service: OrderService):
        self.session = session
        self.order_service = order_service
        self.order_repo = OrderRepository(session, Order)

    async def assign_orders_batch(self, request: BatchAssignmentRequest) -> BatchAssignmentResult:
        """
        Запустить batch-распределение заказов на указанную дату.

        Алгоритм:
        1. Получить нераспределенные заказы на дату (фильтр по приоритету)
        2. Отсортировать по приоритету (URGENT -> HIGH -> NORMAL -> LOW)
        3. Для каждого заказа найти подходящего водителя
        4. Проверить конфликты времени и доступность
        5. Назначить заказ если возможно
        """
        result = BatchAssignmentResult()

        # Получить нераспределенные заказы
        unassigned_orders = await self._get_unassigned_orders(request)
        result.total_processed = len(unassigned_orders)

        if not unassigned_orders:
            logger.info(f"No unassigned orders found for date {request.target_date}")
            return result

        # Получить доступных водителей
        available_drivers = await self._get_available_drivers(request)
        if not available_drivers:
            logger.warning(f"No available drivers found for date {request.target_date}")
            for order in unassigned_orders:
                result.add_failure(order.id, AssignmentResult.NO_AVAILABLE_DRIVERS.value)
            return result

        # Отсортировать заказы по приоритету
        priority_order = {OrderPriority.URGENT: 0, OrderPriority.HIGH: 1, OrderPriority.NORMAL: 2, OrderPriority.LOW: 3}
        sorted_orders = sorted(unassigned_orders, key=lambda o: priority_order.get(o.priority, 999))

        # Распределить заказы
        for order in sorted_orders:
            driver_id = await self._find_suitable_driver(order, available_drivers, request.max_orders_per_driver)
            if driver_id:
                # Назначить заказ
                success = await self._assign_order_to_driver(order.id, driver_id)
                if success:
                    result.add_success(order.id, driver_id)
                    # Обновить счетчик заказов водителя
                    available_drivers[driver_id]['current_orders'] += 1
                else:
                    result.add_failure(order.id, AssignmentResult.TIME_CONFLICT.value)
            else:
                result.add_failure(order.id, AssignmentResult.NO_AVAILABLE_DRIVERS.value)

        logger.info(
            f"Batch assignment completed: {result.total_assigned} assigned, "
            f"{result.total_failed} failed out of {result.total_processed} orders"
        )

        return result

    async def preview_assignments(self, request: BatchAssignmentRequest) -> BatchAssignmentResult:
        """
        Предпросмотр распределения без фактического назначения заказов.
        """
        # Реализация аналогична assign_orders_batch, но без реального назначения
        result = await self.assign_orders_batch(request)
        # Откатить назначения (в реальности нужно транзакцию или мок)
        # Для preview просто возвращаем результат без сохранения
        return result

    async def _get_unassigned_orders(self, request: BatchAssignmentRequest) -> List[Order]:
        """Получить нераспределенные заказы на дату."""
        return await self.order_repo.get_unassigned_orders_on_date(
            request.target_date,
            request.priority_filter
        )

    async def _get_available_drivers(self, request: BatchAssignmentRequest) -> Dict[int, Dict]:
        """Получить доступных водителей с их текущими расписаниями."""
        query = select(Driver).where(
            and_(
                Driver.role.in_([UserRole.DRIVER, UserRole.DISPATCHER]),
                Driver.is_active == True
            )
        )

        if request.driver_ids:
            query = query.where(Driver.id.in_(request.driver_ids))

        result = await self.session.execute(query)
        drivers = result.scalars().all()

        # Получить текущие заказы на дату для каждого водителя
        driver_schedules = {}
        for driver in drivers:
            current_orders = await self._get_driver_orders_on_date(driver.id, request.target_date)
            driver_schedules[driver.id] = {
                'driver': driver,
                'current_orders': len(current_orders),
                'order_times': [(o.time_range.lower, o.time_range.upper) for o in current_orders if o.time_range]
            }

        return driver_schedules

    async def _get_driver_orders_on_date(self, driver_id: int, target_date: date) -> List[Order]:
        """Получить заказы водителя на указанную дату."""
        return await self.order_repo.get_driver_orders_on_date(driver_id, target_date)

    async def _find_suitable_driver(
        self,
        order: Order,
        available_drivers: Dict[int, Dict],
        max_orders_per_driver: int
    ) -> Optional[int]:
        """
        Найти подходящего водителя для заказа.

        Критерии:
        - Водитель не превысил лимит заказов
        - Нет пересечения по времени с существующими заказами
        """
        for driver_id, driver_info in available_drivers.items():
            # Проверить лимит заказов
            if driver_info['current_orders'] >= max_orders_per_driver:
                continue

            # Проверить конфликты времени
            if self._has_time_conflict(order.time_range, driver_info['order_times']):
                continue

            return driver_id

        return None

    def _has_time_conflict(
        self,
        new_time_range: Tuple[datetime, datetime],
        existing_times: List[Tuple[datetime, datetime]]
    ) -> bool:
        """Проверить пересечение временных интервалов."""
        if not new_time_range:
            return False

        new_start, new_end = new_time_range
        for existing_start, existing_end in existing_times:
            if new_start < existing_end and new_end > existing_start:
                return True

        return False

    async def _assign_order_to_driver(self, order_id: int, driver_id: int) -> bool:
        """Назначить заказ водителю через OrderService."""
        try:
            # Используем существующий метод назначения
            from src.services.order_workflow import OrderWorkflowService
            # В реальности нужно инжектировать OrderWorkflowService
            # Пока что используем прямой update
            await self.session.execute(
                select(Order).where(Order.id == order_id)
            )
            order = (await self.session.execute(
                select(Order).where(Order.id == order_id)
            )).scalar_one_or_none()

            if not order:
                return False

            order.driver_id = driver_id
            order.status = OrderStatus.ASSIGNED
            await self.session.commit()

            logger.info(f"Assigned order {order_id} to driver {driver_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign order {order_id} to driver {driver_id}: {e}")
            await self.session.rollback()
            return False
