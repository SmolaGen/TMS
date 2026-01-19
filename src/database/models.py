#TRUNCATE
# src/database/models.py

import datetime
import enum
from typing import List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger, # Added BigInteger
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from src.database.database import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    CLIENT = "client"
    MANAGER = "manager"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.CLIENT)

    driver = relationship("Driver", back_populates="user", uselist=False)
    client = relationship("Client", back_populates="user", uselist=False)


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True) # New field
    name = Column(String, nullable=True) # New field
    username = Column(String, unique=True, nullable=True) # New field
    is_active = Column(Boolean, default=True) # New field, default True as per PRD
    phone_number = Column(String, unique=True, index=True, nullable=True)
    status = Column(String, default="offline")  # e.g., 'online', 'offline', 'on_delivery'
    current_location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    last_location_update = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="driver")
    orders = relationship("Order", back_populates="driver")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="client")
    orders = relationship("Order", back_populates="client")


class OrderStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    pickup_location = Column(Geometry(geometry_type="POINT", srid=4326))
    delivery_location = Column(Geometry(geometry_type="POINT", srid=4326))
    pickup_address = Column(String)
    delivery_address = Column(String)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    price = Column(Float, nullable=True)
    distance = Column(Float, nullable=True)
    estimated_time = Column(Integer, nullable=True)  # in seconds
    notes = Column(Text, nullable=True)

    client = relationship("Client", back_populates="orders")
    driver = relationship("Driver", back_populates="orders")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    route_geometry = Column(Geometry(geometry_type="LINESTRING", srid=4326))
    distance = Column(Float)
    duration = Column(Integer)  # in seconds
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")


class AdminSettings(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, index=True)
    setting_value = Column(String)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class BatchAssignment(Base):
    __tablename__ = "batch_assignments"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")  # e.g., 'pending', 'processing', 'completed', 'failed'
    assigned_orders_count = Column(Integer, default=0)
    failed_assignments_count = Column(Integer, default=0)
    log_message = Column(Text, nullable=True)


class BatchAssignmentOrder(Base):
    __tablename__ = "batch_assignment_orders"

    id = Column(Integer, primary_key=True, index=True)
    batch_assignment_id = Column(Integer, ForeignKey("batch_assignments.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(String, default="pending")  # e.g., 'pending', 'assigned', 'skipped', 'error'
    message = Column(String, nullable=True)

    batch_assignment = relationship("BatchAssignment", back_populates="batch_assignment_orders")
    order = relationship("Order")


BatchAssignment.batch_assignment_orders = relationship(
    "BatchAssignmentOrder", order_by=BatchAssignmentOrder.id, back_populates="batch_assignment"
)
