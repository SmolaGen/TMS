from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models import UserRole, Driver
from src.database.uow import SQLAlchemyUnitOfWork
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = Router(name="admin")

from typing import Optional

def is_admin(user_id: int, username: Optional[str] = None) -> bool:
    if user_id == settings.ADMIN_TELEGRAM_ID:
        return True
    if not username or not settings.ADMIN_USERNAME:
        return False
    return username.lower() == settings.ADMIN_USERNAME.lower()

def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏳ Ожидающие одобрения", callback_data="admin:pending"))
    builder.row(InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin:users:all"))
    builder.row(InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin:users:blocked"))
    return builder.as_markup()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not message.from_user or not is_admin(message.from_user.id, message.from_user.username):
        return
    
    await message.answer(
        "👋 Добро пожаловать в панель администратора!\nВыберите действие:",
        reply_markup=get_admin_main_kb()
    )

@router.callback_query(F.data == "admin:pending")
async def show_pending_users(callback: CallbackQuery):
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    async with SQLAlchemyUnitOfWork() as uow:
        users = await uow.drivers.get_all(role=UserRole.PENDING)
    
    if not users:
        await callback.message.edit_text("Нет пользователей, ожидающих одобрения.", reply_markup=get_admin_main_kb())
        return

    builder = InlineKeyboardBuilder()
    for user in users:
        name = user.name or f"ID: {user.telegram_id}"
        builder.row(InlineKeyboardButton(text=f"👤 {name}", callback_data=f"admin:user:{user.id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:main"))
    await callback.message.edit_text("Пользователи, ожидающие одобрения:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin:users:all"))
async def show_all_users(callback: CallbackQuery):
    """Показать всех активных пользователей."""
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    # Парсим страницу (page:0, page:1, ...)
    parts = callback.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    per_page = 10

    async with SQLAlchemyUnitOfWork() as uow:
        # Получаем всех пользователей кроме PENDING
        all_users = await uow.drivers.get_all()
        active_users = [u for u in all_users if u.role != UserRole.PENDING and u.is_active]
    
    if not active_users:
        await callback.message.edit_text("Нет активных пользователей.", reply_markup=get_admin_main_kb())
        return

    # Пагинация
    total_pages = (len(active_users) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    users_page = active_users[start_idx:end_idx]

    builder = InlineKeyboardBuilder()
    for user in users_page:
        role_emoji = "🚗" if user.role == UserRole.DRIVER else "🎧" if user.role == UserRole.DISPATCHER else "👑"
        name = user.name or f"ID: {user.telegram_id}"
        builder.row(InlineKeyboardButton(text=f"{role_emoji} {name}", callback_data=f"admin:user:{user.id}"))
    
    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"admin:users:all:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"admin:users:all:{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:main"))
    await callback.message.edit_text(
        f"👥 Все пользователи ({len(active_users)}) — стр. {page + 1}/{total_pages}:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("admin:users:blocked"))
async def show_blocked_users(callback: CallbackQuery):
    """Показать заблокированных пользователей."""
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    async with SQLAlchemyUnitOfWork() as uow:
        all_users = await uow.drivers.get_all()
        blocked_users = [u for u in all_users if not u.is_active]
    
    if not blocked_users:
        await callback.message.edit_text("Нет заблокированных пользователей.", reply_markup=get_admin_main_kb())
        return

    builder = InlineKeyboardBuilder()
    for user in blocked_users:
        name = user.name or f"ID: {user.telegram_id}"
        builder.row(InlineKeyboardButton(text=f"🚫 {name}", callback_data=f"admin:user:{user.id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:main"))
    await callback.message.edit_text(f"🚫 Заблокированные пользователи ({len(blocked_users)}):", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin:user:"))
async def show_user_card(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    status_str = "🔴 Заблокирован" if not user.is_active else "🟢 Активен"
    role_name = {
        UserRole.DRIVER: "🚗 Водитель",
        UserRole.DISPATCHER: "🎧 Диспетчер",
        UserRole.ADMIN: "👑 Администратор",
        UserRole.PENDING: "⏳ Ожидает"
    }.get(user.role, user.role.value)
    
    text = (
        f"👤 Карта пользователя: {user.name}\n"
        f"🔹 Telegram ID: {user.telegram_id}\n"
        f"🔹 Роль: {role_name}\n"
        f"🔹 Статус: {status_str}\n"
        f"📅 Регистрация: {user.created_at.strftime('%Y-%m-%d %H:%M')}"
    )
    
    builder = InlineKeyboardBuilder()
    
    if user.role == UserRole.PENDING:
        # Для ожидающих — выбор роли
        builder.row(
            InlineKeyboardButton(text="🚗 Водитель", callback_data=f"admin:set_role:{user_id}:{UserRole.DRIVER.value}"),
            InlineKeyboardButton(text="🎧 Диспетчер", callback_data=f"admin:set_role:{user_id}:{UserRole.DISPATCHER.value}")
        )
    elif user.role in (UserRole.DRIVER, UserRole.DISPATCHER):
        # Для активных — смена роли (водитель ↔ диспетчер)
        if user.role == UserRole.DRIVER:
            builder.row(InlineKeyboardButton(text="🔄 Сделать диспетчером", callback_data=f"admin:switch_role:{user_id}"))
        else:
            builder.row(InlineKeyboardButton(text="🔄 Сделать водителем", callback_data=f"admin:switch_role:{user_id}"))
    
    # Блокировка / Разблокировка
    if user.is_active:
        builder.row(InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin:toggle_block:{user_id}"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin:toggle_block:{user_id}"))
    
    # Кнопка удаления (для всех кроме админов)
    if user.role != UserRole.ADMIN:
        builder.row(InlineKeyboardButton(text="🗑 Удалить полностью", callback_data=f"admin:delete_user:{user_id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:users:all"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin:set_role:"))
async def set_user_role(callback: CallbackQuery, bot: Bot):
    _, _, user_id, role_val = callback.data.split(":")
    user_id = int(user_id)
    new_role = UserRole(role_val)
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
        if user:
            user.role = new_role
            user.is_active = True
            await uow.commit()
            
            # Уведомляем пользователя
            try:
                role_name = "Водитель" if new_role == UserRole.DRIVER else "Диспетчер"
                await bot.send_message(
                    user.telegram_id, 
                    f"🎉 Ваша заявка одобрена! Вам назначена роль: **{role_name}**.\n"
                    "Теперь вы можете пользоваться ботом."
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")

    await callback.answer(f"Роль {role_val} назначена")
    await show_pending_users(callback)

@router.callback_query(F.data.startswith("admin:toggle_block:"))
async def toggle_user_block(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
        if user:
            user.is_active = not user.is_active
            await uow.commit()
            action = "разблокирован" if user.is_active else "заблокирован"
            await callback.answer(f"Пользователь {action}")
    
    await show_user_card(callback)

@router.callback_query(F.data.startswith("admin:switch_role:"))
async def switch_user_role(callback: CallbackQuery, bot: Bot):
    """Переключить роль пользователя: водитель ↔ диспетчер."""
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Смена роли
        if user.role == UserRole.DRIVER:
            user.role = UserRole.DISPATCHER
            new_role_name = "Диспетчер"
        else:
            user.role = UserRole.DRIVER
            new_role_name = "Водитель"
        
        await uow.commit()
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user.telegram_id,
                f"ℹ️ Ваша роль изменена на: **{new_role_name}**."
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")
    
    await callback.answer(f"Роль изменена на {new_role_name}")
    await show_user_card(callback)

@router.callback_query(F.data.startswith("admin:delete_user:"))
async def delete_user_confirm(callback: CallbackQuery):
    """Показать подтверждение удаления пользователя."""
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚠️ Да, удалить!", callback_data=f"admin:confirm_delete:{user_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin:user:{user_id}")
    )
    
    await callback.message.edit_text(
        f"⚠️ **ВНИМАНИЕ!**\n\n"
        f"Вы собираетесь **полностью удалить** пользователя:\n"
        f"👤 {user.name}\n"
        f"🆔 Telegram ID: {user.telegram_id}\n\n"
        f"Это действие **необратимо**. Все данные пользователя будут удалены.",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("admin:confirm_delete:"))
async def confirm_delete_user(callback: CallbackQuery):
    """Выполнить жёсткое удаление пользователя."""
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        user_name = user.name
        deleted = await uow.drivers.delete(user_id)
        await uow.commit()
    
    if deleted:
        logger.info(f"User {user_id} ({user_name}) deleted by admin {callback.from_user.id}")
        await callback.answer(f"Пользователь {user_name} удалён")
        await callback.message.edit_text(
            f"✅ Пользователь **{user_name}** успешно удалён из системы.",
            reply_markup=get_admin_main_kb()
        )
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)

@router.callback_query(F.data == "admin:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Добро пожаловать в панель администратора!\nВыберите действие:",
        reply_markup=get_admin_main_kb()
    )

async def notify_admin_new_user(bot: Bot, user_data: dict):
    """Отправляет уведомление админу о новом пользователе."""
    admin_id = settings.ADMIN_TELEGRAM_ID

    text = (
        f"🔔 **Новая заявка на регистрацию!**\n\n"
        f"👤 Имя: {user_data.get('first_name')}\n"
        f"🆔 ID: {user_data.get('id')}\n"
        f"👤 Username: @{user_data.get('username')}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔎 Посмотреть", callback_data=f"admin:pending"))
    
    try:
        await bot.send_message(admin_id, text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
