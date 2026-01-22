from fastapi import APIRouter, Depends, HTTPException, status
from src.schemas.auth import TelegramAuthRequest, TokenResponse
from src.services.auth_service import AuthService
from src.services.driver_service import DriverService
from src.api.dependencies import get_auth_service, get_driver_service
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
async def login(
    data: TelegramAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
    driver_service: DriverService = Depends(get_driver_service)
):
    """
    Вход через Telegram WebApp.
    Валидирует initData и возвращает JWT токен.
    Если водитель новый - регистрирует его.
    """
    # 1. Валидация данных от Telegram
    user_data = auth_service.validate_init_data(data.init_data)
    telegram_id = user_data["id"]
    
    # 2. Поиск или регистрация водителя
    driver = await driver_service.get_by_telegram_id(telegram_id)
    if not driver:
        # Авто-регистрация
        driver = await driver_service.create_driver_from_telegram(
            telegram_id=telegram_id,
            name=user_data.get("first_name", "Unknown Driver"),
            username=user_data.get("username")
        )
        logger.info("driver_auto_registered", telegram_id=telegram_id, driver_id=driver.id)
    
    # 3. Генерация токена
    return auth_service.get_token_response(driver)
