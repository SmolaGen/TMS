from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.schemas.availability import (
    DriverAvailabilityCreate,
    DriverAvailabilityUpdate,
    DriverAvailabilityResponse
)
from src.services.availability_service import DriverAvailabilityService
from src.api.dependencies import get_availability_service

router = APIRouter()


@router.get("/drivers/{driver_id}/availability", response_model=List[DriverAvailabilityResponse])
async def get_driver_availability(
    driver_id: int,
    date_from: Optional[datetime] = Query(None, description="Начало временного диапазона"),
    date_until: Optional[datetime] = Query(None, description="Конец временного диапазона"),
    availability_service: DriverAvailabilityService = Depends(get_availability_service)
):
    """
    Получить список периодов недоступности водителя.

    Можно фильтровать по временному диапазону с помощью параметров date_from и date_until.
    """
    date_range = None
    if date_from and date_until:
        if date_until <= date_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_until должен быть позже date_from"
            )
        date_range = (date_from, date_until)
    elif date_from or date_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать оба параметра: date_from и date_until"
        )

    try:
        availabilities = await availability_service.get_driver_availability(
            driver_id=driver_id,
            date_range=date_range
        )
        return availabilities
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@router.post("/drivers/{driver_id}/availability", response_model=DriverAvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_availability(
    driver_id: int,
    data: DriverAvailabilityCreate,
    availability_service: DriverAvailabilityService = Depends(get_availability_service)
):
    """
    Создать новый период недоступности для водителя.

    Периоды недоступности не должны пересекаться для одного водителя.
    """
    # Проверяем, что driver_id в URL совпадает с driver_id в теле запроса
    if data.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="driver_id в URL и в теле запроса должны совпадать"
        )

    try:
        availability = await availability_service.create_availability_period(data)
        return availability
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании периода недоступности: {str(e)}"
        )


@router.patch("/availability/{availability_id}", response_model=DriverAvailabilityResponse)
async def update_availability(
    availability_id: int,
    data: DriverAvailabilityUpdate,
    availability_service: DriverAvailabilityService = Depends(get_availability_service)
):
    """
    Обновить период недоступности водителя.

    Можно обновить тип, временные границы и описание периода.
    """
    try:
        updated_availability = await availability_service.update_period(
            period_id=availability_id,
            data=data
        )

        if not updated_availability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Период недоступности с id {availability_id} не найден"
            )

        return updated_availability
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении периода недоступности: {str(e)}"
        )


@router.delete("/availability/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_availability(
    availability_id: int,
    availability_service: DriverAvailabilityService = Depends(get_availability_service)
):
    """
    Удалить период недоступности водителя.
    """
    try:
        deleted = await availability_service.delete_period(availability_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Период недоступности с id {availability_id} не найден"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении периода недоступности: {str(e)}"
        )
