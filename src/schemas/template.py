from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.database.models import OrderPriority

class OrderTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Название шаблона")
    contractor_id: Optional[int] = Field(None, description="ID подрядчика")
    priority: OrderPriority = OrderPriority.NORMAL
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта погрузки")
    pickup_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота погрузки")
    dropoff_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта выгрузки")
    dropoff_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота выгрузки")
    pickup_address: Optional[str] = Field(None, max_length=500, description="Адрес погрузки")
    dropoff_address: Optional[str] = Field(None, max_length=500, description="Адрес выгрузки")
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_telegram_id: Optional[int] = Field(None, description="Telegram ID заказчика")
    customer_webhook_url: Optional[str] = Field(None, max_length=500, description="URL вебхука заказчика")
    price: Optional[Decimal] = Field(None, description="Стоимость заказа по умолчанию")
    comment: Optional[str] = Field(None, description="Комментарий к шаблону")
    is_active: bool = Field(True, description="Флаг активности шаблона")

    @model_validator(mode='after')
    def validate_coordinates_or_address(self) -> 'OrderTemplateBase':
        """Проверяем, что указаны либо координаты, либо адрес для обеих точек."""
        if not (self.pickup_lat and self.pickup_lon) and not self.pickup_address:
            raise ValueError("Необходимо указать либо координаты погрузки, либо адрес")

        if not (self.dropoff_lat and self.dropoff_lon) and not self.dropoff_address:
            raise ValueError("Необходимо указать либо координаты выгрузки, либо адрес")

        return self

class OrderTemplateCreate(OrderTemplateBase):
    pass

class OrderTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название шаблона")
    contractor_id: Optional[int] = Field(None, description="ID подрядчика")
    priority: Optional[OrderPriority] = None
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта погрузки")
    pickup_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота погрузки")
    dropoff_lat: Optional[float] = Field(None, ge=-90, le=90, description="Широта выгрузки")
    dropoff_lon: Optional[float] = Field(None, ge=-180, le=180, description="Долгота выгрузки")
    pickup_address: Optional[str] = Field(None, max_length=500, description="Адрес погрузки")
    dropoff_address: Optional[str] = Field(None, max_length=500, description="Адрес выгрузки")
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_telegram_id: Optional[int] = Field(None, description="Telegram ID заказчика")
    customer_webhook_url: Optional[str] = Field(None, max_length=500, description="URL вебхука заказчика")
    price: Optional[Decimal] = Field(None, description="Стоимость заказа по умолчанию")
    comment: Optional[str] = Field(None, description="Комментарий к шаблону")
    is_active: Optional[bool] = Field(None, description="Флаг активности шаблона")

class OrderTemplateResponse(OrderTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

class GenerateOrdersRequest(BaseModel):
    """Запрос на генерацию заказов из шаблона."""
    date_from: datetime = Field(..., description="Начало периода генерации")
    date_until: datetime = Field(..., description="Конец периода генерации")
    driver_id: Optional[int] = Field(None, description="ID водителя для назначения (опционально)")
