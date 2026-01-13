# telegram-bot Specification

## Purpose
TBD - created by archiving change add-missing-specs. Update Purpose after archive.
## Requirements
### Requirement: Telegram Bot Webhook
Система SHALL обрабатывать обновления от Telegram через webhook.

#### Scenario: Получение обновления от Telegram
- **WHEN** Telegram отправляет POST запрос на `/bot/webhook` с update
- **THEN** система обрабатывает update через Dispatcher
- **AND** применяются middleware (Idempotency, Auth)
- **AND** вызываются соответствующие обработчики

### Requirement: Driver Location Updates via Bot
Система SHALL позволять водителям отправлять свою локацию через Telegram бота.

#### Scenario: Отправка локации через бота
- **WHEN** водитель отправляет геолокацию через Telegram бота
- **THEN** система обрабатывает сообщение через location handler
- **AND** координаты сохраняются в Redis через LocationManager
- **AND** применяется идемпотентность для предотвращения дубликатов

### Requirement: Order Management via Bot
Система SHALL позволять водителям управлять заказами через Telegram бота.

#### Scenario: Просмотр заказов через бота
- **WHEN** водитель запрашивает список заказов через бота
- **THEN** система возвращает список заказов водителя с их статусами

#### Scenario: Обновление статуса заказа через бота
- **WHEN** водитель использует команды бота для изменения статуса заказа
- **THEN** система обрабатывает команду через orders handler
- **AND** статус заказа обновляется через OrderWorkflowService

### Requirement: Bot Authentication Middleware
Система SHALL проверять авторизацию водителей для всех команд бота.

#### Scenario: Проверка авторизации
- **WHEN** водитель отправляет команду боту
- **THEN** AuthMiddleware проверяет, что водитель зарегистрирован и активен
- **AND** неавторизованные запросы отклоняются

#### Scenario: Проверка активности водителя
- **WHEN** водитель с is_active=false пытается использовать бота
- **THEN** запрос отклоняется с сообщением о неактивном статусе

### Requirement: Idempotency Middleware
Система SHALL предотвращать дублирование обработки обновлений.

#### Scenario: Идемпотентная обработка
- **WHEN** Telegram отправляет повторное обновление (retry)
- **THEN** IdempotencyMiddleware проверяет, было ли обновление уже обработано
- **AND** дубликаты игнорируются без повторной обработки

### Requirement: Bot Configuration
Система SHALL использовать настройки из конфигурации для работы бота.

#### Scenario: Использование токена бота
- **WHEN** бот инициализируется
- **THEN** используется TELEGRAM_BOT_TOKEN из настроек
- **AND** бот работает в режиме HTML parse mode

#### Scenario: Настройка webhook
- **WHEN** бот запускается
- **THEN** устанавливается webhook на TELEGRAM_WEBHOOK_URL
- **AND** pending updates удаляются при установке webhook

