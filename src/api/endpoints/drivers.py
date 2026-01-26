from fastapi import APIRouter, Depends, HTTPException, status
from src.schemas.driver import DriverResponse, DriverUpdate, OnboardingStatusResponse, OnboardingUpdate
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


@router.get("/users/me/onboarding", response_model=OnboardingStatusResponse)
async def get_my_onboarding_status(
    current_driver: Driver = Depends(get_current_driver)
):
    """
    Получить статус онбординга текущего пользователя.
    """
    return OnboardingStatusResponse(
        onboarding_completed=current_driver.onboarding_completed,
        onboarding_step=current_driver.onboarding_step,
        onboarding_skipped=current_driver.onboarding_skipped
    )


@router.patch("/users/me/onboarding", response_model=OnboardingStatusResponse)
async def update_my_onboarding(
    onboarding_data: OnboardingUpdate,
    current_driver: Driver = Depends(get_current_driver),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Обновить прогресс онбординга текущего пользователя.
    """
    # Подготавливаем данные для обновления
    update_data = DriverUpdate()

    if onboarding_data.onboarding_step is not None:
        update_data.onboarding_step = str(onboarding_data.onboarding_step)

    if onboarding_data.onboarding_completed is not None:
        update_data.onboarding_completed = onboarding_data.onboarding_completed

    if onboarding_data.onboarding_skipped is not None:
        update_data.onboarding_skipped = onboarding_data.onboarding_skipped

    # Если нет данных для обновления, возвращаем текущий статус
    if not onboarding_data.model_dump(exclude_unset=True):
        return OnboardingStatusResponse(
            onboarding_completed=current_driver.onboarding_completed,
            onboarding_step=current_driver.onboarding_step,
            onboarding_skipped=current_driver.onboarding_skipped
        )

    # Обновляем водителя
    updated_driver = await driver_service.update_driver(
        driver_id=current_driver.id,
        data=update_data
    )

    if not updated_driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )

    return OnboardingStatusResponse(
        onboarding_completed=updated_driver.onboarding_completed,
        onboarding_step=updated_driver.onboarding_step,
        onboarding_skipped=updated_driver.onboarding_skipped
    )
