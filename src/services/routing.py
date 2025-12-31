import re
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional, Tuple
import httpx

from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RouteResult:
    """Результат расчёта маршрута."""
    distance_meters: float      # Дистанция в метрах
    duration_seconds: float     # Время в пути (секунды)
    geometry: Optional[str] = None  # Polyline геометрия (для отрисовки на карте)


@dataclass
class PriceResult:
    """Результат расчёта стоимости."""
    distance_km: Decimal        # Дистанция в километрах
    base_price: Decimal         # Базовая ставка
    distance_price: Decimal     # Стоимость за километры
    total_price: Decimal        # Итоговая стоимость


class RoutingServiceError(Exception):
    """Базовое исключение сервиса маршрутизации."""
    pass


class RouteNotFoundError(RoutingServiceError):
    """Маршрут не найден (нет дороги между точками)."""
    pass


class OSRMUnavailableError(RoutingServiceError):
    """OSRM сервер недоступен."""
    pass


class RoutingService:
    """Сервис маршрутизации и расчёта стоимости."""
    
    def __init__(
        self,
        osrm_url: str = settings.OSRM_URL,
        price_base: Decimal = settings.PRICE_BASE,
        price_per_km: Decimal = settings.PRICE_PER_KM,
        timeout: float = settings.OSRM_TIMEOUT
    ):
        self.osrm_url = osrm_url.rstrip("/")
        self.price_base = price_base
        self.price_per_km = price_per_km
        self.timeout = timeout
    
    async def get_route(
        self,
        origin: Tuple[float, float],       # (lon, lat)
        destination: Tuple[float, float],  # (lon, lat)
        with_geometry: bool = False
    ) -> RouteResult:
        """
        Рассчитывает маршрут между двумя точками через OSRM.
        
        Args:
            origin: Координаты начала (lon, lat)
            destination: Координаты конца (lon, lat)
            with_geometry: Включить polyline геометрию
            
        Returns:
            RouteResult с дистанцией и временем
            
        Raises:
            RouteNotFoundError: Маршрут не найден
            OSRMUnavailableError: OSRM недоступен
        """
        # Формат: lon,lat
        coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        overview = "full" if with_geometry else "false"
        url = f"{self.osrm_url}/route/v1/driving/{coords}?overview={overview}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            logger.error(f"OSRM request failed: {str(e)}")
            raise OSRMUnavailableError(f"OSRM service at {self.osrm_url} is unavailable") from e
        except Exception as e:
            logger.exception("Unexpected error during OSRM request")
            raise RoutingServiceError(f"Failed to fetch route: {str(e)}") from e

        code = data.get("code")
        if code != "Ok":
            logger.warning(f"OSRM returned error code: {code} for points {coords}")
            if code in ("NoRoute", "NoSegment"):
                raise RouteNotFoundError(f"No route found between points: {coords}")
            raise RoutingServiceError(f"OSRM error: {code}")

        routes = data.get("routes", [])
        if not routes:
            raise RouteNotFoundError(f"No routes in OSRM response for {coords}")

        best_route = routes[0]
        return RouteResult(
            distance_meters=float(best_route["distance"]),
            duration_seconds=float(best_route["duration"]),
            geometry=best_route.get("geometry") if with_geometry else None
        )
    
    def calculate_price(
        self,
        distance_meters: float
    ) -> PriceResult:
        """
        Рассчитывает стоимость доставки по дистанции.
        
        Args:
            distance_meters: Дистанция в метрах
            
        Returns:
            PriceResult с детализацией стоимости
        """
        # Конвертация в км с округлением до 2 знаков для расчета
        dist_km = Decimal(str(distance_meters / 1000)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        dist_price = (dist_km * self.price_per_km).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        total = (self.price_base + dist_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        return PriceResult(
            distance_km=dist_km,
            base_price=self.price_base,
            distance_price=dist_price,
            total_price=total
        )
    
    async def get_route_with_price(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> Tuple[RouteResult, PriceResult]:
        """
        Комбинированный метод: маршрут + стоимость.
        """
        route = await self.get_route(origin, destination)
        price = self.calculate_price(route.distance_meters)
        return route, price
    
    @staticmethod
    def parse_geometry_point(wkt_or_ewkt: str) -> Tuple[float, float]:
        """
        Парсит WKT/EWKT POINT в кортеж (lon, lat).
        Поддерживает: 
        - POINT(131.8869 43.1150)
        - SRID=4326;POINT(131.8869 43.1150)
        """
        if not wkt_or_ewkt:
            raise ValueError("Empty geometry string")
            
        # Ищем числа в скобках POINT(...)
        match = re.search(r"POINT\s*\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)", wkt_or_ewkt, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid POINT format: {wkt_or_ewkt}")
            
        lon = float(match.group(1))
        lat = float(match.group(2))
        return lon, lat
