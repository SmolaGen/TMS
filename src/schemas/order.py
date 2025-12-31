from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import OrderStatus, OrderPriority

class OrderCreate(BaseModel):
    """Схема создания заказа."""
    driver_id: Optional[int] = Field(None, description="ID водителя (может быть пустым)")
    time_start: datetime = Field(..., description="Начало интервала выполнения")
    time_end: datetime = Field(..., description="Конец интервала выполнения")
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lon: float = Field(..., ge=-180, le=180)
    dropoff_lat: float = Field(..., ge=-90, le=90)
    dropoff_lon: float = Field(..., ge=-180, le=180)
    priority: OrderPriority = OrderPriority.NORMAL
    comment: Optional[str] = None

class OrderMoveRequest(BaseModel):
    """Схема для Drag-and-Drop (изменение времени)."""
    new_time_start: datetime
    new_time_end: datetime

class OrderResponse(BaseModel):
    """Схема ответа с данными заказа."""
    id: int
    driver_id: Optional[int]
    status: OrderStatus
    priority: OrderPriority
    time_start: Optional[datetime] = None  # Извлекается из tstzrange
    time_end: Optional[datetime] = None    # Извлекается из tstzrange
    
    # Данные маршрута и ценообразования
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    price: Optional[float] = None  # Decimal конвертируется в float для JSON
    
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Lifecycle timestamps
    arrived_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LocationUpdate(BaseModel):
    """Схема обновления координат водителем."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    status: Optional[str] = "available"
    timestamp: Optional[datetime] = None
