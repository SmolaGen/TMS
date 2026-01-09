import asyncio
import math
from datetime import datetime
from sqlalchemy import text
from src.database.connection import async_session_factory
from src.services.location_manager import LocationManager, LocationEntry
from src.core.logging import get_logger

logger = get_logger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Дистанция между двумя точками в метрах."""
    R = 6371000  # Радиус земли
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class SyncLocationWorker:
    """
    Воркер для переноса координат из Redis Stream в PostgreSQL.
    Фильтрует точки: пишет в БД только если пройдено > 100 метров.
    """

    INTERVAL = 60  # раз в минуту
    MIN_DISTANCE = 100  # метров

    def __init__(self, location_manager: LocationManager):
        self.location_manager = location_manager

    async def run(self):
        logger.info("sync_worker_started", interval=self.INTERVAL)
        while True:
            try:
                await self._sync_all()
            except Exception as e:
                logger.exception("sync_worker_error", error=str(e))
            await asyncio.sleep(self.INTERVAL)

    async def _sync_all(self):
        driver_ids = await self.location_manager.get_active_driver_ids()
        if not driver_ids:
            return

        logger.info("sync_worker_running", drivers_count=len(driver_ids))
        for d_id in driver_ids:
            await self._sync_driver(d_id)

    async def _sync_driver(self, driver_id: int):
        # 1. Читаем новые точки из стрима (и удаляем их оттуда)
        entries = await self.location_manager.consume_stream_entries(driver_id)
        if not entries:
            return

        async with async_session_factory() as session:
            # 2. Получаем последнюю точку из БД
            last_point_result = await session.execute(
                text("""
                    SELECT ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon 
                    FROM driver_location_history 
                    WHERE driver_id = :d_id 
                    ORDER BY recorded_at DESC LIMIT 1
                """),
                {"d_id": driver_id}
            )
            last_point = last_point_result.fetchone()

            # 3. Фильтруем точки
            to_save = []
            curr_lat = last_point.lat if last_point else None
            curr_lon = last_point.lon if last_point else None

            for entry in entries:
                if curr_lat is None or haversine_distance(curr_lat, curr_lon, entry.latitude, entry.longitude) >= self.MIN_DISTANCE:
                    to_save.append(entry)
                    curr_lat, curr_lon = entry.latitude, entry.longitude

            # 4. Batch Insert
            if to_save:
                # SQLAlchemy Core для быстрого батча
                stmt = text("""
                    INSERT INTO driver_location_history (driver_id, location, recorded_at)
                    VALUES (:d_id, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :ts)
                """)
                params = [
                    {"d_id": driver_id, "lat": e.latitude, "lon": e.longitude, "ts": e.timestamp}
                    for e in to_save
                ]
                await session.execute(stmt, params)
                await session.commit()
                logger.info("synced_driver_locations", driver_id=driver_id, points_saved=len(to_save))
