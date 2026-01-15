import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Location, User, Chat
from datetime import datetime, timezone

from src.bot.handlers.location import on_location_message, on_location_edited, process_location
from src.database.models import Driver, UserRole

@pytest.fixture
def mock_user():
    return User(id=1, is_bot=False, first_name="Driver", username="driver")

@pytest.fixture
def mock_chat():
    return Chat(id=1, type="private")

@pytest.fixture
def mock_location():
    loc = MagicMock(spec=Location)
    loc.latitude = 55.75
    loc.longitude = 37.61
    loc.live_period = None
    return loc

@pytest.fixture
def mock_message(mock_user, mock_chat, mock_location):
    msg = MagicMock(spec=Message)
    msg.from_user = mock_user
    msg.chat = mock_chat
    msg.location = mock_location
    msg.date = datetime.now(timezone.utc)
    msg.edit_date = None
    msg.reply = AsyncMock()
    return msg

@pytest.fixture
def mock_driver():
    driver = MagicMock(spec=Driver)
    driver.id = 1
    driver.role = UserRole.DRIVER
    return driver

@pytest.fixture
def mock_admin():
    driver = MagicMock(spec=Driver)
    driver.id = 2
    driver.role = UserRole.ADMIN
    return driver

@pytest.mark.asyncio
async def test_on_location_message_simple(mock_message, mock_driver):
    """Тест обработки обычной геолокации от водителя."""
    with patch("src.bot.handlers.location.get_location_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.update_driver_location = AsyncMock()
        mock_factory.return_value = mock_manager
        
        await on_location_message(mock_message, driver=mock_driver)
        
        mock_manager.update_driver_location.assert_called_once()
        mock_message.reply.assert_called_once_with("📍 Геолокация получена!")

@pytest.mark.asyncio
async def test_on_location_message_live(mock_message, mock_location, mock_driver):
    """Тест обработки Live Location от водителя."""
    mock_location.live_period = 3600  # 1 час
    mock_message.location = mock_location
    
    with patch("src.bot.handlers.location.get_location_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.update_driver_location = AsyncMock()
        mock_factory.return_value = mock_manager
        
        await on_location_message(mock_message, driver=mock_driver)
        
        assert "Live Location активирован" in mock_message.reply.call_args.args[0]

@pytest.mark.asyncio
async def test_on_location_edited(mock_message, mock_driver):
    """Тест обработки обновления Live Location."""
    mock_message.edit_date = datetime.now(timezone.utc)
    
    with patch("src.bot.handlers.location.get_location_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.update_driver_location = AsyncMock()
        mock_factory.return_value = mock_manager
        
        await on_location_edited(mock_message, driver=mock_driver)
        
        mock_manager.update_driver_location.assert_called_once()

@pytest.mark.asyncio
async def test_process_location_no_location(mock_message, mock_driver):
    """Тест: сообщение без геолокации."""
    mock_message.location = None
    
    with patch("src.bot.handlers.location.get_location_manager") as mock_factory:
        await process_location(mock_message, driver=mock_driver)
        mock_factory.assert_not_called()

@pytest.mark.asyncio
async def test_allow_admin_location(mock_message, mock_admin):
    """Тест: разрешение сохранения геолокации от админа (для тестирования)."""
    with patch("src.bot.handlers.location.get_location_manager") as mock_factory:
        mock_manager = MagicMock()
        mock_manager.update_driver_location = AsyncMock()
        mock_factory.return_value = mock_manager
        
        await on_location_message(mock_message, driver=mock_admin)
        
        # Менеджер ДОЛЖЕН быть вызван
        mock_manager.update_driver_location.assert_called_once()
        # Бот НЕ должен отвечать админу (чтобы не спамить), согласно логике в handlers/location.py:70
        mock_message.reply.assert_not_called()
