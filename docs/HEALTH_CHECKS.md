# Health Checks

Система мониторинга здоровья TMS включает HTTP-эндпоинты для проверки состояния приложения и его зависимостей, а также Docker healthcheck для автоматического мониторинга и перезапуска сервисов.

## Обзор

TMS реализует многоуровневую систему health checks:

1. **HTTP API эндпоинты** - для внешнего мониторинга и load balancer
2. **Docker healthcheck** - для автоматического перезапуска при сбоях
3. **Circuit Breaker** - для защиты от каскадных отказов внешних сервисов

## HTTP Эндпоинты

### GET /health

Базовая проверка здоровья приложения с проверкой критических зависимостей (БД и Redis).

**URL:** `http://localhost:8000/health`

**HTTP Status Codes:**
| Код | Описание |
|-----|----------|
| `200 OK` | Все критические зависимости работают |
| `503 Service Unavailable` | Одна или несколько зависимостей недоступны |

**Response Schema:**
```json
{
  "status": "ok" | "degraded" | "failed",
  "timestamp": 1738167600.123456,
  "checks": {
    "database": {
      "status": "ok",
      "message": "Database connection successful",
      "response_time_ms": 5.23
    },
    "redis": {
      "status": "ok",
      "message": "Redis connection successful",
      "response_time_ms": 1.15
    }
  }
}
```

**Примеры запросов:**

```bash
# Простая проверка
curl http://localhost:8000/health

# С форматированием
curl -s http://localhost:8000/health | jq

# Проверка с ожидаемым статусом
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
```

### GET /health/detailed

Расширенная проверка всех внешних сервисов и зависимостей.

**URL:** `http://localhost:8000/health/detailed`

**HTTP Status Codes:**
| Код | Описание |
|-----|----------|
| `200 OK` | Все сервисы работают |
| `503 Service Unavailable` | Один или несколько сервисов недоступны |

**Response Schema:**
```json
{
  "status": "ok" | "degraded" | "failed",
  "timestamp": 1738167600.123456,
  "checks": {
    "database": {
      "status": "ok",
      "message": "Database connection successful",
      "response_time_ms": 5.23
    },
    "redis": {
      "status": "ok",
      "message": "Redis connection successful",
      "response_time_ms": 1.15
    },
    "osrm": {
      "status": "ok",
      "message": "OSRM service is available",
      "response_time_ms": 15.47
    },
    "photon": {
      "status": "ok",
      "message": "Photon service is available",
      "response_time_ms": 23.89
    }
  }
}
```

**Проверяемые сервисы:**

| Сервис | Описание | Проверка |
|--------|----------|----------|
| `database` | PostgreSQL + PostGIS | SELECT 1 |
| `redis` | Redis cache | PING |
| `osrm` | OSRM маршрутизация | GET /status |
| `photon` | Photon геокодинг | GET /api?q=test |

## Статусы здоровья

Система использует три статуса:

| Статус | Описание | HTTP Code |
|--------|----------|-----------|
| `ok` | Все компоненты работают нормально | 200 |
| `degraded` | Некоторые компоненты работают с ограничениями | 503 |
| `failed` | Один или несколько критических компонентов недоступны | 503 |

### Логика определения статуса

```
IF any check == FAILED:
    overall = FAILED (503)
ELSE IF any check == DEGRADED:
    overall = DEGRADED (503)
ELSE:
    overall = OK (200)
```

## Docker Health Checks

Каждый сервис в docker-compose.yml настроен с healthcheck:

### PostgreSQL (PostGIS)
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U tms -d tms_db"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### OSRM
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/status"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Photon
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:2322/api?q=test"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 120s
```

### Backend
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Workers (Ingest Worker, Scheduler)
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import redis; redis.Redis(host='redis', port=6379).ping()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Nginx
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:80/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

## Проверка состояния сервисов

```bash
# Посмотреть состояние всех сервисов
docker-compose ps

# Посмотреть только healthy сервисы
docker-compose ps | grep healthy

# Подсчитать healthy сервисы
docker-compose ps | grep -c 'healthy'

# Логи health check для конкретного сервиса
docker inspect --format='{{json .State.Health}}' tms-backend | jq
```

## Конфигурация

Настройки health check в `src/config.py`:

```python
# Health Checks
HEALTH_CHECK_TIMEOUT: float = 5.0  # секунды - таймаут для каждой проверки
HEALTH_CHECK_INTERVAL: int = 30    # секунды - интервал между проверками
HEALTH_CHECK_RETRIES: int = 3      # количество попыток

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5   # ошибок до открытия CB
CIRCUIT_BREAKER_TIMEOUT: int = 60            # секунд до перехода в half-open
CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 120  # секунд для полного восстановления
```

## Circuit Breaker

Система использует паттерн Circuit Breaker для защиты от каскадных отказов при обращении к внешним сервисам (OSRM, Photon).

### Состояния Circuit Breaker

```
┌─────────┐     >=5 failures     ┌──────┐
│ CLOSED  │ ─────────────────────▶ OPEN │
│(normal) │                      │(fail)│
└────┬────┘                      └──┬───┘
     │                              │
     │     success                  │ 60s timeout
     │                              │
     │  ┌───────────┐               │
     └──│ HALF_OPEN │◀──────────────┘
        │  (test)   │
        └─────┬─────┘
              │ failure
              └──────────▶ OPEN
```

| Состояние | Описание |
|-----------|----------|
| `CLOSED` | Нормальная работа, все запросы проходят |
| `OPEN` | Слишком много ошибок, запросы отклоняются сразу |
| `HALF_OPEN` | Тестирование восстановления сервиса |

### Защищенные сервисы

- **OSRM** (`src/services/routing.py`) - маршрутизация
- **Photon** (`src/services/geocoding.py`) - геокодинг

При открытом Circuit Breaker система использует:
- Кэшированные данные (если доступны)
- Резервные алгоритмы (fallback)
- Возвращает ошибку с понятным сообщением

## Graceful Degradation

При недоступности внешних сервисов система продолжает работать:

| Сервис | Fallback поведение |
|--------|-------------------|
| OSRM | Прямое расстояние с коэффициентом 1.3 |
| Photon | Кэшированные результаты геокодинга |
| Redis | Прямой доступ к БД (без кэша) |

## Мониторинг

### Prometheus метрики

Метрики доступны по адресу `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### Логирование

Health check результаты логируются структурированно:

```json
{
  "event": "health_check_completed",
  "status": "ok",
  "status_code": 200,
  "response_time_ms": 25.67
}
```

### Интеграция с внешними системами

Эндпоинты совместимы с:
- **Kubernetes** liveness/readiness probes
- **AWS ELB/ALB** health checks
- **Prometheus** + **AlertManager**
- **Grafana** dashboards

## Примеры использования

### Проверка перед деплоем

```bash
#!/bin/bash
# Ожидание готовности сервиса

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$STATUS" = "200" ]; then
        echo "Service is healthy"
        exit 0
    fi
    echo "Waiting for service... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done

echo "Service failed to become healthy"
exit 1
```

### Kubernetes Deployment

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Load Balancer (Nginx)

```nginx
upstream backend {
    server backend:8000;
    keepalive 32;
}

server {
    location /health {
        proxy_pass http://backend;
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }
}
```

## Устранение неполадок

### Сервис не проходит health check

1. Проверьте логи сервиса:
   ```bash
   docker-compose logs -f backend
   ```

2. Проверьте зависимости:
   ```bash
   curl -s http://localhost:8000/health/detailed | jq
   ```

3. Проверьте сетевое подключение:
   ```bash
   docker-compose exec backend ping postgis
   docker-compose exec backend ping redis
   ```

### Circuit Breaker открыт

1. Проверьте доступность внешнего сервиса:
   ```bash
   curl http://localhost:5000/status  # OSRM
   curl http://localhost:2322/api?q=test  # Photon
   ```

2. Дождитесь автоматического восстановления (60 секунд)

3. При необходимости перезапустите сервис:
   ```bash
   docker-compose restart backend
   ```

### Медленные health checks

1. Увеличьте таймаут в конфигурации:
   ```python
   HEALTH_CHECK_TIMEOUT: float = 10.0
   ```

2. Проверьте производительность зависимостей

3. Используйте `/health` вместо `/health/detailed` для критических проверок

## Связанные файлы

| Файл | Описание |
|------|----------|
| `src/fastapi_routes.py` | HTTP эндпоинты /health и /health/detailed |
| `src/core/health_check.py` | Базовые классы HealthChecker |
| `src/core/circuit_breaker.py` | Реализация Circuit Breaker |
| `src/core/graceful_degradation.py` | Fallback механизмы |
| `src/api/endpoints/health_detailed.py` | Альтернативная реализация |
| `healthcheck.py` | Скрипт для Docker HEALTHCHECK |
| `docker-compose.yml` | Конфигурация Docker healthchecks |
| `src/config.py` | Настройки health checks |
