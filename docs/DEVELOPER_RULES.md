# Правила разработки и решения проблем (TMS Project)

Этот документ содержит важные технические правила и паттерны, выявленные в ходе разработки и отладки проекта. Обязательно к прочтению при внесении изменений.

## 1. База данных и SQLAlchemy (Async)

### 1.1. Работа с Range типами (asyncpg)
Драйвер `asyncpg` **не поддерживает** автоматическое приведение строк вида `"[start, end)"` к типу `tstzrange` через `CAST(:val AS tstzrange)` или `::tstzrange`.

**Правило:** Всегда используйте SQL-функцию конструктора или передавайте нативные объекты (если поддерживается):
```sql
-- ПРАВИЛЬНО:
VALUES (..., tstzrange(:start, :end, '[)'))
```
```sql
-- НЕПРАВИЛЬНО:
VALUES (..., :time_range_string::tstzrange)
```

### 1.2. Обработка IntegrityError и Session Rollback
При ошибке `commit()` (например, нарушение Constraint), транзакция откатывается, и привязанные к сессии объекты переходят в состояние `expired`.
Попытка доступа к их атрибутам (например, `order.driver_id`) вызовет ошибку `PendingRollbackError` или новый запрос к БД, который упадет.

**Правило (Safe Commit Pattern):**
Кэшируйте все необходимые для логирования/ошибок данные в локальные переменные **до** вызова `commit()`.
```python
# ПРАВИЛЬНО:
driver_id = order.driver_id  # Cache local variable
try:
    await uow.commit()
except IntegrityError:
    logger.warning("Conflict", driver_id=driver_id) # Safe access
```

## 2. Тестирование (Pytest)

### 2.1. Изоляция транзакций (Nested Transactions)
Для тестов, которые ожидают ошибки БД (например, проверку `IntegrityError`), необходимо использовать `SAVEPOINT`. Иначе ошибка сломает основную транзакцию теста.

**Реализация:**
В фикстуре `TestUnitOfWork` или `client` используйте `await session.begin_nested()`.
```python
class TestUnitOfWork(SQLAlchemyUnitOfWork):
    async def __aenter__(self):
        self._savepoint = await self.session.begin_nested()
        ...
```

### 2.2. Flush vs Commit в тестах
В тестах, использующих общую сессию (в фикстурах), нельзя вызывать `session.commit()`, так как это закроет транзакцию.
**Правило:** Используйте `session.flush()` для отправки изменений в БД, оставляя транзакцию открытой для последующего отката.

### 2.3. Запуск тестов в Docker
Для корректного импорта модулей внутри контейнера требуется переменная окружения:
`PYTHONPATH=/app`

## 3. API и Роутинг

### 3.1. Порядок определения роутов
FastAPI обрабатывает роуты по порядку определения.
**Правило:** Статические пути (например, `/orders/active`) должны быть определены **ДО** динамических путей с параметрами `/orders/{order_id}`, чтобы избежать ошибочного матчинга (422 Error).

## 4. Инфраструктура

### 4.1. Синхронизация кода в Docker
Для отладки на удаленном сервере используйте комбинацию `rsync` (на хост) и `docker cp` (в контейнер).
```bash
rsync src/app.py root@host:~/tms/src/
ssh root@host "docker cp ~/tms/src/app.py tms-backend:/app/src/"
```
