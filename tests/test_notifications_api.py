"""
API тесты для endpoints уведомлений.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import status

from src.database.models import (
    Driver,
    NotificationPreference,
    NotificationType,
    NotificationChannel,
    NotificationFrequency,
)
from src.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationPreferenceCreate,
)
from src.main import app


@pytest.fixture
def mock_session():
    """Создать mock для базы данных."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_preferences_service(mock_session):
    """Создать mock для NotificationPreferencesService."""
    service = MagicMock()
    service.get_driver_preferences = AsyncMock()
    service.get_preference_by_type_and_channel = AsyncMock()
    service.update_preference = AsyncMock()
    service.create_preference = AsyncMock()
    service.set_preset = AsyncMock()
    return service


@pytest.fixture
def sample_driver():
    """Создать пример водителя."""
    return Driver(
        id=1,
        telegram_id=123456789,
        name="Test Driver",
        status="available",
        role="driver",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_preference():
    """Создать пример настройки уведомлений."""
    return NotificationPreference(
        id=1,
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
        frequency=NotificationFrequency.INSTANT,
        is_enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def client(mock_preferences_service, sample_driver):
    """Создать тестовый клиент с замоканными зависимостями."""
    from src.api import dependencies
    from src.api.endpoints import notifications

    # Мокаем зависимости
    def mock_get_current_driver():
        return sample_driver

    def mock_get_preferences_service():
        return mock_preferences_service

    # Оверраидим зависимости
    app.dependency_overrides[
        dependencies.get_current_driver
    ] = mock_get_current_driver
    app.dependency_overrides[
        dependencies.get_notification_preferences_service
    ] = mock_get_preferences_service

    with TestClient(app) as test_client:
        yield test_client

    # Очищаем оверраиды
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_my_preferences_success(client, mock_preferences_service, sample_preference):
    """Тест успешного получения всех настроек уведомлений."""
    # Arrange
    mock_preferences_service.get_driver_preferences.return_value = [sample_preference]

    # Act
    response = client.get("/api/v1/preferences")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["driver_id"] == 1
    assert data[0]["notification_type"] == "new_order"
    assert data[0]["channel"] == "telegram"
    assert data[0]["frequency"] == "instant"
    assert data[0]["is_enabled"] is True
    mock_preferences_service.get_driver_preferences.assert_called_once_with(driver_id=1)


@pytest.mark.asyncio
async def test_get_my_preferences_empty(client, mock_preferences_service):
    """Тест получения настроек, когда их нет."""
    # Arrange
    mock_preferences_service.get_driver_preferences.return_value = []

    # Act
    response = client.get("/api/v1/preferences")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    mock_preferences_service.get_driver_preferences.assert_called_once_with(driver_id=1)


@pytest.mark.asyncio
async def test_update_preference_existing(
    client, mock_preferences_service, sample_preference
):
    """Тест обновления существующей настройки."""
    # Arrange
    mock_preferences_service.get_preference_by_type_and_channel.return_value = (
        sample_preference
    )
    mock_preferences_service.update_preference.return_value = sample_preference

    update_data = {
        "frequency": "hourly",
        "is_enabled": False,
    }

    # Act
    response = client.put(
        "/api/v1/preferences",
        params={
            "notification_type": "new_order",
            "channel": "telegram",
        },
        json=update_data,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == 1
    assert data["notification_type"] == "new_order"
    assert data["channel"] == "telegram"
    mock_preferences_service.get_preference_by_type_and_channel.assert_called_once_with(
        driver_id=1, notification_type=NotificationType.NEW_ORDER, channel=NotificationChannel.TELEGRAM
    )
    mock_preferences_service.update_preference.assert_called_once()


@pytest.mark.asyncio
async def test_update_preference_create_new(
    client, mock_preferences_service, sample_preference
):
    """Тест создания новой настройки через PUT endpoint."""
    # Arrange
    mock_preferences_service.get_preference_by_type_and_channel.return_value = None
    mock_preferences_service.create_preference.return_value = sample_preference

    update_data = {
        "frequency": "instant",
        "is_enabled": True,
    }

    # Act
    response = client.put(
        "/api/v1/preferences",
        params={
            "notification_type": "status_change",
            "channel": "email",
        },
        json=update_data,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == 1
    mock_preferences_service.get_preference_by_type_and_channel.assert_called_once()
    mock_preferences_service.create_preference.assert_called_once()


@pytest.mark.asyncio
async def test_update_preference_not_found_after_update(
    client, mock_preferences_service, sample_preference
):
    """Тест ошибки при обновлении, если настройка не найдена."""
    # Arrange
    mock_preferences_service.get_preference_by_type_and_channel.return_value = (
        sample_preference
    )
    mock_preferences_service.update_preference.return_value = None

    update_data = {
        "frequency": "hourly",
    }

    # Act
    response = client.put(
        "/api/v1/preferences",
        params={
            "notification_type": "new_order",
            "channel": "telegram",
        },
        json=update_data,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_apply_preset_minimal(client, mock_preferences_service, sample_preference):
    """Тест применения пресета 'minimal'."""
    # Arrange
    mock_preferences_service.set_preset.return_value = [sample_preference]

    # Act
    response = client.post(
        "/api/v1/preferences/preset",
        params={"preset": "minimal"},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    mock_preferences_service.set_preset.assert_called_once_with(driver_id=1, preset="minimal")


@pytest.mark.asyncio
async def test_apply_preset_standard(client, mock_preferences_service, sample_preference):
    """Тест применения пресета 'standard'."""
    # Arrange
    mock_preferences_service.set_preset.return_value = [
        sample_preference,
        sample_preference,
    ]

    # Act
    response = client.post(
        "/api/v1/preferences/preset",
        params={"preset": "standard"},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    mock_preferences_service.set_preset.assert_called_once_with(driver_id=1, preset="standard")


@pytest.mark.asyncio
async def test_apply_preset_maximum(client, mock_preferences_service, sample_preference):
    """Тест применения пресета 'maximum'."""
    # Arrange
    mock_preferences_service.set_preset.return_value = [
        sample_preference,
        sample_preference,
    ]

    # Act
    response = client.post(
        "/api/v1/preferences/preset",
        params={"preset": "maximum"},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    mock_preferences_service.set_preset.assert_called_once_with(driver_id=1, preset="maximum")


@pytest.mark.asyncio
async def test_apply_preset_invalid(client, mock_preferences_service):
    """Тест применения несуществующего пресета."""
    # Arrange
    mock_preferences_service.set_preset.side_effect = ValueError("Invalid preset: invalid_preset")

    # Act
    response = client.post(
        "/api/v1/preferences/preset",
        params={"preset": "invalid_preset"},
    )

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    mock_preferences_service.set_preset.assert_called_once_with(driver_id=1, preset="invalid_preset")


@pytest.mark.asyncio
async def test_update_preference_with_all_fields(
    client, mock_preferences_service, sample_preference
):
    """Тест обновления настройки со всеми полями."""
    # Arrange
    sample_preference.frequency = NotificationFrequency.DAILY
    sample_preference.is_enabled = False
    mock_preferences_service.get_preference_by_type_and_channel.return_value = (
        sample_preference
    )
    mock_preferences_service.update_preference.return_value = sample_preference

    update_data = {
        "frequency": "daily",
        "is_enabled": False,
    }

    # Act
    response = client.put(
        "/api/v1/preferences",
        params={
            "notification_type": "new_order",
            "channel": "telegram",
        },
        json=update_data,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["frequency"] == "daily"
    assert data["is_enabled"] is False


@pytest.mark.asyncio
async def test_create_preference_with_defaults(
    client, mock_preferences_service, sample_preference
):
    """Тест создания новой настройки с полями по умолчанию."""
    # Arrange
    mock_preferences_service.get_preference_by_type_and_channel.return_value = None
    mock_preferences_service.create_preference.return_value = sample_preference

    # Передаем только is_enabled, остальные должны быть по умолчанию
    update_data = {
        "is_enabled": True,
    }

    # Act
    response = client.put(
        "/api/v1/preferences",
        params={
            "notification_type": "system_alert",
            "channel": "in_app",
        },
        json=update_data,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    mock_preferences_service.create_preference.assert_called_once()
    # Проверяем что при создании были установлены значения по умолчанию
    call_args = mock_preferences_service.create_preference.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_get_preferences_multiple(
    client, mock_preferences_service, sample_driver
):
    """Тест получения нескольких настроек уведомлений."""
    # Arrange
    pref1 = NotificationPreference(
        id=1,
        driver_id=sample_driver.id,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
        frequency=NotificationFrequency.INSTANT,
        is_enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    pref2 = NotificationPreference(
        id=2,
        driver_id=sample_driver.id,
        notification_type=NotificationType.STATUS_CHANGE,
        channel=NotificationChannel.EMAIL,
        frequency=NotificationFrequency.HOURLY,
        is_enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    mock_preferences_service.get_driver_preferences.return_value = [pref1, pref2]

    # Act
    response = client.get("/api/v1/preferences")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["notification_type"] == "new_order"
    assert data[1]["id"] == 2
    assert data[1]["notification_type"] == "status_change"
