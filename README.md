# TMS - Transport Management System

Отказоустойчивая система управления транспортом.

## Быстрый старт

### 1. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env и установите безопасные пароли
```

### 2. Системные требования

**Для Photon (геокодинг) требуется увеличить `vm.max_map_count`:**

```bash
# Временно (до перезагрузки)
sudo sysctl -w vm.max_map_count=262144

# Постоянно
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 3. Запуск базовых сервисов

```bash
# Только PostgreSQL + Redis (минимальный набор)
docker-compose up -d postgis redis

# Проверка статуса
docker-compose ps
```

### 4. Запуск с маршрутизацией (OSRM)

**Подготовка данных OSM (один раз):**

```bash
mkdir -p osrm-data
cd osrm-data

# Скачать данные Дальневосточного федерального округа
# (включает Приморский край и Якутию)
wget https://download.geofabrik.de/russia/far-eastern-fed-district-latest.osm.pbf

# Извлечение графа
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/far-eastern-fed-district-latest.osm.pbf

# Разбиение на ячейки
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/far-eastern-fed-district-latest.osrm

# Настройка весов
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/far-eastern-fed-district-latest.osrm

cd ..
```

**Запуск с OSRM:**

```bash
docker-compose --profile routing up -d
```

### 5. Запуск с геокодингом (Photon)

```bash
docker-compose --profile geocoding up -d
```

### 6. Миграции базы данных

```bash
# Применить миграции
docker-compose exec backend alembic upgrade head

# Создать новую миграцию
docker-compose exec backend alembic revision --autogenerate -m "описание"
```

## Структура проекта

```
tms/
├── docker-compose.yml      # Оркестрация сервисов
├── Dockerfile              # Образ backend
├── .env.example            # Пример переменных окружения
├── requirements.txt        # Python зависимости
├── src/                   # Backend (Python/FastAPI)
│   ├── __init__.py
│   ├── config.py           # Конфигурация приложения
│   ├── main.py             # FastAPI приложение
│   ├── api/               # API эндпоинты
│   ├── bot/               # Telegram бот
│   ├── core/              # Core модули (logging, middleware)
│   ├── database/           # Модели и подключения
│   ├── schemas/           # Pydantic схемы
│   ├── services/           # Бизнес-логика
│   └── workers/           # Воркеры (ingest_worker)
├── frontend/              # Frontend (React/TypeScript)
│   └── src/
│       ├── components/      # React компоненты
│       ├── pages/          # Страницы
│       ├── api/            # API клиент
│       ├── hooks/          # Custom hooks
│       └── stores/         # Zustand stores
├── openspec/              # OpenSpec спецификации
│   ├── project.md         # Контекст проекта
│   ├── AGENTS.md          # Инструкции для AI агентов
│   ├── specs/             # Текущие спецификации
│   ├── changes/           # Предложения изменений
│   └── archive/           # Архивированные изменения
├── docs/                  # Документация
├── alembic/               # Миграции БД
│   ├── alembic.ini
│   ├── env.py
│   └── versions/           # Миграции
├── tests/                 # Тесты
├── nginx/                 # Nginx конфигурация
└── osrm-data/             # Данные OSRM (не в git)
```

## API Endpoints

После запуска доступна документация:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Команды Docker

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v

# Логи конкретного сервиса
docker-compose logs -f backend

# Подключиться к PostgreSQL
docker-compose exec postgis psql -U tms -d tms_db
```

## OpenSpec

Система использует OpenSpec для spec-driven развития. Все изменения проходят через proposal process:

```bash
# Посмотреть список активных изменений
openspec list

# Посмотреть список спецификаций
openspec spec list --long

# Валидировать изменение
openspec validate <change-id> --strict

# Заархивировать изменение после деплоя
openspec archive <change-id> --yes
```

Полная документация в `openspec/AGENTS.md` и `openspec/project.md`.

## Exclusion Constraint

Система использует PostgreSQL Exclusion Constraint для гарантии, что один водитель не может иметь пересекающиеся по времени заказы:

```sql
EXCLUDE USING gist (
    driver_id WITH =,
    time_range WITH &&
) WHERE (status NOT IN ('completed', 'cancelled'))
```

## Health Checks и Автоматическое Восстановление

Система реализует многоуровневую систему health checks с автоматическим восстановлением:

### HTTP эндпоинты

| Эндпоинт | Описание | HTTP Codes |
|----------|----------|------------|
| `/health` | Базовая проверка (БД + Redis) | 200 OK / 503 Error |
| `/health/detailed` | Полная проверка всех сервисов | 200 OK / 503 Error |

```bash
# Проверка здоровья
curl http://localhost:8000/health

# Детальный статус всех сервисов
curl http://localhost:8000/health/detailed | jq
```

### Docker Health Checks

Все сервисы настроены с автоматическим перезапуском при сбоях:

```bash
# Проверка статуса всех сервисов
docker-compose ps

# Посмотреть только healthy сервисы
docker-compose ps | grep healthy
```

### Circuit Breaker

Внешние сервисы (OSRM, Photon) защищены паттерном Circuit Breaker:
- **CLOSED**: Нормальная работа
- **OPEN**: Сервис недоступен → запросы отклоняются, используются fallback
- **HALF_OPEN**: Тестирование восстановления

При недоступности внешних сервисов система продолжает работать:
- **OSRM недоступен** → расчёт прямого расстояния с коэффициентом 1.3
- **Photon недоступен** → использование кэшированных результатов геокодинга

### Время восстановления

- Автоматическое восстановление сервиса: **< 30 секунд**
- Circuit Breaker timeout: **60 секунд**

Подробная документация: [docs/HEALTH_CHECKS.md](docs/HEALTH_CHECKS.md)

## Мониторинг и CI/CD

- **Prometheus**: Метрики доступны по пути `/metrics`.
- **Sentry**: Логирование ошибок в production (требует `SENTRY_DSN`).
- **CI/CD**: GitHub Actions настроен для тестирования, линтинга и сборки Docker образа.

## Frontend (Phase 1-6)

Система включает современный SPA на React:
- **Phase 4**: Кластеризация маркеров на карте, режим наблюдения за водителем.
- **Phase 5**: Управление водителями (Грид/Таблица, детальная статистика).
- **Phase 6**: Тёмная тема, адаптивный дизайн для мобильных устройств.
- **PWA**: Поддержка Service Worker для кэширования и offline режима.

## Разработка

Для запуска фронтенда в режиме разработки:
```bash
cd frontend
npm install
npm run dev
```

Для сборки и деплоя:
```bash
cd frontend
npm run build
# Скопировать dist/ на веб-сервер
```
