from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import DriverStatus

class DriverBase(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[DriverStatus] = None

class DriverResponse(DriverBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DriverStatus
    created_at: datetime
    updated_at: datetime
