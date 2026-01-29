from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.order import OrderResponse
from src.schemas.availability import DriverAvailabilityResponse
from src.schemas.driver import DriverResponse

class ScheduleDayView(BaseModel):
    """Представление одного дня в календаре."""
    date: datetime = Field(..., description="Дата")
    orders: List[OrderResponse] = Field(default_factory=list, description="Заказы на этот день")
    available_drivers: List[int] = Field(default_factory=list, description="ID доступных водителей")
    unavailable_periods: List[DriverAvailabilityResponse] = Field(
        default_factory=list,
        description="Периоды недоступности водителей в этот день"
    )

class ScheduleViewResponse(BaseModel):
    """Ответ с данными календарного представления расписания."""
    date_from: datetime = Field(..., description="Начало периода")
    date_until: datetime = Field(..., description="Конец периода")
    days: List[ScheduleDayView] = Field(default_factory=list, description="Данные по дням")
    total_orders: int = Field(0, description="Общее количество заказов в периоде")
    total_drivers: int = Field(0, description="Общее количество водителей")

class DriverScheduleResponse(BaseModel):
    """Расписание конкретного водителя."""
    model_config = ConfigDict(from_attributes=True)

    driver: DriverResponse = Field(..., description="Данные водителя")
    date_from: datetime = Field(..., description="Начало периода")
    date_until: datetime = Field(..., description="Конец периода")
    orders: List[OrderResponse] = Field(default_factory=list, description="Заказы водителя в периоде")
    unavailable_periods: List[DriverAvailabilityResponse] = Field(
        default_factory=list,
        description="Периоды недоступности водителя"
    )

class CreateScheduledOrderRequest(BaseModel):
    """Запрос на создание запланированного заказа."""
    scheduled_date: datetime = Field(..., description="Запланированная дата выполнения")
    driver_id: Optional[int] = Field(None, description="ID водителя (может быть пустым)")
    contractor_id: Optional[int] = Field(None, description="ID подрядчика")
    external_id: Optional[str] = Field(None, description="ID заказа во внешней системе")
    time_start: datetime = Field(..., description="Начало интервала выполнения")
    time_end: Optional[datetime] = Field(None, description="Конец интервала выполнения")
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта погрузки")
    pickup_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота погрузки")
    dropoff_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта выгрузки")
    dropoff_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота выгрузки")
    pickup_address: Optional[str] = Field(None, description="Адрес погрузки")
    dropoff_address: Optional[str] = Field(None, description="Адрес выгрузки")
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    comment: Optional[str] = None
