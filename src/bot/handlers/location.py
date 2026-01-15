from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ContentType
from redis.asyncio import Redis
from datetime import datetime, timezone

from src.services.location_manager import LocationManager
from src.config import settings
from src.core.logging import get_logger
from src.database.models import Driver, UserRole

logger = get_logger(__name__)
router = Router(name="location")

async def get_location_manager() -> LocationManager:
    """Фабрика для LocationManager."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return LocationManager(redis)

async def process_location(message: Message, driver: Driver) -> None:
    """
    Общая логика обработки геолокации.
    Используется как для message, так и для edited_message.
    """
    # 1. Проверяем роль пользователя
    if driver.role not in (UserRole.DRIVER, UserRole.ADMIN, UserRole.DISPATCHER):
        # Другие роли (например, PENDING) игнорируем
        logger.debug(
            "location_update_ignored",
            driver_id=driver.id,
            role=driver.role,
            reason="not_authorized_role"
        )
        return
    
    if driver.role != UserRole.DRIVER:
        logger.info(
            "staff_location_received",
            user_id=driver.id,
            role=driver.role,
            lat=message.location.latitude if message.location else None,
            lon=message.location.longitude if message.location else None
        )

    location = message.location
    if location is None:
        return
    
    manager = await get_location_manager()
    
    # Определяем timestamp (edit_date для edited_message, date для message)
    ts = message.edit_date or message.date or datetime.now(timezone.utc)
    
    await manager.update_driver_location(
        driver_id=driver.id,
        latitude=location.latitude,
        longitude=location.longitude,
        timestamp=ts
    )
    
    logger.info(
        "location_received",
        driver_id=driver.id,
        lat=location.latitude,
        lon=location.longitude,
        is_live=location.live_period is not None
    )

# ============ ОБРАБОТЧИКИ ============

@router.message(F.content_type == ContentType.LOCATION)
async def on_location_message(message: Message, driver: Driver) -> None:
    """
    Обработка первичного сообщения с геолокацией.
    """
    await process_location(message, driver)
    
    # Отвечаем только если это водитель, чтобы не спамить админу
    if driver.role == UserRole.DRIVER:
        if message.location and message.location.live_period:
            await message.reply(
                "📍 Live Location активирован!\n"
                f"Трансляция: {message.location.live_period // 60} мин."
            )
        else:
            await message.reply("📍 Геолокация получена!")

@router.edited_message(F.content_type == ContentType.LOCATION)
async def on_location_edited(message: Message, driver: Driver) -> None:
    """
    Обработка обновлений Live Location.
    """
    await process_location(message, driver)
    
    # Проверяем завершение трансляции
    if message.location and message.location.live_period == 0:
        logger.info("live_location_stopped", driver_id=driver.id)
