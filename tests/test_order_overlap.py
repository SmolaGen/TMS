"""
Tests for Order Time Overlap Prevention

Тесты на проверку Exclusion Constraint, который предотвращает
создание пересекающихся по времени заказов для одного водителя.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Driver, DriverStatus, Order, OrderStatus, OrderPriority

def get_time_range_dates(start_hour: int, end_hour: int, days_offset: int = 0):
    """
    Helper возвращает кортеж (start, end) datetime объектов.
    """
    base_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=days_offset)
    
    start = base_date.replace(hour=start_hour)
    end = base_date.replace(hour=end_hour)
    return start, end


class TestOrderOverlapConstraint:
    """
    Тесты на Exclusion Constraint no_driver_time_overlap.
    """
    
    @pytest.mark.asyncio
    async def test_overlapping_orders_raises_integrity_error(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        # Arrange: Создаём первый заказ 10:00-12:00
        start1, end1 = get_time_range_dates(10, 12)
        
        stmt = text("""
            INSERT INTO orders (driver_id, status, priority, time_range)
            VALUES (:driver_id, 'assigned', 'normal', tstzrange(:start, :end, '[)'))
        """)
        
        await session.execute(stmt, {
            "driver_id": test_driver.id, 
            "start": start1, 
            "end": end1
        })
        await session.flush()
        
        # Act & Assert: Попытка создать пересекающийся заказ 11:00-13:00
        start2, end2 = get_time_range_dates(11, 13)
        
        with pytest.raises(IntegrityError) as exc_info:
            await session.execute(stmt, {
                "driver_id": test_driver.id, 
                "start": start2, 
                "end": end2
            })
            await session.flush()
        
        assert "no_driver_time_overlap" in str(exc_info.value)
        await session.rollback()
    
    @pytest.mark.asyncio
    async def test_adjacent_orders_allowed(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        # Arrange & Act: Создаём два смежных заказа
        start1, end1 = get_time_range_dates(10, 12)
        start2, end2 = get_time_range_dates(12, 14)
        
        stmt = text("""
            INSERT INTO orders (driver_id, status, priority, time_range)
            VALUES (:driver_id, 'assigned', 'normal', tstzrange(:start, :end, '[)'))
        """)
        
        await session.execute(stmt, {
            "driver_id": test_driver.id, 
            "start": start1, 
            "end": end1
        })
        await session.execute(stmt, {
            "driver_id": test_driver.id, 
            "start": start2, 
            "end": end2
        })
        await session.flush()
        
        # Assert: Проверяем, что оба заказа созданы
        result = await session.execute(
            text("SELECT COUNT(*) FROM orders WHERE driver_id = :driver_id"),
            {"driver_id": test_driver.id}
        )
        count = result.scalar()
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_different_drivers_overlapping_allowed(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        # Arrange: Создаём второго водителя
        driver2 = Driver(
            telegram_id=987654321,
            name="Driver Two",
            phone="+79009876543",
            status=DriverStatus.AVAILABLE,
            is_active=True
        )
        session.add(driver2)
        await session.flush()
        await session.refresh(driver2)
        
        # Act: Создаём заказы с одинаковым временем для разных водителей
        start, end = get_time_range_dates(10, 12)
        
        stmt = text("""
            INSERT INTO orders (driver_id, status, priority, time_range)
            VALUES (:driver_id, 'assigned', 'normal', tstzrange(:start, :end, '[)'))
        """)
        
        await session.execute(stmt, {
            "driver_id": test_driver.id, 
            "start": start, 
            "end": end
        })
        await session.execute(stmt, {
            "driver_id": driver2.id, 
            "start": start, 
            "end": end
        })
        await session.flush()
        
        # Assert: Проверяем, что оба заказа созданы (проверяем по времени)
        result = await session.execute(
            text("SELECT COUNT(*) FROM orders WHERE time_range = tstzrange(:start, :end, '[)')"),
            {"start": start, "end": end}
        )
        count = result.scalar()
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_completed_order_allows_overlap(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        # Arrange: Создаём завершённый заказ
        start, end = get_time_range_dates(10, 12)
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'completed', 'normal', tstzrange(:start, :end, '[)'))
            """),
            {
                "driver_id": test_driver.id, 
                "start": start, 
                "end": end
            }
        )
        await session.flush()
        
        # Act: Создаём новый активный заказ с тем же временем
        stmt_assigned = text("""
            INSERT INTO orders (driver_id, status, priority, time_range)
            VALUES (:driver_id, 'assigned', 'normal', tstzrange(:start, :end, '[)'))
        """)
        
        await session.execute(stmt_assigned, {
            "driver_id": test_driver.id, 
            "start": start, 
            "end": end
        })
        await session.flush()
        
        # Assert: Проверяем, что оба заказа созданы
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM orders 
                WHERE driver_id = :driver_id AND time_range = tstzrange(:start, :end, '[)')
            """),
            {
                "driver_id": test_driver.id, 
                "start": start, 
                "end": end
            }
        )
        count = result.scalar()
        assert count == 2
