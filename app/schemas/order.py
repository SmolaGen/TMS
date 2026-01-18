from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.order import OrderStatus

class OrderBase(BaseModel):
    start_location: str
    end_location: str
    price: float
    status: Optional[OrderStatus] = OrderStatus.PENDING

class OrderCreate(OrderBase):
    client_id: int

class OrderUpdate(OrderBase):
    status: Optional[OrderStatus] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    price: Optional[float] = None
    driver_id: Optional[int] = None # Allow updating driver_id

class OrderInDB(OrderBase):
    id: int
    client_id: int
    driver_id: Optional[int] = None # Include driver_id in response schema
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OrderAssignDriver(BaseModel):
    driver_id: int
