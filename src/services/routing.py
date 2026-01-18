from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any
import httpx
from pydantic import BaseModel, Field
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class OSRMUnavailableError(Exception):
    """Custom exception for when the OSRM service is unavailable."""
    pass

class RouteNotFoundError(Exception):
    """Custom exception for when a route cannot be found by OSRM."""
    pass

class Coordinate(BaseModel):
    """Represents a geographical coordinate (longitude, latitude)."""
    lon: float
    lat: float

    def to_osrm_format(self) -> str:
        """Converts coordinate to OSRM string format 'longitude,latitude'."""
        return f"{self.lon},{self.lat}"

class RouteResult(BaseModel):
    """Result of a routing request."""
    distance_km: float
    duration_minutes: float
    route_geometry: Optional[str] = None  # GeoJSON LineString or similar encoded polyline

class PriceResult(BaseModel):
    """Result of a price calculation based on routing."""
    total_price: Decimal
    base_price: Decimal
    price_per_km: Decimal
    distance_km: float

class RoutingService:
    """
    Service for interacting with the OSRM routing engine.
    Provides methods to calculate routes and estimate prices.
    """
    def __init__(
        self,
        osrm_base_url: str = settings.OSRM_URL,
        price_base: Decimal = settings.PRICE_BASE,
        price_per_km: Decimal = settings.PRICE_PER_KM,
    ):
        self.osrm_base_url = osrm_base_url
        self.price_base = price_base
        self.price_per_km = price_per_km
        self.http_client = httpx.AsyncClient(base_url=self.osrm_base_url, timeout=10.0)

    async def _make_osrm_request(self, endpoint: str, coordinates: List[Coordinate]) -> Dict[str, Any]:
        """
        Makes a request to the OSRM service.
        Args:
            endpoint: OSRM endpoint (e.g., "route", "table").
            coordinates: List of Coordinate objects for the request.
        Returns:
            JSON response from OSRM.
        Raises:
            OSRMUnavailableError: If OSRM service is unreachable or returns an error.
            RouteNotFoundError: If OSRM cannot find a route.
        """
        coords_str = ";".join([coord.to_osrm_format() for coord in coordinates])
        url = f"/{endpoint}/v1/driving/{coords_str}"
        
        try:
            response = await self.http_client.get(url, params={"overview": "full", "geometries": "geojson"})
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "Ok":
                return data
            elif data.get("code") == "NoRoute":
                raise RouteNotFoundError(f"OSRM could not find a route for coordinates: {coords_str}")
            else:
                raise OSRMUnavailableError(f"OSRM error: {data.get('code', 'Unknown')} - {data.get('message', 'No message')}")
        except httpx.RequestError as e:
            logger.error(f"OSRM request failed: {e}")
            raise OSRMUnavailableError(f"OSRM service is unreachable: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"OSRM HTTP error: {e.response.status_code} - {e.response.text}")
            raise OSRMUnavailableError(f"OSRM service returned HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during OSRM request: {e}")
            raise OSRMUnavailableError(f"Unexpected error during OSRM request: {e}")

    async def get_route(self, origin: Coordinate, destination: Coordinate) -> RouteResult:
        """
        Calculates a route between two points.
        Args:
            origin: Starting point.
            destination: Ending point.
        Returns:
            RouteResult containing distance, duration, and route geometry.
        """
        data = await self._make_osrm_request("route", [origin, destination])
        
        if not data.get("routes"):
            raise RouteNotFoundError("OSRM returned no routes.")

        route = data["routes"][0]
        distance_meters = route["distance"]
        duration_seconds = route["duration"]
        geometry = route.get("geometry") # GeoJSON LineString

        return RouteResult(
            distance_km=round(distance_meters / 1000, 2),
            duration_minutes=round(duration_seconds / 60, 2),
            route_geometry=geometry
        )

    async def calculate_price(self, origin: Coordinate, destination: Coordinate) -> PriceResult:
        """
        Calculates the price for a route based on distance.
        Args:
            origin: Starting point.
            destination: Ending point.
        Returns:
            PriceResult containing total price, base price, price per km, and distance.
        """
        route_result = await self.get_route(origin, destination)
        
        total_price = self.price_base + (self.price_per_km * Decimal(str(route_result.distance_km)))
        
        return PriceResult(
            total_price=round(total_price, 2),
            base_price=self.price_base,
            price_per_km=self.price_per_km,
            distance_km=route_result.distance_km
        )

    async def close(self):
        """Closes the underlying HTTP client session."""
        await self.http_client.aclose()
