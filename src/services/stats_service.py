from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_
from src.database.uow import AbstractUnitOfWork
from src.database.models import Order, OrderStatus, Driver, DriverStatus
from src.schemas.stats import (
    DetailedStatsResponse,
    Period,
    OrdersStats,
    DriversStats,
    RoutesStats,
    WaitTimeStats,
    HourlyStats,
    DailyStats,
    TopDriver,
    LongestRoute
)

class StatsService:
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def get_detailed_stats(self, start_date: datetime, end_date: datetime) -> DetailedStatsResponse:
        """Получить детальную статистику за период."""
        async with self.uow:
            session = self.uow.session

            # 1. Статистика заказов
            total_orders = await session.scalar(
                select(func.count(Order.id))
                .where(Order.created_at.between(start_date, end_date))
            ) or 0

            # По статусам
            status_counts = await session.execute(
                select(Order.status, func.count(Order.id))
                .where(Order.created_at.between(start_date, end_date))
                .group_by(Order.status)
            )
            by_status = {s.value: count for s, count in status_counts}

            # По приоритетам
            priority_counts = await session.execute(
                select(Order.priority, func.count(Order.id))
                .where(Order.created_at.between(start_date, end_date))
                .group_by(Order.priority)
            )
            by_priority = {p.value: count for p, count in priority_counts}

            # По часам
            hourly_data = await session.execute(
                select(
                    func.extract('hour', Order.created_at).label('hour'),
                    func.count(Order.id)
                )
                .where(Order.created_at.between(start_date, end_date))
                .group_by(func.extract('hour', Order.created_at), 'hour')
                .order_by('hour')
            )
            by_hour = [HourlyStats(hour=int(h), count=c) for h, c in hourly_data]

            # По дням
            daily_data = await session.execute(
                select(
                    func.to_char(Order.created_at, 'YYYY-MM-DD').label('date'),
                    func.count(Order.id),
                    func.sum(Order.price)
                )
                .where(Order.created_at.between(start_date, end_date))
                .group_by(func.to_char(Order.created_at, 'YYYY-MM-DD'), 'date')
                .order_by('date')
            )
            by_day = [DailyStats(date=d, count=c, revenue=float(r or 0)) for d, c, r in daily_data]

            total_revenue = await session.scalar(
                select(func.sum(Order.price))
                .where(Order.created_at.between(start_date, end_date))
                .where(Order.status == OrderStatus.COMPLETED)
            ) or 0

            avg_revenue = float(total_revenue) / total_orders if total_orders > 0 else 0

            orders_stats = OrdersStats(
                total=total_orders,
                byStatus=by_status,
                byPriority=by_priority,
                byHour=by_hour,
                byDay=by_day,
                averageRevenue=avg_revenue,
                totalRevenue=float(total_revenue)
            )

            # 2. Статистика водителей
            total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
            active_drivers = await session.scalar(
                select(func.count(Driver.id))
                .where(Driver.status != DriverStatus.OFFLINE)
            ) or 0

            top_drivers_data = await session.execute(
                select(
                    Driver.id,
                    Driver.name,
                    func.count(Order.id).label('completed_count'),
                    func.sum(Order.price).label('revenue')
                )
                .join(Order, Order.driver_id == Driver.id)
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at.between(start_date, end_date))
                .group_by(Driver.id, Driver.name)
                .order_by(func.count(Order.id).desc())
                .limit(5)
            )
            top_drivers = [
                TopDriver(
                    driver_id=row[0],
                    name=row[1],
                    completed_orders=row[2],
                    total_revenue=float(row[3] or 0)
                ) for row in top_drivers_data
            ]

            drivers_stats = DriversStats(
                total=total_drivers,
                active=active_drivers,
                topDrivers=top_drivers
            )

            # 3. Статистика маршрутов
            total_distance = await session.scalar(
                select(func.sum(Order.distance_meters))
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at.between(start_date, end_date))
            ) or 0

            completed_count = by_status.get(OrderStatus.COMPLETED.value, 0)
            avg_distance = float(total_distance) / completed_count if completed_count > 0 else 0

            longest_order = await session.execute(
                select(Order.id, Order.distance_meters)
                .where(Order.status == OrderStatus.COMPLETED)
                .where(Order.created_at.between(start_date, end_date))
                .order_by(Order.distance_meters.desc())
                .limit(1)
            )
            longest_row = longest_order.first()
            longest_route = LongestRoute(
                order_id=longest_row[0],
                distance=float(longest_row[1] or 0)
            ) if longest_row else LongestRoute(order_id=0, distance=0)

            routes_stats = RoutesStats(
                totalDistance=float(total_distance),
                averageDistance=avg_distance,
                longestRoute=longest_route
            )

            # 4. Время ожидания (Wait Times)
            # averageWaitTime: created_at -> assigned_at
            avg_wait = await session.scalar(
                select(func.avg(
                    func.extract('epoch', Order.assigned_at - Order.created_at)
                ))
                .where(Order.assigned_at.isnot(None))
                .where(Order.created_at.between(start_date, end_date))
            ) or 0

            # averagePickupTime: assigned_at -> arrived_at
            avg_pickup = await session.scalar(
                select(func.avg(
                    func.extract('epoch', Order.arrived_at - Order.assigned_at)
                ))
                .where(Order.assigned_at.isnot(None))
                .where(Order.arrived_at.isnot(None))
                .where(Order.created_at.between(start_date, end_date))
            ) or 0

            # averageDeliveryTime: started_at -> end_time
            avg_delivery = await session.scalar(
                select(func.avg(
                    func.extract('epoch', Order.end_time - Order.started_at)
                ))
                .where(Order.started_at.isnot(None))
                .where(Order.end_time.isnot(None))
                .where(Order.created_at.between(start_date, end_date))
            ) or 0

            wait_times = WaitTimeStats(
                averageWaitTime=float(avg_wait),
                averagePickupTime=float(avg_pickup),
                averageDeliveryTime=float(avg_delivery)
            )

            return DetailedStatsResponse(
                period=Period(start=start_date.isoformat(), end=end_date.isoformat()),
                orders=orders_stats,
                drivers=drivers_stats,
                routes=routes_stats,
                waitTimes=wait_times
            )
