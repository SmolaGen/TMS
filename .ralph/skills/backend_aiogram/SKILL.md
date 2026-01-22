---
name: Telegram Bot Development (Aiogram v3)
description: Best practices for implementing Telegram Bots in TMS using Aiogram v3 and Redis.
---

# Telegram Bot Skill

## Technology Stack
- **Framework**: Aiogram 3.x
- **Storage**: Redis (for FSM and Caching)
- **Architecture**: Router-based (Modular)

## Key Patterns

### 1. Router Setup
Use `Router` for modularity. Do not attach handlers directly to `Dispatcher` in modules.
```python
from aiogram import Router
router = Router(name="feature_name")

@router.message(...)
async def handler(...): ...
```

### 2. Dependency Injection (Middleware)
Common objects like `driver` (User model) or configuration are injected via Middlewares (`AuthMiddleware`).
- **Handlers** should type-hint expected injected middleware arguments:
```python
@router.message(...)
async def handle_msg(message: Message, driver: Driver): 
    # 'driver' is injected by AuthMiddleware
    ...
```

### 3. Location & State Handling
- Use `src.services.location_manager.LocationManager` with Redis for handling geo-updates.
- Use `F.content_type == ContentType.LOCATION` filters.
- Support both `message` (one-time) and `edited_message` (Live Location updates).

### 4. Logging
Use `structlog` via `src.core.logging.get_logger`.
```python
logger = get_logger(__name__)
logger.info("event_name", user_id=123, key="value")
```
