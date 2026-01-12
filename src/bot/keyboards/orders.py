from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.database.models import OrderStatus, OrderPriority

def get_orders_list_kb(orders) -> InlineKeyboardMarkup:
    """Клавиатура со списком заказов."""
    builder = InlineKeyboardBuilder()
    for order in orders:
        # Текст кнопки: #ID Время Статус
        time_str = ""
        if order.time_range:
            time_str = order.time_range.lower.strftime("%H:%M")
        
        status_emoji = "⏳"
        if order.status == OrderStatus.ASSIGNED: status_emoji = "🚗"
        elif order.status == OrderStatus.EN_ROUTE_PICKUP: status_emoji = "🚚"
        elif order.status == OrderStatus.IN_PROGRESS: status_emoji = "▶️"
        elif order.status == OrderStatus.COMPLETED: status_emoji = "✅"
        
        btn_text = f"#{order.id} {time_str} {status_emoji}"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"order_view:{order.id}"))
    
    return builder.as_markup()

def get_order_actions_kb(order_id: int, status: OrderStatus) -> InlineKeyboardMarkup:
    """Кнопки действий для конкретного заказа."""
    builder = InlineKeyboardBuilder()
    
    if status == OrderStatus.ASSIGNED:
        builder.row(InlineKeyboardButton(text="🚗 Выехал", callback_data=f"order_status:{order_id}:departed"))
    elif status == OrderStatus.EN_ROUTE_PICKUP:
        builder.row(InlineKeyboardButton(text="📍 Прибыл", callback_data=f"order_status:{order_id}:arrived"))
    elif status == OrderStatus.DRIVER_ARRIVED:
        builder.row(InlineKeyboardButton(text="▶️ Поехали", callback_data=f"order_status:{order_id}:started"))
    elif status == OrderStatus.IN_PROGRESS:
        builder.row(InlineKeyboardButton(text="✅ Завершён", callback_data=f"order_status:{order_id}:completed"))
    
    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data="orders_list"))
    
    return builder.as_markup()

def get_shift_kb(is_on_shift: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления сменой."""
    builder = InlineKeyboardBuilder()
    if is_on_shift:
        builder.row(InlineKeyboardButton(text="🛑 Завершить смену", callback_data="shift:off"))
    else:
        builder.row(InlineKeyboardButton(text="🚀 Начать смену", callback_data="shift:on"))
    return builder.as_markup()
