from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from src.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationPreferenceCreate,
)
from src.database.models import Driver, NotificationType, NotificationChannel, NotificationFrequency
from src.services.notification_preferences_service import NotificationPreferencesService
from src.api.dependencies import (
    get_notification_preferences_service,
    get_current_driver,
)

router = APIRouter()


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def get_my_preferences(
    current_driver: Driver = Depends(get_current_driver),
    preferences_service: NotificationPreferencesService = Depends(
        get_notification_preferences_service
    ),
):
    """
    Получить все настройки уведомлений текущего водителя.
    """
    preferences = await preferences_service.get_driver_preferences(
        driver_id=current_driver.id
    )
    return preferences


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preference(
    notification_type: NotificationType,
    channel: NotificationChannel,
    data: NotificationPreferenceUpdate,
    current_driver: Driver = Depends(get_current_driver),
    preferences_service: NotificationPreferencesService = Depends(
        get_notification_preferences_service
    ),
):
    """
    Обновить настройку уведомлений для указанного типа и канала.

    Если настройка не существует, она будет создана.
    """
    # Пытаемся найти существующую настройку
    existing = await preferences_service.get_preference_by_type_and_channel(
        driver_id=current_driver.id,
        notification_type=notification_type,
        channel=channel,
    )

    if existing:
        # Обновляем существующую
        updated = await preferences_service.update_preference(
            preference_id=existing.id, data=data
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Не удалось обновить настройку",
            )
        return updated
    else:
        # Создаем новую настройку
        create_data = NotificationPreferenceCreate(
            driver_id=current_driver.id,
            notification_type=notification_type,
            channel=channel,
            frequency=data.frequency or NotificationFrequency.INSTANT,
            is_enabled=data.is_enabled if data.is_enabled is not None else True,
        )
        created = await preferences_service.create_preference(data=create_data)
        return created


@router.post("/preferences/preset", response_model=List[NotificationPreferenceResponse])
async def apply_preset(
    preset: str,
    current_driver: Driver = Depends(get_current_driver),
    preferences_service: NotificationPreferencesService = Depends(
        get_notification_preferences_service
    ),
):
    """
    Применить пресет настроек уведомлений.

    Доступные пресеты:
    - minimal: Только важные уведомления в Telegram
    - standard: Все уведомления в Telegram
    - maximum: Все уведомления во всех каналах
    """
    try:
        preferences = await preferences_service.set_preset(
            driver_id=current_driver.id, preset=preset
        )
        return preferences
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
