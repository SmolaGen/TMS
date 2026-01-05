## 1. Исправление авторизации
- [x] 1.1 Добавлена поддержка Telegram Login Widget в AuthGuard
- [x] 1.2 Обновлен useTelegramAuth для проверки localStorage перед initData
- [x] 1.3 Добавлена валидация Login Widget формата в auth_service.py
- [x] 1.4 Добавлен метод get_by_telegram_id в DriverService
- [x] 1.5 Добавлен метод create_driver_from_telegram в DriverService

## 2. Исправление ошибок API
- [x] 2.1 Добавлен shapely>=2.0.0 в requirements.txt
- [x] 2.2 Пересобран Docker образ backend с новой зависимостью
- [x] 2.3 Проверена работа /orders эндпоинта

## 3. Исправление WebSocket
- [x] 3.1 Проверена конфигурация Nginx для WebSocket (upgrade headers)
- [x] 3.2 Обновлен VITE_WS_URL на wss://myappnf.ru/ws
- [x] 3.3 Проверена работа WebSocket подключения

## 4. Исправление API маршрутизации
- [x] 4.1 Исправлена конфигурация Nginx для проксирования /v1/ → /api/v1/
- [x] 4.2 Проверена передача заголовка Authorization через прокси
- [x] 4.3 Обновлен frontend/.env с правильным VITE_API_URL
- [x] 4.4 Добавлен location /v1/ в nginx.conf для совместимости с фронтендом

## 5. Исправление Login Widget
- [x] 5.1 Исправлено формирование initData в AuthGuard (hash не в data_check_string)
- [x] 5.2 Добавлены комментарии в auth_service.py о порядке обработки hash

## 6. Валидация
- [x] 6.1 Запуск `openspec validate fix-auth-api-websocket-errors --strict`
- [x] 6.2 Исправление всех ошибок валидации
