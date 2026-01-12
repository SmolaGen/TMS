from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.database.models import OrderPriority, OrderStatus

class ContractorOrderCreate(BaseModel):
    """Схема создания заказа от подрядчика."""
    external_id: str = Field(..., description="ID заказа во внешней системе")
    pickup_address: str = Field(..., description="Адрес подачи")
    pickup_lat: float
    pickup_lon: float
    dropoff_address: str = Field(..., description="Адрес назначения")
    dropoff_lat: float
    dropoff_lon: float
    time_start: datetime = Field(..., description="Время подачи")
    priority: OrderPriority = OrderPriority.NORMAL
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    comment: Optional[str] = None

class ContractorOrdersRequest(BaseModel):
    """Схема пакетного создания заказов."""
    orders: List[ContractorOrderCreate]

class ContractorOrderResponse(BaseModel):
    """Схема ответа по заказу для подрядчика."""
    id: int
    external_id: str
    status: OrderStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ContractorBatchResponse(BaseModel):
    """Схема ответа на пакетное создание."""
    processed: int
    created: int
    errors: List[dict] = []
