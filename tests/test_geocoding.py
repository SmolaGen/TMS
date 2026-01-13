import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.geocoding import GeocodingService
from src.schemas.geocoding import GeocodingResult

@pytest.fixture
def geocoding_service():
    return GeocodingService(url="http://local-photon:2322")

@pytest.mark.asyncio
async def test_search_success(geocoding_service):
    mock_response_data = {
        "features": [
            {
                "properties": {
                    "name": "Point A",
                    "city": "Vladivostok",
                    "street": "Svetlanskaya",
                    "housenumber": "1"
                },
                "geometry": {
                    "coordinates": [131.88, 43.11]
                }
            }
        ]
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_data
        mock_get.return_value.raise_for_status = MagicMock()
        
        results = await geocoding_service.search("Владивосток")
        
        assert len(results) == 1
        assert results[0].name == "Point A"
        assert results[0].lat == 43.11
        assert results[0].lon == 131.88
        assert "Vladivostok" in results[0].address_full

@pytest.mark.asyncio
async def test_search_short_query(geocoding_service):
    results = await geocoding_service.search("Vl")
    assert results == []

@pytest.mark.asyncio
async def test_search_fallback(geocoding_service):
    # First call fails, second (fallback) succeeds
    mock_fail = AsyncMock(side_effect=httpx.ConnectError("Local down"))
    
    mock_success = MagicMock(spec=httpx.Response)
    mock_success.status_code = 200
    mock_success.json.return_value = {"features": []}
    mock_success.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [httpx.ConnectError("Local down"), mock_success]
        
        results = await geocoding_service.search("Vladivostok")
        
        assert results == []
        assert mock_get.call_count == 2
        # Verify first call was to local, second to public
        assert "local-photon" in mock_get.call_args_list[0][0][0]
        assert "photon.komoot.io" in mock_get.call_args_list[1][0][0]

@pytest.mark.asyncio
async def test_reverse_success(geocoding_service):
    mock_response_data = {
        "features": [
            {
                "properties": {
                    "name": "Home",
                    "city": "Vladivostok"
                },
                "geometry": {
                    "coordinates": [131.88, 43.11]
                }
            }
        ]
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_data
        mock_get.return_value.raise_for_status = MagicMock()
        
        result = await geocoding_service.reverse(43.11, 131.88)
        
        assert result is not None
        assert result.name == "Home"
        assert result.lat == 43.11
        assert result.lon == 131.88

@pytest.mark.asyncio
async def test_reverse_no_results(geocoding_service):
    mock_response_data = {"features": []}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_data
        mock_get.return_value.raise_for_status = MagicMock()
        
        result = await geocoding_service.reverse(0, 0)
        assert result is None
