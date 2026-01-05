"""
Tests for Order Time Overlap Prevention

Тесты на проверку Exclusion Constraint, который предотвращает
создание пересекающихся по времени заказов для одного водителя.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Driver, DriverStatus, Order, OrderStatus, OrderPriority
from tests.conftest import make_time_range


class TestOrderOverlapConstraint:
    """
    Тесты на Exclusion Constraint no_driver_time_overlap.
    
    Constraint гарантирует:
    - Один водитель НЕ может иметь два активных заказа с пересекающимся временем
    - Заказы разных водителей могут пересекаться
    - Смежные заказы (конец одного = начало другого) разрешены
    - Завершённые/отменённые заказы не блокируют новые
    """
    
    @pytest.mark.asyncio
    async def test_overlapping_orders_raises_integrity_error(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        """
        Тест: Создание двух заказов с пересекающимся временем 
        для одного водителя должно вызвать IntegrityError.
        
        Scenario:
        - Order 1: 10:00 - 12:00
        - Order 2: 11:00 - 13:00 (пересекается с Order 1)
        - Ожидаем: IntegrityError при попытке создать Order 2
        """
        # Arrange: Создаём первый заказ 10:00-12:00
        time_range_1 = make_time_range(10, 12)
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range_1}
        )
        await session.commit()
        
        # Act & Assert: Попытка создать пересекающийся заказ 11:00-13:00
        time_range_2 = make_time_range(11, 13)
        
        with pytest.raises(IntegrityError) as exc_info:
            await session.execute(
                text("""
                    INSERT INTO orders (driver_id, status, priority, time_range)
                    VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
                """),
                {"driver_id": test_driver.id, "time_range": time_range_2}
            )
            await session.commit()
        
        # Проверяем, что это именно ошибка exclusion constraint
        assert "no_driver_time_overlap" in str(exc_info.value)
        await session.rollback()
    
    @pytest.mark.asyncio
    async def test_adjacent_orders_allowed(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        """
        Тест: Смежные заказы (без пересечения) должны быть разрешены.
        
        Scenario:
        - Order 1: 10:00 - 12:00
        - Order 2: 12:00 - 14:00 (начинается, когда заканчивается Order 1)
        - Ожидаем: Оба заказа успешно созданы
        
        Note: tstzrange использует полуоткрытый интервал [start, end),
        поэтому 12:00 не входит в первый интервал.
        """
        # Arrange & Act: Создаём два смежных заказа
        time_range_1 = make_time_range(10, 12)
        time_range_2 = make_time_range(12, 14)
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range_1}
        )
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range_2}
        )
        
        await session.commit()
        
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
        """
        Тест: Пересекающиеся заказы для РАЗНЫХ водителей должны быть разрешены.
        
        Scenario:
        - Driver 1, Order: 10:00 - 12:00
        - Driver 2, Order: 10:00 - 12:00 (то же время, другой водитель)
        - Ожидаем: Оба заказа успешно созданы
        """
        # Arrange: Создаём второго водителя
        driver2 = Driver(
            telegram_id=987654321,
            name="Driver Two",
            phone="+79009876543",
            status=DriverStatus.AVAILABLE,
        )
        session.add(driver2)
        await session.commit()
        await session.refresh(driver2)
        
        # Act: Создаём заказы с одинаковым временем для разных водителей
        time_range = make_time_range(10, 12)
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range}
        )
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": driver2.id, "time_range": time_range}
        )
        
        await session.commit()
        
        # Assert: Проверяем, что оба заказа созданы
        result = await session.execute(
            text("SELECT COUNT(*) FROM orders WHERE time_range = :time_range::tstzrange"),
            {"time_range": time_range}
        )
        count = result.scalar()
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_completed_order_allows_overlap(
        self,
        session: AsyncSession,
        test_driver: Driver
    ):
        """
        Тест: Завершённый заказ НЕ должен блокировать новый с тем же временем.
        
        Scenario:
        - Order 1: 10:00 - 12:00, status='completed'
        - Order 2: 10:00 - 12:00, status='assigned'
        - Ожидаем: Order 2 успешно создан (завершённый заказ не блокирует)
        """
        # Arrange: Создаём завершённый заказ
        time_range = make_time_range(10, 12)
        
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'completed', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range}
        )
        await session.commit()
        
        # Act: Создаём новый активный заказ с тем же временем
        await session.execute(
            text("""
                INSERT INTO orders (driver_id, status, priority, time_range)
                VALUES (:driver_id, 'assigned', 'normal', :time_range::tstzrange)
            """),
            {"driver_id": test_driver.id, "time_range": time_range}
        )
        await session.commit()
        
        # Assert: Проверяем, что оба заказа созданы
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM orders 
                WHERE driver_id = :driver_id AND time_range = :time_range::tstzrange
            """),
            {"driver_id": test_driver.id, "time_range": time_range}
        )
        count = result.scalar()
        assert count == 2
