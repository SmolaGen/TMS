from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import async_session_factory
from src.database.repository import SQLAlchemyRepository, DriverRepository, OrderRepository
from src.database.models import Driver, Order

class AbstractUnitOfWork(ABC):
    drivers: DriverRepository[Driver]
    orders: OrderRepository[Order]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rollback()

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError

class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=async_session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory()
        self.drivers = DriverRepository(self.session, Driver)
        self.orders = OrderRepository(self.session, Order)
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
