# 🏗️ Архитектура Проекта TMS

---

## Общая Схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        КЛИЕНТЫ                                   │
├──────────────────┬──────────────────┬──────────────────────────┤
│   Web App        │   Telegram Bot   │   Mobile (PWA)           │
│   (Next.js)      │   (Aiogram)      │   (Next.js + TWA)        │
└────────┬─────────┴────────┬─────────┴──────────┬───────────────┘
         │                  │                    │
         └──────────────────┼────────────────────┘
                            │
                    ┌───────▼───────┐
                    │    Nginx      │
                    │   (Reverse    │
                    │    Proxy)     │
                    └───────┬───────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   ┌─────▼─────┐     ┌──────▼──────┐    ┌──────▼──────┐
   │  Frontend │     │   Backend   │    │  Telegram   │
   │  :3000    │     │   :8000     │    │   Bot       │
   └───────────┘     └──────┬──────┘    └──────┬──────┘
                            │                  │
                    ┌───────▼──────────────────▼───────┐
                    │                                   │
         ┌──────────┴──────────┐          ┌────────────┴───┐
         │                     │          │                │
   ┌─────▼─────┐        ┌──────▼─────┐   ┌▼────────┐  ┌────▼───┐
   │ PostgreSQL│        │   Redis     │   │  OSRM  │  │ Celery │
   │ + PostGIS │        │   (Cache)   │   │ (Maps) │  │(Tasks) │
   └───────────┘        └────────────┘   └─────────┘  └────────┘
```

---

## Слои Приложения

### 1. API Layer (Presentation)
**Путь:** `src/api/`

- Принимает HTTP запросы
- Валидирует входные данные (Pydantic)
- Вызывает Service Layer
- Форматирует ответы

```python
# src/api/v1/orders.py
@router.post("/orders")
async def create_order(data: OrderCreate) -> OrderResponse:
    return await order_service.create(data)
```

### 2. Service Layer (Business Logic)
**Путь:** `src/services/`

- Содержит бизнес-логику
- Оркестрирует операции
- Не знает о HTTP/FastAPI

```python
# src/services/order.py
class OrderService:
    async def create(self, data: OrderCreate) -> Order:
        # Бизнес-логика
        order = Order(**data.dict())
        await self.db.add(order)
        return order
```

### 3. Data Layer (Persistence)
**Путь:** `src/db/`

- Модели SQLAlchemy
- Репозитории (опционально)
- Миграции Alembic

```python
# src/db/models/order.py
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    status = Column(Enum(OrderStatus))
```

---

## Ключевые Модули

### Orders (Заказы)
```
src/api/v1/orders.py      # API endpoints
src/services/order.py     # Бизнес-логика
src/db/models/order.py    # ORM модель
src/schemas/order.py      # Pydantic схемы
```

### Users (Пользователи)
```
src/api/v1/users.py
src/services/user.py
src/db/models/user.py
src/schemas/user.py
```

### Shifts (Смены)
```
src/api/v1/shifts.py
src/services/shift.py
src/db/models/shift.py
src/schemas/shift.py
```

### Geolocation (Геолокация)
```
src/api/v1/geo.py
src/services/geo.py       # Работа с PostGIS
src/services/osrm.py      # Маршрутизация
```

---

## Frontend Архитектура

### App Router (Next.js 14)
```
frontend/src/app/
├── (auth)/               # Группа авторизации
│   ├── login/
│   └── register/
├── (dashboard)/          # Защищённые страницы
│   ├── orders/
│   ├── shifts/
│   └── settings/
├── api/                  # API routes (BFF)
└── layout.tsx            # Корневой layout
```

### Компоненты
```
frontend/src/components/
├── ui/                   # Базовые UI компоненты
│   ├── Button/
│   ├── Input/
│   └── Modal/
├── features/             # Фичевые компоненты
│   ├── OrderCard/
│   └── ShiftForm/
└── layouts/              # Layouts
    ├── Header/
    └── Sidebar/
```

---

## Потоки Данных

### Создание Заказа
```
1. User → Frontend (форма)
2. Frontend → POST /api/v1/orders
3. API Layer → Validate OrderCreate
4. Service Layer → Create Order
5. Data Layer → INSERT INTO orders
6. WebSocket → Notify drivers
7. Response → Frontend
```

### Обновление Геолокации
```
1. Telegram Bot → Получает location
2. Bot → POST /api/v1/geo/update
3. Service → UPDATE drivers SET location
4. Redis → Cache current position
5. WebSocket → Broadcast to dashboard
```

---

## Важные Паттерны

### Dependency Injection
```python
async def get_order_service(
    db: AsyncSession = Depends(get_db),
) -> OrderService:
    return OrderService(db)
```

### Repository Pattern (опционально)
```python
class OrderRepository:
    async def get_by_id(self, id: int) -> Order | None:
        return await self.db.get(Order, id)
```

### Event-Driven (для уведомлений)
```python
# При создании заказа
await event_bus.publish(OrderCreated(order_id=order.id))
```
