"""
TMS Project Scheduler Worker

Воркер для управления фоновыми задачами проекта.

Особенности:
- Утренние уведомления водителям
- Напоминания за 15 минут до заказа
- Health check support for monitoring and Docker integration

Usage:
    scheduler = TMSProjectScheduler(bot)
    await scheduler.start()
"""

import time
import logging
from datetime import datetime, timedelta, date, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import settings
from src.database.uow import SQLAlchemyUnitOfWork
from src.database.connection import async_session_factory
from src.services.notification_service import NotificationService
from src.services.notification_preferences_service import NotificationPreferencesService
from src.database.models import OrderStatus, NotificationFrequency
from src.core.health_check import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SchedulerMetrics:
    """Метрики работы scheduler worker."""
    started_at: Optional[float] = None
    last_job_at: Optional[float] = None
    total_jobs_executed: int = 0
    total_morning_notifications: int = 0
    total_order_reminders: int = 0
    total_errors: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует метрики в словарь."""
        return {
            "started_at": self.started_at,
            "last_job_at": self.last_job_at,
            "total_jobs_executed": self.total_jobs_executed,
            "total_morning_notifications": self.total_morning_notifications,
            "total_order_reminders": self.total_order_reminders,
            "total_errors": self.total_errors,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "uptime_seconds": time.time() - self.started_at if self.started_at else 0,
        }


# ============================================================================
# Scheduler Worker
# ============================================================================

class TMSProjectScheduler:
    """
    Класс для управления фоновыми задачами проекта.

    Особенности:
    - Утренние уведомления водителям в 07:00
    - Напоминания за 15 минут до заказа каждые 5 минут
    - Health check support for monitoring
    """

    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._metrics = SchedulerMetrics()
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
            self._running = True
            self._metrics.started_at = time.time()
            logger.info("scheduler_started")

    async def shutdown(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("scheduler_shutdown")

    async def morning_notifications(self):
        """Отправить водителям расписание на день."""
        logger.info("running_morning_notifications")
        try:
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

            # Update metrics on success
            self._metrics.total_jobs_executed += 1
            self._metrics.total_morning_notifications += 1
            self._metrics.last_job_at = time.time()
        except Exception as e:
            self._metrics.total_errors += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_at = time.time()
            logger.exception("morning_notifications_error", error=str(e))

    async def order_reminders(self):
        """Напоминания за 15 мин до заказа."""
        logger.info("running_order_reminders")
        try:
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

            # Update metrics on success
            self._metrics.total_jobs_executed += 1
            self._metrics.total_order_reminders += 1
            self._metrics.last_job_at = time.time()
        except Exception as e:
            self._metrics.total_errors += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_at = time.time()
            logger.exception("order_reminders_error", error=str(e))

    # =========================================================================
    # Health Check Methods
    # =========================================================================

    async def get_health_status(self) -> HealthCheckResult:
        """
        Возвращает общий статус здоровья планировщика.

        Проверяет:
        - Статус планировщика (running/stopped)
        - Количество зарегистрированных задач
        - Время последней активности
        - Количество ошибок

        Returns:
            HealthCheckResult с общим статусом здоровья планировщика
        """
        start_time = time.time()

        # Check scheduler running status
        if not self._running or not self.scheduler.running:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="scheduler",
                status=HealthStatus.FAILED,
                message="Scheduler is not running",
                details={"metrics": self._metrics.to_dict()},
                response_time_ms=response_time,
            )

        # Get scheduled jobs info
        jobs = self.scheduler.get_jobs()
        jobs_info = [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]

        # Determine overall status
        overall_status = HealthStatus.OK
        message = "Scheduler is healthy"

        # Check for high error rate
        if self._metrics.total_errors > 0 and self._metrics.total_jobs_executed > 0:
            error_rate = self._metrics.total_errors / self._metrics.total_jobs_executed
            if error_rate > 0.5:  # More than 50% errors
                overall_status = HealthStatus.DEGRADED
                message = f"High error rate: {error_rate:.1%}"

        # Check for no jobs registered
        if not jobs:
            overall_status = HealthStatus.DEGRADED
            message = "No scheduled jobs registered"

        response_time = (time.time() - start_time) * 1000
        return HealthCheckResult(
            name="scheduler",
            status=overall_status,
            message=message,
            details={
                "jobs_count": len(jobs),
                "jobs": jobs_info,
                "metrics": self._metrics.to_dict(),
            },
            response_time_ms=response_time,
        )

    @property
    def metrics(self) -> SchedulerMetrics:
        """Возвращает текущие метрики планировщика."""
        return self._metrics

    @property
    def is_running(self) -> bool:
        """Возвращает статус работы планировщика."""
        return self._running


# ============================================================================
# Health Checker for External Use
# ============================================================================

class SchedulerHealthChecker(HealthChecker):
    """
    Health checker для scheduler worker, реализующий стандартный интерфейс.

    Позволяет интегрировать проверку здоровья планировщика в общую систему
    мониторинга через CompositeHealthChecker.

    Usage:
        scheduler = TMSProjectScheduler(bot)
        checker = SchedulerHealthChecker(scheduler)
        result = await checker.check()
    """

    def __init__(
        self,
        scheduler: TMSProjectScheduler,
        timeout: float = settings.HEALTH_CHECK_TIMEOUT,
    ):
        """
        Инициализация health checker для scheduler.

        Args:
            scheduler: Экземпляр TMSProjectScheduler для проверки
            timeout: Таймаут для проверки в секундах
        """
        super().__init__(name="scheduler", timeout=timeout)
        self.scheduler = scheduler

    async def check(self) -> HealthCheckResult:
        """
        Выполняет проверку здоровья scheduler.

        Returns:
            HealthCheckResult с результатом проверки
        """
        return await self.scheduler.get_health_status()
