"""
Сервис для управления настройками уведомлений пользователей.
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    NotificationPreference,
    NotificationType,
    NotificationChannel,
    NotificationFrequency,
)
from src.schemas.notification import (
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class NotificationPreferencesService:
    """Сервис для управления настройками уведомлений."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_preference(
        self, data: NotificationPreferenceCreate
    ) -> NotificationPreferenceResponse:
        """
        Создать новую настройку уведомлений.

        Args:
            data: Данные для создания настройки

        Returns:
            Созданная настройка уведомлений

        Raises:
            ValueError: Если настройка с такими параметрами уже существует
        """
        # Проверка на уникальность (driver_id, notification_type, channel)
        existing = await self._get_preference_by_driver_type_channel(
            driver_id=data.driver_id,
            notification_type=data.notification_type,
            channel=data.channel,
        )
        if existing:
            logger.warning(
                "preference_already_exists",
                driver_id=data.driver_id,
                notification_type=data.notification_type.value,
                channel=data.channel.value,
            )
            raise ValueError(
                f"Preference for driver {data.driver_id}, "
                f"type {data.notification_type.value}, "
                f"channel {data.channel.value} already exists"
            )

        preference = NotificationPreference(
            driver_id=data.driver_id,
            notification_type=data.notification_type,
            channel=data.channel,
            frequency=data.frequency,
            is_enabled=data.is_enabled,
        )
        self.session.add(preference)
        await self.session.commit()
        await self.session.refresh(preference)

        logger.info(
            "preference_created",
            preference_id=preference.id,
            driver_id=data.driver_id,
            notification_type=data.notification_type.value,
            channel=data.channel.value,
        )

        return NotificationPreferenceResponse.model_validate(preference)

    async def get_preference(self, preference_id: int) -> Optional[NotificationPreferenceResponse]:
        """
        Получить настройку по ID.

        Args:
            preference_id: ID настройки

        Returns:
            Настройка уведомлений или None
        """
        query = select(NotificationPreference).where(
            NotificationPreference.id == preference_id
        )
        result = await self.session.execute(query)
        preference = result.scalar_one_or_none()

        if preference:
            return NotificationPreferenceResponse.model_validate(preference)
        return None

    async def get_driver_preferences(
        self, driver_id: int
    ) -> List[NotificationPreferenceResponse]:
        """
        Получить все настройки водителя.

        Args:
            driver_id: ID водителя

        Returns:
            Список настроек уведомлений водителя
        """
        query = select(NotificationPreference).where(
            NotificationPreference.driver_id == driver_id
        )
        result = await self.session.execute(query)
        preferences = result.scalars().all()

        return [
            NotificationPreferenceResponse.model_validate(p) for p in preferences
        ]

    async def update_preference(
        self, preference_id: int, data: NotificationPreferenceUpdate
    ) -> Optional[NotificationPreferenceResponse]:
        """
        Обновить настройку уведомлений.

        Args:
            preference_id: ID настройки
            data: Данные для обновления

        Returns:
            Обновленная настройка или None
        """
        preference = await self._get_preference_by_id(preference_id)
        if not preference:
            logger.warning("preference_not_found", preference_id=preference_id)
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(preference, key, value)

        await self.session.commit()
        await self.session.refresh(preference)

        logger.info(
            "preference_updated",
            preference_id=preference_id,
            update_data=update_data,
        )

        return NotificationPreferenceResponse.model_validate(preference)

    async def delete_preference(self, preference_id: int) -> bool:
        """
        Удалить настройку уведомлений.

        Args:
            preference_id: ID настройки

        Returns:
            True если успешно удалено, иначе False
        """
        preference = await self._get_preference_by_id(preference_id)
        if not preference:
            logger.warning("preference_not_found_for_deletion", preference_id=preference_id)
            return False

        await self.session.delete(preference)
        await self.session.commit()

        logger.info("preference_deleted", preference_id=preference_id)
        return True

    async def get_preference_by_type_and_channel(
        self, driver_id: int, notification_type: NotificationType, channel: NotificationChannel
    ) -> Optional[NotificationPreferenceResponse]:
        """
        Получить настройку по типу уведомления и каналу.

        Args:
            driver_id: ID водителя
            notification_type: Тип уведомления
            channel: Канал доставки

        Returns:
            Настройка уведомлений или None
        """
        preference = await self._get_preference_by_driver_type_channel(
            driver_id=driver_id,
            notification_type=notification_type,
            channel=channel,
        )

        if preference:
            return NotificationPreferenceResponse.model_validate(preference)
        return None

    async def is_notification_enabled(
        self, driver_id: int, notification_type: NotificationType, channel: NotificationChannel
    ) -> bool:
        """
        Проверить, включен ли конкретный тип уведомлений для канала.

        Args:
            driver_id: ID водителя
            notification_type: Тип уведомления
            channel: Канал доставки

        Returns:
            True если уведомление включено, иначе False
        """
        preference = await self._get_preference_by_driver_type_channel(
            driver_id=driver_id,
            notification_type=notification_type,
            channel=channel,
        )

        if not preference:
            # По умолчанию, если настройки нет - считаем что отключено
            return False

        return preference.is_enabled

    async def set_preset(
        self, driver_id: int, preset: str
    ) -> List[NotificationPreferenceResponse]:
        """
        Применить пресет настроек уведомлений водителю.

        Пресеты:
        - "minimal": Только важные уведомления (new_order, system_alert) в Telegram, мгновенно
        - "standard": Все уведомления в Telegram, мгновенно
        - "maximum": Все уведомления во всех каналах, мгновенно

        Args:
            driver_id: ID водителя
            preset: Название пресета

        Returns:
            Список созданных/обновленных настроек
        """
        # Удалить существующие настройки
        existing_preferences = await self._get_driver_preferences_raw(driver_id)
        for pref in existing_preferences:
            await self.session.delete(pref)

        presets = {
            "minimal": [
                {
                    "notification_type": NotificationType.NEW_ORDER,
                    "channel": NotificationChannel.TELEGRAM,
                    "frequency": NotificationFrequency.INSTANT,
                    "is_enabled": True,
                },
                {
                    "notification_type": NotificationType.SYSTEM_ALERT,
                    "channel": NotificationChannel.TELEGRAM,
                    "frequency": NotificationFrequency.INSTANT,
                    "is_enabled": True,
                },
            ],
            "standard": [
                {
                    "notification_type": ntype,
                    "channel": NotificationChannel.TELEGRAM,
                    "frequency": NotificationFrequency.INSTANT,
                    "is_enabled": True,
                }
                for ntype in NotificationType
            ],
            "maximum": [
                {
                    "notification_type": ntype,
                    "channel": channel,
                    "frequency": NotificationFrequency.INSTANT,
                    "is_enabled": True,
                }
                for ntype in NotificationType
                for channel in NotificationChannel
            ],
        }

        if preset not in presets:
            logger.warning("invalid_preset", preset=preset)
            raise ValueError(f"Invalid preset: {preset}. Available: {list(presets.keys())}")

        preferences_to_create = []
        for pref_data in presets[preset]:
            preference = NotificationPreference(
                driver_id=driver_id,
                notification_type=pref_data["notification_type"],
                channel=pref_data["channel"],
                frequency=pref_data["frequency"],
                is_enabled=pref_data["is_enabled"],
            )
            self.session.add(preference)
            preferences_to_create.append(preference)

        await self.session.commit()

        for preference in preferences_to_create:
            await self.session.refresh(preference)

        logger.info(
            "preset_applied",
            driver_id=driver_id,
            preset=preset,
            count=len(preferences_to_create),
        )

        return [
            NotificationPreferenceResponse.model_validate(p) for p in preferences_to_create
        ]

    async def get_enabled_channels(
        self, driver_id: int, notification_type: NotificationType
    ) -> List[NotificationChannel]:
        """
        Получить список включенных каналов для типа уведомления.

        Args:
            driver_id: ID водителя
            notification_type: Тип уведомления

        Returns:
            Список каналов, для которых включен этот тип уведомлений
        """
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.driver_id == driver_id,
                NotificationPreference.notification_type == notification_type,
                NotificationPreference.is_enabled == True,
            )
        )
        result = await self.session.execute(query)
        preferences = result.scalars().all()

        return [p.channel for p in preferences]

    async def _get_preference_by_id(
        self, preference_id: int
    ) -> Optional[NotificationPreference]:
        """Получить настройку по ID (внутренний метод)."""
        query = select(NotificationPreference).where(
            NotificationPreference.id == preference_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_preference_by_driver_type_channel(
        self, driver_id: int, notification_type: NotificationType, channel: NotificationChannel
    ) -> Optional[NotificationPreference]:
        """Получить настройку по driver_id, типу и каналу (внутренний метод)."""
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.driver_id == driver_id,
                NotificationPreference.notification_type == notification_type,
                NotificationPreference.channel == channel,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_driver_preferences_raw(
        self, driver_id: int
    ) -> List[NotificationPreference]:
        """Получить все настройки водителя (внутренний метод, без валидации)."""
        query = select(NotificationPreference).where(
            NotificationPreference.driver_id == driver_id
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
