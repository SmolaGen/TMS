
import logging
from datetime import datetime, timedelta, date, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.database.uow import SQLAlchemyUnitOfWork
from src.database.connection import async_session_factory
from src.services.notification_service import NotificationService
from src.services.notification_preferences_service import NotificationPreferencesService
from src.database.models import OrderStatus, NotificationFrequency

logger = logging.getLogger(__name__)

class TMSProjectScheduler:
    """Класс для управления фоновыми задачами проекта."""
    
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._setup()

    def _setup(self):
        """Настройка задач."""
        # 1. Утренние уведомления в 07:00
        self.scheduler.add_job(
            self.morning_notifications, 
            CronTrigger(hour=7, minute=0),
            id="morning_notifications",
            replace_existing=True
        )
        
        # 2. Напоминания каждые 5 минут
        self.scheduler.add_job(
            self.order_reminders,
            "interval",
            minutes=5,
            id="order_reminders",
            replace_existing=True
        )

    async def start(self):
        """Запуск планировщика."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("scheduler_started")

    async def shutdown(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("scheduler_shutdown")

    async def morning_notifications(self):
        """Отправить водителям расписание на день."""
        logger.info("running_morning_notifications")
        async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
            # Получаем всех активных водителей
            drivers = await uow.drivers.get_all(is_active=True)
            preferences_service = NotificationPreferencesService(uow.session)
            notification_service = NotificationService(self.bot, uow.session, preferences_service)

            for driver in drivers:
                if not driver.telegram_id:
                    continue

                orders = await uow.orders.get_driver_orders_on_date(driver.id, date.today())
                if orders:
                    await notification_service.notify_morning_schedule(driver.id, len(orders))

    async def order_reminders(self):
        """Напоминания за 15 мин до заказа."""
        logger.info("running_order_reminders")
        async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
            now = datetime.now(timezone.utc)
            soon = now + timedelta(minutes=15)

            preferences_service = NotificationPreferencesService(uow.session)
            notification_service = NotificationService(self.bot, uow.session, preferences_service)

            from sqlalchemy import select, and_
            from src.database.models import NotificationType, NotificationChannel

            query = select(uow.orders.model).where(
                and_(
                    uow.orders.model.status == OrderStatus.ASSIGNED,
                    uow.orders.model.driver_id.isnot(None)
                )
            )
            result = await uow.session.execute(query)
            orders = result.scalars().all()

            for order in orders:
                if not order.time_range:
                    continue

                # SQLAlchemy-utils TSTZRANGE lower/upper boundaries
                start_time = order.time_range.lower
                if now <= start_time <= soon:
                    # Проверяем частоту уведомлений для водителя
                    # Напоминания за 15 мин отправляются только при INSTANT частоте
                    preference = await preferences_service.get_preference_by_type_and_channel(
                        driver_id=order.driver_id,
                        notification_type=NotificationType.NEW_ORDER,
                        channel=NotificationChannel.TELEGRAM
                    )

                    # Если настройки нет или она отключена - пропускаем
                    if not preference or not preference.is_enabled:
                        logger.debug(
                            "reminder_skipped_no_preference",
                            driver_id=order.driver_id,
                            order_id=order.id
                        )
                        continue

                    # Отправляем только для мгновенных уведомлений
                    # Для HOURLY и DAILY будут отдельные задачи
                    if preference.frequency == NotificationFrequency.INSTANT:
                        await notification_service.notify_order_reminder(order.driver_id, order)
                    else:
                        logger.debug(
                            "reminder_skipped_frequency",
                            driver_id=order.driver_id,
                            order_id=order.id,
                            frequency=preference.frequency.value
                        )
