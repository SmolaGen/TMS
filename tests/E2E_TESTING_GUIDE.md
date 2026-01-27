# Руководство по E2E тестированию настроек уведомлений

## Обзор

Данный документ описывает процесс end-to-end проверки настроек уведомлений в системе TMS.

## Что проверяется

1. **API функциональность**
   - Применение пресетов настроек (minimal, standard, maximum)
   - Сохранение настроек в базе данных
   - Обновление настроек уведомлений
   - Отключение конкретных типов уведомлений

2. **Интеграция с БД**
   - Корректность сохранения настроек
   - Уникальность constraints
   - Работа с индексами

3. **Логика отправки уведомлений**
   - Учет настроек при отправке
   - Проверка `should_send_notification()`
   - Корректность работы с частотами

4. **Frontend UI**
   - Отображение страницы настроек
   - Применение пресетов через UI
   - Сохранение изменений

## Способы запуска

### Способ 1: Python E2E тесты (рекомендуется)

#### Требования
- Python 3.10+
- Установленные зависимости из requirements.txt
- Не требует запущенных сервисов (использует тестовую БД)

#### Запуск

```bash
# Активация виртуального окружения
source .venv/bin/activate

# Установка зависимостей (если ещё не установлены)
pip install -r requirements.txt

# Запуск E2E тестов
pytest tests/test_e2e_notifications.py -v -s

# Запуск только определенного теста
pytest tests/test_e2e_notifications.py::TestE2ENotifications::test_e2e_full_workflow -v -s

# Запуск с покрытием
pytest tests/test_e2e_notifications.py -v --cov=src/services/notification_preferences_service --cov=src/services/notification_service
```

#### Ожидаемый результат

```
tests/test_e2e_notifications.py::TestE2ENotifications::test_e2e_full_workflow PASSED
tests/test_e2e_notifications.py::TestE2ENotifications::test_e2e_preset_transitions PASSED
tests/test_e2e_notifications.py::TestE2ENotifications::test_e2e_frequency_settings PASSED
tests/test_e2e_notifications.py::test_database_integration PASSED

✓ Пресет 'minimal' применен
✓ Настройки сохранены в БД
✓ NEW_ORDER отключен
✓ NotificationService учитывает настройки
```

### Способ 2: Bash-скрипт (требует запущенные сервисы)

#### Требования
- Запущенный backend на `http://localhost:8000`
- Запущенный frontend на `http://localhost:5173`
- Доступная база данных PostgreSQL

#### Подготовка окружения

1. **Запуск инфраструктуры** (если используется Docker):
```bash
docker-compose up -d postgres redis
```

2. **Применение миграций**:
```bash
alembic upgrade head
```

3. **Запуск backend**:
```bash
uvicorn src.main:app --reload --port 8000
```

4. **Запуск frontend** (в отдельном терминале):
```bash
cd frontend
npm run dev
```

#### Запуск скрипта

```bash
# Из корня проекта
./tests/test_e2e_notifications.sh
```

#### Ожидаемый результат

```
==========================================
E2E Тест: Настройки уведомлений
==========================================

[INFO] Проверка доступности Backend API: http://localhost:8000/docs
[SUCCESS] Backend API доступен
[INFO] Проверка доступности Frontend: http://localhost:5173
[SUCCESS] Frontend доступен

[INFO] Создание тестового водителя...
[SUCCESS] Тестовый водитель создан

[INFO] Получение авторизационного токена...
[SUCCESS] Токен получен

=== Шаг 1: Проверка сохранения настроек в БД ===
[INFO] Текущие настройки: [...]
[SUCCESS] Настройки успешно сохранены в БД

=== Шаг 2: Отключение уведомлений о новом заказе ===
[SUCCESS] Уведомления о новом заказе отключены

==========================================
Все тесты пройдены успешно!
==========================================
```

### Способ 3: Ручная проверка через браузер

1. **Откройте страницу настроек**:
   ```
   http://localhost:5173/settings
   ```

2. **Проверьте отображение**:
   - Страница загружается без ошибок
   - Виден заголовок "Настройки уведомлений"
   - Присутствуют селекторы для пресетов
   - Таблица с типами уведомлений отображается

3. **Примените пресет 'Минимальный'**:
   - Выберите "Минимальный" из выпадающего списка
   - Нажмите кнопку "Применить"
   - Проверьте, что настройки в таблице обновились

4. **Проверьте в консоли браузера**:
   - Откройте Developer Tools (F12)
   - Перейдите на вкладку Console
   - Убедитесь, что нет ошибок (красного текста)
   - Проверьте Network tab: запросы к API должны возвращать 200 OK

5. **Проверьте через API**:
```bash
# Получите токен авторизации (из LocalStorage в браузере)
TOKEN="ваш_токен"

# Проверьте настройки
curl -X GET "http://localhost:8000/api/v1/notifications/preferences" \
  -H "Authorization: Bearer $TOKEN"
```

## Структура тестов

### Python E2E тесты (`test_e2e_notifications.py`)

```python
class TestE2ENotifications:
    def test_e2e_full_workflow(self):
        """Полный цикл: пресет → БД → отключение → проверка"""

    def test_e2e_preset_transitions(self):
        """Переходы между пресетами"""

    def test_e2e_frequency_settings(self):
        """Настройка частоты уведомлений"""

def test_database_integration():
    """Проверка constraints и индексов"""
```

### Bash скрипт (`test_e2e_notifications.sh`)

```bash
test_api_availability()          # Проверка доступности сервисов
create_test_driver()              # Создание тестового пользователя
get_auth_token()                  # Получение токена
test_apply_minimal_preset()       # Применение пресета
test_verify_preferences_saved()   # Проверка сохранения в БД
test_disable_new_order_notifications()  # Отключение уведомлений
test_notification_disabled()      # Проверка логики
```

## Ручная проверка логики отправки

Для проверки того, что уведомления не отправляются при отключенных настройках:

### Вариант 1: Через Python

```python
from src.database.session import get_db
from src.services.notification_preferences_service import NotificationPreferencesService
from src.services.notification_service import NotificationService
from src.database.models import NotificationType, NotificationChannel

async def test():
    async for db in get_db():
        prefs_service = NotificationPreferencesService(db)
        notification_service = NotificationService(
            telegram_bot_token="your_token",
            preferences_service=prefs_service
        )

        # Проверьте для driver_id
        should_send = await notification_service.should_send_notification(
            driver_id=1,
            notification_type=NotificationType.NEW_ORDER,
            channel=NotificationChannel.TELEGRAM
        )

        print(f"Should send: {should_send}")  # Должно быть False
```

### Вариант 2: Через логи приложения

1. Запустите backend с отладочными логами:
```bash
uvicorn src.main:app --log-level debug
```

2. Инициируйте событие нового заказа

3. Проверьте логи:
   - Должно быть сообщение "Notification disabled by user preferences"
   - Или отсутсвие сообщения об отправке

## Решение проблем

### Проблема: Сервисы недоступны

**Решение**:
```bash
# Проверьте порты
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Перезапустите сервисы
./dev.sh  # Или индивидуально
```

### Проблема: Ошибка авторизации

**Решение**:
```bash
# Создайте тестового пользователя
curl -X POST "http://localhost:8000/api/v1/drivers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'

# Получите токен
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

### Проблема: База данных не мигрирована

**Решение**:
```bash
# Проверьте текущую версию миграции
alembic current

# Примените все миграции
alembic upgrade head

# Проверьте наличие таблицы
psql -U tms -d tms_db -c "\dt notification_preferences"
```

### Проблема: Тесты падают с ошибкой ImportError

**Решение**:
```bash
# Убедитесь, что вы в корне проекта
pwd  # Должен быть .../tasks/011-af1305

# Установите PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Или используйте pytest с правильным pythonpath
pytest --confcutdir=.
```

## Чек-лист для E2E проверки

Перед тем как считать задачу выполненной, убедитесь:

- [ ] Python E2E тесты проходят успешно
- [ ] Баш-скрипт выполняется без ошибок (если сервисы запущены)
- [ ] Frontend страница `/settings` загружается
- [ ] Пресеты применяются корректно через UI
- [ ] Настройки сохраняются в БД (проверить через API)
- [ ] Отключенные уведомления не отправляются
- [ ] В консоли браузера нет ошибок
- [ ] API endpoints возвращают корректные статусы

## Следующие шаги после прохождения тестов

1. **Обновите статус в implementation_plan.json**:
   ```json
   {
     "id": "subtask-4-4",
     "status": "completed"
   }
   ```

2. **Закоммитьте изменения**:
   ```bash
   git add tests/
   git commit -m "auto-claude: subtask-4-4 - End-to-end проверка настроек уведомлений"
   ```

3. **Обновите build-progress.txt**:
   Добавьте информацию о выполненных E2E тестах

## Контакты

При возникновении проблем с E2E тестами:
1. Проверьте логи в `logs/` (если есть)
2. Ознакомьтесь с unit тестами в `tests/test_notification_preferences_service.py`
3. Проверьте документацию API в `docs/api/`
