## Why

В процессе деплоя и тестирования системы были выявлены критические ошибки, препятствующие нормальной работе приложения:

1. **Авторизация работала только в Telegram Mini App** — пользователи не могли войти через обычный браузер
2. **Ошибки 500 на `/orders`** — отсутствовала зависимость `shapely`, необходимая для работы GeoAlchemy2 с геометрией
3. **WebSocket не подключался** — проблемы с маршрутизацией через Nginx и конфигурацией
4. **API пути** — неправильная настройка проксирования через Nginx

Эти проблемы блокировали использование системы в production.

## What Changes

- **MODIFIED**: Authentication — добавлена поддержка Telegram Login Widget для авторизации в браузере (помимо Mini App)
- **MODIFIED**: Order Management — добавлена зависимость `shapely` для корректной работы с геометрией маршрутов
- **MODIFIED**: WebSocket Sync — исправлена конфигурация для работы через Nginx с SSL (wss://)
- **MODIFIED**: API Routing — исправлена настройка Nginx для проксирования `/v1/` → `/api/v1/`

## Impact

- **Affected specs**: 
  - `authentication` — добавлена поддержка Login Widget
  - `websocket-sync` — исправлена конфигурация подключения
  - `order-management` — исправлена работа с геометрией
- **Affected code**: 
  - `frontend/src/components/AuthGuard.tsx` — добавлен Telegram Login Widget
  - `frontend/src/hooks/useTelegramAuth.ts` — улучшена логика авторизации
  - `src/services/auth_service.py` — добавлена поддержка Login Widget формата
  - `requirements.txt` — добавлен `shapely>=2.0.0`
  - `nginx/nginx.conf` — исправлена конфигурация проксирования
- **Breaking changes**: Нет
