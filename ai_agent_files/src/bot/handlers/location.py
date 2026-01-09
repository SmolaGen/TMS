from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ContentType
from redis.asyncio import Redis
from datetime import datetime, timezone

from src.services.location_manager import LocationManager
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = Router(name="location")

async def get_location_manager() -> LocationManager:
    """Фабрика для LocationManager."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return LocationManager(redis)

async def process_location(message: Message, driver_id: int) -> None:
    """
    Общая логика обработки геолокации.
    Используется как для message, так и для edited_message.
    """
    location = message.location
    if location is None:
        return
    
    manager = await get_location_manager()
    
    # Определяем timestamp (edit_date для edited_message, date для message)
    ts = message.edit_date or message.date or datetime.now(timezone.utc)
    
    await manager.update_driver_location(
        driver_id=driver_id,
        latitude=location.latitude,
        longitude=location.longitude,
        timestamp=ts
    )
    
    logger.info(
        "location_received",
        driver_id=driver_id,
        lat=location.latitude,
        lon=location.longitude,
        is_live=location.live_period is not None
    )

# ============ ОБРАБОТЧИКИ ============

@router.message(F.content_type == ContentType.LOCATION)
async def on_location_message(message: Message, driver_id: int) -> None:
    """
    Обработка первичного сообщения с геолокацией.
    """
    await process_location(message, driver_id)
    
    if message.location and message.location.live_period:
        await message.reply(
            "📍 Live Location активирован!\n"
            f"Трансляция: {message.location.live_period // 60} мин."
        )
    else:
        await message.reply("📍 Геолокация получена!")

@router.edited_message(F.content_type == ContentType.LOCATION)
async def on_location_edited(message: Message, driver_id: int) -> None:
    """
    Обработка обновлений Live Location.
    """
    await process_location(message, driver_id)
    
    # Проверяем завершение трансляции
    if message.location and message.location.live_period == 0:
        logger.info("live_location_stopped", driver_id=driver_id)
