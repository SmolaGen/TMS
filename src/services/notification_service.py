"""
Сервис для отправки уведомлений водителям через Telegram.
"""

from typing import Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import Driver, Order
from src.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений."""

    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session

    async def _get_driver_telegram_id(self, driver_id: int) -> Optional[int]:
        """Получить telegram_id по внутреннему id водителя."""
        query = select(Driver.telegram_id).where(Driver.id == driver_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def send_message(self, driver_id: int, text: str, reply_markup=None) -> bool:
        """Универсальный метод отправки сообщения."""
        if not self.bot:
            logger.warning("bot_not_initialized", driver_id=driver_id)
            return False

        telegram_id = await self._get_driver_telegram_id(driver_id)
        if not telegram_id:
            logger.warning("driver_telegram_id_not_found", driver_id=driver_id)
            return False

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            logger.error("failed_to_send_notification", driver_id=driver_id, error=str(e))
            return False

    async def notify_order_assigned(self, driver_id: int, order: Order) -> bool:
        """Уведомить о новом назначенном заказе."""
        pickup = order.pickup_address or "Не указан"
        dropoff = order.dropoff_address or "Не указан"
        time_str = "Не указано"
        if order.time_range and order.time_range.lower and order.time_range.upper:
            time_str = f"{order.time_range.lower.strftime('%H:%M')} - {order.time_range.upper.strftime('%H:%M')}"

        text = (
            f"<b>🚗 Новый заказ #{order.id}</b>\n\n"
            f"📍 <b>Откуда:</b> {pickup}\n"
            f"🏁 <b>Куда:</b> {dropoff}\n"
            f"⏰ <b>Время:</b> {time_str}\n"
            f"⚠️ <b>Приоритет:</b> {order.priority.value if order.priority else 'Обычный'}\n\n"
            f"Посмотрите детали в меню /orders"
        )
        return await self.send_message(driver_id, text)

    async def notify_order_cancelled(self, driver_id: int, order_id: int) -> bool:
        """Уведомить об отмене заказа."""
        text = f"<b>❌ Заказ #{order_id} отменён</b>"
        return await self.send_message(driver_id, text)

    async def notify_morning_schedule(self, driver_id: int, orders_count: int) -> bool:
        """Утреннее приветствие с расписанием."""
        text = (
            f"<b>☀️ Доброе утро!</b>\n\n"
            f"У вас <b>{orders_count}</b> заказов на сегодня.\n"
            f"Нажмите /orders чтобы посмотреть расписание."
        )
        return await self.send_message(driver_id, text)

    async def notify_order_reminder(self, driver_id: int, order: Order) -> bool:
        """Напоминание за 15 минут до начала заказа."""
        pickup = order.pickup_address or "Не указан"
        time_str = ""
        if order.time_range and order.time_range.lower:
            time_str = f" в {order.time_range.lower.strftime('%H:%M')}"
            
        text = (
            f"<b>⏰ Напоминание!</b>\n\n"
            f"Заказ <b>#{order.id}</b> начинается{time_str}.\n"
            f"📍 <b>Подача:</b> {pickup}\n\n"
            f"Пора выезжать! 🚗"
        )
        return await self.send_message(driver_id, text)

    async def notify_customer(self, telegram_id: int, text: str, reply_markup=None) -> bool:
        """Метод для отправки сообщения клиенту."""
        if not self.bot:
            logger.warning("bot_not_initialized", customer_telegram_id=telegram_id)
            return False

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            logger.error("failed_to_send_customer_notification",
                         customer_telegram_id=telegram_id,
                         error=str(e))
            return False

    async def notify_customer_status_change(self, order: Order) -> bool:
        """Уведомить клиента об изменении статуса заказа."""
        if not order.customer_telegram_id:
            return False

        status_messages = {
            "assigned": f"🚗 Для вашего заказа #{order.id} назначен водитель {order.driver_name}.",
            "en_route_pickup": f"🚚 Водитель выехал к вам для забора груза по заказу #{order.id}.",
            "driver_arrived": f"📍 Водитель прибыл на место забора груза по заказу #{order.id}.",
            "in_progress": f"📦 Ваш заказ #{order.id} принят к перевозке и находится в пути.",
            "completed": f"✅ Ваш заказ #{order.id} успешно доставлен. Спасибо, что выбрали нас!",
            "cancelled": f"❌ Ваш заказ #{order.id} был отменен. Причина: {order.cancellation_reason or 'не указана'}.",
        }

        text = status_messages.get(order.status)
        if not text:
            return False

        return await self.notify_customer(order.customer_telegram_id, text)

    async def notify_route_updated(self, driver_id: int, order: Order) -> bool:
        """Уведомить водителя об обновлении маршрута заказа."""
        pickup = order.pickup_address or "Не указан"
        dropoff = order.dropoff_address or "Не указан"
        time_str = "Не указано"
        if order.time_range and order.time_range.lower and order.time_range.upper:
            time_str = f"{order.time_range.lower.strftime('%H:%M')} - {order.time_range.upper.strftime('%H:%M')}"

        text = (
            f"<b>🔄 Маршрут обновлён</b>\n\n"
            f"Заказ <b>#{order.id}</b>\n"
            f"📍 <b>Откуда:</b> {pickup}\n"
            f"🏁 <b>Куда:</b> {dropoff}\n"
            f"⏰ <b>Время:</b> {time_str}\n\n"
            f"Проверьте детали в меню /orders"
        )
        return await self.send_message(driver_id, text)

    async def notify_approaching(self, order: Order, eta_minutes: int) -> bool:
        """Уведомить клиента о приближении водителя."""
        if not order.customer_telegram_id:
            return False

        text = f"⏳ Водитель будет у вас через {eta_minutes} мин. (Заказ #{order.id})"
        return await self.notify_customer(order.customer_telegram_id, text)
