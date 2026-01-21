"""Схемы для детализированной статистики."""
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class TopDriver(BaseModel):
    """Топ-водитель по эффективности."""
    driver_id: int
    name: str
    completed_orders: int
    total_revenue: float
    average_rating: Optional[float] = None


class HourlyStats(BaseModel):
    """Статистика по часам."""
    hour: int
    count: int


class DailyStats(BaseModel):
    """Статистика по дням."""
    date: str
    count: int
    revenue: float


class OrdersStats(BaseModel):
    """Статистика заказов."""
    total: int
    byStatus: Dict[str, int]
    byPriority: Dict[str, int]
    byHour: List[HourlyStats]
    byDay: List[DailyStats]
    averageRevenue: float
    totalRevenue: float


class DriversStats(BaseModel):
    """Статистика водителей."""
    total: int
    active: int
    topDrivers: List[TopDriver]


class LongestRoute(BaseModel):
    """Самый длинный маршрут."""
    distance: float
    order_id: int


class RoutesStats(BaseModel):
    """Статистика маршрутов."""
    totalDistance: float
    averageDistance: float
    longestRoute: LongestRoute


class WaitTimeStats(BaseModel):
    """Статистика времени ожидания."""
    averageWaitTime: float
    averagePickupTime: float
    averageDeliveryTime: float


class Period(BaseModel):
    """Период статистики."""
    start: str
    end: str


class DetailedStatsResponse(BaseModel):
    """Ответ с детализированной статистикой."""
    period: Period
    orders: OrdersStats
    drivers: DriversStats
    routes: RoutesStats
    waitTimes: WaitTimeStats
