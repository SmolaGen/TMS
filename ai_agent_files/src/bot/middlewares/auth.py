from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.database.uow import SQLAlchemyUnitOfWork
from src.database.models import Driver, UserRole
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class AuthMiddleware(BaseMiddleware):
    """
    Проверяет авторизацию пользователя.
    - Если пользователь новый, создает запись со статусом PENDING.
    - Если пользователь PENDING или неактивен, блокирует доступ (кроме админа).
    - Админ (alsmolentsev) всегда имеет доступ.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем telegram_id из события
        if not hasattr(event, 'from_user') or event.from_user is None:
            return await handler(event, data)
        
        user = event.from_user
        telegram_id = user.id
        username = user.username
        
        # 1. Проверка на админа (по username или telegram_id из конфига)
        is_admin = False
        if telegram_id == settings.ADMIN_TELEGRAM_ID:
            is_admin = True
        elif username and settings.ADMIN_USERNAME:
            is_admin = username.lower() == settings.ADMIN_USERNAME.lower()
        
        # 2. Поиск или создание пользователя в БД
        async with SQLAlchemyUnitOfWork() as uow:
            db_user = await uow.drivers.get_by_attribute("telegram_id", telegram_id)
            
            if db_user is None:
                # Регистрируем нового пользователя
                new_user = Driver(
                    telegram_id=telegram_id,
                    name=user.full_name or username or str(telegram_id),
                    role=UserRole.ADMIN if is_admin else UserRole.PENDING,
                    is_active=is_admin # Админ активен сразу
                )
                uow.drivers.add(new_user)
                await uow.commit() # Сохраняем, чтобы получить ID и т.д.
                db_user = new_user
                
                logger.info("new_user_registered", telegram_id=telegram_id, username=username, role=db_user.role)
                
                # Если это не админ, уведомляем админа о новой заявке
                if not is_admin:
                    from src.bot.handlers.admin import notify_admin_new_user
                    bot = data.get("bot")
                    if bot:
                        await notify_admin_new_user(bot, {
                            "id": telegram_id,
                            "username": username,
                            "first_name": user.first_name
                        })
            elif is_admin and db_user.role != UserRole.ADMIN:
                # Автоматически повышаем до админа, если username совпал
                db_user.role = UserRole.ADMIN
                db_user.is_active = True
                await uow.commit()
                logger.info("user_promoted_to_admin", telegram_id=telegram_id, username=username)

        # 3. Проверка прав доступа
        if not is_admin:
            if db_user.role == UserRole.PENDING:
                if isinstance(event, Message):
                    await event.answer(
                        "⏳ **Ваша заявка находится на рассмотрении.**\n"
                        "Администратор скоро назначит вам роль (водитель или диспетчер). "
                        "Вы получите уведомление об одобрении."
                    )
                return
            
            if not db_user.is_active:
                if isinstance(event, Message):
                    await event.answer("⛔ Ваш аккаунт заблокирован администратором.")
                return
        
        # Добавляем данные в context
        data["driver"] = db_user
        data["driver_id"] = db_user.id
        data["is_admin"] = is_admin
        
        return await handler(event, data)
