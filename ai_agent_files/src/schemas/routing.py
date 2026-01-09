"""Pydantic schemas for Routing API."""
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Request for route calculation."""
    origin_lat: float = Field(..., description="Latitude начальной точки")
    origin_lon: float = Field(..., description="Longitude начальной точки")
    destination_lat: float = Field(..., description="Latitude конечной точки")
    destination_lon: float = Field(..., description="Longitude конечной точки")
    with_geometry: bool = Field(default=True, description="Включить polyline геометрию")


class RouteResponse(BaseModel):
    """Response with route details."""
    distance_meters: float = Field(..., description="Дистанция в метрах")
    distance_km: float = Field(..., description="Дистанция в километрах")
    duration_seconds: float = Field(..., description="Время в пути (секунды)")
    duration_minutes: float = Field(..., description="Время в пути (минуты)")
    geometry: Optional[str] = Field(None, description="Polyline геометрия для отрисовки")
    
    # Стоимость
    base_price: Decimal = Field(..., description="Базовая ставка")
    distance_price: Decimal = Field(..., description="Стоимость за километры")
    total_price: Decimal = Field(..., description="Итоговая стоимость")
