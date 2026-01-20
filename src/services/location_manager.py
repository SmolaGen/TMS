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
    status: str = "available"
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
    
    Использует:
    - Redis Hash для текущих координат (real-time карта)
    - Единый Redis Stream для истории (High-Throughput Ingestion в PostgreSQL)
    """

    KEY_PREFIX = "driver:loc"           # Hash: {driver_id} -> {lat, lon, ts}
    SET_ACTIVE = "drivers:active"       # Set: [driver_id, ...]
    STREAM_NAME = "driver:locations"    # Единый Stream для всех водителей
    STREAM_PREFIX = "driver:stream"     # Для персональных стримов водителей
    STREAM_MAXLEN = 100000              # Защита от переполнения RAM (~100K записей)
    TTL = 300  # 5 минут

    async def update_driver_status_only(
        self,
        driver_id: int,
        status: str,
    ) -> None:
        """
        Обновляет только статус водителя в Redis и сбрасывает TTL.
        Используется, когда водитель явно меняет свой статус.
        """
        key = f"{self.KEY_PREFIX}:{driver_id}"
        existing_data = await self.redis.hgetall(key)
        
        if existing_data:
            # Обновляем только статус, сохраняя остальные данные
            existing_data[b"status"] = status.encode()
            await self.redis.hset(key, mapping=existing_data)
            await self.redis.expire(key, self.TTL)
            logger.debug("driver_status_updated_redis", driver_id=driver_id, status=status)
        else:
            # Если данных нет, возможно, водитель не отправлял геолокацию,
            # но мы все равно хотим сохранить его статус.
            # В этом случае создадим минимальную запись.
            # Если водитель потом отправит геолокацию, она обновится.
            ts = datetime.now(timezone.utc)
            hash_data = {
                "lat": 0.0, # Используем 0.0 как заглушку, если нет геопозиции
                "lon": 0.0,
                "status": status,
                "ts": ts.isoformat()
            }
            await self.redis.hset(key, mapping=hash_data)
            await self.redis.expire(key, self.TTL)
            logger.warning(
                "driver_status_set_no_location_redis",
                driver_id=driver_id,
                status=status
            )

    def __init__(self, redis: Redis):
        self.redis = redis

    async def update_driver_location(
        self,
        driver_id: int,
        latitude: float,
        longitude: float,
        status: str = "available",
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Сохраняет координаты в Redis.
        
        1. Записывает текущую позицию (Hash с TTL 5 мин) - для real-time карты
        2. Добавляет ID в список активных водителей (Set)
        3. Пишет в единый Redis Stream с MAXLEN для High-Throughput Ingestion
        """
        ts = timestamp or datetime.now(timezone.utc)
        ts_iso = ts.isoformat()

        hash_data = {
            "lat": latitude,
            "lon": longitude,
            "status": status,
            "ts": ts_iso
        }

        # 1. Текущая позиция (Hash) - для диспетчерской карты
        key = f"{self.KEY_PREFIX}:{driver_id}"
        await self.redis.hset(key, mapping=hash_data)
        await self.redis.expire(key, self.TTL)

        # 2. Список активных водителей (Set)
        await self.redis.sadd(self.SET_ACTIVE, driver_id)

        # 3. Единый Stream для воркера с MAXLEN защитой от переполнения RAM
        # MAXLEN ~ (approximate) позволяет O(1) обрезку вместо O(N)
        stream_data = {
            "driver_id": str(driver_id),
            "lat": str(latitude),
            "lon": str(longitude),
            "ts": ts_iso
        }
        await self.redis.xadd(
            self.STREAM_NAME,
            stream_data,
            maxlen=self.STREAM_MAXLEN,
            approximate=True  # ~ в MAXLEN для производительности
        )

        # 4. Персональный Stream для SyncWorker (история в PG)
        personal_stream = f"{self.STREAM_PREFIX}:{driver_id}"
        await self.redis.xadd(
            personal_stream,
            stream_data,
            maxlen=1000,  # Храним немного, воркер должен быстро вычитывать
            approximate=True
        )

        logger.debug(
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
                status=data.get(b"status", b"available").decode(),
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
            status=data.get(b"status", b"available").decode(),
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
