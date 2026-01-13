import hmac
import hashlib
import json
import pytest
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

from src.services.auth_service import AuthService
from src.database.models import Driver, UserRole
from src.config import settings
from fastapi import HTTPException

@pytest.fixture
def auth_service():
    return AuthService(bot_token="test_bot_token")

def generate_init_data(data: dict, bot_token: str, is_login_widget: bool = False) -> str:
    """Helper to generate valid Telegram initData hash."""
    # 1. Create data_check_string
    sorted_items = sorted(data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)
    
    # 2. Derive secret key
    if is_login_widget:
        secret_key = hashlib.sha256(bot_token.encode()).digest()
    else:
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    
    # 3. Calculate hash
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    # 4. Return as URL-encoded string
    data_with_hash = data.copy()
    data_with_hash["hash"] = calculated_hash
    return urlencode(data_with_hash)

def test_validate_init_data_mini_app_success(auth_service):
    user_data = {"id": 123, "first_name": "Test"}
    data = {
        "user": json.dumps(user_data),
        "auth_date": int(datetime.now(timezone.utc).timestamp())
    }
    init_data = generate_init_data(data, "test_bot_token", is_login_widget=False)
    
    validated_user = auth_service.validate_init_data(init_data)
    assert validated_user["id"] == 123
    assert validated_user["first_name"] == "Test"

def test_validate_init_data_login_widget_success(auth_service):
    data = {
        "id": "123",
        "first_name": "Test",
        "auth_date": int(datetime.now(timezone.utc).timestamp())
    }
    init_data = generate_init_data(data, "test_bot_token", is_login_widget=True)
    
    validated_user = auth_service.validate_init_data(init_data)
    assert validated_user["id"] == 123
    assert validated_user["first_name"] == "Test"

def test_validate_init_data_invalid_hash(auth_service):
    data = {
        "user": json.dumps({"id": 123}),
        "auth_date": int(datetime.now(timezone.utc).timestamp()),
        "hash": "wrong_hash"
    }
    init_data = urlencode(data)
    
    with pytest.raises(HTTPException) as exc:
        auth_service.validate_init_data(init_data)
    assert exc.value.status_code == 401
    assert "Hash verification failed" in exc.value.detail

def test_validate_init_data_expired(auth_service):
    # Expired 2 days ago
    auth_date = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    data = {
        "user": json.dumps({"id": 123}),
        "auth_date": auth_date
    }
    init_data = generate_init_data(data, "test_bot_token")
    
    with pytest.raises(HTTPException) as exc:
        auth_service.validate_init_data(init_data)
    assert exc.value.status_code == 401
    assert "initData expired" in exc.value.detail

def test_validate_init_data_missing_hash(auth_service):
    data = {"user": json.dumps({"id": 123})}
    init_data = urlencode(data)
    
    with pytest.raises(HTTPException) as exc:
        auth_service.validate_init_data(init_data)
    assert exc.value.status_code == 401
    assert "Missing hash" in exc.value.detail

def test_create_access_token(auth_service):
    driver = Driver(
        id=1,
        telegram_id=123,
        name="Test",
        role=UserRole.DRIVER
    )
    token = auth_service.create_access_token(driver)
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify token
    import jwt
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == str(driver.telegram_id)
    assert payload["driver_id"] == driver.id
    assert payload["role"] == driver.role.value

def test_get_token_response(auth_service):
    driver = Driver(
        id=1,
        telegram_id=123,
        name="Test",
        role=UserRole.DRIVER
    )
    response = auth_service.get_token_response(driver)
    assert response.access_token
    assert response.driver_id == 1
    assert response.role == "driver"
    assert response.telegram_id == 123
