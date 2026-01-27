# RouteOptimizerService

Сервис для оптимизации multi-stop маршрутов с использованием TSP алгоритма.

## Алгоритм

Используется **жадный алгоритм Nearest Neighbour** для решения задачи коммивояжёра (TSP):

1. Старт с начальной точки (текущее положение водителя или pickup первого заказа)
2. На каждой итерации выбирается ближайшая непосещённая точка
3. Метрика оптимизации (время или расстояние) настраивается
4. Процесс продолжается пока не будут посещены все точки

## Использование

### Через API

```bash
curl -X POST http://localhost:8000/v1/routes/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": 1,
    "order_ids": [1, 2, 3],
    "start_location": {"lat": 43.115, "lon": 131.886},
    "optimize_for": "time"
  }'
```

### Программно

```python
from src.services.route_optimizer import RouteOptimizerService
from src.database.models import RouteOptimizationType

async with get_db() as db:
    service = RouteOptimizerService(session=db)

    route = await service.optimize_route(
        driver_id=1,
        order_ids=[1, 2, 3],
        start_location=(131.886, 43.115),  # (lon, lat)
        optimize_for=RouteOptimizationType.TIME
    )

    print(f"Route ID: {route.id}")
    print(f"Total distance: {route.total_distance_meters}m")
    print(f"Total duration: {route.total_duration_seconds}s")
    print(f"Points: {len(route.route_points)}")
```

## Метрики оптимизации

- **TIME** - оптимизация по времени в пути (учитывает трафик)
- **DISTANCE** - оптимизация по дистанции (кратчайший путь)

## Структура результата

```python
RouteOptimizeResponse(
    route_id=1,
    driver_id=1,
    status="planned",
    optimization_type="time",
    total_distance_meters=5000,
    total_distance_km=5.0,
    total_duration_seconds=300,
    total_duration_minutes=5.0,
    points=[
        RoutePointSchema(
            sequence=1,
            location={"lat": 43.115, "lon": 131.886},
            stop_type="pickup",
            order_id=1,
            estimated_arrival="2026-01-27T10:00:00"
        ),
        # ... больше точек
    ]
)
```

## Ограничения

- Требует запущенного OSRM сервера для расчёта маршрутов
- Использует жадный алгоритм (не гарантирует глобально оптимальное решение)
- Для большого количества точек (>15) рекомендуется использовать более сложные алгоритмы

## Обработка ошибок

- **DriverNotFoundError** - водитель не найден
- **OrdersNotFoundError** - один или несколько заказов не найдены
- **NoValidRouteError** - не удалось построить маршрут (нет доступных точек)
- **RouteOptimizerError** - общая ошибка оптимизации

## Зависимости

- `RoutingService` - для расчёта point-to-point маршрутов через OSRM
- `AsyncSession` - SQLAlchemy сессия для работы с БД
- `Route`, `RoutePoint`, `Order` - модели базы данных

## Testing

```bash
pytest tests/test_route_optimizer.py -v
```

Unit тесты покрывают:
- Подготовку точек из заказов
- TSP алгоритм nearest neighbour
- Обработку пустых списков точек
- Выбор метрики оптимизации
- Парсинг WKT геометрии
