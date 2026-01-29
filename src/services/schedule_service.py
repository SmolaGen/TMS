from datetime import datetime, date
from typing import List, Optional, Dict
from sqlalchemy import select, and_, func, or_
from geoalchemy2.elements import WKTElement

from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, Driver, DriverAvailability, OrderStatus, DriverStatus
from src.schemas.schedule import (
    ScheduleViewResponse,
    ScheduleDayView,
    DriverScheduleResponse,
    CreateScheduledOrderRequest
)
from src.schemas.order import OrderResponse, OrderCreate
from src.schemas.driver import DriverResponse
from src.schemas.availability import DriverAvailabilityResponse
from src.services.order_service import OrderService
from src.core.logging import get_logger

logger = get_logger(__name__)


class ScheduleService:
    """Сервис управления расписанием и планированием заказов."""

    def __init__(self, uow: AbstractUnitOfWork, order_service: Optional[OrderService] = None):
        self.uow = uow
        self.order_service = order_service

    async def get_schedule_view(
        self,
        date_from: datetime,
        date_until: datetime,
        driver_ids: Optional[List[int]] = None
    ) -> ScheduleViewResponse:
        """
        Получить календарное представление расписания за период.

        Args:
            date_from: Начало периода
            date_until: Конец периода
            driver_ids: Опциональный фильтр по водителям

        Returns:
            ScheduleViewResponse: Календарное представление с заказами и доступностью водителей
        """
        logger.info("get_schedule_view", date_from=date_from, date_until=date_until, driver_ids=driver_ids)

        async with self.uow:
            session = self.uow.session

            # Получить все заказы в периоде
            orders_query = select(Order).where(
                or_(
                    # Заказы с scheduled_date в периоде
                    and_(
                        Order.scheduled_date.isnot(None),
                        Order.scheduled_date >= date_from,
                        Order.scheduled_date < date_until
                    ),
                    # Заказы с time_range пересекающимся с периодом
                    and_(
                        Order.time_range.isnot(None),
                        Order.time_range.overlaps((date_from, date_until))
                    )
                )
            )

            # Фильтр по водителям
            if driver_ids:
                orders_query = orders_query.where(Order.driver_id.in_(driver_ids))

            # Сортировка по времени
            orders_query = orders_query.order_by(
                func.coalesce(Order.scheduled_date, func.lower(Order.time_range))
            )

            result = await session.execute(orders_query)
            orders = result.scalars().all()

            # Получить периоды недоступности в периоде
            availability_query = select(DriverAvailability).where(
                DriverAvailability.time_range.overlaps((date_from, date_until))
            )

            if driver_ids:
                availability_query = availability_query.where(
                    DriverAvailability.driver_id.in_(driver_ids)
                )

            result = await session.execute(availability_query)
            availabilities = result.scalars().all()

            # Получить всех водителей
            drivers_query = select(Driver)
            if driver_ids:
                drivers_query = drivers_query.where(Driver.id.in_(driver_ids))

            result = await session.execute(drivers_query)
            all_drivers = result.scalars().all()

            # Группировка заказов по дням
            days_map: Dict[date, ScheduleDayView] = {}

            for order in orders:
                # Определить дату заказа
                order_date = None
                if order.scheduled_date:
                    order_date = order.scheduled_date.date()
                elif order.time_range and order.time_range[0]:
                    order_date = order.time_range[0].date()

                if order_date:
                    if order_date not in days_map:
                        days_map[order_date] = ScheduleDayView(
                            date=datetime.combine(order_date, datetime.min.time()),
                            orders=[],
                            available_drivers=[],
                            unavailable_periods=[]
                        )
                    days_map[order_date].orders.append(OrderResponse.model_validate(order))

            # Добавить информацию о недоступности водителей по дням
            for availability in availabilities:
                # Определить диапазон дат для периода недоступности
                start_date = availability.time_range[0].date() if availability.time_range[0] else date_from.date()
                end_date = availability.time_range[1].date() if availability.time_range[1] else date_until.date()

                # Добавить недоступность ко всем затронутым дням
                current_date = start_date
                while current_date <= end_date:
                    if current_date not in days_map:
                        days_map[current_date] = ScheduleDayView(
                            date=datetime.combine(current_date, datetime.min.time()),
                            orders=[],
                            available_drivers=[],
                            unavailable_periods=[]
                        )
                    days_map[current_date].unavailable_periods.append(
                        DriverAvailabilityResponse.model_validate(availability)
                    )
                    # Переход к следующему дню
                    from datetime import timedelta
                    current_date = current_date + timedelta(days=1)

            # Определить доступных водителей для каждого дня
            for day_date, day_view in days_map.items():
                day_start = datetime.combine(day_date, datetime.min.time())
                day_end = datetime.combine(day_date, datetime.max.time())

                # Водители, у которых нет недоступности в этот день
                unavailable_driver_ids = {av.driver_id for av in day_view.unavailable_periods}
                available_driver_ids = [
                    driver.id for driver in all_drivers
                    if driver.id not in unavailable_driver_ids
                ]
                day_view.available_drivers = available_driver_ids

            # Преобразовать в отсортированный список дней
            sorted_days = sorted(days_map.items())
            days_list = [day_view for _, day_view in sorted_days]

            return ScheduleViewResponse(
                date_from=date_from,
                date_until=date_until,
                days=days_list,
                total_orders=len(orders),
                total_drivers=len(all_drivers)
            )

    async def get_driver_schedule(
        self,
        driver_id: int,
        date_from: datetime,
        date_until: datetime
    ) -> Optional[DriverScheduleResponse]:
        """
        Получить расписание конкретного водителя за период.

        Args:
            driver_id: ID водителя
            date_from: Начало периода
            date_until: Конец периода

        Returns:
            DriverScheduleResponse: Расписание водителя или None если водитель не найден
        """
        logger.info("get_driver_schedule", driver_id=driver_id, date_from=date_from, date_until=date_until)

        async with self.uow:
            session = self.uow.session

            # Получить водителя
            driver = await self.uow.drivers.get(driver_id)
            if not driver:
                return None

            # Получить заказы водителя в периоде
            orders_query = select(Order).where(
                and_(
                    Order.driver_id == driver_id,
                    or_(
                        # Заказы с scheduled_date в периоде
                        and_(
                            Order.scheduled_date.isnot(None),
                            Order.scheduled_date >= date_from,
                            Order.scheduled_date < date_until
                        ),
                        # Заказы с time_range пересекающимся с периодом
                        and_(
                            Order.time_range.isnot(None),
                            Order.time_range.overlaps((date_from, date_until))
                        )
                    )
                )
            ).order_by(
                func.coalesce(Order.scheduled_date, func.lower(Order.time_range))
            )

            result = await session.execute(orders_query)
            orders = result.scalars().all()

            # Получить периоды недоступности водителя
            availability_query = select(DriverAvailability).where(
                and_(
                    DriverAvailability.driver_id == driver_id,
                    DriverAvailability.time_range.overlaps((date_from, date_until))
                )
            ).order_by(func.lower(DriverAvailability.time_range))

            result = await session.execute(availability_query)
            availabilities = result.scalars().all()

            return DriverScheduleResponse(
                driver=DriverResponse.model_validate(driver),
                date_from=date_from,
                date_until=date_until,
                orders=[OrderResponse.model_validate(o) for o in orders],
                unavailable_periods=[
                    DriverAvailabilityResponse.model_validate(av)
                    for av in availabilities
                ]
            )

    async def get_available_drivers(
        self,
        check_date: datetime,
        time_window: Optional[tuple[datetime, datetime]] = None
    ) -> List[DriverResponse]:
        """
        Получить список доступных водителей на указанную дату/время.

        Args:
            check_date: Дата и время для проверки
            time_window: Опциональный временной интервал (start, end)

        Returns:
            List[DriverResponse]: Список доступных водителей
        """
        logger.info("get_available_drivers", check_date=check_date, time_window=time_window)

        async with self.uow:
            session = self.uow.session

            # Получить всех активных водителей
            drivers_query = select(Driver).where(Driver.is_active == True)
            result = await session.execute(drivers_query)
            all_drivers = result.scalars().all()

            # Определить период проверки
            if time_window:
                check_start, check_end = time_window
            else:
                check_start = check_date
                check_end = check_date

            available_drivers = []

            for driver in all_drivers:
                # Проверить, есть ли пересечения с периодами недоступности
                unavailability_query = select(func.count(DriverAvailability.id)).where(
                    and_(
                        DriverAvailability.driver_id == driver.id,
                        DriverAvailability.time_range.overlaps((check_start, check_end))
                    )
                )

                result = await session.execute(unavailability_query)
                unavailable_count = result.scalar()

                # Если нет пересечений с недоступностью - водитель доступен
                if unavailable_count == 0:
                    available_drivers.append(DriverResponse.model_validate(driver))

            logger.info("found_available_drivers", count=len(available_drivers), total=len(all_drivers))
            return available_drivers

    async def create_scheduled_order(
        self,
        data: CreateScheduledOrderRequest
    ) -> OrderResponse:
        """
        Создать запланированный заказ с будущей датой.

        Args:
            data: Данные для создания заказа

        Returns:
            OrderResponse: Созданный заказ

        Raises:
            ValueError: Если данные невалидны или водитель недоступен
        """
        logger.info("create_scheduled_order", scheduled_date=data.scheduled_date, driver_id=data.driver_id)

        # Проверить, что scheduled_date в будущем
        if data.scheduled_date < datetime.utcnow():
            raise ValueError("scheduled_date must be in the future")

        # Если указан водитель, проверить его доступность
        if data.driver_id:
            async with self.uow:
                session = self.uow.session

                # Проверить существование водителя
                driver = await self.uow.drivers.get(data.driver_id)
                if not driver:
                    raise ValueError(f"Driver with id {data.driver_id} not found")

                # Проверить доступность водителя на scheduled_date
                unavailability_query = select(func.count(DriverAvailability.id)).where(
                    and_(
                        DriverAvailability.driver_id == data.driver_id,
                        DriverAvailability.time_range.contains(data.scheduled_date)
                    )
                )

                result = await session.execute(unavailability_query)
                unavailable_count = result.scalar()

                if unavailable_count > 0:
                    raise ValueError(
                        f"Driver {data.driver_id} is not available on {data.scheduled_date}"
                    )

        # Использовать OrderService для создания заказа, если доступен
        if self.order_service:
            # Преобразовать CreateScheduledOrderRequest в OrderCreate
            order_create = OrderCreate(
                driver_id=data.driver_id,
                contractor_id=data.contractor_id,
                external_id=data.external_id,
                time_start=data.time_start,
                pickup_lat=data.pickup_lat,
                pickup_lon=data.pickup_lon,
                dropoff_lat=data.dropoff_lat,
                dropoff_lon=data.dropoff_lon,
                pickup_address=data.pickup_address,
                dropoff_address=data.dropoff_address,
                customer_phone=data.customer_phone,
                customer_name=data.customer_name,
                comment=data.comment
            )

            order_response = await self.order_service.create_order(order_create, driver_id=data.driver_id)

            # Обновить scheduled_date
            async with self.uow:
                order = await self.uow.orders.get(order_response.id)
                if order:
                    order.scheduled_date = data.scheduled_date
                    await self.uow.commit()
                    return OrderResponse.model_validate(order)
                return order_response
        else:
            # Создать заказ напрямую без OrderService
            async with self.uow:
                # Определить time_range
                time_range = None
                if data.time_end:
                    time_range = (data.time_start, data.time_end)
                else:
                    # Если time_end не указан, используем только time_start
                    from datetime import timedelta
                    time_range = (data.time_start, data.time_start + timedelta(hours=1))

                order = Order(
                    driver_id=data.driver_id,
                    contractor_id=data.contractor_id,
                    external_id=data.external_id,
                    status=OrderStatus.ASSIGNED if data.driver_id else OrderStatus.PENDING,
                    time_range=time_range,
                    scheduled_date=data.scheduled_date,
                    pickup_address=data.pickup_address,
                    dropoff_address=data.dropoff_address,
                    customer_phone=data.customer_phone,
                    customer_name=data.customer_name,
                    comment=data.comment
                )

                # Добавить координаты если указаны
                if all([data.pickup_lat, data.pickup_lon]):
                    order.pickup_location = WKTElement(
                        f"POINT({data.pickup_lon} {data.pickup_lat})",
                        srid=4326
                    )

                if all([data.dropoff_lat, data.dropoff_lon]):
                    order.dropoff_location = WKTElement(
                        f"POINT({data.dropoff_lon} {data.dropoff_lat})",
                        srid=4326
                    )

                self.uow.orders.add(order)
                await self.uow.commit()

                logger.info("scheduled_order_created", order_id=order.id, scheduled_date=data.scheduled_date)
                return OrderResponse.model_validate(order)
