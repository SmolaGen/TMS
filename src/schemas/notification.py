from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.database.models import NotificationType, NotificationChannel, NotificationFrequency


class NotificationPreferenceBase(BaseModel):
    """Базовая схема настроек уведомлений."""
    notification_type: NotificationType = Field(..., description="Тип уведомления")
    channel: NotificationChannel = Field(..., description="Канал доставки уведомления")
    frequency: NotificationFrequency = Field(..., description="Частота отправки уведомлений")
    is_enabled: bool = Field(True, description="Включена ли настройка")


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Схема для создания настройки уведомлений."""
    driver_id: int = Field(..., description="ID водителя (пользователя)")


class NotificationPreferenceUpdate(BaseModel):
    """Схема для обновления настройки уведомлений."""
    notification_type: Optional[NotificationType] = Field(None, description="Тип уведомления")
    channel: Optional[NotificationChannel] = Field(None, description="Канал доставки уведомления")
    frequency: Optional[NotificationFrequency] = Field(None, description="Частота отправки уведомлений")
    is_enabled: Optional[bool] = Field(None, description="Включена ли настройка")


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Схема для ответа с настройкой уведомлений."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    driver_id: int
    created_at: datetime
    updated_at: datetime
