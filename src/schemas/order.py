from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.database.models import OrderStatus, OrderPriority

class OrderCreate(BaseModel):
    """Схема создания заказа."""
    driver_id: Optional[int] = Field(None, description="ID водителя (может быть пустым)")
    contractor_id: Optional[int] = Field(None, description="ID подрядчика")
    external_id: Optional[str] = Field(None, description="ID заказа во внешней системе")
    time_start: datetime = Field(..., description="Начало интервала выполнения")
    time_end: Optional[datetime] = Field(None, description="Конец интервала выполнения (если пусто - рассчитается по маршруту)")
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта погрузки")
    pickup_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота погрузки")
    dropoff_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта выгрузки")
    dropoff_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота выгрузки")
    priority: OrderPriority = OrderPriority.NORMAL
    comment: Optional[str] = None
    pickup_address: Optional[str] = Field(None, description="Адрес погрузки (обязателен, если нет координат)")
    dropoff_address: Optional[str] = Field(None, description="Адрес выгрузки (обязателен, если нет координат)")
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None

    @model_validator(mode='after')
    def validate_coordinates_or_address(self) -> 'OrderCreate':
        """Проверяем, что указаны либо координаты, либо адрес для обеих точек."""
        if not (self.pickup_lat and self.pickup_lon) and not self.pickup_address:
            raise ValueError("Необходимо указать либо координаты погрузки, либо адрес")
        
        if not (self.dropoff_lat and self.dropoff_lon) and not self.dropoff_address:
            raise ValueError("Необходимо указать либо координаты выгрузки, либо адрес")
        
        return self

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
    assigned_at: Optional[datetime] = None
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
