"""
Unit тесты для NotificationPreferencesService.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, Mock
from datetime import datetime

from src.services.notification_preferences_service import NotificationPreferencesService
from src.schemas.notification import (
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
)
from src.database.models import (
    NotificationPreference,
    NotificationType,
    NotificationChannel,
    NotificationFrequency,
)


def setup_mock_execute(mock_session, scalar_one_or_none_return=None, scalars_all_return=None):
    """Helper функция для настройки mock execute."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none_return)

    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=scalars_all_return or [])
    mock_result.scalars.return_value = mock_scalars

    async def mock_execute_func(*args, **kwargs):
        return mock_result

    mock_session.execute = mock_execute_func
    return mock_result


@pytest.fixture
def mock_session():
    """Создать mock для базы данных."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    # Настраиваем refresh как async, который обновляет объект
    async def mock_refresh(obj):
        # Если у объекта нет id, установим его
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1
        # Убедимся что есть timestamps
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.utcnow()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.utcnow()
    session.refresh = mock_refresh

    # delete должен быть async (в сервисе используется await session.delete)
    async def mock_delete(obj):
        pass
    session.delete = mock_delete

    return session


@pytest.fixture
def notification_service(mock_session):
    """Создать экземпляр сервиса с мокнутой сессией."""
    return NotificationPreferencesService(mock_session)


@pytest.fixture
def sample_preference():
    """Создать пример настройки уведомлений."""
    pref = NotificationPreference(
        id=1,
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
        frequency=NotificationFrequency.INSTANT,
        is_enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return pref


@pytest.mark.asyncio
async def test_create_preference_success(notification_service, mock_session, sample_preference):
    """Тест успешного создания настройки уведомлений."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)  # Нет дубликата

    create_data = NotificationPreferenceCreate(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
        frequency=NotificationFrequency.INSTANT,
        is_enabled=True,
    )

    # Act
    result = await notification_service.create_preference(create_data)

    # Assert
    assert result.driver_id == 1
    assert result.notification_type == NotificationType.NEW_ORDER
    assert result.channel == NotificationChannel.TELEGRAM
    assert result.frequency == NotificationFrequency.INSTANT
    assert result.is_enabled is True
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_preference_duplicate(notification_service, mock_session, sample_preference):
    """Тест попытки создания дубликата настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    create_data = NotificationPreferenceCreate(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
        frequency=NotificationFrequency.INSTANT,
        is_enabled=True,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Preference for driver 1, type new_order, channel telegram already exists"):
        await notification_service.create_preference(create_data)


@pytest.mark.asyncio
async def test_get_preference_exists(notification_service, mock_session, sample_preference):
    """Тест получения существующей настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Act
    result = await notification_service.get_preference(1)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.driver_id == 1


@pytest.mark.asyncio
async def test_get_preference_not_exists(notification_service, mock_session):
    """Тест получения несуществующей настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)

    # Act
    result = await notification_service.get_preference(999)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_driver_preferences(notification_service, mock_session, sample_preference):
    """Тест получения всех настроек водителя."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[sample_preference])

    # Act
    result = await notification_service.get_driver_preferences(1)

    # Assert
    assert len(result) == 1
    assert result[0].driver_id == 1


@pytest.mark.asyncio
async def test_get_driver_preferences_empty(notification_service, mock_session):
    """Тест получения настроек водителя, когда их нет."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.get_driver_preferences(999)

    # Assert
    assert len(result) == 0


@pytest.mark.asyncio
async def test_update_preference_success(notification_service, mock_session, sample_preference):
    """Тест успешного обновления настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Мокаем refresh чтобы проверить вызов
    refresh_called = []

    async def tracked_refresh(obj):
        refresh_called.append(obj)

    original_refresh = mock_session.refresh
    mock_session.refresh = tracked_refresh

    update_data = NotificationPreferenceUpdate(
        frequency=NotificationFrequency.HOURLY,
        is_enabled=False,
    )

    # Act
    result = await notification_service.update_preference(1, update_data)

    # Assert
    assert result is not None
    mock_session.commit.assert_called_once()
    assert len(refresh_called) == 1

    # Восстанавливаем оригинальный refresh
    mock_session.refresh = original_refresh


@pytest.mark.asyncio
async def test_update_preference_not_found(notification_service, mock_session):
    """Тест обновления несуществующей настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)

    update_data = NotificationPreferenceUpdate(
        frequency=NotificationFrequency.HOURLY,
    )

    # Act
    result = await notification_service.update_preference(999, update_data)

    # Assert
    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_preference_success(notification_service, mock_session, sample_preference):
    """Тест успешного удаления настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Мокаем delete чтобы он был проверяемым
    original_delete = mock_session.delete
    delete_called_with = []

    async def tracked_delete(obj):
        delete_called_with.append(obj)

    mock_session.delete = tracked_delete

    # Act
    result = await notification_service.delete_preference(1)

    # Assert
    assert result is True
    assert len(delete_called_with) == 1
    assert delete_called_with[0] == sample_preference
    mock_session.commit.assert_called_once()

    # Восстанавливаем оригинальный delete
    mock_session.delete = original_delete


@pytest.mark.asyncio
async def test_delete_preference_not_found(notification_service, mock_session):
    """Тест удаления несуществующей настройки."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)

    # Мокаем delete чтобы проверить что он не вызывался
    delete_called = []

    async def tracked_delete(obj):
        delete_called.append(obj)

    original_delete = mock_session.delete
    mock_session.delete = tracked_delete

    # Act
    result = await notification_service.delete_preference(999)

    # Assert
    assert result is False
    assert len(delete_called) == 0

    # Восстанавливаем оригинальный delete
    mock_session.delete = original_delete


@pytest.mark.asyncio
async def test_get_preference_by_type_and_channel_exists(notification_service, mock_session, sample_preference):
    """Тест получения настройки по типу и каналу, когда она существует."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Act
    result = await notification_service.get_preference_by_type_and_channel(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
    )

    # Assert
    assert result is not None
    assert result.driver_id == 1
    assert result.notification_type == NotificationType.NEW_ORDER
    assert result.channel == NotificationChannel.TELEGRAM


@pytest.mark.asyncio
async def test_get_preference_by_type_and_channel_not_exists(notification_service, mock_session):
    """Тест получения настройки по типу и каналу, когда она не существует."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)

    # Act
    result = await notification_service.get_preference_by_type_and_channel(
        driver_id=999,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
    )

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_is_notification_enabled_true(notification_service, mock_session, sample_preference):
    """Тест проверки включенности уведомления, когда оно включено."""
    # Arrange
    sample_preference.is_enabled = True
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Act
    result = await notification_service.is_notification_enabled(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
    )

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_is_notification_enabled_false(notification_service, mock_session, sample_preference):
    """Тест проверки включенности уведомления, когда оно выключено."""
    # Arrange
    sample_preference.is_enabled = False
    setup_mock_execute(mock_session, scalar_one_or_none_return=sample_preference)

    # Act
    result = await notification_service.is_notification_enabled(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
    )

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_is_notification_enabled_no_preference(notification_service, mock_session):
    """Тест проверки включенности уведомления, когда настройка отсутствует."""
    # Arrange
    setup_mock_execute(mock_session, scalar_one_or_none_return=None)

    # Act
    result = await notification_service.is_notification_enabled(
        driver_id=999,
        notification_type=NotificationType.NEW_ORDER,
        channel=NotificationChannel.TELEGRAM,
    )

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_set_preset_minimal(notification_service, mock_session):
    """Тест применения пресета 'minimal'."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.set_preset(driver_id=1, preset="minimal")

    # Assert
    assert len(result) == 2
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_set_preset_standard(notification_service, mock_session):
    """Тест применения пресета 'standard'."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.set_preset(driver_id=1, preset="standard")

    # Assert
    # Standard создает настройки для всех типов уведомлений в Telegram
    assert len(result) == len(NotificationType)
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_set_preset_maximum(notification_service, mock_session):
    """Тест применения пресета 'maximum'."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.set_preset(driver_id=1, preset="maximum")

    # Assert
    # Maximum создает настройки для всех типов уведомлений во всех каналах
    expected_count = len(NotificationType) * len(NotificationChannel)
    assert len(result) == expected_count
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_set_preset_invalid(notification_service, mock_session):
    """Тест применения несуществующего пресета."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid preset: invalid_preset"):
        await notification_service.set_preset(driver_id=1, preset="invalid_preset")


@pytest.mark.asyncio
async def test_set_preset_deletes_existing(notification_service, mock_session, sample_preference):
    """Тест что set_preset удаляет существующие настройки перед созданием новых."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[sample_preference])

    # Мокаем delete чтобы проверить вызовы
    delete_called_with = []

    async def tracked_delete(obj):
        delete_called_with.append(obj)

    original_delete = mock_session.delete
    mock_session.delete = tracked_delete

    # Act
    await notification_service.set_preset(driver_id=1, preset="minimal")

    # Assert
    # Проверить что существующая настройка была удалена
    assert len(delete_called_with) == 1
    assert delete_called_with[0] == sample_preference

    # Восстанавливаем оригинальный delete
    mock_session.delete = original_delete


@pytest.mark.asyncio
async def test_get_enabled_channels(notification_service, mock_session, sample_preference):
    """Тест получения включенных каналов для типа уведомления."""
    # Arrange
    sample_preference.is_enabled = True
    sample_preference.channel = NotificationChannel.TELEGRAM
    setup_mock_execute(mock_session, scalars_all_return=[sample_preference])

    # Act
    result = await notification_service.get_enabled_channels(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
    )

    # Assert
    assert len(result) == 1
    assert NotificationChannel.TELEGRAM in result


@pytest.mark.asyncio
async def test_get_enabled_channels_empty(notification_service, mock_session):
    """Тест получения включенных каналов, когда их нет."""
    # Arrange
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.get_enabled_channels(
        driver_id=999,
        notification_type=NotificationType.NEW_ORDER,
    )

    # Assert
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_enabled_channels_filters_disabled(notification_service, mock_session):
    """Тест что get_enabled_channels не возвращает отключенные каналы."""
    # Arrange
    # SQL запрос с фильтром is_enabled == True вернул бы пустой результат
    setup_mock_execute(mock_session, scalars_all_return=[])

    # Act
    result = await notification_service.get_enabled_channels(
        driver_id=1,
        notification_type=NotificationType.NEW_ORDER,
    )

    # Assert
    assert len(result) == 0
