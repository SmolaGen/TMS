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

def is_admin(username: str) -> bool:
    return username == settings.ADMIN_USERNAME

def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏳ Ожидающие одобрения", callback_query_data="admin:pending"))
    builder.row(InlineKeyboardButton(text="👥 Все пользователи", callback_query_data="admin:users:all"))
    builder.row(InlineKeyboardButton(text="🚫 Заблокированные", callback_query_data="admin:users:blocked"))
    return builder.as_markup()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not message.from_user or not is_admin(message.from_user.username):
        return
    
    await message.answer(
        "👋 Добро пожаловать в панель администратора!\nВыберите действие:",
        reply_markup=get_admin_main_kb()
    )

@router.callback_query(F.data == "admin:pending")
async def show_pending_users(callback: CallbackQuery):
    if not callback.from_user or not is_admin(callback.from_user.username):
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
        builder.row(InlineKeyboardButton(text=f"👤 {name}", callback_query_data=f"admin:user:{user.id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_query_data="admin:main"))
    await callback.message.edit_text("Пользователи, ожидающие одобрения:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin:user:"))
async def show_user_card(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[-1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        user = await uow.drivers.get(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    status_str = "🔴 Заблокирован" if not user.is_active else "🟢 Активен"
    text = (
        f"👤 Карта пользователя: {user.name}\n"
        f"🔹 Telegram ID: {user.telegram_id}\n"
        f"🔹 Роль: {user.role.value}\n"
        f"🔹 Статус: {status_str}\n"
        f"📅 Регистрация: {user.created_at.strftime('%Y-%m-%d %H:%M')}"
    )
    
    builder = InlineKeyboardBuilder()
    if user.role == UserRole.PENDING:
        builder.row(
            InlineKeyboardButton(text="🚗 Водитель", callback_query_data=f"admin:set_role:{user_id}:{UserRole.DRIVER.value}"),
            InlineKeyboardButton(text="🎧 Диспетчер", callback_query_data=f"admin:set_role:{user_id}:{UserRole.DISPATCHER.value}")
        )
    
    if user.is_active:
        builder.row(InlineKeyboardButton(text="🚫 Заблокировать", callback_query_data=f"admin:toggle_block:{user_id}"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Разблокировать", callback_query_data=f"admin:toggle_block:{user_id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_query_data="admin:pending"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin:set_role:"))
async def set_user_role(callback: CallbackQuery, bot: Bot):
    _, _, _, user_id, role_val = callback.data.split(":")
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

@router.callback_query(F.data == "admin:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Добро пожаловать в панель администратора!\nВыберите действие:",
        reply_markup=get_admin_main_kb()
    )

async def notify_admin_new_user(bot: Bot, user_data: dict):
    """Отправляет уведомление админу о новом пользователе."""
    admin_id = None
    # Нам нужно найти telegram_id админа. 
    # В идеале он должен быть в конфиге как ID, а не только username.
    # Но пока попробуем найти его в БД или использовать username если бот может начать диалог (нет, не может).
    # Предположим, админ уже взаимодействовал с ботом и мы можем найти его по username в БД.
    
    async with SQLAlchemyUnitOfWork() as uow:
        admin = await uow.drivers.get_by_attribute("name", settings.ADMIN_USERNAME) # Временно ищем по имени
        if not admin:
             # Если не нашли, логгируем. В продакшене лучше иметь ADMIN_ID в .env
             logger.warning("Admin not found in DB to send notification")
             return
        admin_id = admin.telegram_id

    text = (
        f"🔔 **Новая заявка на регистрацию!**\n\n"
        f"👤 Имя: {user_data.get('first_name')}\n"
        f"🆔 ID: {user_data.get('id')}\n"
        f"👤 Username: @{user_data.get('username')}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔎 Посмотреть", callback_query_data=f"admin:pending"))
    
    try:
        await bot.send_message(admin_id, text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
