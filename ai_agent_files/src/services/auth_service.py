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
        Валидирует данные от Telegram WebApp или Login Widget.
        
        Поддерживает два формата:
        1. Mini App initData (с полем user в JSON)
        2. Login Widget данные (прямые поля id, first_name и т.д.)
        """
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.info(f"Validating initData, length={len(init_data)}")
            
            # Парсинг строки запроса
            parsed_data = {k: v[0] for k, v in parse_qs(init_data).items()}
            
            logger.info(f"Parsed keys: {list(parsed_data.keys())}")
            
            if "hash" not in parsed_data:
                raise ValueError("Missing hash in initData")
            
            # Извлекаем hash ДО формирования data_check_string
            received_hash = parsed_data.pop("hash")
            logger.info(f"Received hash: {received_hash[:20]}...")
            
            # 1. Проверка auth_date на свежесть
            auth_date = int(parsed_data.get("auth_date", 0))
            current_time = int(datetime.now(tz=timezone.utc).timestamp())
            
            logger.info(f"auth_date={auth_date}, current_time={current_time}, diff={current_time - auth_date}s")
            
            if current_time - auth_date > settings.TELEGRAM_INIT_DATA_EXPIRE_SECONDS:
                raise ValueError(f"initData expired (age={current_time - auth_date}s, max={settings.TELEGRAM_INIT_DATA_EXPIRE_SECONDS}s)")
            
            # 2. Формирование data_check_string (БЕЗ hash, он уже извлечен)
            # Сортируем ключи по алфавиту и склеиваем в формате key=value через \n
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(parsed_data.items())
            )
            
            logger.info(f"data_check_string (first 200 chars): {data_check_string[:200]}")
            logger.info(f"Using bot_token: {self.bot_token[:10]}...{self.bot_token[-5:]}")
            
            # 3. Определяем тип данных и вычисляем хеш
            is_login_widget = "user" not in parsed_data and "id" in parsed_data
            
            if is_login_widget:
                # Login Widget: secret_key = SHA256(bot_token)
                logger.info("Detected Login Widget format")
                secret_key = hashlib.sha256(self.bot_token.encode()).digest()
            else:
                # Mini App: secret_key = HMAC-SHA256("WebAppData", bot_token)
                logger.info("Detected Mini App initData format")
                secret_key = hmac.new(
                    b"WebAppData",
                    self.bot_token.encode(),
                    hashlib.sha256
                ).digest()
            
            # Вычисляем хеш данных
            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            logger.info(f"Calculated hash: {calculated_hash[:20]}...")
            logger.info(f"Hash match: {calculated_hash == received_hash}")
            
            # 4. Сравнение хешей
            if not hmac.compare_digest(calculated_hash, received_hash):
                raise ValueError("Hash verification failed")
            
            # 5. Формирование user_data
            if is_login_widget:
                # Login Widget: данные пользователя в корне
                user_data = {
                    "id": int(parsed_data.get("id", 0)),
                    "first_name": parsed_data.get("first_name", "Unknown"),
                    "last_name": parsed_data.get("last_name"),
                    "username": parsed_data.get("username"),
                    "photo_url": parsed_data.get("photo_url"),
                }
                logger.info(f"User validated (Login Widget): id={user_data.get('id')}, name={user_data.get('first_name')}")
            else:
                # Mini App: данные пользователя в JSON поле user
                user_data_json = parsed_data.get("user")
                if not user_data_json:
                    raise ValueError("Missing user data")
                user_data = json.loads(user_data_json)
                logger.info(f"User validated (Mini App): id={user_data.get('id')}, name={user_data.get('first_name')}")
            
            return user_data
            
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Validation failed: {str(e)}")
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
            "role": driver.role.value,
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
            telegram_id=driver.telegram_id,
            role=driver.role.value
        )
