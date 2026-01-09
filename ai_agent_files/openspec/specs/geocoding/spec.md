# geocoding Specification

## Purpose
TBD - created by archiving change add-missing-specs. Update Purpose after archive.
## Requirements
### Requirement: Address Search
Система SHALL предоставлять поиск адресов через локальный сервис Photon.

#### Scenario: Поиск адреса по тексту
- **WHEN** отправляется GET запрос на `/api/v1/geocoding/search` с параметром q (текст запроса)
- **THEN** система обращается к Photon API для поиска адресов
- **AND** возвращается список GeocodingResult с координатами и полными адресами
- **AND** результаты ограничены параметром limit (по умолчанию 10)

#### Scenario: Пустой результат поиска
- **WHEN** поиск не находит совпадений
- **THEN** возвращается пустой список

### Requirement: Reverse Geocoding
Система SHALL предоставлять обратный геокодинг (адрес по координатам).

#### Scenario: Получение адреса по координатам
- **WHEN** отправляется GET запрос на `/api/v1/geocoding/reverse` с параметрами lat и lon
- **THEN** система обращается к Photon API для обратного геокодинга
- **AND** возвращается GeocodingResult с адресом для указанных координат

#### Scenario: Координаты вне зоны покрытия
- **WHEN** координаты находятся вне зоны покрытия Photon
- **THEN** возвращается null или пустой результат

### Requirement: Geocoding Service Integration
Система SHALL использовать локальный инстанс Photon для независимости от внешних API.

#### Scenario: Работа с локальным Photon
- **WHEN** система обращается к геокодингу
- **THEN** запросы направляются на локальный Photon (порт 2322)
- **AND** не требуется подключение к внешним сервисам

