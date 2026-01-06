## Why

В системе реализована админская панель в Telegram боте для управления пользователями, но этот функционал не описан в спекификациях. Также отсутствует документация по Role-Based Access Control (RBAC) и системе ролей (ADMIN, DISPATCHER, DRIVER, PENDING).

## What Changes

- **ADDED**: Admin Panel — спекификация админской панели в Telegram боте
- **MODIFIED**: Authentication — добавлены требования для RBAC и ролей пользователей

## Impact

- **Affected specs**:
  - `admin-panel` — новая спекификация для админской панели
  - `authentication` — обновлена с RBAC
- **Affected code**:
  - `src/bot/handlers/admin.py` — реализация админской панели
  - `src/database/models.py` — UserRole enum и Driver.is_active
  - `src/services/auth_service.py` — валидация ролей
- **Breaking changes**: Нет
