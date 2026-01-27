from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import date

from src.config import settings
from src.database.uow import SQLAlchemyUnitOfWork
from src.database.models import OrderStatus, DriverStatus
from src.services.order_workflow import OrderWorkflowService
from src.services.routing import RoutingService
from src.bot.keyboards.orders import get_orders_list_kb, get_order_actions_kb, get_shift_kb

router = Router(name="orders")

@router.message(Command("orders"))
async def cmd_orders(message: Message, driver_id: int) -> None:
    """Список заказов на сегодня."""
    async with SQLAlchemyUnitOfWork() as uow:
        orders = await uow.orders.get_driver_orders_on_date(driver_id, date.today())
    
    if not orders:
        await message.answer("📭 У вас нет заказов на сегодня.")
        return

    text = f"<b>📋 Ваши заказы на {date.today().strftime('%d.%m.%Y')}</b>\n\nВыберите заказ для просмотра деталей:"
    await message.answer(text, reply_markup=get_orders_list_kb(orders))

@router.callback_query(F.data == "orders_list")
async def cb_orders_list(callback: CallbackQuery, driver_id: int):
    """Возврат к списку заказов через callback."""
    async with SQLAlchemyUnitOfWork() as uow:
        orders = await uow.orders.get_driver_orders_on_date(driver_id, date.today())
    
    if not orders:
        await callback.message.edit_text("📭 У вас нет заказов на сегодня.")
        return

    text = f"<b>📋 Ваши заказы на {date.today().strftime('%d.%m.%Y')}</b>"
    await callback.message.edit_text(text, reply_markup=get_orders_list_kb(orders))

@router.callback_query(F.data.startswith("order_view:"))
async def cb_order_view(callback: CallbackQuery):
    """Просмотр деталей конкретного заказа."""
    order_id = int(callback.data.split(":")[1])
    
    async with SQLAlchemyUnitOfWork() as uow:
        order = await uow.orders.get(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    time_str = "Не указано"
    if order.time_range:
        time_str = f"{order.time_range.lower.strftime('%H:%M')} - {order.time_range.upper.strftime('%H:%M')}"

    text = (
        f"<b>📦 Заказ #{order.id}</b>\n\n"
        f"📍 <b>Откуда:</b> {order.pickup_address}\n"
        f"🏁 <b>Куда:</b> {order.dropoff_address}\n"
        f"⏰ <b>Время:</b> {time_str}\n"
        f"📊 <b>Статус:</b> {order.status.value}\n"
        f"⚠️ <b>Приоритет:</b> {order.priority.value}\n"
    )
    if order.comment:
        text += f"\n💬 <b>Комментарий:</b> {order.comment}"
    
    await callback.message.edit_text(text, reply_markup=get_order_actions_kb(order.id, order.status))

@router.callback_query(F.data.startswith("order_status:"))
async def cb_order_status(callback: CallbackQuery):
    """Смена статуса заказа."""
    _, order_id, action = callback.data.split(":")
    order_id = int(order_id)

    async with SQLAlchemyUnitOfWork() as uow:
        routing_service = RoutingService()
        workflow = OrderWorkflowService(uow, routing_service=routing_service)
        try:
            if action == "departed":
                await workflow.mark_departed(order_id)
            elif action == "arrived":
                await workflow.mark_arrived(order_id)
            elif action == "started":
                await workflow.start_trip(order_id)
            elif action == "completed":
                await workflow.complete_order(order_id)

            await callback.answer("Статус обновлен!")
            # Обновляем карточку заказа
            await cb_order_view(callback)

        except Exception as e:
            await callback.answer(f"Ошибка: {str(e)}", show_alert=True)

@router.message(Command("current"))
async def cmd_current(message: Message, driver_id: int):
    """Показать текущий активный заказ."""
    async with SQLAlchemyUnitOfWork() as uow:
        # Ищем заказ в статусе IN_PROGRESS или DRIVER_ARRIVED
        orders = await uow.orders.get_all(driver_id=driver_id)
        current = next((o for o in orders if o.status in [
            OrderStatus.EN_ROUTE_PICKUP,
            OrderStatus.DRIVER_ARRIVED, 
            OrderStatus.IN_PROGRESS
        ]), None)
        
        if not current:
            # Если нет активного, берем ближайший ASSIGNED
            current = next((o for o in sorted(orders, key=lambda x: x.time_range.lower if x.time_range else date.max) 
                           if o.status == OrderStatus.ASSIGNED), None)

    if not current:
        await message.answer("📭 У вас нет активных заказов.")
        return

    # Эмулируем нажатие на просмотр заказа
    callback = CallbackQuery(
        id="0", from_user=message.from_user, chat_instance="0", 
        message=message, data=f"order_view:{current.id}"
    )
    await cb_order_view(callback)

@router.message(Command("shift"))
async def cmd_shift(message: Message, driver: 'Driver'):
    """Управление сменой."""
    is_on_shift = driver.status != DriverStatus.OFFLINE
    status_text = "🟢 Вы на смене" if is_on_shift else "🔴 Вы вне смены"
    
    await message.answer(
        f"<b>💼 Управление сменой</b>\n\nТекущий статус: {status_text}",
        reply_markup=get_shift_kb(is_on_shift)
    )

@router.callback_query(F.data.startswith("shift:"))
async def cb_shift_toggle(callback: CallbackQuery, driver_id: int):
    """Переключение статуса смены."""
    action = callback.data.split(":")[1]
    new_status = DriverStatus.AVAILABLE if action == "on" else DriverStatus.OFFLINE
    
    async with SQLAlchemyUnitOfWork() as uow:
        driver = await uow.drivers.get(driver_id)
        if driver:
            driver.status = new_status
            await uow.commit()
    
    is_on_shift = new_status != DriverStatus.OFFLINE
    status_text = "🟢 Вы на смене" if is_on_shift else "🔴 Вы вне смены"
    
    await callback.message.edit_text(
        f"<b>💼 Управление сменой</b>\n\nТекущий статус: {status_text}",
        reply_markup=get_shift_kb(is_on_shift)
    )
    await callback.answer(f"Смена {'начата' if is_on_shift else 'завершена'}")

@router.message(Command("start"))
async def cmd_start(message: Message, driver_id: int) -> None:
    """Приветственное сообщение для авторизованного водителя."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "<b>👋 Добро пожаловать в TMS!</b>\n\n"
        "Вы авторизованы как водитель.\n\n"
        "<b>Доступные команды:</b>\n"
        "/orders - Список заказов\n"
        "/shift - Управление сменой\n"
        "/current - Текущий заказ\n\n"
        "Нажмите кнопку ниже для открытия приложения 👇",
        reply_markup=keyboard
    )
