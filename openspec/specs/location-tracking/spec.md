# location-tracking Specification

## Purpose
TBD - created by archiving change add-missing-specs. Update Purpose after archive.
## Requirements
### Requirement: Real-time Location Updates
Система SHALL обеспечивать высокопроизводительное обновление координат водителей через Redis.

#### Scenario: Обновление локации водителя
- **WHEN** водитель отправляет POST запрос на `/api/v1/drivers/{driver_id}/location` с координатами
- **THEN** координаты сохраняются в Redis с ключом `driver:location:{driver_id}`
- **AND** данные включают latitude, longitude, status и timestamp
- **AND** применяется rate limiting (30 запросов в минуту)

#### Scenario: Получение текущих локаций активных водителей
- **WHEN** отправляется GET запрос на `/api/v1/drivers/live` с валидным токеном
- **THEN** возвращаются текущие координаты всех активных водителей из Redis
- **AND** данные включают driver_id, координаты, статус и timestamp

#### Scenario: Защита от обновления чужой локации
- **WHEN** водитель пытается обновить локацию другого водителя
- **THEN** возвращается ошибка 403 Forbidden

### Requirement: Location History Persistence
Система SHALL сохранять историю перемещений водителей в PostgreSQL.

#### Scenario: Периодическое сохранение координат
- **WHEN** воркер sync_worker запускается периодически
- **THEN** координаты из Redis сохраняются в таблицу driver_location_history
- **AND** записываются только координаты, изменившиеся более чем на 50 метров
- **AND** используется партиционирование по месяцам для оптимизации

#### Scenario: Запрос истории перемещений
- **WHEN** запрашивается история перемещений водителя за период
- **THEN** возвращаются все записи из driver_location_history за указанный период
- **AND** данные отсортированы по времени recorded_at

### Requirement: Location Data Structure
Система SHALL хранить координаты в формате PostGIS POINT.

#### Scenario: Сохранение координат в БД
- **WHEN** координаты сохраняются в PostgreSQL
- **THEN** используется тип Geometry(POINT, SRID=4326) для WGS84
- **AND** данные индексируются для быстрого поиска

