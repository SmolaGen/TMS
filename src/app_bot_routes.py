from fastapi import FastAPI
from aiogram.types import Update

def configure_bot_webhook(app: FastAPI):
    """
    Configures the Telegram bot webhook endpoint.
    """
    @app.post("/bot/webhook")
    async def bot_webhook(update: dict):
        """Эндпоинт для получения обновлений от Telegram."""
        bot = app.state.bot
        dp = app.state.dp

        telegram_update = Update.model_validate(update, context={"bot": bot})
        await dp.feed_update(bot, telegram_update)
        return {"ok": True}
