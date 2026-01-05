from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class IdempotencyMiddleware(BaseMiddleware):
    """
    Outer middleware для фильтрации повторных update_id.
    
    Telegram гарантирует доставку "at-least-once", поэтому один и тот же
    update может прийти несколько раз. Используем Redis SET NX для защиты.
    
    Стратегия: Fail Open (при ошибке Redis пропускаем, но логируем)
    """
    
    KEY_PREFIX = "tg:update"
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = settings.IDEMPOTENCY_TTL_SECONDS
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        update_id = event.update_id
        key = f"{self.KEY_PREFIX}:{update_id}"
        
        try:
            # SET NX - установится только если ключа нет
            is_new = await self.redis.set(key, "1", ex=self.ttl, nx=True)
            
            if not is_new:
                # Дубликат - пропускаем без ошибки
                logger.debug(
                    "duplicate_update_skipped",
                    update_id=update_id
                )
                return None
                
        except RedisError as e:
            # Fail Open: при ошибке Redis пропускаем проверку
            logger.warning(
                "idempotency_check_failed",
                update_id=update_id,
                error=str(e)
            )
        
        # Продолжаем обработку
        return await handler(event, data)
