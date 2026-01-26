"""
Тесты совместимости frontend и backend типов данных.
Эти тесты проверяют, что данные, отправляемые из frontend,
могут быть валидированы backend Pydantic схемами.
"""
import pytest
from src.schemas.notification import NotificationPreferenceCreate, NotificationPreferenceUpdate
from pydantic import ValidationError


def test_notification_type_frontend_backend_compatibility():
    """Проверка что frontend типы уведомлений совместимы с backend."""
    # Backend использует эти типы (из models.py):
    # new_order, status_change, system_alert, driver_assignment, order_completion

    # Этот запрос должен пройти валидацию:
    valid_data = {
        "driver_id": 1,
        "notification_type": "new_order",
        "channel": "telegram",
        "frequency": "instant",
        "is_enabled": True
    }
    preference = NotificationPreferenceCreate(**valid_data)
    assert preference.notification_type.value == "new_order"

    # Эти типы из frontend должны вызывать ошибку:
    invalid_types = [
        "order_status_change",  # frontend использует, но backend не знает
        "order_assigned",
        "order_cancelled",
        "driver_location",
    ]

    for invalid_type in invalid_types:
        with pytest.raises(ValidationError):
            NotificationPreferenceCreate(
                driver_id=1,
                notification_type=invalid_type,
                channel="telegram",
                frequency="instant",
                is_enabled=True
            )


def test_notification_frequency_frontend_backend_compatibility():
    """Проверка что frontend частота уведомлений совместима с backend."""
    # Backend ожидает "instant", не "immediate"

    # Этот запрос должен пройти валидацию:
    valid_data = {
        "driver_id": 1,
        "notification_type": "new_order",
        "channel": "telegram",
        "frequency": "instant",  # Правильное значение
        "is_enabled": True
    }
    preference = NotificationPreferenceCreate(**valid_data)
    assert preference.frequency.value == "instant"

    # "immediate" (frontend старое значение) должно вызывать ошибку:
    with pytest.raises(ValidationError):
        NotificationPreferenceCreate(
            driver_id=1,
            notification_type="new_order",
            channel="telegram",
            frequency="immediate",  # Неправильное значение
            is_enabled=True
        )


def test_all_backend_types_are_valid():
    """Проверка что все backend типы проходят валидацию."""
    backend_types = [
        "new_order",
        "status_change",
        "system_alert",
        "driver_assignment",
        "order_completion"
    ]

    backend_channels = ["telegram", "email", "in_app", "push"]
    backend_frequencies = ["instant", "hourly", "daily", "disabled"]

    for ntype in backend_types:
        for channel in backend_channels:
            for freq in backend_frequencies:
                data = {
                    "driver_id": 1,
                    "notification_type": ntype,
                    "channel": channel,
                    "frequency": freq,
                    "is_enabled": True
                }
                # Не должно вызывать ошибок
                preference = NotificationPreferenceCreate(**data)
                assert preference.notification_type.value == ntype
                assert preference.channel.value == channel
                assert preference.frequency.value == freq


def test_notification_preference_update_validation():
    """Проверка валидации для обновления настроек уведомлений."""
    # Обновление с правильными типами должно работать:
    valid_update = {
        "channel": "email",
        "frequency": "daily",
        "is_enabled": False
    }
    update = NotificationPreferenceUpdate(**valid_update)
    assert update.channel.value == "email"
    assert update.frequency.value == "daily"

    # Обновление с неправильной частотой должно падать:
    with pytest.raises(ValidationError):
        NotificationPreferenceUpdate(
            frequency="immediate"  # Неправильное значение
        )

    # Обновление с неправильным типом уведомления:
    with pytest.raises(ValidationError):
        NotificationPreferenceUpdate(
            notification_type="order_status_change"  # Неправильное значение
        )
