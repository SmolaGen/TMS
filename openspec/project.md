# Project Context

## Purpose
TMS (Transport Management System) — отказоустойчивая система управления транспортом для логистических компаний. Позволяет:
- Отслеживать водителей в реальном времени на карте
- Управлять заказами с защитой от пересечений по времени (Exclusion Constraint)
- Составлять расписание смен для сотрудников
- Интеграция с Telegram-ботом для водителей

**Домен:** https://myappnf.ru

## Tech Stack

### Backend
- **Python 3.11+** — основной язык
- **FastAPI** — высокопроизводительный веб-фреймворк (async)
- **SQLAlchemy 2.0 (Async)** — ORM для работы с БД
- **PostgreSQL + PostGIS** — СУБД с расширением для гео-данных
- **Redis** — хранение "живых" координат водителей, кэширование
- **Alembic** — миграции базы данных
- **Aiogram 3.x** — Telegram бот
- **Uvicorn** — ASGI сервер
- **structlog** — структурное логирование

### Frontend
- **React 19** — UI библиотека
- **TypeScript** — типизация
- **Vite** — быстрый сборщик с HMR
- **Ant Design 6** — UI компоненты
- **TanStack React Query** — серверное состояние и кэширование
- **Zustand** — менеджер клиентского состояния
- **Leaflet / React-Leaflet** — интерактивные карты
- **Vis-Timeline** — Gantt-диаграммы расписания

### Инфраструктура
- **Docker + Docker Compose** — контейнеризация
- **OSRM** — маршрутизация и расчёт ETA
- **Photon** — локальный геокодинг
- **PM2** — процесс-менеджер для production
- **Nginx** — обратный прокси (SSL, статика)

## Project Conventions

### Code Style
**Python:**
- PEP 8 с максимальной длиной строки 120 символов
- Type hints обязательны для публичных функций
- Async/await для всех I/O операций
- Именование: `snake_case` для функций/переменных, `PascalCase` для классов

**TypeScript/React:**
- Функциональные компоненты с хуками
- Именование: `PascalCase` для компонентов, `camelCase` для функций/переменных
- Интерфейсы предпочтительнее типов-алиасов
- Строгий режим TypeScript (`strict: true`)

### Architecture Patterns

**Backend:**
- **Layered Architecture**: Routes → Services → Database
- **Dependency Injection** через FastAPI `Depends()`
- **Repository Pattern** для доступа к данным
- **Exclusion Constraints** в PostgreSQL для проверки конфликтов времени

**Frontend:**
- **Feature-based структура**: компоненты сгруппированы по функциональности
- **Container/Presentational** разделение для сложных компонентов
- **React Query** для серверного состояния, **Zustand** для UI состояния

### Testing Strategy
- **Unit тесты:** pytest + pytest-asyncio для backend
- **API тесты:** httpx + TestClient для эндпоинтов
- **Проверка конфликтов:** тестирование Exclusion Constraint
- **Чек-лист приёмки:** функциональные, нагрузочные, инфраструктурные тесты (см. `docs/testing.md`)

### Git Workflow
- Основная ветка: `main`
- Коммиты на русском языке с подробным описанием изменений
- Формат коммитов: краткое описание + детальный список изменений
- Сборка проекта после каждого изменения перед коммитом

## Domain Context

### Ключевые сущности
- **Driver (Водитель):** профиль, статус (active/inactive), live-координаты
- **Order (Заказ):** точки маршрута, временной слот, назначенный водитель
- **Shift (Смена):** расписание работы сотрудников (день/ночь)
- **Location:** гео-координаты с timestamp

### Бизнес-правила
1. Один водитель не может иметь пересекающиеся по времени заказы (Exclusion Constraint)
2. Координаты водителей кэшируются в Redis для высокой скорости записи
3. Воркер периодически сохраняет координаты из Redis в PostgreSQL

### Временная зона
Все времена в Владивостоке (UTC+10). Настроено через `TIMEZONE` в конфигурации бота.

## Important Constraints

### Технические
- PostgreSQL требует расширения `btree_gist` для Exclusion Constraints
- Photon требует `vm.max_map_count=262144` для Elasticsearch
- Минимум 4GB RAM на сервере (из-за OSRM и Photon)
- OSRM данные региона должны быть подготовлены заранее

### Безопасность
- `DEBUG=False` в production
- Порты БД и Redis закрыты снаружи
- CORS ограничен конкретными доменами (не `*`)
- SSL/TLS через Nginx

## External Dependencies

### Обязательные сервисы
| Сервис | Порт | Назначение |
|--------|------|------------|
| PostgreSQL + PostGIS | 5432 | Основная БД |
| Redis | 6379 | Кэш координат |

### Опциональные сервисы
| Сервис | Порт | Назначение |
|--------|------|------------|
| OSRM | 5000 | Маршрутизация |
| Photon | 2322 | Геокодинг |

### Внешние API
- **Telegram Bot API** — для бота водителей
- **OpenStreetMap** — данные карт (через self-hosted OSRM/Photon)
