from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import OrderStatus, OrderPriority

class OrderCreate(BaseModel):
    """Схема создания заказа."""
    driver_id: Optional[int] = Field(None, description="ID водителя (может быть пустым)")
    contractor_id: Optional[int] = Field(None, description="ID подрядчика")
    external_id: Optional[str] = Field(None, description="ID заказа во внешней системе")
    time_start: datetime = Field(..., description="Начало интервала выполнения")
    time_end: Optional[datetime] = Field(None, description="Конец интервала выполнения (если пусто - рассчитается по маршруту)")
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lon: float = Field(..., ge=-180, le=180)
    dropoff_lat: float = Field(..., ge=-90, le=90)
    dropoff_lon: float = Field(..., ge=-180, le=180)
    priority: OrderPriority = OrderPriority.NORMAL
    comment: Optional[str] = None
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None

class OrderMoveRequest(BaseModel):
    """Схема для Drag-and-Drop (изменение времени и водителя)."""
    new_time_start: datetime
    new_time_end: datetime
    new_driver_id: Optional[int] = None

class OrderResponse(BaseModel):
    """Схема ответа с данными заказа."""
    id: int
    driver_id: Optional[int]
    driver_name: Optional[str] = None
    contractor_id: Optional[int] = None
    external_id: Optional[str] = None
    status: OrderStatus
    priority: OrderPriority
    pickup_lat: Optional[float] = None
    pickup_lon: Optional[float] = None
    dropoff_lat: Optional[float] = None
    dropoff_lon: Optional[float] = None
    time_start: Optional[datetime] = None  # Извлекается из tstzrange
    time_end: Optional[datetime] = None    # Извлекается из tstzrange
    comment: Optional[str]
    pickup_address: Optional[str]
    dropoff_address: Optional[str]
    customer_phone: Optional[str]
    customer_name: Optional[str]
    price: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    # Lifecycle timestamps
    arrived_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    route_geometry: Optional[str] = None  # Polyline для отрисовки на карте

    model_config = ConfigDict(from_attributes=True)

class LocationUpdate(BaseModel):
    """Схема обновления координат водителем."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    status: Optional[str] = "available"
    timestamp: Optional[datetime] = None
