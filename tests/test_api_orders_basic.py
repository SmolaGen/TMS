import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from starlette import status
from src.database.models import Driver

@pytest.mark.asyncio
async def test_order_lifecycle_basic(client: AsyncClient, test_driver: Driver):
    """Тест базового жизненного цикла заказа через API."""
    base_time = datetime.utcnow() + timedelta(hours=1)
    
    # 1. Создание заказа
    order_data = {
        "driver_id": test_driver.id,
        "time_start": base_time.isoformat(),
        "time_end": (base_time + timedelta(hours=1)).isoformat(),
        "pickup_lat": 43.1, "pickup_lon": 131.9,
        "dropoff_lat": 43.2, "dropoff_lon": 132.0,
        "pickup_address": "Ул. Пушкина, 1",
        "dropoff_address": "Ул. Колотушкина, 2"
    }
    
    response = await client.post("/api/v1/orders", json=order_data)
    assert response.status_code == status.HTTP_201_CREATED
    order = response.json()
    order_id = order["id"]
    assert order["status"] == "pending"
    
    # 2. Получение заказа
    response = await client.get(f"/api/v1/orders/{order_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["pickup_address"] == "Ул. Пушкина, 1"

    # 3. Список заказов
    response = await client.get("/api/v1/orders")
    assert response.status_code == status.HTTP_200_OK
    orders = response.json()
    assert any(o["id"] == order_id for o in orders)

@pytest.mark.asyncio
async def test_get_active_orders(client: AsyncClient, test_driver: Driver):
    """Тест получения активных заказов."""
    response = await client.get("/api/v1/orders/active")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
