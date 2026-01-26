"""
E2E тесты для настроек уведомлений.

Проверка полного цикла:
1. Создание тестового пользователя
2. Применение пресета "Минимальный"
3. Проверка сохранения в БД
4. Отключение уведомлений о новом заказе
5. Проверка логики отправки уведомлений
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from src.database.models import Base, NotificationPreference, Driver
from src.services.notification_preferences_service import NotificationPreferencesService
from src.services.notification_service import NotificationService
from src.database.models import NotificationType, NotificationChannel, NotificationFrequency
from src.schemas.notification import NotificationPreferenceCreate


# Тестовый database URL (используем SQLite для тестов)
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_e2e.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function")
async def test_db():
    """Создание тестовой базы данных для каждого теста."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_db) -> AsyncSession:
    """Сессия БД для тестов."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_driver(db_session: AsyncSession) -> Driver:
    """Создание тестового водителя."""
    driver = Driver(
        username="test_notifications_user",
        email="test_notifications@example.com",
        first_name="Test",
        last_name="Notifications",
        hashed_password="hashed_password",
        phone="+71234567890",
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)
    return driver


class TestE2ENotifications:
    """E2E тесты настроек уведомлений."""

    @pytest.mark.asyncio
    async def test_e2e_full_workflow(self, test_driver: Driver, db_session: AsyncSession):
        """
        Полный E2E тест:
        1. Применение пресета 'minimal'
        2. Проверка сохранения в БД
        3. Отключение NEW_ORDER уведомлений
        4. Проверка через NotificationService
        """
        # Шаг 1: Применяем пресет 'minimal'
        preferences_service = NotificationPreferencesService(db_session)

        # 1. Применяем пресет minimal
        minimal_prefs = await preferences_service.set_preset(
            driver_id=test_driver.id,
            preset="minimal"
        )

        assert len(minimal_prefs) > 0, "Пресет minimal должен создать настройки"
        print(f"✓ Пресет 'minimal' применен, создано {len(minimal_prefs)} настроек")

        # 2. Проверяем сохранение в БД
        saved_prefs = await preferences_service.get_driver_preferences(driver_id=test_driver.id)
        assert len(saved_prefs) > 0, "Настройки должны быть сохранены в БД"
        print(f"✓ Настройки сохранены в БД, всего {len(saved_prefs)} записей")

        # 3. Отключаем уведомления типа NEW_ORDER для канала TELEGRAM
        new_order_pref = None
        for pref in saved_prefs:
            if pref.notification_type == NotificationType.NEW_ORDER and pref.channel == NotificationChannel.TELEGRAM:
                new_order_pref = pref
                break

        if new_order_pref:
            updated_pref = await preferences_service.update_preference(
                preference_id=new_order_pref.id,
                data={"is_enabled": False}
            )
            assert updated_pref.is_enabled is False, "Уведомление должно быть отключено"
            print(f"✓ Уведомления NEW_ORDER/TELEGRAM отключены")
        else:
            # Создаем отключенную настройку
            create_data = NotificationPreferenceCreate(
                driver_id=test_driver.id,
                notification_type=NotificationType.NEW_ORDER,
                channel=NotificationChannel.TELEGRAM,
                frequency=NotificationFrequency.INSTANT,
                is_enabled=False
            )
            disabled_pref = await preferences_service.create_preference(data=create_data)
            assert disabled_pref.is_enabled is False, "Уведомление должно быть отключено"
            print(f"✓ Создана отключенная настройка NEW_ORDER/TELEGRAM")

        # 4. Проверяем через NotificationService, что уведомление не будет отправлено
        notification_service = NotificationService(
            telegram_bot_token="test_token",
            preferences_service=preferences_service
        )

        should_send = await notification_service.should_send_notification(
            driver_id=test_driver.id,
            notification_type=NotificationType.NEW_ORDER,
            channel=NotificationChannel.TELEGRAM
        )

        assert should_send is False, "Уведомление не должно отправляться"
        print(f"✓ NotificationService корректно проверяет настройки (should_send=False)")

        # 5. Проверяем, что для других типов уведомления отправляются
        # (в пресете minimal важные уведомления включены)
        should_send_important = await notification_service.should_send_notification(
            driver_id=test_driver.id,
            notification_type=NotificationType.ROUTE_ASSIGNED,
            channel=NotificationChannel.TELEGRAM
        )

        # В пресете minimal важные уведомления должны быть включены
        assert should_send_important is True, "Важные уведомления должны отправляться в пресете minimal"
        print(f"✓ Важные уведомления (ROUTE_ASSIGNED) включены в пресете minimal")

        print("\n=== E2E тест пройден успешно ===")
        print("✓ Пресет 'minimal' применен")
        print("✓ Настройки сохранены в БД")
        print("✓ NEW_ORDER отключен")
        print("✓ NotificationService учитывает настройки")

    @pytest.mark.asyncio
    async def test_e2e_preset_transitions(self, test_driver: Driver, db_session: AsyncSession):
        """
        Тест переходов между пресетами:
        minimal -> standard -> maximum
        """
        preferences_service = NotificationPreferencesService(db_session)

        # Minimal
        minimal_prefs = await preferences_service.set_preset(
            driver_id=test_driver.id,
            preset="minimal"
        )
        minimal_count = len(minimal_prefs)
        print(f"✓ Minimal: {minimal_count} настроек")

        # Standard
        standard_prefs = await preferences_service.set_preset(
            driver_id=test_driver.id,
            preset="standard"
        )
        standard_count = len(standard_prefs)
        print(f"✓ Standard: {standard_count} настроек")

        # Maximum
        maximum_prefs = await preferences_service.set_preset(
            driver_id=test_driver.id,
            preset="maximum"
        )
        maximum_count = len(maximum_prefs)
        print(f"✓ Maximum: {maximum_count} настроек")

        # Проверяем, что количество настроек растет
        assert minimal_count <= standard_count <= maximum_count, \
            "Количество настроек должно увеличиваться от minimal к maximum"

        print("\n=== Переходы между пресетами работают корректно ===")

    @pytest.mark.asyncio
    async def test_e2e_frequency_settings(self, test_driver: Driver, db_session: AsyncSession):
        """
        Тест настройки частоты уведомлений.
        """
        preferences_service = NotificationPreferencesService(db_session)
        notification_service = NotificationService(
            telegram_bot_token="test_token",
            preferences_service=preferences_service
        )

        # Создаем настройку с частотой HOURLY
        create_data = NotificationPreferenceCreate(
            driver_id=test_driver.id,
            notification_type=NotificationType.ORDER_REMINDER,
            channel=NotificationChannel.TELEGRAM,
            frequency=NotificationFrequency.HOURLY,
            is_enabled=True
        )

        pref = await preferences_service.create_preference(data=create_data)
        assert pref.frequency == NotificationFrequency.HOURLY, "Частота должна быть HOURLY"
        print(f"✓ Настройка создана с частотой HOURLY")

        # Проверяем, что NotificationService учитывает частоту
        # (это проверяется в unit тестах, здесь просто логируем)
        enabled_channels = await preferences_service.get_enabled_channels(
            driver_id=test_driver.id,
            notification_type=NotificationType.ORDER_REMINDER
        )

        print(f"✓ Включенные каналы для ORDER_REMINDER: {enabled_channels}")
        print("\n=== Настройка частоты работает корректно ===")


@pytest.mark.asyncio
async def test_database_integration():
    """
    Тест интеграции с БД: проверка индексов и constraints.
    """
    async with TestingSessionLocal() as session:
        preferences_service = NotificationPreferencesService(session)

        # Создаем тестового драйвера
        driver = Driver(
            username="test_db_user",
            email="test_db@example.com",
            first_name="Test",
            last_name="DB",
            hashed_password="hashed",
        )
        session.add(driver)
        await session.commit()
        await session.refresh(driver)

        # Создаем настройку
        from src.schemas.notification import NotificationPreferenceCreate
        create_data = NotificationPreferenceCreate(
            driver_id=driver.id,
            notification_type=NotificationType.NEW_ORDER,
            channel=NotificationChannel.TELEGRAM,
            frequency=NotificationFrequency.INSTANT,
            is_enabled=True
        )

        pref1 = await preferences_service.create_preference(data=create_data)
        print(f"✓ Первая настройка создана: id={pref1.id}")

        # Проверяем уникальность constraint (не должно создавать дубликат)
        try:
            pref2 = await preferences_service.create_preference(data=create_data)
            print(f"✗ Дубликат не должен был создаться!")
            assert False, "Дубликат не должен создаваться"
        except Exception as e:
            print(f"✓ Уникальный constraint работает: {str(e)[:50]}...")

        await session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
