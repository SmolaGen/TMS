from typing import List, Optional
from src.database.uow import AbstractUnitOfWork
from src.database.models import Driver
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
