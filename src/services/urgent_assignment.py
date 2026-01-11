import math
from typing import Optional, List, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Order, Driver, DriverStatus, OrderStatus
from src.services.location_manager import LocationManager
from src.core.logging import get_logger

logger = get_logger(__name__)

class UrgentAssignmentService:
    """
    Сервис для срочного автоматического назначения заказов.
    Ищет ближайшего свободного водителя в реальном времени.
    """
    def __init__(self, session: AsyncSession, location_manager: LocationManager):
        self.session = session
        self.location_manager = location_manager

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Расчет расстояния между двумя точками в км (Haversine)."""
        R = 6371  # Радиус Земли в км
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def find_nearest_driver(self, pickup_lat: float, pickup_lon: float, max_radius_km: float = 20.0) -> Optional[int]:
        """
        Найти ID ближайшего доступного водителя.
        """
        # 1. Получить всех доступных водителей
        query = select(Driver.id).where(
            Driver.status == DriverStatus.AVAILABLE,
            Driver.is_active == True
        )
        result = await self.session.execute(query)
        available_driver_ids = [r[0] for r in result.all()]
        
        if not available_driver_ids:
            return None

        # 2. Получить их последние позиции из Redis
        nearest_driver_id = None
        min_distance = float('inf')

        for driver_id in available_driver_ids:
            location = await self.location_manager.get_driver_location(driver_id)
            if not location:
                continue

            dist = self._haversine(pickup_lat, pickup_lon, location.latitude, location.longitude)
            if dist < min_distance and dist <= max_radius_km:
                min_distance = dist
                nearest_driver_id = driver_id

        return nearest_driver_id

    async def assign_urgent_order(self, order: Order) -> Optional[int]:
        """
        Авто-назначение для срочного заказа.
        """
        from src.database.repository import OrderRepository
        
        # Нам нужны координаты погрузки
        # В модели Order они хранятся как Geometry Point
        # Но у нас есть property pickup_lat, pickup_lon
        
        lat = order.pickup_lat
        lon = order.pickup_lon
        
        if lat is None or lon is None:
            logger.warning("urgent_order_missing_coords", order_id=order.id)
            return None

        driver_id = await self.find_nearest_driver(lat, lon)
        
        if driver_id:
            logger.info("urgent_assignment_found_driver", order_id=order.id, driver_id=driver_id)
            return driver_id
        
        logger.info("urgent_assignment_no_driver_found", order_id=order.id)
        return None
