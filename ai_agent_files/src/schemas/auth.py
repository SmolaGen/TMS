from pydantic import BaseModel
from typing import Optional

class TelegramAuthRequest(BaseModel):
    """Данные для входа через Telegram WebApp."""
    init_data: str

class TokenResponse(BaseModel):
    """Ответ с JWT токеном."""
    access_token: str
    token_type: str = "bearer"
    driver_id: int
    name: str
    telegram_id: int
