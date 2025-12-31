import pytest
import httpx
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from src.services.routing import RoutingService, RouteResult, PriceResult, RouteNotFoundError, OSRMUnavailableError


@pytest.fixture
def routing_service():
    return RoutingService(
        osrm_url="http://osrm-test:5000",
        price_base=Decimal("300"),
        price_per_km=Decimal("25")
    )


def test_parse_geometry_point_valid(routing_service):
    # WKT
    lon, lat = routing_service.parse_geometry_point("POINT(131.8869 43.1150)")
    assert lon == 131.8869
    assert lat == 43.1150
    
    # EWKT
    lon, lat = routing_service.parse_geometry_point("SRID=4326;POINT(132.0 42.0)")
    assert lon == 132.0
    assert lat == 42.0
    
    # Mix case
    lon, lat = routing_service.parse_geometry_point("point ( 10.5 -20.3 )")
    assert lon == 10.5
    assert lat == -20.3


def test_parse_geometry_point_invalid(routing_service):
    with pytest.raises(ValueError):
        routing_service.parse_geometry_point("LINESTRING(0 0, 1 1)")
    
    with pytest.raises(ValueError):
        routing_service.parse_geometry_point("")


def test_calculate_price(routing_service):
    # 10 км: 300 + 10 * 25 = 550
    price = routing_service.calculate_price(10000)
    assert price.distance_km == Decimal("10.00")
    assert price.total_price == Decimal("550.00")
    
    # 2.555 км (округление до 2.56): 300 + 2.56 * 25 = 300 + 64 = 364
    price = routing_service.calculate_price(2555)
    assert price.distance_km == Decimal("2.56")
    assert price.total_price == Decimal("364.00")


@pytest.mark.asyncio
async def test_get_route_success(routing_service):
    mock_request = httpx.Request("GET", "http://osrm-test:5000/route/v1/driving/")
    mock_response = httpx.Response(200, json={
        "code": "Ok",
        "routes": [{"distance": 1500.5, "duration": 200.2}]
    }, request=mock_request)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await routing_service.get_route((10.0, 20.0), (30.0, 40.0))
        
        assert result.distance_meters == 1500.5
        assert result.duration_seconds == 200.2
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_route_no_route(routing_service):
    mock_request = httpx.Request("GET", "http://osrm-test:5000/route/v1/driving/")
    mock_response = httpx.Response(200, json={"code": "NoRoute"}, request=mock_request)
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        with pytest.raises(RouteNotFoundError):
            await routing_service.get_route((0, 0), (1, 1))


@pytest.mark.asyncio
async def test_get_route_osrm_down(routing_service):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")
        
        with pytest.raises(OSRMUnavailableError):
            await routing_service.get_route((0, 0), (1, 1))
