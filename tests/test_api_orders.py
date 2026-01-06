import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from starlette import status

from src.database.models import Driver

@pytest.mark.asyncio
async def test_create_overlapping_order_returns_409(
    client: AsyncClient, 
    test_driver: Driver
):
    """
    Тест: создание двух заказов с пересекающимся временем в одном API-запросе.
    Ожидаем, что второй запрос вернет 409 Conflict.
    """
    base_time = datetime(2025, 12, 1, 12, 0)
    
    # 1. Создаем первый заказ (12:00 - 14:00)
    order1_data = {
        "driver_id": test_driver.id,
        "time_start": base_time.isoformat(),
        "time_end": (base_time + timedelta(hours=2)).isoformat(),
        "pickup_lat": 43.1, "pickup_lon": 131.9,
        "dropoff_lat": 43.2, "dropoff_lon": 132.0,
        "priority": "normal"
    }
    
    response1 = await client.post("/api/v1/orders", json=order1_data)
    assert response1.status_code == status.HTTP_201_CREATED
    
    # 2. Пытаемся создать второй заказ, который пересекается (12:00:01 - ...)
    order2_data = {
        "driver_id": test_driver.id,
        "time_start": (base_time + timedelta(seconds=1)).isoformat(),
        "time_end": (base_time + timedelta(hours=3)).isoformat(),
        "pickup_lat": 43.1, "pickup_lon": 131.9,
        "dropoff_lat": 43.2, "dropoff_lon": 132.0,
        "priority": "high"
    }
    
    response2 = await client.post("/api/v1/orders", json=order2_data)
    
    # 3. Проверяем результат
    assert response2.status_code == status.HTTP_409_CONFLICT
    assert response2.json()["detail"]["error"] == "time_overlap"
    assert "занят" in response2.json()["detail"]["message"]

@pytest.mark.asyncio
async def test_move_order_overlap_returns_409(
    client: AsyncClient, 
    test_driver: Driver
):
    """Тест: перенос заказа на время, которое уже занято."""
    base_time = datetime(2025, 12, 1, 12, 0)
    
    # Заказ 1: 10:00 - 11:00
    await client.post("/api/v1/orders", json={
        "driver_id": test_driver.id,
        "time_start": (base_time - timedelta(hours=2)).isoformat(),
        "time_end": (base_time - timedelta(hours=1)).isoformat(),
        "pickup_lat": 43.1, "pickup_lon": 131.9,
        "dropoff_lat": 43.2, "dropoff_lon": 132.0
    })
    
    # Заказ 2: 14:00 - 15:00
    res2 = await client.post("/api/v1/orders", json={
        "driver_id": test_driver.id,
        "time_start": (base_time + timedelta(hours=2)).isoformat(),
        "time_end": (base_time + timedelta(hours=3)).isoformat(),
        "pickup_lat": 43.1, "pickup_lon": 131.9,
        "dropoff_lat": 43.2, "dropoff_lon": 132.0
    })
    order2_id = res2.json()["id"]
    
    # Пытаемся передвинуть Заказ 2 на 10:00:01 (пересекается с Заказом 1 который 10:00-...)
    response_move = await client.patch(f"/api/v1/orders/{order2_id}/move", json={
        "new_time_start": (base_time - timedelta(hours=2, seconds=-1)).isoformat(),
        "new_time_end": (base_time - timedelta(hours=1)).isoformat()
    })
    
    assert response_move.status_code == status.HTTP_409_CONFLICT
