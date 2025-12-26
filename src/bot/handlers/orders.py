from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import settings

router = Router(name="orders")

@router.message(Command("orders"))
async def cmd_orders(message: Message, driver_id: int) -> None:
    """
    Отправляет inline-кнопку для открытия Mini App с заказами.
    """
    webapp_url = f"{settings.WEBAPP_URL}?driver_id={driver_id}"
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📋 Открыть заказы",
        web_app=WebAppInfo(url=webapp_url)
    )
    
    await message.answer(
        "<b>🚚 Мои заказы</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть список ваших заказов.",
        reply_markup=builder.as_markup()
    )

@router.message(Command("start"))
async def cmd_start(message: Message, driver_id: int) -> None:
    """Приветственное сообщение для авторизованного водителя."""
    await message.answer(
        "<b>👋 Добро пожаловать в TMS!</b>\n\n"
        "Вы авторизованы как водитель.\n\n"
        "<b>Доступные команды:</b>\n"
        "/orders - Открыть список заказов\n\n"
        "<b>📍 Отправка геолокации:</b>\n"
        "Используйте 'Отправить геолокацию' → 'Share Live Location' "
        "для трансляции своего местоположения диспетчеру."
    )
