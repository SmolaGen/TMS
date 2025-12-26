import asyncio
import argparse
import httpx
import time
from datetime import datetime, timezone

async def simulate_driver(
    driver_id: int, 
    endpoint: str, 
    start_lat: float, 
    start_lon: float,
    steps: int = 10,
    interval: float = 2.0
):
    """
    Симулирует движение водителя, отправляя координаты в бота (через webhook API).
    """
    print(f"🚀 Запуск симуляции для водителя #{driver_id}")
    print(f"📍 Старт: {start_lat}, {start_lon}")
    
    async with httpx.AsyncClient() as client:
        for i in range(steps):
            # Простейшее смещение для имитации движения
            lat = start_lat + (i * 0.0001)
            lon = start_lon + (i * 0.0001)
            
            # Формируем структуру Update, похожую на Telegram
            update = {
                "update_id": int(time.time() * 1000) + i,
                "message": {
                    "message_id": 100 + i,
                    "from": {
                        "id": 12345678, # Должен совпадать с telegram_id в БД для прохода AuthMiddleware
                        "is_bot": False,
                        "first_name": "Test Driver"
                    },
                    "chat": {"id": 12345678, "type": "private"},
                    "date": int(time.time()),
                    "location": {
                        "latitude": lat,
                        "longitude": lon
                    }
                }
            }
            
            try:
                response = await client.post(endpoint, json=update)
                print(f"[{i+1}/{steps}] {lat:.6f}, {lon:.6f} -> Status: {response.status_code}")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")
            
            await asyncio.sleep(interval)

    print("✅ Симуляция завершена")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver-id", type=int, default=1)
    parser.add_argument("--endpoint", type=str, default="http://localhost:8000/bot/webhook")
    parser.add_argument("--lat", type=float, default=43.115)
    parser.add_argument("--lon", type=float, default=131.885)
    parser.add_argument("--steps", type=int, default=10)
    
    args = parser.parse_args()
    
    asyncio.run(simulate_driver(
        args.driver_id, 
        args.endpoint, 
        args.lat, 
        args.lon, 
        args.steps
    ))
