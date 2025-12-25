import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.services.driver_service import DriverService
from src.database.uow import AbstractUnitOfWork
from src.schemas.driver import DriverCreate, DriverUpdate
from src.database.models import Driver, DriverStatus

@pytest.fixture
def mock_uow():
    uow = MagicMock(spec=AbstractUnitOfWork)
    uow.drivers = MagicMock()
    # Mock context manager
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow

@pytest.fixture
def driver_service(mock_uow):
    return DriverService(mock_uow)

@pytest.mark.asyncio
async def test_register_driver_success(driver_service, mock_uow):
    # Arrange
    data = DriverCreate(telegram_id=123, name="Ivan", phone="+79991234567")
    mock_uow.drivers.get_by_attribute = AsyncMock(return_value=None)
    
    # Act
    # Имитируем поведение БД: после add и commit у объекта появляются id и даты
    original_add = mock_uow.drivers.add
    def side_effect(driver):
        driver.id = 1
        driver.created_at = datetime.utcnow()
        driver.updated_at = datetime.utcnow()
        return driver
    mock_uow.drivers.add.side_effect = side_effect

    result = await driver_service.register_driver(data)
    
    # Assert
    assert result.id == 1
    assert result.telegram_id == 123
    assert result.name == "Ivan"
    mock_uow.drivers.add.assert_called_once()
    mock_uow.commit.assert_called_once()

@pytest.mark.asyncio
async def test_register_driver_duplicate(driver_service, mock_uow):
    # Arrange
    data = DriverCreate(telegram_id=123, name="Ivan")
    mock_uow.drivers.get_by_attribute = AsyncMock(return_value=Driver(id=1, telegram_id=123))
    
    # Act & Assert
    with pytest.raises(ValueError, match="already exists"):
        await driver_service.register_driver(data)
    
    mock_uow.drivers.add.assert_not_called()
    mock_uow.commit.assert_not_called()

@pytest.mark.asyncio
async def test_get_driver_found(driver_service, mock_uow):
    # Arrange
    now = datetime.utcnow()
    driver = Driver(
        id=1, 
        telegram_id=123, 
        name="Ivan", 
        status=DriverStatus.AVAILABLE,
        created_at=now,
        updated_at=now
    )
    mock_uow.drivers.get = AsyncMock(return_value=driver)
    
    # Act
    result = await driver_service.get_driver(1)
    
    # Assert
    assert result.id == 1
    assert result.name == "Ivan"

@pytest.mark.asyncio
async def test_get_driver_not_found(driver_service, mock_uow):
    # Arrange
    mock_uow.drivers.get = AsyncMock(return_value=None)
    
    # Act
    result = await driver_service.get_driver(999)
    
    # Assert
    assert result is None
