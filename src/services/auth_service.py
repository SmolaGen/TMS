import hmac
import hashlib
import json
import jwt
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote
from fastapi import HTTPException, status

from src.config import settings
from src.database.models import Driver
from src.schemas.auth import TokenResponse

class AuthService:
    def __init__(self, bot_token: str = settings.TELEGRAM_BOT_TOKEN):
        self.bot_token = bot_token

    def validate_init_data(self, init_data: str) -> dict:
        """
        Валидирует данные от Telegram WebApp.
        
        Алгоритм согласно документации Telegram:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        """
        try:
            # Парсинг строки запроса
            parsed_data = {k: v[0] for k, v in parse_qs(init_data).items()}
            
            if "hash" not in parsed_data:
                raise ValueError("Missing hash in initData")
            
            received_hash = parsed_data.pop("hash")
            
            # 1. Проверка auth_date на свежесть
            auth_date = int(parsed_data.get("auth_date", 0))
            current_time = int(datetime.now(tz=timezone.utc).timestamp())
            
            if current_time - auth_date > settings.TELEGRAM_INIT_DATA_EXPIRE_SECONDS:
                raise ValueError("initData expired")
            
            # 2. Формирование data_check_string
            # Сортируем ключи по алфавиту и склеиваем в формате key=value через \n
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(parsed_data.items())
            )
            
            # 3. Вычисление HMAC-SHA256
            # Сначала вычисляем секретный ключ на основе токена бота
            secret_key = hmac.new(
                b"WebAppData",
                self.bot_token.encode(),
                hashlib.sha256
            ).digest()
            
            # Затем вычисляем хеш данных
            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 4. Сравнение хешей
            if not hmac.compare_digest(calculated_hash, received_hash):
                raise ValueError("Hash verification failed")
            
            # 5. Десериализация user данных
            user_data_json = parsed_data.get("user")
            if not user_data_json:
                raise ValueError("Missing user data")
                
            user_data = json.loads(user_data_json)
            return user_data
            
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Telegram initData: {str(e)}"
            )

    def create_access_token(self, driver: Driver) -> str:
        """Создает JWT токен для водителя."""
        expire = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(driver.telegram_id),
            "driver_id": driver.id,
            "name": driver.name,
            "exp": expire,
            "iat": datetime.now(tz=timezone.utc)
        }
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

    def get_token_response(self, driver: Driver) -> TokenResponse:
        """Формирует полный ответ с токеном."""
        token = self.create_access_token(driver)
        return TokenResponse(
            access_token=token,
            driver_id=driver.id,
            name=driver.name,
            telegram_id=driver.telegram_id
        )
