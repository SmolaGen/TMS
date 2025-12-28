# Установка и запуск

## Требования

- **Docker** и **Docker Compose**
- **Node.js** v18+ (для локальной разработки фронтенда)
- **Python** 3.11+ (для локальной разработки бэкенда)

## Быстрый старт (Docker)

Самый простой способ запустить всю систему целиком:

```bash
# Клонировать репозиторий
git clone <repository_url>
cd tms_new

# Создать файл окружения
cp .env.example .env

# Запустить сервисы
docker-compose up -d --build
```

После запуска будут доступны:
- **Frontend**: http://localhost:5173 (если запущен через vite) или порт, указанный в nginx
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/docs
- **OSRM**: http://localhost:5000
- **Photon**: http://localhost:2322

> **Важно**: Для работы OSRM и Photon требуются предварительно загруженные данные. См. раздел "Подготовка данных" ниже или в корневом README.md.

## Локальная разработка

### Backend

1. Создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Запустите инфраструктурные сервисы (DB, Redis, OSRM, Photon) через Docker:
   ```bash
   docker-compose up -d postgis redis osrm photon
   ```
4. Примените миграции (если используются):
   ```bash
   alembic upgrade head
   ```
5. Запустите сервер:
   ```bash
   uvicorn src.main:app --reload
   ```

### Frontend

1. Перейдите в папку frontend:
   ```bash
   cd frontend
   ```
2. Установите зависимости:
   ```bash
   npm install
   ```
3. Запустите dev-сервер:
   ```bash
   npm run dev
   ```

## Подготовка гео-данных

Для работы OSRM и Photon необходимо скачать данные OSM (pbf файл) и подготовить их.

1. **OSRM**: Положите файл `.osm.pbf` в папку `osrm-data` и запустите предварительную обработку (см. документацию OSRM image).
2. **Photon**: При первом запуске Photon начнет индексацию, если ему подсунуть pbf файл, или его нужно настроить на скачивание готового индекса.
