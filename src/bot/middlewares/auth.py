from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.database.uow import SQLAlchemyUnitOfWork

class AuthMiddleware(BaseMiddleware):
    """
    Проверяет, зарегистрирован ли telegram_id отправителя в таблице drivers.
    Прерывает обработку если водитель не найден или не активен.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем telegram_id из события
        if not hasattr(event, 'from_user') or event.from_user is None:
            return  # Системное сообщение без отправителя
        
        telegram_id = event.from_user.id
        
        # Проверка в БД
        async with SQLAlchemyUnitOfWork() as uow:
            driver = await uow.drivers.get_by_attribute(
                "telegram_id", telegram_id
            )
        
        if driver is None:
            # Водитель не зарегистрирован
            if isinstance(event, Message):
                await event.answer(
                    "⛔ Доступ запрещён.\n"
                    "Вы не зарегистрированы как водитель в системе."
                )
            return  # Прерываем обработку
            
        if not getattr(driver, "is_active", True):
             # Водитель деактивирован
            if isinstance(event, Message):
                await event.answer(
                    "⛔ Доступ ограничен.\n"
                    "Ваша учетная запись водителя неактивна."
                )
            return  # Прерываем обработку
        
        # Добавляем driver в data для использования в хендлерах
        data["driver"] = driver
        data["driver_id"] = driver.id
        
        return await handler(event, data)
