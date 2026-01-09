from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Sequence, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Base

T = TypeVar("T", bound=Base)

class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    def add(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    async def get(self, id: int) -> Optional[T]:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self, **kwargs) -> Sequence[T]:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_attribute(self, attr_name: str, value: any) -> Optional[T]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: int) -> bool:
        raise NotImplementedError

class SQLAlchemyRepository(AbstractRepository[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    async def get(self, id: int) -> Optional[T]:
        query = select(self.model).filter_by(id=id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, **kwargs) -> Sequence[T]:
        query = select(self.model).filter_by(**kwargs)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_attribute(self, attr_name: str, value: any) -> Optional[T]:
        query = select(self.model).filter(getattr(self.model, attr_name) == value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        query = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.rowcount > 0

class DriverRepository(SQLAlchemyRepository[T]):
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[T]:
        query = select(self.model).filter_by(telegram_id=telegram_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

class OrderRepository(SQLAlchemyRepository[T]):
    async def get_all(self, start_date=None, end_date=None) -> Sequence[T]:
        from sqlalchemy import func
        query = select(self.model)
        if start_date:
            # func.lower(Order.time_range) >= start_date
            query = query.where(func.lower(self.model.time_range) >= start_date)
        if end_date:
            # func.upper(Order.time_range) <= end_date
            query = query.where(func.upper(self.model.time_range) <= end_date)
        
        result = await self.session.execute(query)
        return result.scalars().all()
