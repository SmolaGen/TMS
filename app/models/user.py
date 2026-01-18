from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
import enum
# from app.models.order import Order # Import Order model - not needed here, only for type hinting if used directly

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    CLIENT = "client"

from app.database import Base # Import Base from database.py

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.CLIENT)

    client_orders = relationship("Order", foreign_keys="[Order.client_id]", back_populates="client") # Renamed from 'orders'
    driver_orders = relationship("Order", foreign_keys="[Order.driver_id]", back_populates="driver") # New relationship for driver
