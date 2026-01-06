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
from src.database.models import Base, Driver, Order, DriverLocationHistory, DriverStatus


# Используем тестовую базу данных
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/tms_db", "/tms_test_db")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


from sqlalchemy.pool import NullPool

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
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
    Создает сессию для каждого теста с откатом транзакции.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
        
        await trans.rollback()


@pytest_asyncio.fixture
async def test_driver(session: AsyncSession) -> Driver:
    """Create a test driver."""
    driver = Driver(
        telegram_id=123456789,
        name="Test Driver",
        phone="+79001234567",
        status=DriverStatus.AVAILABLE,
        is_active=True
    )
    session.add(driver)
    await session.flush()
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
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database.uow import SQLAlchemyUnitOfWork
from src.api.dependencies import get_uow, get_current_driver

# Import OrderRepository and DriverRepository for TestUnitOfWork
from src.database.repository import DriverRepository, OrderRepository
from src.database.models import Order as OrderModel

@pytest_asyncio.fixture
async def client(session: AsyncSession, test_driver: Driver) -> AsyncGenerator[AsyncClient, None]:
    """Create async client for tests."""
    
    class TestUnitOfWork(SQLAlchemyUnitOfWork):
        async def __aenter__(self):
            self.session = session  # Use the one from fixture
            # Запускаем SAVEPOINT, чтобы ошибки (например, IntegrityError)
            # не ломали основную транзакцию теста
            self._savepoint = await self.session.begin_nested()
            self.drivers = DriverRepository(self.session, Driver)
            self.orders = OrderRepository(self.session, OrderModel)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                # Если было исключение, откатываем savepoint
                if self._savepoint.is_active:
                    await self._savepoint.rollback()
            else:
                # Если все ок, коммитим savepoint
                if self._savepoint.is_active:
                    await self._savepoint.commit()
        
        async def commit(self):
            try:
                await self.session.flush()
            except Exception:
                # Если flush упал (например constraints), откатываем savepoint
                if self._savepoint.is_active:
                    await self._savepoint.rollback()
                raise
        
        async def rollback(self):
            if self._savepoint.is_active:
                await self._savepoint.rollback()
        
    async def get_test_uow():
        return TestUnitOfWork()
        
    async def mock_get_current_driver():
        return test_driver

    app.dependency_overrides[get_uow] = get_test_uow
    app.dependency_overrides[get_current_driver] = mock_get_current_driver
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
