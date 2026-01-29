from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select
from geoalchemy2.elements import WKTElement

from src.database.uow import AbstractUnitOfWork
from src.database.models import OrderTemplate, Order, OrderStatus
from src.schemas.template import (
    OrderTemplateCreate,
    OrderTemplateUpdate,
    OrderTemplateResponse,
    GenerateOrdersRequest
)
from src.schemas.order import OrderCreate, OrderResponse
from src.services.geocoding import GeocodingService
from src.core.logging import get_logger

logger = get_logger(__name__)


class TemplateService:
    """
    Сервис управления шаблонами заказов.
    Позволяет создавать, редактировать шаблоны и генерировать заказы на их основе.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        geocoding_service: Optional[GeocodingService] = None
    ):
        self.uow = uow
        self.geocoding_service = geocoding_service

    async def _ensure_coordinates(self, dto: OrderTemplateCreate) -> OrderTemplateCreate:
        """
        Гарантирует наличие координат, выполняя геокодинг если нужно.
        """
        # Если все координаты уже есть - ничего не делаем
        if all([dto.pickup_lat, dto.pickup_lon, dto.dropoff_lat, dto.dropoff_lon]):
            return dto

        if not self.geocoding_service:
            # Если координат нет и геокодинга нет - оставляем как есть, сохраняем только адреса
            return dto

        # Геокодинг погрузки
        if not dto.pickup_lat or not dto.pickup_lon:
            if dto.pickup_address:
                logger.info("geocoding_template_pickup", address=dto.pickup_address)
                results = await self.geocoding_service.search(dto.pickup_address)
                result = results[0] if results else None

                if result:
                    dto.pickup_lat = result.lat
                    dto.pickup_lon = result.lon
                    logger.info("geocoded_template_pickup", lat=result.lat, lon=result.lon)

        # Геокодинг выгрузки
        if not dto.dropoff_lat or not dto.dropoff_lon:
            if dto.dropoff_address:
                logger.info("geocoding_template_dropoff", address=dto.dropoff_address)
                results = await self.geocoding_service.search(dto.dropoff_address)
                result = results[0] if results else None

                if result:
                    dto.dropoff_lat = result.lat
                    dto.dropoff_lon = result.lon
                    logger.info("geocoded_template_dropoff", lat=result.lat, lon=result.lon)

        return dto

    async def create_template(self, data: OrderTemplateCreate) -> OrderTemplateResponse:
        """
        Создать новый шаблон заказа.

        Args:
            data: Данные для создания шаблона

        Returns:
            OrderTemplateResponse: Созданный шаблон

        Raises:
            ValueError: Если данные невалидны
        """
        # Выполняем геокодинг, если нужно
        data = await self._ensure_coordinates(data)

        async with self.uow:
            # Проверка существования подрядчика, если указан
            if data.contractor_id:
                from src.database.models import Contractor
                contractor = await self.uow.session.get(Contractor, data.contractor_id)
                if not contractor:
                    raise ValueError(f"Contractor with id {data.contractor_id} not found")

            # Создаем объект Location для pickup и dropoff, если есть координаты
            pickup_location = None
            if data.pickup_lat is not None and data.pickup_lon is not None:
                pickup_location = WKTElement(f"POINT({data.pickup_lon} {data.pickup_lat})", srid=4326)

            dropoff_location = None
            if data.dropoff_lat is not None and data.dropoff_lon is not None:
                dropoff_location = WKTElement(f"POINT({data.dropoff_lon} {data.dropoff_lat})", srid=4326)

            template = OrderTemplate(
                name=data.name,
                contractor_id=data.contractor_id,
                priority=data.priority,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_address=data.pickup_address,
                dropoff_address=data.dropoff_address,
                customer_phone=data.customer_phone,
                customer_name=data.customer_name,
                customer_telegram_id=data.customer_telegram_id,
                customer_webhook_url=data.customer_webhook_url,
                price=data.price,
                comment=data.comment,
                is_active=data.is_active
            )

            self.uow.order_templates.add(template)
            await self.uow.commit()

            logger.info("template_created", template_id=template.id, name=template.name)
            return OrderTemplateResponse.model_validate(template)

    async def update_template(
        self,
        template_id: int,
        data: OrderTemplateUpdate
    ) -> Optional[OrderTemplateResponse]:
        """
        Обновить существующий шаблон.

        Args:
            template_id: ID шаблона
            data: Данные для обновления

        Returns:
            OrderTemplateResponse: Обновленный шаблон или None, если не найден

        Raises:
            ValueError: Если обновление невалидно
        """
        async with self.uow:
            template = await self.uow.order_templates.get(template_id)
            if not template:
                return None

            # Проверка существования подрядчика, если он обновляется
            if data.contractor_id is not None:
                from src.database.models import Contractor
                contractor = await self.uow.session.get(Contractor, data.contractor_id)
                if not contractor:
                    raise ValueError(f"Contractor with id {data.contractor_id} not found")

            update_data = data.model_dump(exclude_unset=True)

            # Обновляем координаты, если изменились
            if any(key in update_data for key in ["pickup_lat", "pickup_lon"]):
                pickup_lat = update_data.get("pickup_lat")
                pickup_lon = update_data.get("pickup_lon")

                # Если оба координаты заданы, обновляем location
                if pickup_lat is not None and pickup_lon is not None:
                    template.pickup_location = WKTElement(f"POINT({pickup_lon} {pickup_lat})", srid=4326)

                # Удаляем из update_data, так как уже обработали
                update_data.pop("pickup_lat", None)
                update_data.pop("pickup_lon", None)

            if any(key in update_data for key in ["dropoff_lat", "dropoff_lon"]):
                dropoff_lat = update_data.get("dropoff_lat")
                dropoff_lon = update_data.get("dropoff_lon")

                if dropoff_lat is not None and dropoff_lon is not None:
                    template.dropoff_location = WKTElement(f"POINT({dropoff_lon} {dropoff_lat})", srid=4326)

                update_data.pop("dropoff_lat", None)
                update_data.pop("dropoff_lon", None)

            # Обновляем остальные поля
            for key, value in update_data.items():
                setattr(template, key, value)

            await self.uow.commit()

            logger.info("template_updated", template_id=template_id)
            return OrderTemplateResponse.model_validate(template)

    async def delete_template(self, template_id: int) -> bool:
        """
        Удалить шаблон заказа.

        Args:
            template_id: ID шаблона

        Returns:
            bool: True, если шаблон был удален, False если не найден
        """
        async with self.uow:
            result = await self.uow.order_templates.delete(template_id)
            await self.uow.commit()

            if result:
                logger.info("template_deleted", template_id=template_id)

            return result

    async def list_templates(
        self,
        contractor_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[OrderTemplateResponse]:
        """
        Получить список шаблонов с фильтрами.

        Args:
            contractor_id: Опциональный фильтр по подрядчику
            is_active: Опциональный фильтр по активности

        Returns:
            List[OrderTemplateResponse]: Список шаблонов
        """
        async with self.uow:
            session = self.uow.session

            query = select(OrderTemplate)

            # Применяем фильтры
            if contractor_id is not None:
                query = query.where(OrderTemplate.contractor_id == contractor_id)

            if is_active is not None:
                query = query.where(OrderTemplate.is_active == is_active)

            # Сортировка по имени
            query = query.order_by(OrderTemplate.name)

            result = await session.execute(query)
            templates = result.scalars().all()

            return [
                OrderTemplateResponse.model_validate(template)
                for template in templates
            ]

    async def get_template(self, template_id: int) -> Optional[OrderTemplateResponse]:
        """
        Получить шаблон по ID.

        Args:
            template_id: ID шаблона

        Returns:
            OrderTemplateResponse: Шаблон или None, если не найден
        """
        async with self.uow:
            template = await self.uow.order_templates.get(template_id)
            if not template:
                return None
            return OrderTemplateResponse.model_validate(template)

    async def generate_orders_from_template(
        self,
        template_id: int,
        request: GenerateOrdersRequest,
        order_service=None
    ) -> List[OrderResponse]:
        """
        Создать заказы на основе шаблона для заданного периода.

        Args:
            template_id: ID шаблона
            request: Параметры генерации (date_from, date_until, driver_id)
            order_service: Опциональный сервис для создания заказов
                          (если не передан, создаются напрямую)

        Returns:
            List[OrderResponse]: Список созданных заказов

        Raises:
            ValueError: Если шаблон не найден или неактивен
        """
        async with self.uow:
            template = await self.uow.order_templates.get(template_id)
            if not template:
                raise ValueError(f"Template with id {template_id} not found")

            if not template.is_active:
                raise ValueError(f"Template {template_id} is not active")

            # Валидация периода
            if request.date_until <= request.date_from:
                raise ValueError("date_until must be after date_from")

        # Извлекаем координаты из геометрии
        pickup_lat = None
        pickup_lon = None
        if template.pickup_location:
            from geoalchemy2.shape import to_shape
            point = to_shape(template.pickup_location)
            pickup_lon = point.x
            pickup_lat = point.y

        dropoff_lat = None
        dropoff_lon = None
        if template.dropoff_location:
            from geoalchemy2.shape import to_shape
            point = to_shape(template.dropoff_location)
            dropoff_lon = point.x
            dropoff_lat = point.y

        # Генерируем заказы по дням
        created_orders = []
        current_date = request.date_from

        logger.info(
            "generating_orders_from_template",
            template_id=template_id,
            date_from=request.date_from,
            date_until=request.date_until
        )

        while current_date < request.date_until:
            # Создаем OrderCreate для каждого дня
            order_data = OrderCreate(
                driver_id=request.driver_id,
                contractor_id=template.contractor_id,
                time_start=current_date,
                priority=template.priority,
                pickup_lat=pickup_lat,
                pickup_lon=pickup_lon,
                dropoff_lat=dropoff_lat,
                dropoff_lon=dropoff_lon,
                pickup_address=template.pickup_address,
                dropoff_address=template.dropoff_address,
                customer_phone=template.customer_phone,
                customer_name=template.customer_name,
                comment=template.comment
            )

            # Если передан order_service, используем его для создания заказа
            # (это позволит применить всю бизнес-логику, включая расчет маршрута и цены)
            if order_service:
                order = await order_service.create_order(order_data, driver_id=request.driver_id)
                created_orders.append(order)
            else:
                # Иначе создаем заказ напрямую
                async with self.uow:
                    # Создаем упрощенный заказ без расчета маршрута
                    # (координаты должны быть уже заданы в шаблоне)
                    if not all([pickup_lat, pickup_lon, dropoff_lat, dropoff_lon]):
                        raise ValueError(
                            "Template must have coordinates set to generate orders without order_service"
                        )

                    order = Order(
                        driver_id=request.driver_id,
                        contractor_id=template.contractor_id,
                        status=OrderStatus.ASSIGNED if request.driver_id else OrderStatus.PENDING,
                        priority=template.priority,
                        time_range=(current_date, current_date + timedelta(hours=1)),  # Default 1 hour
                        scheduled_date=current_date,
                        pickup_location=WKTElement(f"POINT({pickup_lon} {pickup_lat})", srid=4326),
                        dropoff_location=WKTElement(f"POINT({dropoff_lon} {dropoff_lat})", srid=4326),
                        pickup_address=template.pickup_address,
                        dropoff_address=template.dropoff_address,
                        customer_phone=template.customer_phone,
                        customer_name=template.customer_name,
                        price=template.price,
                        comment=template.comment
                    )

                    self.uow.orders.add(order)
                    await self.uow.commit()

                    from src.schemas.order import OrderResponse
                    created_orders.append(OrderResponse.model_validate(order))

            current_date += timedelta(days=1)

        logger.info(
            "orders_generated_from_template",
            template_id=template_id,
            count=len(created_orders)
        )

        return created_orders
