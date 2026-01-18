from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal, engine, Base
from app.models import user as models_user, order as models_order
from app.schemas import user as schemas_user, order as schemas_order
from app.crud import user as crud_user, order as crud_order
from app.api import auth

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.post("/users/", response_model=schemas_user.UserInDB)
def create_user(user: schemas_user.UserCreate, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_telegram_id(db, telegram_id=user.telegram_id)
    if db_user:
        raise HTTPException(status_code=400, detail="Telegram ID already registered")
    return crud_user.create_user(db=db, user=user)

@app.get("/users/", response_model=List[schemas_user.UserInDB])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=schemas_user.UserInDB)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/orders/", response_model=schemas_order.OrderInDB)
def create_order(order: schemas_order.OrderCreate, db: Session = Depends(get_db)):
    return crud_order.create_order(db=db, order=order)

@app.get("/orders/", response_model=List[schemas_order.OrderInDB])
def read_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    orders = crud_order.get_orders(db, skip=skip, limit=limit)
    return orders

@app.get("/orders/{order_id}", response_model=schemas_order.OrderInDB)
def read_order(order_id: int, db: Session = Depends(get_db)):
    db_order = crud_order.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@app.put("/orders/{order_id}", response_model=schemas_order.OrderInDB)
def update_order(order_id: int, order: schemas_order.OrderUpdate, db: Session = Depends(get_db)):
    db_order = crud_order.update_order(db, order_id=order_id, order=order)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    db_order = crud_order.delete_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return

@app.post("/orders/{order_id}/assign_driver", response_model=schemas_order.OrderInDB)
def assign_driver_to_order(
    order_id: int,
    driver_assignment: schemas_order.OrderAssignDriver,
    db: Session = Depends(get_db)
):
    db_order = crud_order.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db_driver = crud_user.get_user(db, user_id=driver_assignment.driver_id)
    if db_driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")
    if db_driver.role != models_user.UserRole.DRIVER:
        raise HTTPException(status_code=400, detail="User is not a driver")

    updated_order = crud_order.assign_driver_to_order(db, order_id=order_id, driver_id=driver_assignment.driver_id)
    return updated_order
