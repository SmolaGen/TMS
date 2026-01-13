
import pytest
import pandas as pd
import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import UploadFile

from src.services.excel_import import ExcelImportService
from src.services.order_service import OrderService
from src.services.geocoding import GeocodingService
from src.schemas.order import OrderCreate
from src.database.models import OrderPriority

@pytest.fixture
def mock_order_service():
    service = MagicMock(spec=OrderService)
    service.create_order = AsyncMock()
    return service

@pytest.fixture
def mock_geocoding_service():
    service = MagicMock(spec=GeocodingService)
    service.geocode = AsyncMock(return_value={"lat": 55.75, "lon": 37.61})
    return service

@pytest.fixture
def excel_service(mock_order_service):
    return ExcelImportService(mock_order_service)

@pytest.mark.asyncio
async def test_parse_excel_success(excel_service):
    # Arrange: Create a dummy Excel file in memory
    df = pd.DataFrame({
        "Адрес погрузки": ["Moscow"],
        "Адрес выгрузки": ["SPb"],
        "Телефон": ["+79001112233"],
        "Имя": ["Иван"],
        "Дата": ["2026-01-12"],
        "Время": ["10:00"],
        "Приоритет": ["high"]
    })
    
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)
    
    upload_file = UploadFile(filename="test.xlsx", file=excel_file)
    
    # Act
    orders = await excel_service.parse_excel(upload_file)
    
    # Assert
    assert len(orders) == 1
    assert orders[0]["pickup_address"] == "Moscow"
    assert orders[0]["customer_name"] == "Иван"

@pytest.mark.asyncio
async def test_import_orders_success(excel_service, mock_order_service, mock_geocoding_service):
    # Arrange
    orders_data = [{
        "pickup_address": "Moscow",
        "dropoff_address": "SPb",
        "customer_phone": "+79001112233",
        "customer_name": "Иван",
        "time_start": datetime(2026, 1, 12, 10, 0),
        "priority": OrderPriority.HIGH
    }]
    
    mock_order_service.create_order.return_value = MagicMock(id=1)
    # Geocoding mock needs to return objects with .lat and .lon
    mock_geocoding_service.geocode.return_value = MagicMock(lat=55.75, lon=37.61)
    
    # Act
    result = await excel_service.import_orders(orders_data)
    
    # Assert
    assert result["created"] == 1
    assert result["failed"] == 0
    mock_order_service.create_order.assert_called_once()

@pytest.mark.asyncio
async def test_import_orders_geocoding_failure(excel_service, mock_order_service, mock_geocoding_service):
    # Arrange
    orders_data = [{
        "pickup_address": "Unknown Place",
        "dropoff_address": "SPb",
        "time_start": datetime(2026, 1, 12, 10, 0),
        "priority": OrderPriority.NORMAL
    }]
    
    # Настраиваем мок OrderService на выброс ошибки (которую бы выбросил реальный сервис при неудаче геокодинга)
    from fastapi import HTTPException
    mock_order_service.create_order.side_effect = HTTPException(status_code=422, detail="Не удалось найти адрес погрузки: Unknown Place")
    
    # Act
    result = await excel_service.import_orders(orders_data)
    
    # Assert
    assert result["created"] == 0
    assert result["failed"] == 1
    assert "Не удалось найти адрес погрузки" in result["errors"][0]["error"]

@pytest.mark.asyncio
async def test_parse_excel_missing_data_skips_row(excel_service):
    # Arrange: Row with missing mandatory "Дата"
    df = pd.DataFrame({
        "Адрес погрузки": ["Moscow"],
        "Адрес выгрузки": ["SPb"],
        "Дата": [None]
    })
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)
    upload_file = UploadFile(filename="test.xlsx", file=excel_file)
    
    # Act
    orders = await excel_service.parse_excel(upload_file)
    
    # Assert
    assert len(orders) == 0
