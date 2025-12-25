"""
Pytest Configuration and Fixtures

Фикстуры для тестирования с async PostgreSQL.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import sys
from unittest.mock import MagicMock

try:
    import geoalchemy2
except ImportError:
    mock_geo = MagicMock()
    sys.modules["geoalchemy2"] = mock_geo
    sys.modules["geoalchemy2.functions"] = mock_geo

from sqlalchemy import text

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings
from src.database.models import Base, Driver, DriverStatus


# Используем тестовую базу данных
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/tms_db", "/tms_test_db")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine):
    """
    Setup test database - create extensions and tables.
    
    Выполняется один раз для всей сессии тестов.
    """
    async with engine.begin() as conn:
        # Создаём расширения
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        
        # Создаём таблицы
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
        # Добавляем колонку time_range вручную (т.к. её нет в модели напрямую)
        await conn.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN IF NOT EXISTS time_range tstzrange;
        """))
        
        # Добавляем exclusion constraint
        await conn.execute(text("""
            ALTER TABLE orders DROP CONSTRAINT IF EXISTS no_driver_time_overlap;
        """))
        await conn.execute(text("""
            ALTER TABLE orders ADD CONSTRAINT no_driver_time_overlap
            EXCLUDE USING gist (
                driver_id WITH =,
                time_range WITH &&
            )
            WHERE (
                driver_id IS NOT NULL 
                AND status NOT IN ('completed', 'cancelled')
            );
        """))
    
    yield
    
    # Cleanup после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session(engine, setup_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async session for each test.
    
    Каждый тест получает чистую транзакцию, которая откатывается после теста.
    """
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_driver(session: AsyncSession) -> Driver:
    """Create a test driver."""
    driver = Driver(
        telegram_id=123456789,
        name="Test Driver",
        phone="+79001234567",
        status=DriverStatus.AVAILABLE,
    )
    session.add(driver)
    await session.commit()
    await session.refresh(driver)
    return driver


def make_time_range(start_hour: int, end_hour: int, days_offset: int = 0) -> str:
    """
    Helper для создания tstzrange строки.
    
    Args:
        start_hour: Час начала (0-23)
        end_hour: Час окончания (0-23)
        days_offset: Смещение в днях от текущей даты
    
    Returns:
        Строка tstzrange для использования в SQL
    """
    base_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_offset)
    
    start = base_date.replace(hour=start_hour)
    end = base_date.replace(hour=end_hour)
    
    return f"[{start.isoformat()},{end.isoformat()})"
