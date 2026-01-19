# Project Analysis Report (TMS Backend)

## Проектная структура
Основной код находится в директории `src/`. Проект представляет собой бэкенд на FastAPI с интегрированным Telegram-ботом и фоновыми воркерами.

### 1. Ядро и Конфигурация
- `src/main.py`: Инициализация FastAPI приложения, настройка роутов, логирования и жизненного цикла (lifespan). В lifespan инициализируются Bot и Scheduler.
- `src/config.py`: Настройки приложения через `pydantic-settings`. Основные параметры: БД, Redis, Telegram, JWT, логирование.
- `src/core/`: Общие компоненты (middleware, логирование).

### 2. База данных (`src/database/`)
- `models.py`: SQLAlchemy 2.0 модели (Base, Driver, Order, Contractor, и др.). Использует GeoAlchemy2 для координат.
- `repository.py` / `uow.py`: Реализация паттернов Repository и Unit of Work для абстракции над БД.
- `connection.py`: Настройка асинхронного движка и сессий (asyncpg).

### 3. API Слой (`src/api/`)
- `routes.py`: Агрегатор всех роутеров.
- `endpoints/`: Конкретные обработчики запросов (Health, Auth, Contractors).
- `dependencies.py`: Зависимости FastAPI (get_db, get_current_user).

### 4. Telegram Бот (`src/bot/`)
- `main.py`: Инициализация Bot и Dispatcher.
- `handlers/`: Обработчики команд и сообщений (Admin, Orders, Location).
- `keyboards/`: Генерация кнопок для интерфейса бота.
- `middlewares/`: Middleware для авторизации и идемпотентности в боте.

### 5. Бизнес-логика (`src/services/`)
- `auth_service.py`: Логика аутентификации, генерация JWT.
- `order_service.py`: Управление жизненным циклом заказов.
- `driver_service.py`: Управление водителями.
- `routing.py` / `geocoding.py`: Интеграция с OSRM и Photon.
- `order_workflow.py`: Сложная логика переходов состояний заказов.

### 6. Схемы данных (`src/schemas/`)
- Pydantic модели для валидации входящих и исходящих данных (Auth, Order, Driver, Contractor).

### 7. Фоновые задачи (`src/workers/`)
- `scheduler.py`: Планировщик задач (APScheduler).
- `ingest_worker.py` / `sync_worker.py`: Обработка очередей и синхронизация данных.

## Зависимости (Основные)
- **FastAPI**: Веб-фреймворк.
- **SQLAlchemy / Alembic**: ORM и миграции.
- **GeoAlchemy2**: Работа с ГИС.
- **aiogram**: Библиотека для Telegram бота.
- **APScheduler**: Фоновые задачи.
- **Pydantic**: Валидация данных.
- **structlog**: Структурированное логирование.

## Выявленные проблемы/риски
- В проекте присутствуют циклические импорты (особенно между services и models), требующие аудита.
- Смешение логики API и Бота в lifespan `main.py`.
- Необходимость стабилизации системы сессий.
