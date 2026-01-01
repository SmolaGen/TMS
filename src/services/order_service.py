from datetime import timedelta
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, OrderStatus
from src.schemas.order import OrderCreate, OrderResponse, OrderMoveRequest
from src.services.routing import RoutingService, OSRMUnavailableError, RouteNotFoundError
from src.services.order_workflow import OrderStateMachine
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
        routing_service: RoutingService
    ):
        self.uow = uow
        self.routing_service = routing_service

    def _get_sm(self, order: Order) -> OrderStateMachine:
        """Создаёт экземпляр машины состояний для заказа."""
        return OrderStateMachine(order)

    async def create_order(self, dto: OrderCreate, driver_id: Optional[int] = None) -> OrderResponse:
        """
        Создаёт новый заказ с автоматическим расчётом цены и времени.
        """
        target_driver_id = driver_id if driver_id is not None else dto.driver_id
        logger.info("creating_order", driver_id=target_driver_id, pickup=(dto.pickup_lat, dto.pickup_lon))
        
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
            # Превращаем координаты в WKT для PostGIS
            pickup_wkt = f"SRID=4326;POINT({dto.pickup_lon} {dto.pickup_lat})"
            dropoff_wkt = f"SRID=4326;POINT({dto.dropoff_lon} {dto.dropoff_lat})"
            
            order = Order(
                driver_id=target_driver_id,
                status=OrderStatus.ASSIGNED if target_driver_id else OrderStatus.PENDING,
                priority=dto.priority,
                time_range=time_range,
                pickup_location=pickup_wkt,
                dropoff_location=dropoff_wkt,
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
            except IntegrityError as e:
                # Обработка Exclusion Constraint: no_driver_time_overlap
                error_msg = str(e).lower()
                if "no_driver_time_overlap" in error_msg:
                    logger.warning("order_overlap_detected", driver_id=target_driver_id, time_range=time_range)
                    raise HTTPException(
                        status_code=409, 
                        detail=f"Водитель #{target_driver_id} уже занят в указанный интервал времени ({time_start.strftime('%H:%M')} - {time_end.strftime('%H:%M')})"
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

    async def get_orders_list(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[OrderResponse]:
        """Получает список заказов с опциональной фильтрацией по времени."""
        async with self.uow:
            orders = await self.uow.orders.get_all(start_date=start_date, end_date=end_date)
            return [OrderResponse.model_validate(o) for o in orders]

    async def move_order(self, order_id: int, dto: OrderMoveRequest) -> Optional[OrderResponse]:
        """
        Изменяет время выполнения заказа (Drag-and-Drop).
        """
        logger.info("moving_order", order_id=order_id, new_start=dto.new_time_start)
        
        async with self.uow:
            order = await self.uow.orders.get(order_id)
            if not order:
                return None
            
            # Обновляем интервал
            new_range = (dto.new_time_start, dto.new_time_end)
            order.time_range = new_range
            
            try:
                await self.uow.commit()
                logger.info("order_moved", order_id=order_id, new_range=new_range)
                return OrderResponse.model_validate(order)
            except IntegrityError as e:
                error_msg = str(e).lower()
                if "no_driver_time_overlap" in error_msg:
                    logger.warning("order_overlap_on_move", order_id=order_id, driver_id=order.driver_id)
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "time_overlap", "message": f"Водитель #{order.driver_id} занят в новый интервал времени"}
                    )
                raise HTTPException(status_code=500, detail="Ошибка базы данных при перемещении заказа")
