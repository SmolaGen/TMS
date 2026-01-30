from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import AvailabilityType

class DriverAvailabilityBase(BaseModel):
    driver_id: int = Field(..., description="ID водителя")
    availability_type: AvailabilityType = Field(
        AvailabilityType.OTHER,
        description="Тип недоступности"
    )
    time_start: datetime = Field(..., description="Начало периода недоступности")
    time_end: datetime = Field(..., description="Конец периода недоступности")
    description: Optional[str] = Field(None, description="Описание/причина недоступности")

class DriverAvailabilityCreate(DriverAvailabilityBase):
    pass

class DriverAvailabilityUpdate(BaseModel):
    availability_type: Optional[AvailabilityType] = Field(
        None,
        description="Тип недоступности"
    )
    time_start: Optional[datetime] = Field(None, description="Начало периода недоступности")
    time_end: Optional[datetime] = Field(None, description="Конец периода недоступности")
    description: Optional[str] = Field(None, description="Описание/причина недоступности")

class DriverAvailabilityResponse(DriverAvailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
