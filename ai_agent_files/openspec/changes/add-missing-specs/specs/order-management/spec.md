## ADDED Requirements

### Requirement: Order Creation
Система SHALL предоставлять возможность создания новых заказов с проверкой конфликтов времени.

#### Scenario: Успешное создание заказа
- **WHEN** отправляется POST запрос на `/api/v1/orders` с валидными данными (pickup/dropoff адреса, time_range)
- **THEN** создается новый заказ со статусом PENDING
- **AND** заказ автоматически привязывается к текущему авторизованному водителю
- **AND** возвращается OrderResponse с данными созданного заказа

#### Scenario: Создание заказа с конфликтом времени
- **WHEN** создается заказ с временным интервалом, пересекающимся с существующим заказом того же водителя
- **THEN** PostgreSQL Exclusion Constraint предотвращает создание заказа
- **AND** возвращается ошибка 400 с описанием конфликта

#### Scenario: Автоматический расчет маршрута при создании
- **WHEN** создается заказ с координатами pickup и dropoff
- **THEN** система автоматически рассчитывает маршрут через OSRM
- **AND** сохраняются distance_meters, duration_seconds и route_geometry

### Requirement: Order List Retrieval
Система SHALL предоставлять список заказов с опциональной фильтрацией.

#### Scenario: Получение всех заказов
- **WHEN** отправляется GET запрос на `/api/v1/orders` с валидным токеном
- **THEN** возвращается список всех заказов текущего водителя

#### Scenario: Фильтрация заказов по времени
- **WHEN** отправляется GET запрос с параметрами start и end
- **THEN** возвращаются только заказы, попадающие в указанный временной диапазон

### Requirement: Order Workflow Management
Система SHALL управлять жизненным циклом заказа через State Machine.

#### Scenario: Назначение водителя на заказ
- **WHEN** отправляется POST запрос на `/api/v1/orders/{order_id}/assign/{driver_id}`
- **THEN** заказ переходит в статус ASSIGNED
- **AND** водитель получает статус BUSY
- **AND** driver_id сохраняется в заказе

#### Scenario: Отметка прибытия водителя
- **WHEN** отправляется POST запрос на `/api/v1/orders/{order_id}/arrive`
- **THEN** заказ переходит в статус DRIVER_ARRIVED
- **AND** сохраняется timestamp arrived_at

#### Scenario: Начало поездки
- **WHEN** отправляется POST запрос на `/api/v1/orders/{order_id}/start`
- **THEN** заказ переходит в статус IN_PROGRESS
- **AND** сохраняется timestamp started_at

#### Scenario: Завершение заказа
- **WHEN** отправляется POST запрос на `/api/v1/orders/{order_id}/complete`
- **THEN** заказ переходит в статус COMPLETED
- **AND** сохраняется timestamp end_time
- **AND** статус водителя меняется на AVAILABLE

#### Scenario: Отмена заказа
- **WHEN** отправляется POST запрос на `/api/v1/orders/{order_id}/cancel` с опциональной причиной
- **THEN** заказ переходит в статус CANCELLED
- **AND** сохраняется cancellation_reason и cancelled_at
- **AND** статус водителя меняется на AVAILABLE

### Requirement: Order Time Modification
Система SHALL позволять изменять время выполнения заказа с проверкой конфликтов.

#### Scenario: Перемещение заказа по времени
- **WHEN** отправляется PATCH запрос на `/api/v1/orders/{order_id}/move` с новым time_range
- **THEN** время заказа обновляется в БД
- **AND** проверяется отсутствие конфликтов с другими заказами водителя
- **AND** изменения отражаются в реальном времени на фронтенде

#### Scenario: Конфликт при перемещении
- **WHEN** перемещение заказа создает конфликт времени с другим заказом
- **THEN** операция отклоняется с ошибкой 400
- **AND** исходное время заказа сохраняется
