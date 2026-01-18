from sqlalchemy.orm import Session
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderUpdate, OrderAssignDriver # Import OrderAssignDriver

def get_order(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()

def get_orders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Order).offset(skip).limit(limit).all()

def create_order(db: Session, order: OrderCreate):
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order(db: Session, order_id: int, order: OrderUpdate):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        update_data = order.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_order, key, value)
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
    return db_order

def delete_order(db: Session, order_id: int):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        db.delete(db_order)
        db.commit()
    return db_order

def assign_driver_to_order(db: Session, order_id: int, driver_id: int):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        db_order.driver_id = driver_id
        # Optionally, change order status to ACCEPTED when assigned
        if db_order.status == OrderStatus.PENDING:
            db_order.status = OrderStatus.ACCEPTED
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
    return db_order
