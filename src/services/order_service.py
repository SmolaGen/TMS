from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from geoalchemy2.elements import WKTElement

from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, OrderStatus, OrderPriority
from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest
from src.services.routing import RoutingService, OSRMUnavailableError, RouteNotFoundError
from src.services.order_workflow import OrderStateMachine
from src.services.urgent_assignment import UrgentAssignmentService
from src.services.notification_service import NotificationService
from src.services.webhook_service import WebhookService
from src.services.geocoding import GeocodingService
from src.core.logging import get_logger

logger = get_logger(__name__)

class OrderService:
    """
    Сервис управления заказами.
    Интегрирует RoutingService для расчёта маршрутов и цен,
    и OrderStateMachine для управления состояниями.
    """
    
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        routing_service: RoutingService,
        geocoding_service: Optional[GeocodingService] = None,
        urgent_service: Optional[UrgentAssignmentService] = None,
        notification_service: Optional[NotificationService] = None,
        webhook_service: Optional[WebhookService] = None
    ):
        self.uow = uow
        self.routing_service = routing_service
        self.geocoding_service = geocoding_service
        self.urgent_service = urgent_service
        self.notification_service = notification_service
        self.webhook_service = webhook_service

    def _get_sm(self, order: Order) -> OrderStateMachine:
        """Создаёт экземпляр машины состояний для заказа."""
        return OrderStateMachine(order)

    async def _ensure_coordinates(self, dto: OrderCreate) -> OrderCreate:
        """
        Гарантирует наличие координат, выполняя геокодинг если нужно.
        """
        # Если все координаты уже есть - ничего не делаем
        if all([dto.pickup_lat, dto.pickup_lon, dto.dropoff_lat, dto.dropoff_lon]):
            return dto
        
        if not self.geocoding_service:
            raise HTTPException(
                status_code=422,
                detail="Координаты не указаны, а сервис геокодинга недоступен"
            )
        
        # Геокодинг погрузки
        if not dto.pickup_lat or not dto.pickup_lon:
            if not dto.pickup_address:
                raise HTTPException(
                    status_code=422,
                    detail="Необходимо указать либо координаты, либо адрес погрузки"
                )
            
            logger.info("geocoding_pickup", address=dto.pickup_address)
            result = await self.geocoding_service.geocode(dto.pickup_address)
            
            if not result:
                raise HTTPException(
                    status_code=422,
                    detail=f"Не удалось найти адрес погрузки: {dto.pickup_address}"
                )
            
            dto.pickup_lat = result.lat
            dto.pickup_lon = result.lon
            logger.info("geocoded_pickup", lat=result.lat, lon=result.lon)
        
        # Геокодинг выгрузки
        if not dto.dropoff_lat or not dto.dropoff_lon:
            if not dto.dropoff_address:
                raise HTTPException(
                    status_code=422,
                    detail="Необходимо указать либо координаты, либо адрес выгрузки"
                )
            
            logger.info("geocoding_dropoff", address=dto.dropoff_address)
            result = await self.geocoding_service.geocode(dto.dropoff_address)
            
            if not result:
                raise HTTPException(
                    status_code=422,
                    detail=f"Не удалось найти адрес выгрузки: {dto.dropoff_address}"
                )
            
            dto.dropoff_lat = result.lat
            dto.dropoff_lon = result.lon
            logger.info("geocoded_dropoff", lat=result.lat, lon=result.lon)
        
        return dto

    async def create_order(self, dto: OrderCreate, driver_id: Optional[int] = None) -> OrderResponse:
        """
        Создаёт новый заказ с автоматическим расчётом цены и времени.
        Выполняет геокодинг, если координаты не указаны.
        """
        # 0. Гарантируем наличие координат
        dto = await self._ensure_coordinates(dto)

        target_driver_id = driver_id if driver_id is not None else dto.driver_id
        logger.info("creating_order", 
                    driver_id=target_driver_id, 
                    pickup_addr=dto.pickup_address,
                    pickup_coords=(dto.pickup_lat, dto.pickup_lon))
        
        # 1. Запрос к RoutingService для получения дистанции и времени
        origin = (dto.pickup_lon, dto.pickup_lat)
        destination = (dto.dropoff_lon, dto.dropoff_lat)
        
        try:
            route, price = await self.routing_service.get_route_with_price(
                origin=origin,
                destination=destination
            )
        except OSRMUnavailableError as e:
            logger.error("routing_unavailable", error=str(e))
            raise HTTPException(status_code=503, detail="Сервис маршрутизации временно недоступен")
        except RouteNotFoundError as e:
            logger.warning("route_not_found", origin=origin, destination=destination)
            raise HTTPException(status_code=422, detail="Невозможно построить маршрут между указанными точками")
        except Exception as e:
            logger.exception("routing_unexpected_error")
            raise HTTPException(status_code=500, detail=f"Ошибка при расчёте маршрута: {str(e)}")

        # 2. Расчет временного интервала [start, end)
        time_start = dto.time_start
        duration = timedelta(seconds=route.duration_seconds)
        time_end = time_start + duration
        
        # Формат для PostgreSQL tstzrange: '[start, end)'
        time_range = (time_start, time_end)
        
        # 3. Сохранение в БД через UoW
        async with self.uow:
            
            order = Order(
                driver_id=target_driver_id,
                contractor_id=dto.contractor_id,
                external_id=dto.external_id,
                status=OrderStatus.ASSIGNED if target_driver_id else OrderStatus.PENDING,
                priority=dto.priority,
                time_range=time_range,
                pickup_location=WKTElement(f"POINT({dto.pickup_lon} {dto.pickup_lat})", srid=4326),
                dropoff_location=WKTElement(f"POINT({dto.dropoff_lon} {dto.dropoff_lat})", srid=4326),
                pickup_address=dto.pickup_address,
                dropoff_address=dto.dropoff_address,
                customer_phone=dto.customer_phone,
                customer_name=dto.customer_name,
                distance_meters=route.distance_meters,
                duration_seconds=route.duration_seconds,
                price=price.total_price,
                route_geometry=route.geometry,
                comment=dto.comment
            )
            
            self.uow.orders.add(order)
            
            try:
                await self.uow.commit()
                logger.info("order_created", order_id=order.id, price=float(order.price))
                
                # 4. Авто-назначение для срочных заказов (URGENT)
                # from src.database.models import OrderPriority, OrderStatus
                if order.priority == OrderPriority.URGENT and not order.driver_id and self.urgent_service:
                    driver_id = await self.urgent_service.assign_urgent_order(order)
                    if driver_id:
                        async with self.uow:
                            # Получаем свежий объект заказа в новой сессии UOW если нужно 
                            # или используем текущий если сессия еще открыта (она закрылась после await uow.commit()?)
                            # AbstractUnitOfWork обычно закрывает сессию в __aexit__.
                            pass
                        
                        # Поскольку commit закрыл сессию, нам нужно открыть новую для назначения
                        from src.services.order_workflow import OrderWorkflowService
                        workflow = OrderWorkflowService(self.uow)
                        await workflow.assign_driver(order.id, driver_id)
                        
                        # Обновляем объект для ответа
                        async with self.uow:
                            order = await self.uow.orders.get(order.id)
                        
                        # Уведомляем водителя
                        if self.notification_service:
                            await self.notification_service.notify_order_assigned(driver_id, order)
                
                # Или если водитель был назначен сразу вручную
                elif order.driver_id and self.notification_service:
                    await self.notification_service.notify_order_assigned(order.driver_id, order)
                
                # 5. Уведомляем подрядчика (вебхук)
                if self.webhook_service:
                    await self.webhook_service.notify_status_change(order)

            except IntegrityError as e:
                # Обработка Exclusion Constraint: no_driver_time_overlap
                error_msg = str(e).lower()
                if "no_driver_time_overlap" in error_msg:
                    # Используем локальные переменные, так как объект order может быть недоступен (expired)
                    logger.warning("order_overlap_detected", driver_id=target_driver_id, time_range=time_range)
                    # Форматируем время из локальных переменных
                    t_start_str = time_start.strftime('%H:%M')
                    t_end_str = time_end.strftime('%H:%M')
                    raise HTTPException(
                        status_code=409, 
                        detail={"error": "time_overlap", "message": f"Водитель #{target_driver_id} уже занят в указанный интервал времени ({t_start_str} - {t_end_str})"}
                    )
                raise HTTPException(status_code=500, detail="Ошибка базы данных при создании заказа")
            
            return OrderResponse.model_validate(order)

    async def get_order(self, order_id: int) -> OrderResponse:
        """Получает данные заказа по ID."""
        async with self.uow:
            order = await self.uow.orders.get(order_id)
            if not order:
                raise HTTPException(status_code=404, detail=f"Заказ #{order_id} не найден")
            return OrderResponse.model_validate(order)

    async def get_orders_list(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, include_geometry: bool = False) -> List[OrderResponse]:
        """Получает список заказов с опциональной фильтрацией по времени."""
        async with self.uow:
            orders = await self.uow.orders.get_all(start_date=start_date, end_date=end_date)
            responses = []
            for o in orders:
                resp = OrderResponse.model_validate(o)
                if not include_geometry:
                    resp.route_geometry = None
                responses.append(resp)
            return responses

    async def move_order(self, order_id: int, dto: OrderMoveRequest) -> Optional[OrderResponse]:
        """
        Изменяет время выполнения и/или водителя заказа (Drag-and-Drop).
        """
        logger.info("moving_order", order_id=order_id, new_start=dto.new_time_start, new_driver=dto.new_driver_id)
        
        async with self.uow:
            order = await self.uow.orders.get(order_id)
            if not order:
                return None
            
            # 1. Обновляем время
            new_range = (dto.new_time_start, dto.new_time_end)
            order.time_range = new_range
            
            # 2. Обновляем водителя если нужно
            old_driver_id = order.driver_id
            new_driver_id = None
            
            # Проверяем, был ли передан new_driver_id явно
            # Сначала пробуем Pydantic v2 API, затем fallback на v1
            fields_set = getattr(dto, "model_fields_set", None)
            if fields_set is None:
                fields_set = getattr(dto, "__fields_set__", set())
            
            driver_changed = False
            if "new_driver_id" in fields_set:
                new_driver_id = dto.new_driver_id
                
                if new_driver_id != old_driver_id:
                    order.driver_id = new_driver_id
                    
                    if new_driver_id is None:
                         # Снятие с водителя
                         order.status = OrderStatus.PENDING
                    elif order.status == OrderStatus.PENDING:
                         # Назначение на водителя
                         order.status = OrderStatus.ASSIGNED
                    
                    driver_changed = True

            try:
                await self.uow.commit()
                logger.info("order_moved", order_id=order_id, new_range=new_range, new_driver=order.driver_id)
                
                # 3. Уведомляем нового водителя
                if driver_changed and order.driver_id and self.notification_service:
                    await self.notification_service.notify_order_assigned(order.driver_id, order)
                
                # 4. Уведомляем подрядчика
                if self.webhook_service:
                    await self.webhook_service.notify_status_change(order)

                return OrderResponse.model_validate(order)
            except IntegrityError as e:
                error_msg = str(e).lower()
                if "no_driver_time_overlap" in error_msg:
                    # Используем ID из DTO или из базы если не менялся
                    target_driver = new_driver_id if new_driver_id is not None else old_driver_id
                    logger.warning("order_overlap_on_move", order_id=order_id, driver_id=target_driver)
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "time_overlap", "message": f"Водитель #{target_driver} занят в новый интервал времени"}
                    )
                raise HTTPException(status_code=500, detail="Ошибка базы данных при перемещении заказа")
