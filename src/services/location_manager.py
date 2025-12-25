import json
from datetime import datetime, timezone
from typing import List, Optional
from redis.asyncio import Redis

from pydantic import BaseModel, Field
from src.core.logging import get_logger

logger = get_logger(__name__)

class DriverLocation(BaseModel):
    """Схема текущего местоположения водителя."""
    driver_id: int
    latitude: float
    longitude: float
    timestamp: datetime

class LocationEntry(BaseModel):
    """Схема записи из Redis Stream."""
    entry_id: str
    latitude: float
    longitude: float
    timestamp: datetime

class LocationManager:
    """
    Класс для управления геолокацией водителей через Redis.
    Использует Redis Hash для текущих координат и Redis Stream для истории (синхронизация с БД).
    """

    KEY_PREFIX = "driver:loc"      # Hash: {driver_id} -> {lat, lon, ts}
    SET_ACTIVE = "drivers:active"  # Set: [driver_id, ...]
    STREAM_PREFIX = "driver:stream" # Stream: {driver_id} -> [points...]
    TTL = 300  # 5 минут

    def __init__(self, redis: Redis):
        self.redis = redis

    async def update_driver_location(
        self,
        driver_id: int,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Сохраняет координаты в Redis.
        1. Записывает текущую позицию (TTL 5 мин)
        2. Добавляет ID в список активных
        3. Пишет в Stream для последующей синхронизации с PostgreSQL
        """
        ts = timestamp or datetime.now(timezone.utc)
        ts_iso = ts.isoformat()

        loc_data = {
            "lat": latitude,
            "lon": longitude,
            "ts": ts_iso
        }

        # 1. Текущая позиция (Hash)
        key = f"{self.KEY_PREFIX}:{driver_id}"
        await self.redis.hset(key, mapping=loc_data)
        await self.redis.expire(key, self.TTL)

        # 2. Список активных водителей (Set)
        await self.redis.sadd(self.SET_ACTIVE, driver_id)

        # 3. Добавляем в стрим для воркера
        stream_key = f"{self.STREAM_PREFIX}:{driver_id}"
        await self.redis.xadd(stream_key, loc_data)

        logger.info(
            "location_updated",
            driver_id=driver_id,
            lat=latitude,
            lon=longitude
        )

    async def get_active_drivers(self) -> List[DriverLocation]:
        """
        Возвращает список активных водителей с их последними координатами.
        Для диспетчерской карты.
        """
        active_ids = await self.redis.smembers(self.SET_ACTIVE)
        if not active_ids:
            return []

        results = []
        for d_id in active_ids:
            d_id = int(d_id)
            key = f"{self.KEY_PREFIX}:{d_id}"
            data = await self.redis.hgetall(key)
            
            if not data:
                # Водитель устарел (TTL вышел), удаляем из активных
                await self.redis.srem(self.SET_ACTIVE, d_id)
                continue

            results.append(DriverLocation(
                driver_id=d_id,
                latitude=float(data[b"lat"]),
                longitude=float(data[b"lon"]),
                timestamp=datetime.fromisoformat(data[b"ts"].decode())
            ))
        
        return results

    async def get_driver_location(self, driver_id: int) -> Optional[DriverLocation]:
        """Получить текущие координаты конкретного водителя."""
        key = f"{self.KEY_PREFIX}:{driver_id}"
        data = await self.redis.hgetall(key)
        
        if not data:
            return None

        return DriverLocation(
            driver_id=driver_id,
            latitude=float(data[b"lat"]),
            longitude=float(data[b"lon"]),
            timestamp=datetime.fromisoformat(data[b"ts"].decode())
        )

    async def get_active_driver_ids(self) -> List[int]:
        """Возвращает ID всех активных водителей."""
        ids = await self.redis.smembers(self.SET_ACTIVE)
        return [int(d_id) for d_id in ids]

    async def consume_stream_entries(self, driver_id: int, count: int = 100) -> List[LocationEntry]:
        """
        Читает и удаляет записи из стрима водителя. 
        Используется воркером для синхронизации.
        """
        stream_key = f"{self.STREAM_PREFIX}:{driver_id}"
        # Читаем записи
        entries = await self.redis.xrange(stream_key, count=count)
        if not entries:
            return []

        results = []
        entry_ids = []
        for e_id, data in entries:
            results.append(LocationEntry(
                entry_id=e_id.decode(),
                latitude=float(data[b"lat"]),
                longitude=float(data[b"lon"]),
                timestamp=datetime.fromisoformat(data[b"ts"].decode())
            ))
            entry_ids.append(e_id)

        # Удаляем прочитанные записи
        if entry_ids:
            await self.redis.xdel(stream_key, *entry_ids)

        return results
