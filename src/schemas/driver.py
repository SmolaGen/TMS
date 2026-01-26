from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import DriverStatus

class DriverBase(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: bool = Field(True, description="Флаг активности водителя")

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[DriverStatus] = None
    is_active: Optional[bool] = None
    onboarding_completed: Optional[bool] = Field(None, description="Завершён ли онбординг")
    onboarding_step: Optional[str] = Field(None, max_length=50, description="Текущий шаг онбординга")
    onboarding_skipped: Optional[bool] = Field(None, description="Пропустил ли онбординг")

class DriverResponse(DriverBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DriverStatus
    is_online: bool = Field(False, description="Реально онлайн (отправлял геолокацию < 5 мин)")
    onboarding_completed: bool = Field(False, description="Завершён ли онбординг")
    onboarding_step: Optional[str] = Field(None, description="Текущий шаг онбординга")
    onboarding_skipped: bool = Field(False, description="Пропустил ли онбординг")
    created_at: datetime
    updated_at: datetime

class DriverStatsResponse(BaseModel):
    """Статистика водителя за период."""
    driver_id: int
    period_days: int
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    active_orders: int
    completion_rate: float  # Процент завершённых
    total_revenue: float    # Сумма заработка
    total_distance_km: float
    
    model_config = ConfigDict(from_attributes=True)


class DriverWithStats(DriverResponse):
    """Водитель с краткой статистикой."""
    orders_today: int = 0
    orders_this_week: int = 0
    last_location_at: datetime | None = None
