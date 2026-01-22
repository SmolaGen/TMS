import pytest
import time
import hmac
import hashlib
import json
from typing import Optional
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.services.auth_service import AuthService
from src.services.driver_service import DriverService
from src.schemas.auth import TokenResponse
from src.database.models import Driver, UserRole
from src.config import settings

# Helper to generate valid init_data for testing
def generate_telegram_init_data(user_data: dict, bot_token: str, auth_date: Optional[int] = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())

    data_params = {
        "query_id": "AAH_dummy_query_id",
        "user": json.dumps(user_data),
        "auth_date": str(auth_date),
        "hash": "" # Placeholder, will be calculated
    }

    data_check_string_parts = []
    for key in sorted(data_params.keys()):
        if key != 'hash':
            data_check_string_parts.append(f"{key}={data_params[key]}")
    
    data_check_string = "\n".join(data_check_string_parts)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()
    
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    data_params['hash'] = calculated_hash
    
    # Reconstruct the init_data string
    init_data_parts = []
    for key, value in data_params.items():
        init_data_parts.append(f"{key}={value}")
    
    return "&".join(init_data_parts)


@pytest.fixture
def mock_driver_service():
    return MagicMock(spec=DriverService)

@pytest.fixture
def auth_service_with_mock(mock_driver_service):
    return AuthService(mock_driver_service)

@pytest.fixture
def test_user_data():
    return {
        "id": 12345,
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "language_code": "en",
        "is_premium": True,
        "allows_write_to_pm": True
    }

def test_validate_init_data_valid(auth_service_with_mock, test_user_data, telegram_bot_token):
    init_data = generate_telegram_init_data(test_user_data, telegram_bot_token)
    
    validated_data = auth_service_with_mock.validate_init_data(init_data)
    
    assert validated_data["id"] == test_user_data["id"]
    assert validated_data["username"] == test_user_data["username"]
    assert validated_data["first_name"] == test_user_data["first_name"]

def test_validate_init_data_invalid_hash(auth_service_with_mock, test_user_data, telegram_bot_token):
    init_data = generate_telegram_init_data(test_user_data, telegram_bot_token)
    invalid_init_data = init_data.replace(init_data[-10:], "invalidhash") # Corrupt the hash
    
    with pytest.raises(ValueError, match="Init data hash is invalid"):
        auth_service_with_mock.validate_init_data(invalid_init_data)

def test_validate_init_data_expired(auth_service_with_mock, test_user_data, telegram_bot_token):
    # Set auth_date far in the past
    past_auth_date = int(time.time()) - settings.TELEGRAM_INIT_DATA_EXPIRE_SECONDS - 100
    init_data = generate_telegram_init_data(test_user_data, telegram_bot_token, auth_date=past_auth_date)
    
    with pytest.raises(ValueError, match="Init data has expired"):
        auth_service_with_mock.validate_init_data(init_data)

def test_validate_init_data_missing_hash(auth_service_with_mock, test_user_data, telegram_bot_token):
    init_data = generate_telegram_init_data(test_user_data, telegram_bot_token)
    init_data_missing_hash = "&".join([p for p in init_data.split('&') if not p.startswith('hash=')])
    
    with pytest.raises(ValueError, match="Init data is missing 'hash'"):
        auth_service_with_mock.validate_init_data(init_data_missing_hash)

def test_validate_init_data_missing_user(auth_service_with_mock, telegram_bot_token):
    # Create init_data without 'user' field
    auth_date = int(time.time())
    data_params = {
        "query_id": "AAH_dummy_query_id",
        "auth_date": str(auth_date),
    }
    data_check_string_parts = []
    for key in sorted(data_params.keys()):
        data_check_string_parts.append(f"{key}={data_params[key]}")
    data_check_string = "\n".join(data_check_string_parts)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=telegram_bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    init_data_missing_user = f"query_id=AAH_dummy_query_id&auth_date={auth_date}&hash={calculated_hash}"

    with pytest.raises(ValueError, match="Init data is missing 'user' information"):
        auth_service_with_mock.validate_init_data(init_data_missing_user)


def test_create_access_token(auth_service_with_mock):
    data = {"sub": "123", "role": "driver"}
    token = auth_service_with_mock.create_access_token(data, expires_delta=timedelta(minutes=1))
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token content (optional, but good for sanity check)
    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded_token["sub"] == "123"
    assert decoded_token["role"] == "driver"
    assert "exp" in decoded_token

def test_get_token_response_existing_driver(auth_service_with_mock, mock_driver_service, db_session, test_user_data):
    # Mock an existing driver
    existing_driver = Driver(
        id=1,
        telegram_id=test_user_data["id"],
        name=f"{test_user_data['first_name']} {test_user_data['last_name']}",
        username=test_user_data["username"],
        role=UserRole.DRIVER,
        is_active=True
    )
    mock_driver_service.get_by_telegram_id.return_value = existing_driver
    
    response = auth_service_with_mock.get_token_response(test_user_data, db_session)
    
    assert isinstance(response, TokenResponse)
    assert response.token_type == "bearer"
    assert isinstance(response.access_token, str)
    mock_driver_service.get_by_telegram_id.assert_called_once_with(db_session, telegram_id=test_user_data["id"])
    mock_driver_service.create_driver_from_telegram.assert_not_called()

def test_get_token_response_new_driver(auth_service_with_mock, mock_driver_service, db_session, test_user_data):
    # Mock no existing driver, so a new one should be created
    mock_driver_service.get_by_telegram_id.return_value = None
    new_driver = Driver(
        id=2,
        telegram_id=test_user_data["id"],
        name=f"{test_user_data['first_name']} {test_user_data['last_name']}",
        username=test_user_data["username"],
        role=UserRole.DRIVER,
        is_active=True
    )
    mock_driver_service.create_driver_from_telegram.return_value = new_driver
    
    response = auth_service_with_mock.get_token_response(test_user_data, db_session)
    
    assert isinstance(response, TokenResponse)
    mock_driver_service.get_by_telegram_id.assert_called_once_with(db_session, telegram_id=test_user_data["id"])
    mock_driver_service.create_driver_from_telegram.assert_called_once_with(db_session, user_data=test_user_data)

def test_get_token_response_inactive_driver(auth_service_with_mock, mock_driver_service, db_session, test_user_data):
    inactive_driver = Driver(
        id=3,
        telegram_id=test_user_data["id"],
        name="Inactive Driver",
        username="inactive",
        role=UserRole.DRIVER,
        is_active=False
    )
    mock_driver_service.get_by_telegram_id.return_value = inactive_driver

    with pytest.raises(ValueError, match="Driver account is inactive."):
        auth_service_with_mock.get_token_response(test_user_data, db_session)
    
    mock_driver_service.get_by_telegram_id.assert_called_once_with(db_session, telegram_id=test_user_data["id"])
    mock_driver_service.create_driver_from_telegram.assert_not_called()

def test_get_token_response_missing_telegram_id(auth_service_with_mock, mock_driver_service, db_session):
    invalid_user_data = {"first_name": "No ID"}
    with pytest.raises(ValueError, match="Telegram user ID not found in user data."):
        auth_service_with_mock.get_token_response(invalid_user_data, db_session)
    mock_driver_service.get_by_telegram_id.assert_not_called()
    mock_driver_service.create_driver_from_telegram.assert_not_called()

