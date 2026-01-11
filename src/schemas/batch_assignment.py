"""
Схемы для batch-распределения заказов.
"""

from datetime import date
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from src.schemas.order import OrderPriority


class BatchAssignmentRequest(BaseModel):
    """Запрос на batch-распределение заказов."""

    target_date: date = Field(..., description="Дата для распределения заказов")
    priority_filter: Optional[OrderPriority] = Field(
        None,
        description="Фильтр по приоритету заказов"
    )
    driver_ids: Optional[List[int]] = Field(
        None,
        description="Список ID водителей для распределения (None = все доступные)"
    )
    max_orders_per_driver: Optional[int] = Field(
        10,
        description="Максимальное количество заказов на водителя в день",
        ge=1,
        le=20
    )


class AssignmentDetail(BaseModel):
    """Детали одного назначения."""

    order_id: int
    driver_id: int
    driver_name: str


class FailedAssignment(BaseModel):
    """Детали неудачного назначения."""

    order_id: int
    reason: str
    order_details: Optional[Dict] = None


class BatchAssignmentResult(BaseModel):
    """Результат batch-распределения."""

    assigned_orders: List[AssignmentDetail] = Field(default_factory=list)
    failed_orders: List[FailedAssignment] = Field(default_factory=list)
    total_processed: int = Field(0, description="Общее количество обработанных заказов")
    total_assigned: int = Field(0, description="Количество успешно назначенных заказов")
    total_failed: int = Field(0, description="Количество неудачных назначений")
    success_rate: float = Field(0.0, description="Процент успешных назначений")


class BatchPreviewResponse(BaseModel):
    """Ответ на запрос предпросмотра распределения."""

    result: BatchAssignmentResult
    note: str = Field(
        "Это предварительный расчет. Назначения не сохранены в базе данных.",
        description="Пояснение, что это preview"
    )


class UnassignedOrdersResponse(BaseModel):
    """Ответ со списком нераспределенных заказов на дату."""

    orders: List[Dict] = Field(default_factory=list, description="Список нераспределенных заказов")
    total_count: int = Field(0, description="Общее количество нераспределенных заказов")
    target_date: date


class DriverScheduleItem(BaseModel):
    """Элемент расписания водителя."""

    order_id: int
    time_start: str
    time_end: str
    pickup_address: Optional[str]
    dropoff_address: Optional[str]
    status: str
    priority: str


class DriverScheduleResponse(BaseModel):
    """Расписание водителя на дату."""

    driver_id: int
    driver_name: str
    target_date: date
    schedule: List[DriverScheduleItem] = Field(default_factory=list)
    total_orders: int = Field(0, description="Общее количество заказов на день")
    available_slots: int = Field(0, description="Примерное количество доступных слотов")
