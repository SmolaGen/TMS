from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.schemas.stats import DetailedStatsResponse
from src.services.stats_service import StatsService
from src.api.dependencies import get_stats_service
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/detailed", response_model=DetailedStatsResponse)
async def get_detailed_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    stats_service: StatsService = Depends(get_stats_service)
):
    """
    Получить детальную статистику за период.
    Если даты не указаны, возвращает статистику за сегодня.
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = date.today()

    # Конвертируем date в datetime (начало и конец дня)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    logger.info("get_detailed_stats_request", start_date=start_date, end_date=end_date)
    return await stats_service.get_detailed_stats(start_dt, end_dt)
