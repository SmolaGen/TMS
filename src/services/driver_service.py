from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, func
from src.database.uow import AbstractUnitOfWork
from src.database.models import Driver, Order, OrderStatus
from src.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from src.database.models import DriverStatus

class DriverService:
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def register_driver(self, data: DriverCreate) -> DriverResponse:
        async with self.uow:
            # Проверка уникальности telegram_id
            existing = await self.uow.drivers.get_by_attribute("telegram_id", data.telegram_id)
            if existing:
                raise ValueError(f"Driver with telegram_id {data.telegram_id} already exists")

            driver = Driver(
                telegram_id=data.telegram_id,
                name=data.name,
                phone=data.phone,
                status=DriverStatus.OFFLINE,
                is_active=data.is_active
            )
            self.uow.drivers.add(driver)
            await self.uow.commit()
            return DriverResponse.model_validate(driver)

    async def get_driver(self, driver_id: int) -> Optional[DriverResponse]:
        async with self.uow:
            driver = await self.uow.drivers.get(driver_id)
            return DriverResponse.model_validate(driver) if driver else None

    async def get_all_drivers(self) -> List[DriverResponse]:
        async with self.uow:
            drivers = await self.uow.drivers.get_all()
            return [DriverResponse.model_validate(d) for d in drivers]

    async def update_driver(self, driver_id: int, data: DriverUpdate) -> Optional[DriverResponse]:
        async with self.uow:
            driver = await self.uow.drivers.get(driver_id)
            if not driver:
                return None
            
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(driver, key, value)
            
            await self.uow.commit()
            return DriverResponse.model_validate(driver)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Driver]:
        """Получить водителя по Telegram ID."""
        async with self.uow:
            driver = await self.uow.drivers.get_by_attribute("telegram_id", telegram_id)
            return driver

    async def create_driver_from_telegram(self, telegram_id: int, name: str, username: str = None) -> Driver:
        """Создать нового водителя из данных Telegram."""
        async with self.uow:
            driver = Driver(
                telegram_id=telegram_id,
                name=name,
                phone=username or "",
                status=DriverStatus.OFFLINE,
                is_active=True
            )
            self.uow.drivers.add(driver)
            await self.uow.commit()
            return driver

    async def get_driver_stats(self, driver_id: int, days: int = 30) -> Optional[dict]:
        """Получить статистику водителя за период."""
        async with self.uow:
            driver = await self.uow.drivers.get(driver_id)
            if not driver:
                return None
            
            # Период для статистики
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Подсчёт заказов через session
            session = self.uow._session
            
            # Всего заказов
            total_orders = await session.scalar(
                select(func.count(Order.id))
                .where(Order.driver_id == driver_id)
                .where(Order.created_at >= start_date)
            )
            
            # Завершённых
            completed_orders = await session.scalar(
                select(func.count(Order.id))
                .where(Order.driver_id == driver_id)
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at >= start_date)
            )
            
            # Отменённых
            cancelled_orders = await session.scalar(
                select(func.count(Order.id))
                .where(Order.driver_id == driver_id)
                .where(Order.status == OrderStatus.CANCELLED)
                .where(Order.created_at >= start_date)
            )
            
            # Активных сейчас
            active_orders = await session.scalar(
                select(func.count(Order.id))
                .where(Order.driver_id == driver_id)
                .where(Order.status.in_([
                    OrderStatus.ASSIGNED, 
                    OrderStatus.DRIVER_ARRIVED, 
                    OrderStatus.IN_PROGRESS
                ]))
            )
            
            # Сумма заработка
            total_revenue = await session.scalar(
                select(func.sum(Order.price))
                .where(Order.driver_id == driver_id)
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at >= start_date)
            ) or 0
            
            # Общая дистанция
            total_distance = await session.scalar(
                select(func.sum(Order.distance_meters))
                .where(Order.driver_id == driver_id)
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at >= start_date)
            ) or 0
            
            return {
                "driver_id": driver_id,
                "period_days": days,
                "total_orders": total_orders or 0,
                "completed_orders": completed_orders or 0,
                "cancelled_orders": cancelled_orders or 0,
                "active_orders": active_orders or 0,
                "completion_rate": round(completed_orders / total_orders * 100, 1) if total_orders else 0,
                "total_revenue": float(total_revenue),
                "total_distance_km": round(total_distance / 1000, 1),
            }
