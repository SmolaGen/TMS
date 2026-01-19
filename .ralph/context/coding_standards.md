# 📏 Стандарты Кодирования

---

## Python (Backend)

### Именование
```python
# Переменные и функции — snake_case
user_name = "John"
def get_user_by_id(user_id: int) -> User: ...

# Классы — PascalCase
class UserService: ...

# Константы — UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
```

### Типизация
```python
# ✅ ПРАВИЛЬНО — всегда типизируй
def create_order(data: OrderCreate) -> Order:
    ...

# ❌ НЕПРАВИЛЬНО — без типов
def create_order(data):
    ...
```

### Структура API endpoint
```python
@router.post("/orders", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Создание нового заказа."""
    service = OrderService(db)
    return await service.create(data, current_user)
```

### Обработка ошибок
```python
from fastapi import HTTPException, status

# Используй стандартные HTTP исключения
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Order not found"
)
```

---

## TypeScript (Frontend)

### Именование
```typescript
// Переменные и функции — camelCase
const userName = "John";
function getUserById(userId: string): User { ... }

// Компоненты и типы — PascalCase
interface UserData { ... }
function UserCard({ user }: Props) { ... }

// Константы — UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3;
```

### Компоненты React
```typescript
// ✅ ПРАВИЛЬНО — функциональные компоненты с типами
interface UserCardProps {
  user: User;
  onEdit?: (id: string) => void;
}

export function UserCard({ user, onEdit }: UserCardProps) {
  return (
    <div className={styles.card}>
      <h2>{user.name}</h2>
    </div>
  );
}

// ❌ НЕПРАВИЛЬНО — any, отсутствие типов
export function UserCard({ user }: any) { ... }
```

### Хуки
```typescript
// Кастомные хуки начинаются с "use"
function useUserData(userId: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => api.getUser(userId),
  });
  
  return { user: data, isLoading, error };
}
```

### Стили
```typescript
// Используй CSS Modules
import styles from './UserCard.module.css';

// Или Tailwind с cn() для условных классов
import { cn } from '@/lib/utils';

<div className={cn(
  'p-4 rounded-lg',
  isActive && 'bg-primary',
  isDisabled && 'opacity-50'
)} />
```

---

## Общие Правила

### Комментарии
```python
# ✅ ПРАВИЛЬНО — объясняй ПОЧЕМУ, а не ЧТО
# Используем кэш, т.к. запрос к БД занимает >500ms
cached_result = cache.get(key)

# ❌ НЕПРАВИЛЬНО — очевидные комментарии
# Получаем результат из кэша
cached_result = cache.get(key)
```

### Файлы
- Один файл = одна ответственность
- Имена файлов в `kebab-case`: `user-service.ts`
- Максимум 300 строк на файл (разбивай, если больше)

### Импорты
```python
# Python: группируй импорты
# 1. Стандартная библиотека
import os
from datetime import datetime

# 2. Сторонние пакеты
from fastapi import APIRouter
from sqlalchemy import select

# 3. Локальные модули
from src.db.models import User
from src.services.user import UserService
```

```typescript
// TypeScript: группируй импорты
// 1. React/Next.js
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. Сторонние пакеты
import { useQuery } from '@tanstack/react-query';

// 3. Локальные модули
import { UserCard } from '@/components/UserCard';
import { useAuth } from '@/hooks/useAuth';
```

---

## Запреты ⛔

- **Никогда не используй `any`** в TypeScript
- **Никогда не используй `# type: ignore`** в Python (кроме редких случаев с обоснованием)
- **Не добавляй новые зависимости** без согласования
- **Не меняй структуру БД** без миграции
- **Не удаляй тесты**, даже если они "мешают"
