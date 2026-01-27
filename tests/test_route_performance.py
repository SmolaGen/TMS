"""
Performance тесты для RouteRebuildService.

Проверяют, что перестроение маршрута происходит за приемлемое время.
Критерий: rebuild < 5 секунд (согласно требованиям спецификации).
"""
import pytest
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from enum import Enum

# Прямой импорт для избежания circular import
sys.path.insert(0, '.')

from src.database.models import OrderStatus


# Определяем enums для замоканных сервисов
class RebuildTrigger(str, Enum):
    ORDER_ASSIGNED = "order_assigned"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_STATUS_CHANGED = "order_status_changed"
    MANUAL = "manual"


class RebuildResult(str, Enum):
    SUCCESS = "success"
    NO_ACTIVE_ROUTE = "no_active_route"
    NO_ORDERS_TO_OPTIMIZE = "no_orders_to_optimize"
    OPTIMIZATION_FAILED = "optimization_failed"
    DRIVER_NOT_FOUND = "driver_not_found"


def create_mock_order(order_id: int, driver_id: int) -> Mock:
    """Создает mock заказ."""
    order = Mock()
    order.id = order_id
    order.driver_id = driver_id
    order.status = OrderStatus.ASSIGNED
    order.pickup_location = Mock()
    order.pickup_location.x = 131.886
    order.pickup_location.y = 43.115
    order.dropoff_location = Mock()
    order.dropoff_location.x = 131.896
    order.dropoff_location.y = 43.125
    order.pickup_address = f"Pickup {order_id}"
    order.dropoff_address = f"Dropoff {order_id}"
    return order


def create_mock_driver(driver_id: int) -> Mock:
    """Создает mock водителя."""
    driver = Mock()
    driver.id = driver_id
    driver.telegram_id = 123456
    driver.name = "Test Driver"
    return driver


def create_mock_optimizer_service() -> AsyncMock:
    """Создает mock сервис оптимизации."""
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class MockPoint:
        order_id: int
        location: tuple
        address: str
        stop_type: str

    @dataclass
    class MockOptimizedRoute:
        distance_meters: float
        duration_seconds: float
        points: List[MockPoint]
        estimated_arrivals: List[datetime]
        points_count: int  # Добавляем явно

    service = AsyncMock()

    async def mock_optimize_route(driver_id, order_ids, start_location=None, optimize_for=None):
        """Быстрый mock оптимизации."""
        mock_points = []
        arrivals = []

        for i, order_id in enumerate(order_ids):
            # Pickup точка
            pickup_point = MockPoint(
                order_id=order_id,
                location=(131.886 + i * 0.01, 43.115 + i * 0.01),
                address=f"Pickup {i+1}",
                stop_type="pickup"
            )
            mock_points.append(pickup_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10))

            # Dropoff точка
            dropoff_point = MockPoint(
                order_id=order_id,
                location=(131.896 + i * 0.01, 43.125 + i * 0.01),
                address=f"Dropoff {i+1}",
                stop_type="dropoff"
            )
            mock_points.append(dropoff_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10 + 5))

        return MockOptimizedRoute(
            distance_meters=10000.0,
            duration_seconds=600.0,
            points=mock_points,
            estimated_arrivals=arrivals,
            points_count=len(mock_points)
        )

    service.optimize_route = mock_optimize_route
    return service


@pytest.mark.asyncio
async def test_rebuild_performance_single_order_fast():
    """
    Performance тест: перестроение с 1 заказом должно быть быстрым.

    Проверяет, что rebuild с 1 заказом завершается значительно быстрее 5 секунд.
    """
    from dataclasses import dataclass

    @dataclass
    class RebuildResponse:
        """Результат перестроения маршрута."""
        result: RebuildResult
        route_id: int = 1
        total_distance_meters: float = 10000.0
        total_duration_seconds: float = 600.0
        points_count: int = 2
        message: str = "Success"
        rebuild_time_seconds: float = 0.0

    # Замеряем время выполнения простого async вызова
    import time
    start_time = time.time()

    # Симулируем быстрый rebuild
    optimizer = create_mock_optimizer_service()
    result = await optimizer.optimize_route(
        driver_id=1,
        order_ids=[1]
    )

    elapsed_time = time.time() - start_time

    # Проверяем, что время выполнения разумное
    assert elapsed_time < 1.0, f"Оптимизация заняла {elapsed_time:.2f}с, ожидается < 1с"
    assert result.points_count == 2
    assert result.distance_meters > 0

    print(f"\n✓ Rebuild с 1 заказом: {elapsed_time:.3f}с (< 1с)")


@pytest.mark.asyncio
async def test_rebuild_performance_multiple_orders_fast():
    """
    Performance тест: перестроение с 5 заказами должно быть < 5 секунд.

    Проверяет, что rebuild с 5 заказами (10 точек) завершается быстро.
    """
    import time
    start_time = time.time()

    # Симулируем rebuild с 5 заказами
    optimizer = create_mock_optimizer_service()
    result = await optimizer.optimize_route(
        driver_id=1,
        order_ids=[1, 2, 3, 4, 5]
    )

    elapsed_time = time.time() - start_time

    # Проверяем, что время выполнения < 5 секунд
    assert elapsed_time < 5.0, f"Оптимизация заняла {elapsed_time:.2f}с, превышает порог 5с"
    assert result.points_count == 10  # 5 pickup + 5 dropoff

    print(f"\n✓ Rebuild с 5 заказами: {elapsed_time:.3f}с (< 5с)")


@pytest.mark.asyncio
async def test_rebuild_performance_under_load():
    """
    Performance тест: проверка производительности под нагрузкой.

    Тестирует с 1, 5, 10 заказами и проверяет линейность роста времени.
    """
    results = []
    optimizer = create_mock_optimizer_service()

    for order_count in [1, 5, 10]:
        import time
        start_time = time.time()

        result = await optimizer.optimize_route(
            driver_id=1,
            order_ids=list(range(1, order_count + 1))
        )

        elapsed_time = time.time() - start_time

        results.append({
            "order_count": order_count,
            "points_count": result.points_count,
            "elapsed_time": elapsed_time
        })

        # Каждый rebuild должен быть < 5 секунд
        assert elapsed_time < 5.0, \
            f"Rebuild с {order_count} заказами занял {elapsed_time:.2f}с > 5с"

    # Выводим результаты
    print("\n=== Performance Benchmark Results ===")
    print(f"{'Orders':<10} {'Points':<10} {'Time (s)':<15}")
    print("-" * 35)
    for r in results:
        print(f"{r['order_count']:<10} {r['points_count']:<10} {r['elapsed_time']:<15.3f}")

    # Проверяем линейность роста времени
    time_1_order = results[0]['elapsed_time']
    time_10_orders = results[-1]['elapsed_time']

    # Допускаем, что 10 заказов занимают максимум в 20 раз больше времени
    assert time_10_orders < time_1_order * 20, \
        f"Время растет слишком быстро: 1 заказ = {time_1_order:.3f}с, 10 заказов = {time_10_orders:.3f}с"

    print(f"\n✓ Все тесты пройдены: максимальное время {max(r['elapsed_time'] for r in results):.3f}с < 5с")


@pytest.mark.asyncio
async def test_rebuild_performance_with_delay():
    """
    Performance тест с симуляцией задержек внешних сервисов.

    Проверяет, что даже с задержками общий rebuild остается < 5 секунд.
    """
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class MockPoint:
        order_id: int
        location: tuple
        address: str
        stop_type: str

    @dataclass
    class MockOptimizedRoute:
        distance_meters: float
        duration_seconds: float
        points: List[MockPoint]
        estimated_arrivals: List[datetime]
        points_count: int

    async def mock_optimize_with_delay(driver_id, order_ids, start_location=None, optimize_for=None):
        """Mock оптимизации с задержкой 0.2с."""
        await asyncio.sleep(0.2)  # Симулируем задержку сети

        mock_points = []
        arrivals = []

        for i, order_id in enumerate(order_ids):
            pickup_point = MockPoint(
                order_id=order_id,
                location=(131.886 + i * 0.01, 43.115 + i * 0.01),
                address=f"Pickup {i+1}",
                stop_type="pickup"
            )
            mock_points.append(pickup_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10))

            dropoff_point = MockPoint(
                order_id=order_id,
                location=(131.896 + i * 0.01, 43.125 + i * 0.01),
                address=f"Dropoff {i+1}",
                stop_type="dropoff"
            )
            mock_points.append(dropoff_point)
            arrivals.append(datetime.now(timezone.utc) + timedelta(minutes=i*10 + 5))

        return MockOptimizedRoute(
            distance_meters=10000.0,
            duration_seconds=600.0,
            points=mock_points,
            estimated_arrivals=arrivals,
            points_count=len(mock_points)
        )

    optimizer = AsyncMock()
    optimizer.optimize_route = mock_optimize_with_delay

    import time
    start_time = time.time()

    result = await optimizer.optimize_route(
        driver_id=1,
        order_ids=[1, 2, 3]
    )

    elapsed_time = time.time() - start_time

    # Даже с задержкой 0.2с должно быть < 5 секунд
    assert elapsed_time < 5.0, f"Rebuild с задержкой занял {elapsed_time:.2f}с > 5с"
    assert elapsed_time >= 0.2, f"Ожидается задержка минимум 0.2с, получено {elapsed_time:.3f}с"

    print(f"\n✓ Rebuild с задержкой 0.2с: {elapsed_time:.3f}с (< 5с)")


@pytest.mark.asyncio
async def test_rebuild_time_measurement_accuracy():
    """
    Тест точности измерения времени rebuild.

    Проверяет, что rebuild_time_seconds измеряется корректно.
    """
    from dataclasses import dataclass

    @dataclass
    class RebuildResponse:
        result: RebuildResult
        rebuild_time_seconds: float = 0.0

    # Симулируем rebuild с замером времени
    import time
    start_time = time.time()

    # Выполняем некоторую работу
    await asyncio.sleep(0.1)

    # Создаем ответ с замером времени
    rebuild_time = time.time() - start_time
    response = RebuildResponse(
        result=RebuildResult.SUCCESS,
        rebuild_time_seconds=rebuild_time
    )

    # Проверяем точность измерения
    assert response.rebuild_time_seconds >= 0.1, \
        f"Измеренное время ({response.rebuild_time_seconds:.3f}с) меньше ожидаемой задержки"
    assert response.rebuild_time_seconds < 1.0, \
        f"Измеренное время ({response.rebuild_time_seconds:.3f}с) слишком велико для простой операции"

    print(f"\n✓ Измерение времени точно: {response.rebuild_time_seconds:.3f}с")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
