## ADDED Requirements

### Requirement: Health Check Availability
Система SHALL предоставлять endpoint `/health` для проверки работоспособности сервиса.

#### Scenario: Получение статуса сервиса
- **WHEN** отправляется GET запрос на `/health`
- **THEN** возвращается JSON с информацией о состоянии сервиса
- **AND** возвращается статус 200 OK при нормальной работе

#### Scenario: Ответ health check
- **WHEN** запрос к `/health` успешен
- **THEN** возвращается JSON с полями:
  - `status` - строка "healthy" или "unhealthy"
  - `service` - название сервиса "tms-backend"
  - `timestamp` - время проверки (опционально)

### Requirement: Service Connectivity Check
Система SHALL проверять подключение к критическим зависимым сервисам.

#### Scenario: Проверка PostgreSQL
- **WHEN** вызывается `/health`
- **THEN** выполняется пробный запрос к PostgreSQL
- **AND** при успешном подключении статус БД помечается как "connected"
- **AND** при ошибке подключения возвращается статус 503

#### Scenario: Проверка Redis
- **WHEN** вызывается `/health`
- **THEN** выполняется проверка подключения к Redis (PING)
- **AND** при успешном подключении статус Redis помечается как "connected"
- **AND** при ошибке подключения возвращается статус 503

#### Scenario: Проверка OSRM (опционально)
- **WHEN** вызывается `/health`
- **THEN** выполняется проверка доступности OSRM (если настроен)
- **AND** при недоступности OSRM сервис может работать в режиме degraded

### Requirement: Health Check Response Format
Система SHALL использовать стандартизированный формат ответа health check.

#### Scenario: Формат при успешной проверке
- **WHEN** все сервисы доступны
- **THEN** ответ содержит:
  ```json
  {
    "status": "healthy",
    "service": "tms-backend",
    "database": "connected",
    "redis": "connected"
  }
  ```

#### Scenario: Формат при ошибке БД
- **WHEN** PostgreSQL недоступен
- **THEN** ответ содержит статус 503
- **AND** возвращается:
  ```json
  {
    "status": "unhealthy",
    "service": "tms-backend",
    "error": "Database connection failed"
  }
  ```

### Requirement: Health Check Usage Patterns
Система SHALL быть совместима с типовыми паттернами использования health check.

#### Scenario: Kubernetes liveness probe
- **WHEN** kubernetes делает запрос на `/health` для liveness
- **THEN** возвращается 200 если приложение живо
- **AND** возвращается 500+ если приложение должно быть перезапущено

#### Scenario: Kubernetes readiness probe
- **WHEN** kubernetes делает запрос на `/health` для readiness
- **THEN** возвращается 200 если приложение готово принимать трафик
- **AND** возвращается 503 если зависимые сервисы недоступны

#### Scenario: Load balancer check
- **WHEN** load balancer проверяет состояние сервиса
- **THEN** `/health` возвращает 200 для healthy инстансов
- **AND** unhealthy инстансы получают статус 503 и исключаются из ротации
