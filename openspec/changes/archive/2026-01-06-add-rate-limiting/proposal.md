## Why

В системе реализован rate limiting через SlowAPI с Redis backend для защиты API от DDoS и перегрузки, но этот функционал не задокументирован в спеках.

## What Changes

- **ADDED**: Спекификация для Rate Limiting:
  - SlowAPI integration
  - Redis backend для хранения счётчиков
  - Персонализированные лимиты по endpoint'ам
  - Rate limiting для WebSocket (origin validation)
  - Rate limiting для location updates

## Impact

- **Affected specs**: Создание 1 новой capability
- **Affected code**: Документирование существующего функционала в `src/main.py`, `src/api/routes.py`, `src/core/middleware.py`
- **Breaking changes**: Нет
