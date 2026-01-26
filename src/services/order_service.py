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
            results = await self.geocoding_service.search(dto.pickup_address)
            result = results[0] if results else None
            
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
            results = await self.geocoding_service.search(dto.dropoff_address)
            result = results[0] if results else None
            
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
        
        # Убедимся, что координаты теперь не None после _ensure_coordinates
        if dto.pickup_lon is None or dto.pickup_lat is None or \
           dto.dropoff_lon is None or dto.dropoff_lat is None:
            raise HTTPException(
                status_code=500,
                detail="Внутренняя ошибка: координаты не определены после геокодинга"
            )

        target_driver_id = driver_id if driver_id is not None else dto.driver_id
        logger.info("creating_order", 
                    driver_id=target_driver_id, 
                    pickup_addr=dto.pickup_address,
                    pickup_coords=(dto.pickup_lat, dto.pickup_lon))
        
        # 1. Запрос к RoutingService для получения дистанции и времени
        origin = (dto.pickup_lon, dto.pickup_lat)  # type: ignore
        destination = (dto.dropoff_lon, dto.dropoff_lat)  # type: ignore
        
        
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
                        workflow = OrderWorkflowService(self.uow, routing_service=self.routing_service)
                        await workflow.assign_driver(order.id, driver_id)
                        
                        # Обновляем объект для ответа
                        async with self.uow:
                            order = await self.uow.orders.get(order.id)
                        
                        # Уведомляем водителя
                        if self.notification_service and order.driver_id:
                            await self.notification_service.notify_order_assigned(int(order.driver_id), order)
                
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
