from fastapi import FastAPI

from src.bot.main import create_bot, setup_webhook
from src.bot_init import initialize_telegram_bot, shutdown_telegram_bot
from src.core.logging import get_logger

logger = get_logger(__name__)



async def setup_telegram_bot(app: FastAPI):
    """
    Initializes and sets up the Telegram bot.
    """
    await initialize_telegram_bot(app)

async def shutdown_telegram_bot_module(app: FastAPI):
    """
    Shuts down the Telegram bot.
    """
    await shutdown_telegram_bot(app)
