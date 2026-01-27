"""
Route History Service для записи истории изменений маршрутов.

Используется для аудита и отслеживания всех изменений
в маршрутах и их точках.
"""

import json
from typing import Optional, Any, Dict, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import Route, RouteChangeHistory, RouteChangeType, Driver
from src.core.logging import get_logger

logger = get_logger(__name__)


class RouteHistoryService:
    """
    Сервис для записи истории изменений маршрутов.

    Обеспечивает аудит всех изменений маршрутов:
    - создание, изменение статуса, оптимизация
    - добавление/удаление/перестановка точек
    - отмена/завершение маршрута
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис с сессией БД.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self.session = session

    async def record_change(
        self,
        route_id: int,
        change_type: RouteChangeType,
        changed_by_id: Optional[int] = None,
        changed_field: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RouteChangeHistory:
        """
        Записать изменение маршрута в историю.

        Args:
            route_id: ID маршрута
            change_type: Тип изменения (enum RouteChangeType)
            changed_by_id: ID пользователя, внесшего изменение
            changed_field: Название изменённого поля
            old_value: Значение до изменения (будет сериализовано в JSON)
            new_value: Значение после изменения (будет сериализовано в JSON)
            description: Текстовое описание изменения
            metadata: Дополнительные метаданные (будут сериализованы в JSON)

        Returns:
            Созданная запись RouteChangeHistory

        Raises:
            ValueError: Если маршрут не найден
        """
        # Проверяем существование маршрута
        route = await self.session.get(Route, route_id)
        if not route:
            logger.error(f"Маршрут с id={route_id} не найден при попытке записи истории")
            raise ValueError(f"Route with id={route_id} not found")

        # Сериализуем значения в JSON
        old_value_json = json.dumps(old_value, ensure_ascii=False) if old_value is not None else None
        new_value_json = json.dumps(new_value, ensure_ascii=False) if new_value is not None else None
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        # Создаём запись истории
        change_record = RouteChangeHistory(
            route_id=route_id,
            change_type=change_type,
            changed_by_id=changed_by_id,
            changed_field=changed_field,
            old_value=old_value_json,
            new_value=new_value_json,
            description=description,
            change_metadata=metadata_json
        )

        self.session.add(change_record)
        await self.session.flush()

        logger.info(
            f"Записано изменение маршрута {route_id}: {change_type.value} "
            f"(пользователь={changed_by_id}, поле={changed_field})"
        )

        return change_record

    async def record_route_created(
        self,
        route_id: int,
        changed_by_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RouteChangeHistory:
        """
        Записать создание нового маршрута.

        Args:
            route_id: ID созданного маршрута
            changed_by_id: ID пользователя, создавшего маршрут
            metadata: Дополнительные метаданные (driver_id, optimization_type и т.д.)

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.CREATED,
            changed_by_id=changed_by_id,
            description="Маршрут создан",
            metadata=metadata
        )

    async def record_status_changed(
        self,
        route_id: int,
        old_status: str,
        new_status: str,
        changed_by_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RouteChangeHistory:
        """
        Записать изменение статуса маршрута.

        Args:
            route_id: ID маршрута
            old_status: Старый статус
            new_status: Новый статус
            changed_by_id: ID пользователя, изменившего статус
            metadata: Дополнительные метаданные

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.STATUS_CHANGED,
            changed_by_id=changed_by_id,
            changed_field="status",
            old_value=old_status,
            new_value=new_status,
            description=f"Статус изменён с {old_status} на {new_status}",
            metadata=metadata
        )

    async def record_driver_assigned(
        self,
        route_id: int,
        driver_id: int,
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать назначение водителя на маршрут.

        Args:
            route_id: ID маршрута
            driver_id: ID назначенного водителя
            changed_by_id: ID пользователя, назначившего водителя

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.DRIVER_ASSIGNED,
            changed_by_id=changed_by_id,
            changed_field="driver_id",
            new_value=driver_id,
            description=f"Назначен водитель {driver_id}",
            metadata={"driver_id": driver_id}
        )

    async def record_point_added(
        self,
        route_id: int,
        point_data: Dict[str, Any],
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать добавление точки в маршрут.

        Args:
            route_id: ID маршрута
            point_data: Данные добавленной точки
            changed_by_id: ID пользователя, добавившего точку

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.POINT_ADDED,
            changed_by_id=changed_by_id,
            new_value=point_data,
            description=f"Добавлена точка маршрута",
            metadata=point_data
        )

    async def record_point_removed(
        self,
        route_id: int,
        point_data: Dict[str, Any],
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать удаление точки из маршрута.

        Args:
            route_id: ID маршрута
            point_data: Данные удалённой точки
            changed_by_id: ID пользователя, удалившего точку

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.POINT_REMOVED,
            changed_by_id=changed_by_id,
            old_value=point_data,
            description=f"Удалена точка маршрута",
            metadata=point_data
        )

    async def record_point_reordered(
        self,
        route_id: int,
        old_sequence: List[int],
        new_sequence: List[int],
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать изменение порядка точек в маршруте.

        Args:
            route_id: ID маршрута
            old_sequence: Старый порядок point_id
            new_sequence: Новый порядок point_id
            changed_by_id: ID пользователя, изменившего порядок

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.POINT_REORDERED,
            changed_by_id=changed_by_id,
            old_value=old_sequence,
            new_value=new_sequence,
            description=f"Изменён порядок точек маршрута",
            metadata={
                "old_sequence": old_sequence,
                "new_sequence": new_sequence
            }
        )

    async def record_optimized(
        self,
        route_id: int,
        optimization_type: str,
        metrics: Dict[str, Any],
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать оптимизацию маршрута.

        Args:
            route_id: ID маршрута
            optimization_type: Тип оптимизации (time/distance)
            metrics: Метрики оптимизации (distance, duration, points_count)
            changed_by_id: ID пользователя, запустившего оптимизацию

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.OPTIMIZED,
            changed_by_id=changed_by_id,
            changed_field="optimization",
            new_value=metrics,
            description=f"Маршрут оптимизирован ({optimization_type})",
            metadata={
                "optimization_type": optimization_type,
                **metrics
            }
        )

    async def record_cancelled(
        self,
        route_id: int,
        reason: Optional[str] = None,
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать отмену маршрута.

        Args:
            route_id: ID маршрута
            reason: Причина отмены
            changed_by_id: ID пользователя, отменившего маршрут

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.CANCELLED,
            changed_by_id=changed_by_id,
            description=f"Маршрут отменён{': ' + reason if reason else ''}",
            metadata={"reason": reason} if reason else None
        )

    async def record_completed(
        self,
        route_id: int,
        metrics: Optional[Dict[str, Any]] = None,
        changed_by_id: Optional[int] = None
    ) -> RouteChangeHistory:
        """
        Записать завершение маршрута.

        Args:
            route_id: ID маршрута
            metrics: Финальные метрики (distance, duration, points_completed)
            changed_by_id: ID водителя, завершившего маршрут

        Returns:
            Созданная запись истории
        """
        return await self.record_change(
            route_id=route_id,
            change_type=RouteChangeType.COMPLETED,
            changed_by_id=changed_by_id,
            description="Маршрут завершён",
            metadata=metrics
        )

    async def get_route_history(
        self,
        route_id: int,
        limit: int = 100
    ) -> List[RouteChangeHistory]:
        """
        Получить историю изменений маршрута.

        Args:
            route_id: ID маршрута
            limit: Максимальное количество записей

        Returns:
            Список записей истории, отсортированный по времени (новые сначала)
        """
        stmt = (
            select(RouteChangeHistory)
            .where(RouteChangeHistory.route_id == route_id)
            .order_by(RouteChangeHistory.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        history = list(result.scalars().all())

        logger.debug(f"Получена история маршрута {route_id}: {len(history)} записей")
        return history
