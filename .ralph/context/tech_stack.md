# 🛠️ Технологический Стек Проекта TMS

---

## Backend (Python)

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Framework | FastAPI | 0.104+ |
| ORM | SQLAlchemy | 2.0+ |
| Миграции | Alembic | 1.13+ |
| Валидация | Pydantic | 2.0+ |
| База данных | PostgreSQL + PostGIS | 15+ |
| Кэш | Redis | 7+ |
| Очереди | Celery | 5+ |
| Тесты | Pytest | 7+ |
| Линтинг | Ruff | latest |

### Структура Backend

```
src/
├── api/           # API endpoints (FastAPI routers)
├── core/          # Настройки, конфиги, зависимости
├── db/            # Модели SQLAlchemy, сессии
├── schemas/       # Pydantic модели
├── services/      # Бизнес-логика
├── utils/         # Утилиты
└── bot/           # Telegram бот
```

---

## Frontend (TypeScript)

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Framework | Next.js | 14+ (App Router) |
| Язык | TypeScript | 5+ |
| Стили | CSS Modules + Tailwind | 3.4+ |
| State | React Query (TanStack) | 5+ |
| Формы | React Hook Form | 7+ |
| Тесты | Jest + Testing Library | latest |

### Структура Frontend

```
frontend/
├── src/
│   ├── app/           # Next.js App Router
│   ├── components/    # React компоненты
│   ├── hooks/         # Кастомные хуки
│   ├── lib/           # Утилиты, API клиент
│   ├── stores/        # Zustand stores
│   └── types/         # TypeScript типы
├── public/            # Статика
└── tests/             # Тесты
```

---

## Инфраструктура

| Компонент | Технология |
|-----------|------------|
| Контейнеризация | Docker + Docker Compose |
| Веб-сервер | Nginx |
| Маршрутизация | OSRM |
| CI/CD | GitHub Actions |
| Мониторинг | Sentry |

---

## Ключевые Команды

### Backend
```bash
# Запуск dev-сервера
python -m uvicorn src.main:app --reload

# Тесты
pytest tests/ -v

# Миграции
alembic upgrade head

# Линтинг
ruff check src/
```

### Frontend
```bash
# Запуск dev-сервера
npm run dev

# Тесты
npm run test

# Type-check
npm run typecheck

# Сборка
npm run build
```

### Docker
```bash
# Запуск всего стека
docker-compose -f docker-compose-network.yml up -d

# Остановка
docker-compose -f docker-compose-network.yml down
```

---

## Важные Порты

| Сервис | Порт |
|--------|------|
| Backend API | 8000 |
| Frontend | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| OSRM | 5001 |
