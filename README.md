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
├── src/
│   ├── __init__.py
│   ├── config.py           # Конфигурация приложения
│   ├── main.py             # FastAPI приложение
│   └── database/
│       ├── __init__.py
│       ├── connection.py   # Async-подключение к БД
│       └── models.py       # SQLAlchemy модели
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/           # Миграции
├── tests/
│   ├── conftest.py
│   └── test_*.py
└── osrm-data/              # Данные OSRM (не в git)
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

## Exclusion Constraint

Система использует PostgreSQL Exclusion Constraint для гарантии, что один водитель не может иметь пересекающиеся по времени заказы:

```sql
EXCLUDE USING gist (
    driver_id WITH =,
    time_range WITH &&
) WHERE (status NOT IN ('completed', 'cancelled'))
```

Это обеспечивает атомарную проверку на уровне БД, исключая race conditions.
