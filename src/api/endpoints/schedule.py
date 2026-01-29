from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException

from src.schemas.schedule import (
    ScheduleViewResponse,
    DriverScheduleResponse,
    CreateScheduledOrderRequest
)
from src.schemas.order import OrderResponse
from src.services.schedule_service import ScheduleService
from src.api.dependencies import get_schedule_service
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("", response_model=ScheduleViewResponse)
async def get_schedule(
    date_from: date = Query(..., description="Начало периода"),
    date_until: date = Query(..., description="Конец периода"),
    driver_ids: Optional[List[int]] = Query(None, description="Фильтр по водителям"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Получить календарное представление расписания за период.
    Возвращает заказы и доступность водителей по дням.
    """
    # Конвертируем date в datetime (начало и конец дня)
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_until, datetime.max.time())

    logger.info("get_schedule_request", date_from=date_from, date_until=date_until, driver_ids=driver_ids)
    return await schedule_service.get_schedule_view(start_dt, end_dt, driver_ids)


@router.get("/drivers/{driver_id}", response_model=DriverScheduleResponse)
async def get_driver_schedule(
    driver_id: int,
    date_from: date = Query(..., description="Начало периода"),
    date_until: date = Query(..., description="Конец периода"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Получить расписание конкретного водителя за период.
    Возвращает заказы водителя и периоды его недоступности.
    """
    # Конвертируем date в datetime (начало и конец дня)
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_until, datetime.max.time())

    logger.info("get_driver_schedule_request", driver_id=driver_id, date_from=date_from, date_until=date_until)

    result = await schedule_service.get_driver_schedule(driver_id, start_dt, end_dt)
    if not result:
        raise HTTPException(status_code=404, detail=f"Driver with id {driver_id} not found")

    return result


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_scheduled_order(
    data: CreateScheduledOrderRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    Создать запланированный заказ с будущей датой доставки.
    Проверяет доступность водителя, если он указан.
    """
    logger.info("create_scheduled_order_request", scheduled_date=data.scheduled_date, driver_id=data.driver_id)

    try:
        return await schedule_service.create_scheduled_order(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
