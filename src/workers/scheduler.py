from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, date, time
from aiogram import Bot

from src.database.connection import async_session_factory
from src.database.uow import SQLAlchemyUnitOfWork
from src.services.notification_service import NotificationService
from src.core.logging import get_logger

logger = get_logger(__name__)

class TMSProjectScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """Запуск планировщика."""
        # Утреннее расписание в 07:00
        self.scheduler.add_job(
            self.morning_schedule_job,
            CronTrigger(hour=7, minute=0),
            id="morning_schedule"
        )
        
        # Напоминания каждые 5 минут
        self.scheduler.add_job(
            self.order_reminder_job,
            IntervalTrigger(minutes=5),
            id="order_reminders"
        )
        
        self.scheduler.start()
        logger.info("scheduler_started")

    async def morning_schedule_job(self):
        """Рассылка утреннего расписания всем активным водителям."""
        logger.info("running_morning_schedule_job")
        async with async_session_factory() as session:
            notification_service = NotificationService(self.bot, session)
            uow = SQLAlchemyUnitOfWork(async_session_factory)
            
            async with uow:
                drivers = await uow.drivers.get_all(is_active=True)
                for driver in drivers:
                    orders = await uow.orders.get_driver_orders_on_date(driver.id, date.today())
                    if orders:
                        await notification_service.notify_morning_schedule(driver.id, len(orders))

    async def order_reminder_job(self):
        """Рассылка напоминаний за 15 минут до начала заказа."""
        logger.info("running_order_reminder_job")
        now = datetime.utcnow()
        reminder_time = now + timedelta(minutes=15)
        
        async with async_session_factory() as session:
            notification_service = NotificationService(self.bot, session)
            uow = SQLAlchemyUnitOfWork(async_session_factory)
            
            async with uow:
                # Ищем заказы, которые начинаются в интервале [15, 20] минут от текущего времени
                start_limit = reminder_time
                end_limit = reminder_time + timedelta(minutes=5)
                
                # Используем get_orders_by_date_range
                orders = await uow.orders.get_orders_by_date_range(
                    start_date=start_limit,
                    end_date=end_limit,
                    status="assigned" # Только назначенные, еще не начатые
                )
                
                for order in orders:
                    if order.driver_id:
                        pickup = order.pickup_address or "Не указан"
                        text = (
                            f"<b>⏰ Напоминание!</b>\n\n"
                            f"Через 15 минут начинается заказ #{order.id}.\n"
                            f"📍 <b>Откуда:</b> {pickup}"
                        )
                        await notification_service.send_message(order.driver_id, text)
