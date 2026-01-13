# monitoring Specification

## Purpose
TBD - created by archiving change add-monitoring. Update Purpose after archive.
## Requirements
### Requirement: Prometheus Metrics Endpoint
Система SHALL предоставлять endpoint `/metrics` для сбора метрик в формате Prometheus.

#### Scenario: Доступ к метрикам
- **WHEN** отправляется GET запрос на `/metrics`
- **THEN** возвращаются метрики в формате Prometheus
- **AND** Content-Type установлен в `text/plain`

#### Scenario: Request Counter Metric
- **WHEN** обрабатывается HTTP запрос
- **THEN** инкрементируется метрика `tms_requests_total`
- **AND** метрика содержит лейблы: method, endpoint, status

#### Scenario: Request Latency Metric
- **WHEN** обрабатывается HTTP запрос
- **THEN** измеряется и записывается метрика `tms_request_latency_seconds`
- **AND** метрика содержит лейблы: method, endpoint
- **AND** время измеряется в секундах

### Requirement: Prometheus Metrics Instrumentation
Система SHALL автоматически собирать метрики для всех HTTP эндпоинтов.

#### Scenario: Автоматический сбор метрик
- **WHEN** приложение запускается
- **THEN** все HTTP эндпоинты автоматически инструментируются
- **AND** каждый запрос увеличивает счетчик `tms_requests_total`
- **AND** каждый запрос записывает время выполнения в `tms_request_latency_seconds`

#### Scenario: Лейблы метода
- **WHEN** запрос обрабатывается
- **THEN** метрика `tms_requests_total` содержит лейбл method с HTTP методом (GET, POST, PATCH, DELETE)

#### Scenario: Лейбл endpoint
- **WHEN** запрос обрабатывается
- **THEN** метрика `tms_requests_total` содержит лейбл endpoint с путём эндпоинта

#### Scenario: Лейбл status
- **WHEN** запрос обрабатывается
- **THEN** метрика `tms_requests_total` содержит лейбл status с HTTP статус кодом (200, 404, 500)

### Requirement: Sentry Error Tracking
Система SHALL отправлять ошибки в Sentry для мониторинга в production.

#### Scenario: Инициализация Sentry
- **WHEN** приложение запускается в production
- **AND** настроен `SENTRY_DSN`
- **THEN** Sentry SDK инициализируется
- **AND** интегрируется с FastAPI и Starlette

#### Scenario: Отправка ошибок
- **WHEN** происходит необработанное исключение
- **THEN** ошибка автоматически отправляется в Sentry
- **AND** включается trace sampling (10%)

#### Scenario: Environment Label
- **WHEN** Sentry инициализируется
- **THEN** события помечаются лейблом environment (production/staging/development)

#### Scenario: Sentry не инициализируется в dev
- **WHEN** приложение запускается не в production
- **THEN** Sentry не инициализируется
- **AND** ошибки не отправляются

### Requirement: Health Check Endpoint
Система SHALL предоставлять endpoint `/health` для проверки работоспособности сервиса.

#### Scenario: Базовый health check
- **WHEN** отправляется GET запрос на `/health`
- **THEN** возвращается JSON с полем status="healthy"
- **AND** возвращается поле service="tms-backend"

#### Scenario: Health check успешный
- **WHEN** все сервисы работают корректно
- **THEN** `/health` возвращает статус 200 OK
- **AND** ответ содержит status: "healthy"

#### Scenario: Health check при критической ошибке
- **WHEN** есть критическая проблема с сервисом
- **THEN** `/health` возвращает статус 503 Service Unavailable
- **AND** ответ содержит статус ошибки

### Requirement: Service Dependencies Check
Система SHALL проверять состояние зависимых сервисов при health check.

#### Scenario: Проверка подключения к PostgreSQL
- **WHEN** вызывается `/health`
- **THEN** проверяется подключение к PostgreSQL
- **AND** при невозможности подключения возвращается ошибка

#### Scenario: Проверка подключения к Redis
- **WHEN** вызывается `/health`
- **THEN** проверяется подключение к Redis
- **AND** при невозможности подключения возвращается ошибка

#### Scenario: Проверка доступности OSRM
- **WHEN** вызывается `/health`
- **THEN** проверяется доступность OSRM (опционально)
- **AND** при недоступности OSRM сервис помечается как degraded

### Requirement: Application Lifecycle Hooks
Система SHALL правильно инициализировать и останавливать мониторинг при запуске/остановке приложения.

#### Scenario: Инициализация при запуске
- **WHEN** приложение запускается (lifespan startup)
- **THEN** Prometheus метрики регистрируются
- **AND** Sentry инициализируется (если production)
- **AND** логируется статус инициализации

#### Scenario: Корректная остановка
- **WHEN** приложение останавливается (lifespan shutdown)
- **THEN** все подключения к БД закрываются
- **AND** флешируются оставшиеся метрики
- **AND** логируется остановка приложения

