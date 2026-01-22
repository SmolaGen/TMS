import os
from fastapi import FastAPI
from src.config import settings
from src.bot.main import create_bot, setup_webhook
from src.core.logging import get_logger
from src.workers.scheduler import TMSProjectScheduler

logger = get_logger(__name__)

async def initialize_telegram_bot(app: FastAPI):
    # Инициализация Бота (graceful fallback если токен невалидный)
    try:
        bot, dp = await create_bot()
        app.state.bot = bot
        app.state.dp = dp

        # Установка webhook (только в prod/staging, при наличии URL)
        if settings.TELEGRAM_WEBHOOK_URL and "your-bot-token" not in settings.TELEGRAM_BOT_TOKEN:
            await setup_webhook(bot)
            logger.info("bot_webhook_set", url=settings.TELEGRAM_WEBHOOK_URL)

        # Запуск планировщика
        if bot:
            scheduler = TMSProjectScheduler(bot)
            await scheduler.start()
            app.state.scheduler = scheduler
    except Exception as e:
        logger.warning("bot_init_failed", error=str(e))
        app.state.bot = None
        app.state.dp = None

async def shutdown_telegram_bot(app: FastAPI):
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        await app.state.scheduler.shutdown()
