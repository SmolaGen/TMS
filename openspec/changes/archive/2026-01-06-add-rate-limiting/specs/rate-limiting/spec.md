## ADDED Requirements

### Requirement: Rate Limiting Middleware
Система SHALL применять rate limiting для защиты API от перегрузки.

#### Scenario: Инициализация Rate Limiter
- **WHEN** приложение запускается
- **THEN** создаётся limiter с Redis backend
- **AND** используется функция `get_remote_address` как ключ
- **AND** лимит по умолчанию считывается из `RATE_LIMIT_DEFAULT`

#### Scenario: Лимит по умолчанию
- **WHEN** запрос не имеет персонализированного лимита
- **THEN** применяется лимит из `RATE_LIMIT_DEFAULT` (например, "100/minute")
- **AND** при превышении возвращается 429 Too Many Requests

#### Scenario: Заголовки Rate Limiting
- **WHEN** включён `headers_enabled` в limiter
- **THEN** в каждый ответ добавляются заголовки:
  - `X-RateLimit-Limit` - максимальное количество запросов
  - `X-RateLimit-Remaining` - оставшиеся запросы
  - `X-RateLimit-Reset` - время сброса лимита

### Requirement: Redis Backend for Rate Limiting
Система SHALL использовать Redis для хранения счётчиков rate limiting.

#### Scenario: Хранение счётчиков в Redis
- **WHEN** запрос обрабатывается
- **THEN** счётчик запросов хранится в Redis
- **AND** ключ счётчика уникален для IP адреса
- **AND** счётчик автоматически истекает по TTL

#### Scenario: Distributed Rate Limiting
- **WHEN** запущено несколько инстансов приложения
- **THEN** rate limiting работает корректно через общий Redis
- **AND** счётчики синхронизируются между инстансами

#### Scenario: Очистка истёкших счётчиков
- **WHEN** TTL счётчика истекает
- **THEN** счётчик автоматически удаляется из Redis
- **AND** новый период rate limiting начинается с нуля

### Requirement: Custom Rate Limits per Endpoint
Система SHALL поддерживать персонализированные лимиты для разных эндпоинтов.

#### Scenario: Rate limiting для location updates
- **WHEN** запрос отправляется на `/drivers/{driver_id}/location`
- **THEN** применяется строгий лимит `RATE_LIMIT_LOCATION` (например, "10/minute")
- **AND** при превышении возвращается 429 Too Many Requests

#### Scenario: Rate limiting для авторизации
- **WHEN** запрос отправляется на `/auth/login`
- **THEN** применяется строгий лимит для защиты от брутфорса
- **AND** при превышении возвращается 429 Too Many Requests

#### Scenario: Применение декоратора limiter
- **WHEN** эндпоинт требует специфического лимита
- **THEN** используется декоратор `@limiter.limit("limit_string")`
- **AND** лимит указывается в формате "N/second", "N/minute", "N/hour"

### Requirement: Rate Limit Exception Handling
Система SHALL корректно обрабатывать превышение лимитов запросов.

#### Scenario: Превышение лимита
- **WHEN** клиент превышает разрешённое количество запросов
- **THEN** возвращается HTTP статус 429 Too Many Requests
- **AND** в теле ответа содержится сообщение о превышении лимита
- **AND** добавляются заголовки с информацией о лимитах

#### Scenario: Retry-After Header
- **WHEN** превышен лимит запросов
- **THEN** добавляется заголовок `Retry-After`
- **AND** указано количество секунд до сброса лимита

#### Scenario: Логирование превышений
- **WHEN** превышен лимит запросов
- **THEN** событие логируется с уровнем WARNING
- **AND** логируется IP адрес и превышенный эндпоинт

### Requirement: WebSocket Origin Validation
Система SHALL проверять Origin для WebSocket соединений.

#### Scenario: Валидный Origin
- **WHEN** WebSocket клиент подключается с валидным Origin
- **THEN** Origin проверяется по списку `CORS_ORIGINS`
- **AND** соединение принимается
- **AND** отправляется приветственное сообщение HELLO

#### Scenario: Невалидный Origin
- **WHEN** WebSocket клиент подключается с невалидным Origin
- **THEN** соединение отклоняется с кодом 1008
- **AND** клиент получает причину "Origin not allowed"

#### Scenario: Логирование отклонённых соединений
- **WHEN** WebSocket соединение отклоняется
- **THEN** событие логируется с уровнем WARNING
- **AND** логируется отклонённый Origin

### Requirement: Rate Limiting Configuration
Система SHALL использовать настройки из конфигурации для rate limiting.

#### Scenario: Конфигурация Redis URL
- **WHEN** limiter инициализируется
- **THEN** используется `REDIS_URL` для подключения к Redis
- **AND** при недоступности Redis логируется ошибка

#### Scenario: Конфигурация лимитов по умолчанию
- **WHEN** limiter инициализируется
- **THEN** используется `RATE_LIMIT_DEFAULT` для всех эндпоинтов без кастомного лимита
- **AND** используется `RATE_LIMIT_LOCATION` для location updates

#### Scenario: Конфигурация CORS Origins для WebSocket
- **WHEN** проверяется WebSocket Origin
- **THEN** используется `CORS_ORIGINS` (разделённый запятыми список)
- **AND** каждый Origin проверяется индивидуально
