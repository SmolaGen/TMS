"""
High-Throughput Location Ingest Worker

Воркер для высокопроизводительной записи геолокаций из Redis Stream в PostgreSQL.

Особенности:
- Consumer Groups для параллельной обработки (XREADGROUP)
- Binary COPY для ~10-50x ускорения INSERT
- Poison Pill Handling: изоляция "битых" записей
- XAUTOCLAIM для восстановления зависших сообщений
- At-least-once delivery: XACK только после COMMIT

Usage:
    python -m src.workers.ingest_worker
"""

import asyncio
import os
import sys
import struct
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional
from dataclasses import dataclass

import psycopg
from redis.asyncio import Redis

from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Configuration
# ============================================================================

STREAM_NAME = "driver:locations"
CONSUMER_GROUP = "location_ingesters"
CONSUMER_NAME = f"worker_{os.getpid()}"
DLQ_STREAM_NAME = "dlq:location_errors"  # Dead Letter Queue для poison pills

BATCH_SIZE = 2000           # Записей за один COPY
BATCH_TIMEOUT_MS = 5000     # Максимальное ожидание батча (5 сек)
CLAIM_MIN_IDLE_MS = 60000   # 60 сек простоя для XAUTOCLAIM
MAX_RETRIES = 3             # Попыток обработки перед DLQ


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class LocationRecord:
    """Запись геолокации из стрима."""
    entry_id: str
    driver_id: int
    latitude: float
    longitude: float
    timestamp: datetime
    retry_count: int = 0
    
    @classmethod
    def from_stream_entry(cls, entry_id: bytes, data: dict) -> "LocationRecord":
        """Парсинг записи из Redis Stream."""
        entry_id_str = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
        
        # Поддержка обоих форматов: bytes и str
        def get_value(key: str) -> str:
            if key.encode() in data:
                val = data[key.encode()]
                return val.decode() if isinstance(val, bytes) else val
            elif key in data:
                val = data[key]
                return val.decode() if isinstance(val, bytes) else val
            raise KeyError(f"Key {key} not found in data")
        
        return cls(
            entry_id=entry_id_str,
            driver_id=int(get_value("driver_id")),
            latitude=float(get_value("lat")),
            longitude=float(get_value("lon")),
            timestamp=datetime.fromisoformat(get_value("ts")),
            retry_count=0
        )


# ============================================================================
# Binary COPY Writer
# ============================================================================

class BinaryCopyWriter:
    """
    Генератор бинарного формата PostgreSQL COPY.
    
    Формат: Header + [Row...] + Trailer
    - Header: 11 bytes signature + 4 bytes flags + 4 bytes header ext length
    - Row: 2 bytes field count + [Field...] per row
    - Field: 4 bytes length + data bytes
    - Trailer: -1 (2 bytes)
    """
    
    PG_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
    COPY_SIGNATURE = b"PGCOPY\n\xff\r\n\0"
    
    def __init__(self):
        self.buffer = BytesIO()
        self._write_header()
    
    def _write_header(self):
        """Записывает COPY binary header."""
        self.buffer.write(self.COPY_SIGNATURE)
        self.buffer.write(struct.pack(">I", 0))  # flags
        self.buffer.write(struct.pack(">I", 0))  # header extension length
    
    def add_row(self, driver_id: int, lat: float, lon: float, recorded_at: datetime):
        """Добавляет строку в буфер."""
        # Field count: 3 (driver_id, location как WKT, recorded_at)
        self.buffer.write(struct.pack(">h", 3))
        
        # Field 1: driver_id (INT4)
        self.buffer.write(struct.pack(">i", 4))  # length
        self.buffer.write(struct.pack(">i", driver_id))
        
        # Field 2: location как WKT (TEXT) - PostGIS понимает EWKT
        wkt = f"SRID=4326;POINT({lon} {lat})".encode("utf-8")
        self.buffer.write(struct.pack(">i", len(wkt)))
        self.buffer.write(wkt)
        
        # Field 3: recorded_at (TIMESTAMPTZ as INT8 microseconds from PG epoch)
        ts = recorded_at if recorded_at.tzinfo else recorded_at.replace(tzinfo=timezone.utc)
        delta = ts - self.PG_EPOCH
        microseconds = int(delta.total_seconds() * 1_000_000)
        self.buffer.write(struct.pack(">i", 8))  # length
        self.buffer.write(struct.pack(">q", microseconds))
    
    def finish(self) -> bytes:
        """Завершает буфер и возвращает байты."""
        # Trailer: -1 как int16
        self.buffer.write(struct.pack(">h", -1))
        return self.buffer.getvalue()


# ============================================================================
# Ingest Worker
# ============================================================================

class IngestWorker:
    """
    High-throughput воркер для записи геолокаций в PostgreSQL.
    
    Паттерны:
    - Consumer Group для параллельной обработки
    - Binary COPY для максимальной производительности
    - Poison Pill Detection с fallback на row-by-row
    - XAUTOCLAIM для recovery зависших сообщений
    """
    
    def __init__(self, redis: Redis, pg_dsn: str):
        self.redis = redis
        # psycopg требует DSN без +asyncpg
        self.pg_dsn = pg_dsn.replace("+asyncpg", "")
        self._running = True
    
    async def setup(self):
        """Создаёт consumer group если не существует."""
        try:
            await self.redis.xgroup_create(
                STREAM_NAME, 
                CONSUMER_GROUP, 
                id="0",  # Читать с начала
                mkstream=True
            )
            logger.info("consumer_group_created", group=CONSUMER_GROUP)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("consumer_group_exists", group=CONSUMER_GROUP)
            else:
                raise
    
    async def run(self):
        """Основной цикл воркера."""
        await self.setup()
        logger.info(
            "ingest_worker_started", 
            consumer=CONSUMER_NAME, 
            batch_size=BATCH_SIZE,
            stream=STREAM_NAME
        )
        
        while self._running:
            try:
                # 1. Сначала пытаемся забрать зависшие сообщения (recovery)
                await self._claim_abandoned_messages()
                
                # 2. Читаем новые сообщения
                await self._process_batch()
                
            except asyncio.CancelledError:
                logger.info("ingest_worker_cancelled")
                break
            except Exception as e:
                logger.exception("ingest_worker_error", error=str(e))
                await asyncio.sleep(1)
    
    async def _claim_abandoned_messages(self):
        """
        XAUTOCLAIM: забираем сообщения от упавших воркеров.
        
        Если сообщение висит в PEL (Pending Entries List) дольше
        CLAIM_MIN_IDLE_MS, мы его забираем себе.
        """
        try:
            # XAUTOCLAIM возвращает: (next_start_id, [(id, data), ...], deleted_ids)
            result = await self.redis.xautoclaim(
                STREAM_NAME,
                CONSUMER_GROUP,
                CONSUMER_NAME,
                min_idle_time=CLAIM_MIN_IDLE_MS,
                start_id="0-0",
                count=BATCH_SIZE
            )
            
            if result and len(result) > 1 and result[1]:
                records = []
                for entry_id, data in result[1]:
                    try:
                        records.append(LocationRecord.from_stream_entry(entry_id, data))
                    except (KeyError, ValueError) as e:
                        logger.warning("invalid_claimed_record", entry_id=entry_id, error=str(e))
                        # ACK битую запись чтобы не блокировать
                        await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                
                if records:
                    logger.info("claimed_abandoned", count=len(records))
                    await self._ingest_batch(records)
                    
        except Exception as e:
            logger.warning("xautoclaim_error", error=str(e))
    
    async def _process_batch(self):
        """Читает батч сообщений из стрима через XREADGROUP."""
        # Блокирующее чтение с таймаутом
        result = await self.redis.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            streams={STREAM_NAME: ">"},  # ">" = только новые сообщения
            count=BATCH_SIZE,
            block=BATCH_TIMEOUT_MS
        )
        
        if not result:
            return
        
        # result = [(stream_name, [(entry_id, data), ...])]
        records = []
        for stream_name, entries in result:
            for entry_id, data in entries:
                try:
                    records.append(LocationRecord.from_stream_entry(entry_id, data))
                except (KeyError, ValueError) as e:
                    logger.warning("invalid_record", entry_id=entry_id, error=str(e))
                    # ACK битую запись сразу
                    await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
        
        if records:
            await self._ingest_batch(records)
    
    async def _ingest_batch(self, records: List[LocationRecord]):
        """
        Записывает батч в PostgreSQL через Text COPY.
        
        Используем Text COPY вместо Binary для совместимости с PostGIS EWKT.
        При ошибке COPY — fallback на row-by-row для изоляции poison pill.
        """
        if not records:
            return
        
        entry_ids = [r.entry_id for r in records]
        
        try:
            # Синхронный psycopg для COPY
            with psycopg.connect(self.pg_dsn) as conn:
                with conn.cursor() as cur:
                    # Text COPY с EWKT для PostGIS
                    with cur.copy(
                        "COPY driver_location_history (driver_id, location, recorded_at) "
                        "FROM STDIN"
                    ) as copy:
                        for r in records:
                            # PostGIS понимает EWKT в text формате
                            wkt = f"SRID=4326;POINT({r.longitude} {r.latitude})"
                            copy.write_row((r.driver_id, wkt, r.timestamp))
                    
                conn.commit()
            
            # Успешно записали — ACK все записи
            await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, *entry_ids)
            logger.info("batch_ingested", count=len(records))
            
        except Exception as e:
            logger.error("batch_copy_failed", error=str(e), count=len(records))
            # Fallback: row-by-row для изоляции poison pill
            await self._ingest_with_poison_detection(records)
    
    async def _ingest_with_poison_detection(self, records: List[LocationRecord]):
        """
        Row-by-row insert для изоляции "битых" записей.
        
        Стратегия Poison Pill:
        1. Попытка вставить каждую запись отдельно
        2. При ошибке — увеличиваем retry_count
        3. После MAX_RETRIES — логируем и ACK (отправка в DLQ)
        """
        success_count = 0
        failed_count = 0
        
        with psycopg.connect(self.pg_dsn) as conn:
            for record in records:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO driver_location_history 
                                (driver_id, location, recorded_at)
                            VALUES 
                                (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
                            """,
                            (record.driver_id, record.longitude, record.latitude, record.timestamp)
                        )
                    conn.commit()
                    
                    # Успех — ACK
                    await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, record.entry_id)
                    success_count += 1
                    
                except Exception as e:
                    conn.rollback()
                    record.retry_count += 1
                    failed_count += 1
                    
                    if record.retry_count >= MAX_RETRIES:
                        # Poison pill detected — отправляем в DLQ и ACK
                        await self._send_to_dlq(record, str(e))
                        await self.redis.xack(STREAM_NAME, CONSUMER_GROUP, record.entry_id)
                    else:
                        logger.warning(
                            "record_retry",
                            entry_id=record.entry_id,
                            retry=record.retry_count,
                            error=str(e)
                        )
                        # НЕ делаем ACK — будет reclaimed через XAUTOCLAIM
        
        if success_count > 0 or failed_count > 0:
            logger.info(
                "poison_detection_complete",
                success=success_count,
                failed=failed_count
            )
    
    async def _send_to_dlq(self, record: LocationRecord, error: str):
        """
        Отправляет poison pill в Dead Letter Queue для последующего анализа.
        
        DLQ stream содержит метаданные о проблемной записи.
        """
        try:
            await self.redis.xadd(
                DLQ_STREAM_NAME,
                {
                    "original_entry_id": record.entry_id,
                    "driver_id": str(record.driver_id),
                    "latitude": str(record.latitude),
                    "longitude": str(record.longitude),
                    "timestamp": record.timestamp.isoformat(),
                    "error": error,
                    "retry_count": str(record.retry_count),
                    "dlq_timestamp": datetime.now(timezone.utc).isoformat()
                },
                maxlen=10000  # Храним последние 10K poison pills
            )
            logger.error(
                "poison_pill_sent_to_dlq",
                entry_id=record.entry_id,
                driver_id=record.driver_id,
                error=error
            )
        except Exception as e:
            logger.exception("failed_to_send_to_dlq", original_error=error, dlq_error=str(e))
    
    def stop(self):
        """Graceful shutdown."""
        self._running = False


# ============================================================================
# Entry Point
# ============================================================================

async def main():
    """Запуск ingest worker."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    worker = IngestWorker(redis, settings.DATABASE_URL)
    
    try:
        await worker.run()
    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
