from fastapi import APIRouter, Depends, HTTPException, status
from src.schemas.driver import DriverResponse, DriverUpdate
from src.database.models import Driver, DriverStatus
from src.services.driver_service import DriverService
from src.api.dependencies import get_driver_service, get_current_driver

router = APIRouter()

@router.patch("/drivers/me/status", response_model=DriverResponse)
async def update_my_status(
    new_status: DriverStatus,
    current_driver: Driver = Depends(get_current_driver),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Эндпоинт для водителя для обновления своего статуса (Online/Offline/Busy).
    """
    if not isinstance(new_status, DriverStatus):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный статус водителя"
        )

    updated_driver = await driver_service.update_driver(
        driver_id=current_driver.id,
        data=DriverUpdate(status=new_status)
    )

    if not updated_driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )
    
    return updated_driver
