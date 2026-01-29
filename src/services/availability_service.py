from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import select, and_, func

from src.database.uow import AbstractUnitOfWork
from src.database.models import DriverAvailability
from src.schemas.availability import (
    DriverAvailabilityCreate,
    DriverAvailabilityUpdate,
    DriverAvailabilityResponse
)

class DriverAvailabilityService:
    """Сервис управления периодами недоступности водителей."""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def create_availability_period(
        self,
        data: DriverAvailabilityCreate
    ) -> DriverAvailabilityResponse:
        """
        Создать период недоступности водителя.

        Args:
            data: Данные для создания периода недоступности

        Returns:
            DriverAvailabilityResponse: Созданный период недоступности

        Raises:
            ValueError: Если период пересекается с существующими периодами
        """
        async with self.uow:
            # Проверка существования водителя
            driver = await self.uow.drivers.get(data.driver_id)
            if not driver:
                raise ValueError(f"Driver with id {data.driver_id} not found")

            # Проверка валидности временного интервала
            if data.time_end <= data.time_start:
                raise ValueError("time_end must be after time_start")

            # Создание периода недоступности
            time_range = (data.time_start, data.time_end)

            availability = DriverAvailability(
                driver_id=data.driver_id,
                availability_type=data.availability_type,
                time_range=time_range,
                description=data.description
            )

            self.uow.driver_availability.add(availability)

            try:
                await self.uow.commit()
            except Exception as e:
                # Exclusion constraint violation (overlapping periods)
                if "no_driver_availability_overlap" in str(e):
                    raise ValueError(
                        f"Availability period overlaps with existing period for driver {data.driver_id}"
                    )
                raise

            return DriverAvailabilityResponse.model_validate(availability)

    async def update_period(
        self,
        period_id: int,
        data: DriverAvailabilityUpdate
    ) -> Optional[DriverAvailabilityResponse]:
        """
        Обновить период недоступности.

        Args:
            period_id: ID периода недоступности
            data: Данные для обновления

        Returns:
            DriverAvailabilityResponse: Обновленный период или None, если не найден

        Raises:
            ValueError: Если обновление невалидно
        """
        async with self.uow:
            availability = await self.uow.driver_availability.get(period_id)
            if not availability:
                return None

            update_data = data.model_dump(exclude_unset=True)

            # Если обновляются временные границы, проверяем валидность
            time_start = update_data.get("time_start", availability.time_range[0])
            time_end = update_data.get("time_end", availability.time_range[1])

            if time_end <= time_start:
                raise ValueError("time_end must be after time_start")

            # Обновление полей
            for key, value in update_data.items():
                if key == "time_start" or key == "time_end":
                    # Обновляем time_range целиком
                    continue
                setattr(availability, key, value)

            # Обновление time_range, если изменились границы
            if "time_start" in update_data or "time_end" in update_data:
                availability.time_range = (time_start, time_end)

            try:
                await self.uow.commit()
            except Exception as e:
                # Exclusion constraint violation (overlapping periods)
                if "no_driver_availability_overlap" in str(e):
                    raise ValueError(
                        f"Updated period overlaps with existing period for driver {availability.driver_id}"
                    )
                raise

            return DriverAvailabilityResponse.model_validate(availability)

    async def delete_period(self, period_id: int) -> bool:
        """
        Удалить период недоступности.

        Args:
            period_id: ID периода недоступности

        Returns:
            bool: True, если период был удален, False если не найден
        """
        async with self.uow:
            result = await self.uow.driver_availability.delete(period_id)
            await self.uow.commit()
            return result

    async def get_driver_availability(
        self,
        driver_id: int,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[DriverAvailabilityResponse]:
        """
        Получить периоды недоступности водителя.

        Args:
            driver_id: ID водителя
            date_range: Опциональный временной интервал для фильтрации (start, end)

        Returns:
            List[DriverAvailabilityResponse]: Список периодов недоступности
        """
        async with self.uow:
            session = self.uow.session

            query = select(DriverAvailability).where(
                DriverAvailability.driver_id == driver_id
            )

            # Фильтрация по временному интервалу
            if date_range:
                start_date, end_date = date_range
                # Используем оператор && для проверки пересечения интервалов
                query = query.where(
                    DriverAvailability.time_range.overlaps((start_date, end_date))
                )

            # Сортировка по началу периода
            query = query.order_by(func.lower(DriverAvailability.time_range))

            result = await session.execute(query)
            availabilities = result.scalars().all()

            return [
                DriverAvailabilityResponse.model_validate(av)
                for av in availabilities
            ]

    async def check_driver_available(
        self,
        driver_id: int,
        check_date: datetime
    ) -> bool:
        """
        Проверить, доступен ли водитель в указанную дату/время.

        Args:
            driver_id: ID водителя
            check_date: Дата и время для проверки

        Returns:
            bool: True, если водитель доступен (нет пересечений с периодами недоступности)
        """
        async with self.uow:
            session = self.uow.session

            # Ищем периоды недоступности, которые содержат указанную дату
            query = select(func.count(DriverAvailability.id)).where(
                and_(
                    DriverAvailability.driver_id == driver_id,
                    DriverAvailability.time_range.contains(check_date)
                )
            )

            result = await session.execute(query)
            count = result.scalar()

            # Если есть хотя бы один период недоступности - водитель недоступен
            return count == 0

    async def get_availability_period(
        self,
        period_id: int
    ) -> Optional[DriverAvailabilityResponse]:
        """
        Получить период недоступности по ID.

        Args:
            period_id: ID периода недоступности

        Returns:
            DriverAvailabilityResponse: Период недоступности или None
        """
        async with self.uow:
            availability = await self.uow.driver_availability.get(period_id)
            if not availability:
                return None
            return DriverAvailabilityResponse.model_validate(availability)
