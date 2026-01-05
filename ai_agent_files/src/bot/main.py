from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from redis.asyncio import Redis

from src.config import settings
from src.bot.middlewares.auth import AuthMiddleware
from src.bot.middlewares.idempotency import IdempotencyMiddleware
from src.bot.handlers import location, orders

async def create_bot() -> tuple[Bot, Dispatcher]:
    """Создание и конфигурация бота."""
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Подключение Redis
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    
    # Outer middleware (до фильтров) - идемпотентность
    dp.update.outer_middleware(IdempotencyMiddleware(redis))
    
    # Inner middleware - авторизация (для сообщений и edited_message)
    dp.message.middleware(AuthMiddleware())
    dp.edited_message.middleware(AuthMiddleware())
    
    # Регистрация роутеров
    dp.include_routers(
        location.router,
        orders.router,
    )
    
    return bot, dp

async def setup_webhook(bot: Bot) -> None:
    """Установка webhook."""
    await bot.set_webhook(
        url=f"{settings.TELEGRAM_WEBHOOK_URL}",
        drop_pending_updates=True
    )
