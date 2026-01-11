"""
TMS Database Models

Модели данных для системы управления транспортом.
Использует SQLAlchemy 2.0 с декларативным стилем и GeoAlchemy2.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from decimal import Decimal

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Numeric,
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
    DRIVER_ARRIVED = "driver_arrived" # Водитель прибыл на место
    IN_PROGRESS = "in_progress"  # Выполняется
    COMPLETED = "completed"      # Завершён
    CANCELLED = "cancelled"      # Отменён


class OrderPriority(str, PyEnum):
    """Приоритет заказа."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class UserRole(str, PyEnum):
    """Роли пользователей."""
    DRIVER = "driver"          # Водитель
    DISPATCHER = "dispatcher"  # Диспетчер
    ADMIN = "admin"            # Администратор
    PENDING = "pending"        # Ожидает одобрения


class Driver(Base):
    """
    Модель водителя.
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
        Enum(DriverStatus, name="driver_status", 
             values_callable=lambda x: [e.value for e in x]),
        default=DriverStatus.OFFLINE,
        server_default=text("'offline'"),
        comment="Текущий статус"
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role",
             values_callable=lambda x: [e.value for e in x]),
        default=UserRole.PENDING,
        server_default=text("'pending'"),
        comment="Роль пользователя в системе"
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
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default=text("true"),
        comment="Флаг активности (разрешен ли вход в бот)"
    )
    
    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="driver",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, name='{self.name}', status={self.status.value})>"


class Contractor(Base):
    """
    Модель подрядчика (внешней системы).
    """
    __tablename__ = "contractors"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="contractor")

    def __repr__(self) -> str:
        return f"<Contractor(id={self.id}, name='{self.name}')>"


class Order(Base):
    """
    Модель заказа.
    
    Note:
        Exclusion Constraint `no_driver_time_overlap` гарантирует,
        что один водитель не может иметь пересекающиеся по времени заказы.
    """
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK на водителя"
    )
    contractor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contractors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK на подрядчика"
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="ID заказа во внешней системе"
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status",
             values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING,
        server_default=text("'pending'"),
        comment="Статус заказа"
    )
    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority, name="order_priority",
             values_callable=lambda x: [e.value for e in x]),
        default=OrderPriority.NORMAL,
        server_default=text("'normal'"),
        comment="Приоритет заказа"
    )
    
    # Временной интервал выполнения заказа
    time_range: Mapped[Optional[tuple]] = mapped_column(
        TSTZRANGE(),
        nullable=True,
        comment="Временной интервал выполнения (с таймзоной)"
    )
    
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
    
    pickup_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dropoff_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Рассчитанные данные от RoutingService
    distance_meters: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Дистанция в метрах (от OSRM)"
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Время в пути в секундах (от OSRM)"
    )
    
    # Стоимость
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Итоговая стоимость заказа"
    )
    
    route_geometry: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Закодированная геометрия маршрута (polyline)"
    )
    
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Комментарий к заказу"
    )
    
    # Lifecycle timestamps
    arrived_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    contractor: Mapped[Optional["Contractor"]] = relationship(
        "Contractor",
        back_populates="orders",
        lazy="selectin"
    )

    @property
    def driver_name(self) -> Optional[str]:
        return self.driver.name if self.driver else None

    @property
    def time_start(self) -> Optional[datetime]:
        return self.time_range.lower if self.time_range else None

    @property
    def time_end(self) -> Optional[datetime]:
        return self.time_range.upper if self.time_range else None

    @property
    def pickup_lat(self) -> Optional[float]:
        return to_shape(self.pickup_location).y if self.pickup_location else None

    @property
    def pickup_lon(self) -> Optional[float]:
        return to_shape(self.pickup_location).x if self.pickup_location else None

    @property
    def dropoff_lat(self) -> Optional[float]:
        return to_shape(self.dropoff_location).y if self.dropoff_location else None

    @property
    def dropoff_lon(self) -> Optional[float]:
        return to_shape(self.dropoff_location).x if self.dropoff_location else None
    
    __table_args__ = (
        Index("ix_orders_status_priority", "status", "priority"),
    )


class DriverLocationHistory(Base):
    """
    История перемещений водителя.
    """
    __tablename__ = "driver_location_history"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"),
        index=True,
        comment="ID водителя"
    )
    location: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        comment="Координаты (WGS84)"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        index=True,
        comment="Время фиксации координат водителем"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Время записи в БД"
    )
    
    driver: Mapped["Driver"] = relationship("Driver", backref="location_history")
    
    __table_args__ = (
        Index("ix_driver_location_time", "driver_id", "recorded_at"),
    )
