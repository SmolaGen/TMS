# Планы тестирования TMS

## Оглавление

1. [Управление заказами (Order Management)](#1-управление-заказами-order-management)
2. [Управление водителями (Driver Management)](#2-управление-водителями-driver-management)
3. [Аутентификация и авторизация (Auth)](#3-аутентификация-и-авторизация-auth)
4. [Геосервисы (Geo Services)](#4-геосервисы-geo-services)
5. [Интеграции (Integrations)](#5-интеграции-integrations)
6. [Telegram бот (Bot)](#6-telegram-бот-bot)
7. [Background Workers](#7-background-workers)
8. [Frontend (React SPA)](#8-frontend-react-spa)

---

## 1. Управление заказами (Order Management)

### 1.1 Область тестирования

- `OrderService` — CRUD операции
- `OrderWorkflowService` — машина состояний
- `BatchAssignmentService` — массовое распределение
- `UrgentAssignmentService` — срочные заказы
- `ExcelImportService` — импорт из Excel
- Exclusion Constraint (no_driver_time_overlap)

### 1.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| ORD-U-001 | `OrderService.create_order()` с валидными данными | Заказ создан, статус PENDING/ASSIGNED, рассчитана цена |
| ORD-U-002 | `OrderService.create_order()` без координат | ValidationError |
| ORD-U-003 | `OrderService.move_order()` изменение времени | Обновлён time_range |
| ORD-U-004 | `OrderService.move_order()` смена водителя | driver_id обновлён, статус корректен |
| ORD-U-005 | `OrderStateMachine` PENDING → ASSIGNED | Переход успешен |
| ORD-U-006 | `OrderStateMachine` PENDING → IN_PROGRESS | TransitionNotAllowed |
| ORD-U-007 | `OrderStateMachine` ASSIGNED → EN_ROUTE_PICKUP | Переход успешен |
| ORD-U-008 | `OrderStateMachine` EN_ROUTE_PICKUP → DRIVER_ARRIVED | arrived_at заполнен |
| ORD-U-009 | `OrderStateMachine` DRIVER_ARRIVED → IN_PROGRESS | started_at заполнен |
| ORD-U-010 | `OrderStateMachine` IN_PROGRESS → COMPLETED | end_time заполнен, водитель AVAILABLE |
| ORD-U-011 | `OrderStateMachine` любой статус → CANCELLED | cancelled_at заполнен, reason сохранён |
| ORD-U-012 | `BatchAssignmentService.assign_orders_batch()` | Заказы распределены по водителям |
| ORD-U-013 | `BatchAssignmentService.preview_assignments()` | Возвращает preview без изменений в БД |
| ORD-U-014 | `UrgentAssignmentService.assign_urgent_order()` | Найден ближайший водитель |
| ORD-U-015 | `ExcelImportService.parse_excel()` валидный файл | Список OrderCreate DTO |
| ORD-U-016 | `ExcelImportService.parse_excel()` невалидный формат | ImportError с деталями |

### 1.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| ORD-I-001 | POST `/v1/orders` создание заказа | 201, заказ в БД |
| ORD-I-002 | GET `/v1/orders` список заказов | 200, массив заказов |
| ORD-I-003 | GET `/v1/orders/{id}` деталь заказа | 200, полные данные |
| ORD-I-004 | PATCH `/v1/orders/{id}/move` перемещение | 200, время обновлено |
| ORD-I-005 | POST `/v1/orders/{id}/assign/{driver_id}` | 200, статус ASSIGNED |
| ORD-I-006 | POST `/v1/orders/{id}/arrive` | 200, статус DRIVER_ARRIVED |
| ORD-I-007 | POST `/v1/orders/{id}/start` | 200, статус IN_PROGRESS |
| ORD-I-008 | POST `/v1/orders/{id}/complete` | 200, статус COMPLETED |
| ORD-I-009 | POST `/v1/orders/{id}/cancel` | 200, статус CANCELLED |
| ORD-I-010 | POST `/v1/orders/import/excel` | 200, imported_count > 0 |
| ORD-I-011 | POST `/v1/orders/batch-assign` | 200, assigned_count > 0 |
| ORD-I-012 | GET `/v1/orders/unassigned/{date}` | 200, список нераспределённых |

### 1.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| ORD-E-001 | Создание заказа с пересечением времени у водителя | 409 Conflict (Exclusion Constraint) |
| ORD-E-002 | Перемещение заказа в занятый слот | 409 Conflict |
| ORD-E-003 | Назначение на OFFLINE водителя | 400 Bad Request |
| ORD-E-004 | Завершение уже завершённого заказа | TransitionNotAllowed |
| ORD-E-005 | Создание заказа в прошлом | 400 Bad Request |
| ORD-E-006 | Excel с дубликатами external_id | Частичный импорт, ошибки в отчёте |
| ORD-E-007 | Batch assignment без доступных водителей | 0 assigned, все в unassigned |
| ORD-E-008 | URGENT заказ без водителей в радиусе | Остаётся PENDING |

### 1.5 Тестовые данные

```python
# Валидный заказ
valid_order = {
    "pickup_lat": 43.1155,
    "pickup_lon": 131.8855,
    "dropoff_lat": 43.1200,
    "dropoff_lon": 131.9000,
    "pickup_address": "ул. Светланская, 1",
    "dropoff_address": "ул. Алеутская, 10",
    "time_start": "2024-01-15T10:00:00+10:00",
    "priority": "normal",
    "customer_name": "Иван Иванов",
    "customer_phone": "+79001234567"
}

# Пересекающийся заказ (для теста overlap)
overlapping_order = {
    **valid_order,
    "driver_id": 1,
    "time_start": "2024-01-15T10:30:00+10:00"  # Пересекается с 10:00-11:00
}
```

### 1.6 Критерии успеха

- [ ] 100% unit-тестов проходят
- [ ] 100% integration-тестов проходят
- [ ] 100% edge cases обработаны корректно
- [ ] 100% code coverage для OrderService
- [ ] 100% code coverage для OrderWorkflowService
- [ ] 100% code coverage для BatchAssignmentService
- [ ] 100% code coverage для UrgentAssignmentService
- [ ] 100% code coverage для ExcelImportService
- [ ] Exclusion Constraint работает на уровне БД
- [ ] Машина состояний не допускает невалидных переходов

---

## 2. Управление водителями (Driver Management)

### 2.1 Область тестирования

- `DriverService` — CRUD, статистика
- `LocationManager` — real-time геолокация
- Модель `Driver` — статусы, роли
- `DriverLocationHistory` — история перемещений

### 2.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| DRV-U-001 | `DriverService.register_driver()` | Водитель создан с ролью PENDING |
| DRV-U-002 | `DriverService.register_driver()` дубликат telegram_id | ValueError |
| DRV-U-003 | `DriverService.get_driver()` существующий | Данные водителя |
| DRV-U-004 | `DriverService.get_driver()` несуществующий | None |
| DRV-U-005 | `DriverService.update_driver()` изменение имени | Имя обновлено |
| DRV-U-006 | `DriverService.update_driver()` изменение статуса | Статус обновлён |
| DRV-U-007 | `DriverService.get_driver_stats()` | Статистика за период |
| DRV-U-008 | `DriverService.get_all_drivers()` | Список всех водителей |
| DRV-U-009 | `LocationManager.update_driver_location()` | Координаты в Redis |
| DRV-U-010 | `LocationManager.get_active_drivers()` | Список активных с координатами |
| DRV-U-011 | `LocationManager.get_driver_location()` | Координаты конкретного водителя |
| DRV-U-012 | `LocationManager.find_nearest_drivers()` | Отсортированный по расстоянию список |
| DRV-U-013 | `LocationManager` TTL истёк | Водитель не в активных |

### 2.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| DRV-I-001 | POST `/v1/drivers` регистрация | 201, водитель создан |
| DRV-I-002 | GET `/v1/drivers` список | 200, массив водителей |
| DRV-I-003 | GET `/v1/drivers/{id}` детали | 200, данные водителя |
| DRV-I-004 | PATCH `/v1/drivers/{id}` обновление | 200, данные обновлены |
| DRV-I-005 | GET `/v1/drivers/{id}/stats` статистика | 200, stats объект |
| DRV-I-006 | GET `/v1/drivers/{id}/schedule/{date}` расписание | 200, список заказов |
| DRV-I-007 | POST `/v1/drivers/{id}/location` обновление геопозиции | 204 No Content |
| DRV-I-008 | GET `/v1/drivers/live` активные водители | 200, список с координатами |

### 2.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| DRV-E-001 | Регистрация с невалидным telegram_id | 400 Bad Request |
| DRV-E-002 | Обновление чужого профиля (не админ) | 403 Forbidden |
| DRV-E-003 | Обновление геопозиции чужой | 403 Forbidden |
| DRV-E-004 | Rate limit на /location (>30/min) | 429 Too Many Requests |
| DRV-E-005 | Деактивированный водитель (is_active=false) | Не может логиниться |
| DRV-E-006 | Водитель с ролью PENDING | Ограниченный доступ |
| DRV-E-007 | find_nearest_drivers() без активных | Пустой список |
| DRV-E-008 | Статистика за 0 дней | Пустая статистика |

### 2.5 Тестовые данные

```python
# Валидный водитель
valid_driver = {
    "telegram_id": 123456789,
    "name": "Иван Петров",
    "phone": "+79001234567"
}

# Геолокация
location_update = {
    "latitude": 43.1155,
    "longitude": 131.8855,
    "status": "available",
    "timestamp": "2024-01-15T10:00:00+10:00"
}
```

### 2.6 Критерии успеха

- [ ] 100% unit-тестов проходят
- [ ] 100% integration-тестов проходят
- [ ] 100% edge cases обработаны корректно
- [ ] 100% code coverage для DriverService
- [ ] 100% code coverage для LocationManager
- [ ] Redis хранит геолокацию с TTL
- [ ] Rate limiting работает
- [ ] Статистика считается правильно
- [ ] Роли и права проверяются

---

## 3. Аутентификация и авторизация (Auth)

### 3.1 Область тестирования

- `AuthService` — валидация Telegram initData, JWT
- Роли: driver, dispatcher, admin, pending
- Middleware авторизации
- Защищённые эндпоинты

### 3.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| AUTH-U-001 | `AuthService.validate_init_data()` валидная подпись | user_data dict |
| AUTH-U-002 | `AuthService.validate_init_data()` невалидная подпись | HTTPException 401 |
| AUTH-U-003 | `AuthService.validate_init_data()` истёкший auth_date | HTTPException 401 |
| AUTH-U-004 | `AuthService.create_access_token()` | JWT строка |
| AUTH-U-005 | `AuthService.verify_token()` валидный | payload dict |
| AUTH-U-006 | `AuthService.verify_token()` истёкший | HTTPException 401 |
| AUTH-U-007 | `AuthService.verify_token()` невалидная подпись | HTTPException 401 |
| AUTH-U-008 | `AuthService.get_token_response()` | TokenResponse с access_token |

### 3.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| AUTH-I-001 | POST `/v1/auth/login` валидный initData | 200, TokenResponse |
| AUTH-I-002 | POST `/v1/auth/login` невалидный initData | 401 Unauthorized |
| AUTH-I-003 | GET `/v1/orders` без токена | 401 Unauthorized |
| AUTH-I-004 | GET `/v1/orders` с валидным токеном | 200 OK |
| AUTH-I-005 | GET `/v1/orders` с истёкшим токеном | 401 Unauthorized |
| AUTH-I-006 | POST `/v1/orders/batch-assign` роль DRIVER | 403 Forbidden |
| AUTH-I-007 | POST `/v1/orders/batch-assign` роль DISPATCHER | 200 OK |
| AUTH-I-008 | POST `/v1/orders/batch-assign` роль ADMIN | 200 OK |

### 3.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| AUTH-E-001 | Первый вход нового пользователя | Авто-регистрация с ролью PENDING |
| AUTH-E-002 | Вход деактивированного пользователя | 403 Forbidden |
| AUTH-E-003 | Токен с несуществующим user_id | 401 Unauthorized |
| AUTH-E-004 | Malformed JWT | 401 Unauthorized |
| AUTH-E-005 | initData старше 24 часов | 401 Unauthorized |
| AUTH-E-006 | PENDING пользователь доступ к /orders | Ограниченный доступ |

### 3.5 Тестовые данные

```python
# Валидный initData (для тестов нужно генерировать с правильной подписью)
# В тестах используется мок или тестовый BOT_TOKEN

# JWT payload
jwt_payload = {
    "sub": "123",  # driver_id
    "telegram_id": 123456789,
    "role": "driver",
    "exp": datetime.utcnow() + timedelta(hours=24)
}
```

### 3.6 Критерии успеха

- [ ] 100% unit-тестов проходят
- [ ] 100% integration-тестов проходят
- [ ] 100% edge cases обработаны корректно
- [ ] 100% code coverage для AuthService
- [ ] Telegram initData валидируется криптографически
- [ ] JWT создаётся и проверяется корректно
- [ ] Все защищённые эндпоинты требуют авторизации
- [ ] Роли проверяются для привилегированных операций
- [ ] Авто-регистрация работает

---

## 4. Геосервисы (Geo Services)

### 4.1 Область тестирования

- `RoutingService` — маршрутизация через OSRM
- `GeocodingService` — геокодинг через Photon
- Расчёт цены на основе расстояния
- PostGIS операции

### 4.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| GEO-U-001 | `RoutingService.calculate_route()` валидные точки | RouteResult с distance/duration |
| GEO-U-002 | `RoutingService.calculate_route()` точки в океане | RouteNotFoundError |
| GEO-U-003 | `RoutingService.get_route_with_price()` | RouteResult + PriceResult |
| GEO-U-004 | `RoutingService` OSRM недоступен | OSRMUnavailableError |
| GEO-U-005 | `GeocodingService.search()` валидный адрес | List[GeocodingResult] |
| GEO-U-006 | `GeocodingService.search()` пустой запрос | Пустой список |
| GEO-U-007 | `GeocodingService.reverse()` валидные координаты | GeocodingResult |
| GEO-U-008 | `GeocodingService.reverse()` координаты в океане | None |
| GEO-U-009 | Расчёт цены: базовая + за км | Корректная сумма |
| GEO-U-010 | Расчёт цены: минимальная цена | Не ниже минимума |

### 4.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| GEO-I-001 | GET `/v1/routing/route` валидные координаты | 200, RouteResponse |
| GEO-I-002 | GET `/v1/routing/route` невозможный маршрут | 404 Not Found |
| GEO-I-003 | GET `/v1/geocoding/search?q=Владивосток` | 200, массив результатов |
| GEO-I-004 | GET `/v1/geocoding/reverse?lat=43.11&lon=131.88` | 200, GeocodingResult |
| GEO-I-005 | Создание заказа с расчётом маршрута | Заказ с distance_meters, duration_seconds |

### 4.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| GEO-E-001 | OSRM timeout | 503 Service Unavailable |
| GEO-E-002 | Photon timeout | Пустой результат или fallback |
| GEO-E-003 | Координаты за пределами региона OSRM | RouteNotFoundError |
| GEO-E-004 | Очень длинный маршрут (>500 км) | Успешный расчёт |
| GEO-E-005 | Одинаковые origin и destination | Маршрут 0 метров |
| GEO-E-006 | Невалидные координаты (lat > 90) | 400 Bad Request |

### 4.5 Тестовые данные

```python
# Владивосток — центр
vladivostok_center = (43.1155, 131.8855)

# Владивосток — аэропорт
vladivostok_airport = (43.3969, 132.1481)

# Ожидаемое расстояние: ~45 км
expected_distance_range = (40000, 50000)  # метры

# Тарифы
TARIFF = {
    "base_price": 100,
    "price_per_km": 40,
    "min_price": 200
}
```

### 4.6 Критерии успеха

- [ ] 100% unit-тестов проходят
- [ ] 100% integration-тестов проходят
- [ ] 100% edge cases обработаны корректно
- [ ] 100% code coverage для RoutingService
- [ ] 100% code coverage для GeocodingService
- [ ] Маршруты рассчитываются через OSRM
- [ ] Геокодинг работает для региона
- [ ] Цены рассчитываются корректно
- [ ] Graceful degradation при недоступности сервисов
- [ ] Координаты валидируются

---

## 5. Интеграции (Integrations)

### 5.1 Область тестирования

- `WebhookService` — уведомление подрядчиков
- `NotificationService` — Telegram push-уведомления
- Contractor API — внешний API для подрядчиков
- API-ключи и аутентификация

### 5.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| INT-U-001 | `WebhookService.notify_status_change()` | HTTP POST на webhook_url |
| INT-U-002 | `WebhookService` webhook_url не задан | Пропуск без ошибки |
| INT-U-003 | `WebhookService` webhook недоступен | Логирование ошибки, без исключения |
| INT-U-004 | `WebhookService` retry при 5xx | Повторная попытка |
| INT-U-005 | `NotificationService.notify_order_assigned()` | Telegram сообщение отправлено |
| INT-U-006 | `NotificationService.notify_order_cancelled()` | Telegram сообщение отправлено |
| INT-U-007 | `NotificationService` бот не инициализирован | Пропуск без ошибки |

### 5.3 Integration-тесты (Contractor API)

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| INT-I-001 | POST `/v1/contractors/orders` с API-ключом | 201, заказ создан |
| INT-I-002 | POST `/v1/contractors/orders` без API-ключа | 401 Unauthorized |
| INT-I-003 | POST `/v1/contractors/orders` невалидный ключ | 401 Unauthorized |
| INT-I-004 | GET `/v1/contractors/orders` список своих заказов | 200, только свои заказы |
| INT-I-005 | GET `/v1/contractors/orders/{id}` чужой заказ | 404 Not Found |
| INT-I-006 | PATCH `/v1/contractors/orders/{id}/cancel` | 200, заказ отменён |
| INT-I-007 | Webhook вызывается при смене статуса | HTTP POST получен |

### 5.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| INT-E-001 | Webhook URL с самоподписанным SSL | Ошибка SSL |
| INT-E-002 | Webhook возвращает 4xx | Не повторять |
| INT-E-003 | Webhook возвращает 5xx | Retry с backoff |
| INT-E-004 | Telegram API недоступен | Логирование, без блокировки |
| INT-E-005 | Деактивированный contractor (is_active=false) | 401 Unauthorized |
| INT-E-006 | Создание заказа с external_id дубликатом | 409 Conflict |

### 5.5 Тестовые данные

```python
# Подрядчик
contractor = {
    "name": "ООО Логистика",
    "api_key": "test_api_key_12345",
    "webhook_url": "https://example.com/webhook"
}

# Заказ от подрядчика
contractor_order = {
    "external_id": "EXT-001",
    "pickup_address": "ул. Светланская, 1",
    "dropoff_address": "ул. Алеутская, 10",
    "pickup_lat": 43.1155,
    "pickup_lon": 131.8855,
    "dropoff_lat": 43.1200,
    "dropoff_lon": 131.9000,
    "time_start": "2024-01-15T10:00:00+10:00"
}

# Webhook payload
webhook_payload = {
    "event": "order.status_changed",
    "order_id": 123,
    "external_id": "EXT-001",
    "status": "assigned",
    "driver_name": "Иван Петров",
    "timestamp": "2024-01-15T10:05:00+10:00"
}
```

### 5.6 Критерии успеха

- [ ] Contractor API работает с API-ключами
- [ ] Webhooks отправляются при изменении статуса
- [ ] Telegram уведомления доставляются
- [ ] Ошибки внешних сервисов не блокируют основной flow
- [ ] Retry логика работает корректно

---

## 6. Telegram бот (Bot)

### 6.1 Область тестирования

- Handlers: команды, callback queries
- Keyboards: inline-кнопки
- Middlewares: авторизация, throttling
- Взаимодействие с сервисами

### 6.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| BOT-U-001 | Handler `/start` новый пользователь | Приветствие, регистрация |
| BOT-U-002 | Handler `/start` существующий пользователь | Главное меню |
| BOT-U-003 | Handler `/orders` водитель | Список его заказов |
| BOT-U-004 | Handler `/orders` диспетчер | Все заказы |
| BOT-U-005 | Handler `/status` | Текущий статус водителя |
| BOT-U-006 | Callback `order_accept_{id}` | Заказ принят |
| BOT-U-007 | Callback `order_arrived_{id}` | Статус DRIVER_ARRIVED |
| BOT-U-008 | Callback `order_start_{id}` | Статус IN_PROGRESS |
| BOT-U-009 | Callback `order_complete_{id}` | Статус COMPLETED |
| BOT-U-010 | Callback `order_cancel_{id}` | Запрос причины отмены |
| BOT-U-011 | Отправка геолокации | Координаты сохранены |
| BOT-U-012 | Middleware auth: неавторизованный | Блокировка с сообщением |
| BOT-U-013 | Middleware auth: PENDING пользователь | Ограниченные команды |

### 6.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| BOT-I-001 | Полный flow: /start → регистрация → /orders | Успешный путь |
| BOT-I-002 | Полный flow: принятие заказа → выполнение | Все статусы корректны |
| BOT-I-003 | Уведомление о новом заказе | Сообщение с кнопками |
| BOT-I-004 | Отмена заказа с причиной | Причина сохранена |
| BOT-I-005 | Live-трекинг геолокации | Координаты обновляются |

### 6.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| BOT-E-001 | Callback на несуществующий заказ | "Заказ не найден" |
| BOT-E-002 | Callback на чужой заказ | "Нет доступа" |
| BOT-E-003 | Двойной клик на кнопку | Идемпотентность |
| BOT-E-004 | Слишком частые команды (flood) | Throttling |
| BOT-E-005 | Невалидная геолокация | Ошибка валидации |
| BOT-E-006 | Команда от заблокированного пользователя | Игнорирование |

### 6.5 Тестовые данные

```python
# Telegram Update (мок)
telegram_update = {
    "update_id": 123456,
    "message": {
        "message_id": 1,
        "from": {
            "id": 123456789,
            "first_name": "Иван",
            "username": "ivan_driver"
        },
        "chat": {"id": 123456789, "type": "private"},
        "text": "/start"
    }
}

# Callback query
callback_query = {
    "id": "callback_123",
    "from": {"id": 123456789},
    "message": {"message_id": 1, "chat": {"id": 123456789}},
    "data": "order_accept_42"
}
```

### 6.6 Критерии успеха

- [ ] Все команды обрабатываются
- [ ] Inline-кнопки работают
- [ ] Авторизация проверяется
- [ ] Геолокация обрабатывается
- [ ] Throttling защищает от flood

---

## 7. Background Workers

### 7.1 Область тестирования

- `ingest_worker` — обработка входящих данных
- Scheduler — периодические задачи
- Dead Letter Queue (DLQ)
- Graceful shutdown

### 7.2 Unit-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| WRK-U-001 | `ingest_worker` обработка валидного сообщения | Данные сохранены |
| WRK-U-002 | `ingest_worker` невалидное сообщение | В DLQ |
| WRK-U-003 | `ingest_worker` ошибка обработки | Retry, затем DLQ |
| WRK-U-004 | Scheduler: запуск периодической задачи | Задача выполнена |
| WRK-U-005 | Scheduler: пропуск при overlap | Не запускать дубль |
| WRK-U-006 | Scheduler: cleanup старых данных | Данные удалены |
| WRK-U-007 | Scheduler: напоминания о заказах | Уведомления отправлены |
| WRK-U-008 | Graceful shutdown | Текущие задачи завершены |

### 7.3 Integration-тесты

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| WRK-I-001 | Redis pub/sub → worker | Сообщение обработано |
| WRK-I-002 | DLQ: сообщение в очереди ошибок | Доступно для анализа |
| WRK-I-003 | Scheduler + NotificationService | Уведомления отправлены |
| WRK-I-004 | Cleanup LocationHistory старше 7 дней | Записи удалены |

### 7.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| WRK-E-001 | Redis недоступен при старте | Retry с backoff |
| WRK-E-002 | БД недоступна | Ошибка, сообщение в DLQ |
| WRK-E-003 | Очень большое сообщение | Обработка или отклонение |
| WRK-E-004 | SIGTERM во время обработки | Graceful завершение |
| WRK-E-005 | Scheduler job превышает интервал | Пропуск следующего запуска |

### 7.5 Тестовые данные

```python
# Сообщение для ingest_worker
ingest_message = {
    "type": "location_update",
    "driver_id": 1,
    "latitude": 43.1155,
    "longitude": 131.8855,
    "timestamp": "2024-01-15T10:00:00+10:00"
}

# Scheduler tasks
scheduler_tasks = [
    {"name": "cleanup_old_locations", "interval": "0 3 * * *"},  # 3:00 daily
    {"name": "send_order_reminders", "interval": "*/15 * * * *"},  # every 15 min
    {"name": "check_stale_orders", "interval": "*/5 * * * *"}  # every 5 min
]
```

### 7.6 Критерии успеха

- [ ] Worker обрабатывает сообщения корректно
- [ ] DLQ работает для ошибочных сообщений
- [ ] Scheduler выполняет задачи по расписанию
- [ ] Graceful shutdown реализован
- [ ] Нет memory leaks при длительной работе

---

## 8. Frontend (React SPA)

### 8.1 Область тестирования

- Components: Dashboard, Map, OrderCard, DriverList
- Hooks: useOrders, useDrivers, useAuth
- API client: запросы, обработка ошибок
- State management: Zustand stores
- UI/UX: темы, адаптивность

### 8.2 Unit-тесты (Jest + React Testing Library)

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| FE-U-001 | `useOrders` загрузка списка | orders[], loading states |
| FE-U-002 | `useOrders` создание заказа | Новый заказ в списке |
| FE-U-003 | `useOrders` обработка ошибки API | error state, сообщение |
| FE-U-004 | `useDrivers` загрузка списка | drivers[] |
| FE-U-005 | `useAuth` login flow | token сохранён |
| FE-U-006 | `useAuth` logout | token удалён |
| FE-U-007 | `OrderCard` рендер с данными | Корректное отображение |
| FE-U-008 | `OrderCard` клик на действие | Callback вызван |
| FE-U-009 | `Dashboard` с заказами | Заказы отображены |
| FE-U-010 | `Dashboard` пустой список | Empty state |
| FE-U-011 | `DriverList` grid/table toggle | Переключение view |
| FE-U-012 | `Map` маркеры водителей | Маркеры на карте |
| FE-U-013 | `Map` кластеризация | Маркеры группируются |
| FE-U-014 | Theme toggle dark/light | Тема применяется |

### 8.3 Integration-тесты (Cypress/Playwright)

| ID | Тест | Ожидаемый результат |
|----|------|---------------------|
| FE-I-001 | Login → Dashboard | Успешный вход, dashboard отображён |
| FE-I-002 | Dashboard → Create Order | Форма, создание, заказ в списке |
| FE-I-003 | Order drag-and-drop | Заказ перемещён, API вызван |
| FE-I-004 | Driver list → Driver details | Переход, данные отображены |
| FE-I-005 | Map → Driver click → Track | Режим отслеживания |
| FE-I-006 | Filters: дата, статус, приоритет | Список отфильтрован |
| FE-I-007 | Real-time updates (WebSocket/polling) | Новые данные появляются |
| FE-I-008 | Mobile responsive | Корректное отображение |
| FE-I-009 | Offline mode (PWA) | Кэшированные данные доступны |

### 8.4 Edge Cases

| ID | Сценарий | Ожидаемый результат |
|----|----------|---------------------|
| FE-E-001 | API недоступен | Error boundary, retry кнопка |
| FE-E-002 | Token истёк | Redirect на login |
| FE-E-003 | 403 на защищённый route | Сообщение о недостатке прав |
| FE-E-004 | Очень длинный список (1000+ заказов) | Виртуализация/пагинация |
| FE-E-005 | Медленное соединение | Loading states, skeleton |
| FE-E-006 | Двойной клик на submit | Дебаунс, одна отправка |
| FE-E-007 | Невалидные данные формы | Валидация, сообщения |
| FE-E-008 | Браузер без geolocation API | Fallback или сообщение |

### 8.5 Тестовые данные

```typescript
// Mock заказ
const mockOrder: Order = {
  id: 1,
  status: "assigned",
  priority: "normal",
  pickup_address: "ул. Светланская, 1",
  dropoff_address: "ул. Алеутская, 10",
  pickup_lat: 43.1155,
  pickup_lon: 131.8855,
  dropoff_lat: 43.1200,
  dropoff_lon: 131.9000,
  time_start: "2024-01-15T10:00:00+10:00",
  time_end: "2024-01-15T11:00:00+10:00",
  driver_id: 1,
  driver_name: "Иван Петров",
  price: 500.00,
  distance_meters: 5000,
  duration_seconds: 900
};

// Mock водитель
const mockDriver: Driver = {
  id: 1,
  name: "Иван Петров",
  phone: "+79001234567",
  status: "available",
  telegram_id: 123456789
};

// Mock геолокация
const mockLocation: DriverLocation = {
  driver_id: 1,
  latitude: 43.1155,
  longitude: 131.8855,
  status: "available",
  last_updated: "2024-01-15T10:00:00+10:00"
};
```

### 8.6 Критерии успеха

- [ ] Все компоненты рендерятся корректно
- [ ] Hooks работают с API
- [ ] State management синхронизирован
- [ ] Темы переключаются
- [ ] Адаптивность на мобильных
- [ ] PWA работает offline
- [ ] Нет console errors в production

---

## Общие рекомендации

### Инструменты

| Тип | Инструмент |
|-----|------------|
| Backend Unit | pytest, pytest-asyncio |
| Backend Integration | pytest + httpx.AsyncClient |
| Mocking | unittest.mock, pytest-mock |
| Database | pytest fixtures с rollback |
| Frontend Unit | Jest, React Testing Library |
| Frontend E2E | Playwright или Cypress |
| Coverage | pytest-cov, istanbul |
| CI/CD | GitHub Actions |

### Структура тестов

```
tests/
├── conftest.py              # Общие фикстуры
├── unit/
│   ├── test_order_service.py
│   ├── test_driver_service.py
│   ├── test_auth_service.py
│   └── ...
├── integration/
│   ├── test_api_orders.py
│   ├── test_api_drivers.py
│   ├── test_contractor_api.py
│   └── ...
├── e2e/
│   ├── test_order_workflow.py
│   └── ...
└── fixtures/
    ├── orders.json
    ├── drivers.json
    └── ...
```

### Команды запуска

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Только unit
pytest tests/unit/

# Только integration
pytest tests/integration/

# Конкретный модуль
pytest tests/test_order_service.py -v

# Frontend
cd frontend && npm test

# Frontend E2E
cd frontend && npx playwright test
```

### Coverage targets

| Модуль | Минимум |
|--------|---------|
| OrderService | 100% |
| DriverService | 100% |
| AuthService | 100% |
| RoutingService | 100% |
| GeocodingService | 100% |
| LocationManager | 100% |
| WebhookService | 100% |
| NotificationService | 100% |
| BatchAssignmentService | 100% |
| UrgentAssignmentService | 100% |
| ExcelImportService | 100% |
| API routes | 100% |
| Bot handlers | 100% |
| Background workers | 100% |
| Frontend components | 100% |
| Frontend hooks | 100% |
| Frontend stores | 100% |
