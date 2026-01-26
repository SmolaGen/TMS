"""Pydantic schemas for Route Optimization API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from src.database.models import RouteOptimizationType, RouteStopType, RouteStatus


class Location(BaseModel):
    """Географические координаты."""
    lat: float = Field(..., ge=-90, le=90, description="Широта")
    lon: float = Field(..., ge=-180, le=180, description="Долгота")


class RouteOptimizeRequest(BaseModel):
    """Запрос на оптимизацию multi-stop маршрута."""
    driver_id: int = Field(..., description="ID водителя")
    order_ids: List[int] = Field(..., min_length=1, description="Список ID заказов для включения в маршрут")
    start_location: Optional[Location] = Field(None, description="Начальная точка маршрута (если не указана, используется текущее положение водителя)")
    optimize_for: RouteOptimizationType = Field(
        default=RouteOptimizationType.TIME,
        description="Критерий оптимизации (time - по времени, distance - по расстоянию)"
    )


class RoutePointSchema(BaseModel):
    """Схема точки маршрута."""
    id: int
    sequence: int
    location: Location = Field(..., description="Координаты точки")
    address: Optional[str] = None
    order_id: Optional[int] = None
    stop_type: RouteStopType
    estimated_arrival: Optional[datetime] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RouteOptimizeResponse(BaseModel):
    """Ответ с оптимизированным маршрутом."""
    route_id: int = Field(..., description="ID созданного маршрута")
    driver_id: int = Field(..., description="ID водителя")
    status: RouteStatus = Field(..., description="Статус маршрута")
    optimization_type: RouteOptimizationType = Field(..., description="Тип оптимизации")

    # Метрики маршрута
    total_distance_meters: float = Field(..., description="Общая дистанция маршрута в метрах")
    total_distance_km: float = Field(..., description="Общая дистанция маршрута в километрах")
    total_duration_seconds: float = Field(..., description="Общее время маршрута в секундах")
    total_duration_minutes: float = Field(..., description="Общее время маршрута в минутах")

    # Точки маршрута в оптимизированном порядке
    points: List[RoutePointSchema] = Field(..., description="Упорядоченный список точек маршрута")

    # Временные метки
    created_at: datetime = Field(..., description="Время создания маршрута")
    started_at: Optional[datetime] = Field(None, description="Время начала выполнения")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")

    model_config = ConfigDict(from_attributes=True)


class RouteRebuildRequest(BaseModel):
    """Запрос на принудительное перестроение маршрута."""
    reason: Optional[str] = Field(None, description="Причина перестроения")


class RouteRebuildResponse(BaseModel):
    """Ответ после перестроения маршрута."""
    route_id: int = Field(..., description="ID обновлённого маршрута")
    previous_status: RouteStatus = Field(..., description="Предыдущий статус")
    new_status: RouteStatus = Field(..., description="Новый статус")
    points_count: int = Field(..., description="Количество точек в маршруте")
    total_distance_meters: float = Field(..., description="Новая дистанция в метрах")
    total_duration_seconds: float = Field(..., description="Новое время в секундах")
    rebuild_time_seconds: float = Field(..., description="Время перестроения в секундах")
    created_at: datetime = Field(..., description="Время последнего обновления")

    model_config = ConfigDict(from_attributes=True)
