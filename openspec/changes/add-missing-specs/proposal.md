## Why

В проекте TMS реализован значительный функционал (управление водителями, заказами, отслеживание локаций, Telegram-бот, фронтенд с картой и таймлайном), но отсутствуют формальные спекификации в `openspec/specs/`. Это затрудняет:
- Понимание текущих возможностей системы
- Планирование изменений и проверку соответствия
- Документирование бизнес-правил и требований

Также в `project.md` упоминается функционал **Shift (Смена)** для расписания работы сотрудников, который не реализован в коде.

## What Changes

- **ADDED**: Спекификации для всех реализованных возможностей:
  - Driver Management (CRUD, статусы, локации)
  - Order Management (CRUD, workflow, exclusion constraints)
  - Location Tracking (Redis кэш, история в PostgreSQL)
  - Authentication (Telegram WebApp)
  - Geocoding (Photon поиск и reverse)
  - Routing (OSRM маршруты и ETA)
  - WebSocket Sync (real-time обновления)
  - Frontend Dashboard (карта, таймлайн, модалы)
  - Telegram Bot (обработка локаций и заказов)
- **ADDED**: Спекификация для Shift Management (не реализовано, но описано в project.md)

## Impact

- **Affected specs**: Создание 10 новых capabilities в `openspec/specs/`
- **Affected code**: Не требуется изменений в коде (только документирование существующего функционала)
- **Breaking changes**: Нет
