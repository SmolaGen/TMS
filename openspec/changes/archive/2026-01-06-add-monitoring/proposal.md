## Why

В системе реализован мониторинг через Prometheus (метрики на `/metrics`), Sentry (трекинг ошибок) и health check на `/health`, но этот функционал не задокументирован в спеках.

## What Changes

- **ADDED**: Спекификация для Monitoring & Observability:
  - Prometheus metrics endpoint (REQUEST_COUNT, REQUEST_LATENCY)
  - Sentry error tracking интеграция
  - Health check endpoint
- **ADDED**: Спекификация для Health Check:
  - Базовый health check
  - Проверка состояния сервисов (PostgreSQL, Redis, OSRM)

## Impact

- **Affected specs**: Создание 2 новых capabilities
- **Affected code**: Документирование существующего функционала в `src/main.py`
- **Breaking changes**: Нет
