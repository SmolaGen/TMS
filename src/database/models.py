"""
TMS Database Models

Модели данных для системы управления транспортом.
Использует SQLAlchemy 2.0 с декларативным стилем и GeoAlchemy2.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class DriverStatus(str, PyEnum):
    """Статусы водителя."""
    AVAILABLE = "available"      # Доступен для заказов
    BUSY = "busy"                # Занят (выполняет заказ)
    OFFLINE = "offline"          # Не на связи


class OrderStatus(str, PyEnum):
    """Статусы заказа."""
    PENDING = "pending"          # Ожидает назначения водителя
    ASSIGNED = "assigned"        # Назначен водитель
    IN_PROGRESS = "in_progress"  # Выполняется
    COMPLETED = "completed"      # Завершён
    CANCELLED = "cancelled"      # Отменён


class OrderPriority(str, PyEnum):
    """Приоритет заказа."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Driver(Base):
    """
    Модель водителя.
    
    Attributes:
        id: Первичный ключ
        telegram_id: Уникальный идентификатор в Telegram
        name: Имя водителя
        phone: Номер телефона
        status: Текущий статус водителя
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    __tablename__ = "drivers"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        unique=True, 
        index=True,
        comment="Telegram user ID"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        comment="Имя водителя"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Номер телефона"
    )
    status: Mapped[DriverStatus] = mapped_column(
        Enum(DriverStatus, name="driver_status", create_constraint=True),
        default=DriverStatus.OFFLINE,
        server_default=text("'offline'"),
        comment="Текущий статус"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow
    )
    
    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="driver",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, name='{self.name}', status={self.status.value})>"


class Order(Base):
    """
    Модель заказа.
    
    Attributes:
        id: Первичный ключ
        driver_id: FK на водителя (nullable - может быть не назначен)
        status: Статус заказа
        priority: Приоритет заказа
        time_range: Временной интервал выполнения (tstzrange)
        pickup_location: Точка погрузки (POINT)
        dropoff_location: Точка выгрузки (POINT)
        comment: Комментарий к заказу
        created_at: Дата создания
        updated_at: Дата обновления
    
    Note:
        Exclusion Constraint `no_driver_time_overlap` гарантирует,
        что один водитель не может иметь пересекающиеся по времени заказы.
        Constraint применяется только к активным заказам 
        (status NOT IN ('completed', 'cancelled')).
    """
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK на водителя"
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_constraint=True),
        default=OrderStatus.PENDING,
        server_default=text("'pending'"),
        comment="Статус заказа"
    )
    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority, name="order_priority", create_constraint=True),
        default=OrderPriority.NORMAL,
        server_default=text("'normal'"),
        comment="Приоритет заказа"
    )
    
    # Временной интервал - будет добавлен через DDL в миграции
    # так как SQLAlchemy не имеет нативной поддержки tstzrange
    # time_range будет типа TSTZRANGE
    
    pickup_location: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Координаты точки погрузки (WGS84)"
    )
    dropoff_location: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Координаты точки выгрузки (WGS84)"
    )
    
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Комментарий к заказу"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow
    )
    
    # Relationships
    driver: Mapped[Optional["Driver"]] = relationship(
        "Driver",
        back_populates="orders",
        lazy="joined"
    )
    
    __table_args__ = (
        # Индекс для быстрого поиска по статусу и приоритету
        Index("ix_orders_status_priority", "status", "priority"),
        # Exclusion Constraint будет добавлен в Alembic миграции через DDL,
        # так как SQLAlchemy не поддерживает EXCLUDE constraints нативно
    )
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, driver_id={self.driver_id}, status={self.status.value})>"
