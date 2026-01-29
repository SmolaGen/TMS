from typing import List, Optional
import httpx
from src.schemas.geocoding import GeocodingResult
from src.config import settings
from src.core.logging import get_logger
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = get_logger(__name__)

class GeocodingService:
    """Сервис геокодинга на базе Photon."""

    def __init__(self, url: str = settings.PHOTON_URL):
        self.url = url.rstrip("/")
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            success_threshold=1,
            name="photon_geocoding"
        )

    async def search(self, query: str, limit: int = 10, lang: str = "ru") -> List[GeocodingResult]:
        """Прямой геокодинг (поиск по строке)."""
        if not query or len(query) < 3:
            return []

        url = f"{self.url}/api"
        params = {
            "q": query,
            "limit": limit,
            "lang": lang
        }
        params = {k: v for k, v in params.items() if v is not None}

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                # Пытаемся использовать локальный API с защитой circuit breaker
                try:
                    async def _fetch_local_search() -> dict:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        return response.json()

                    data = await self.circuit_breaker.call(_fetch_local_search)
                except CircuitBreakerOpenError:
                    logger.warning(f"Circuit breaker open for Photon, using public API fallback")
                    # Fallback на публичный photon.komoot.io
                    public_url = "https://photon.komoot.io/api"
                    # Публичный API не поддерживает lang=ru
                    public_params = params.copy()
                    if "lang" in public_params:
                        del public_params["lang"]
                    public_params = {k: v for k, v in public_params.items() if v is not None}

                    response = await client.get(public_url, params=public_params)
                    response.raise_for_status()
                    data = response.json()
                except (httpx.ConnectError, httpx.HTTPStatusError):
                    # Fallback на публичный photon.komoot.io
                    public_url = "https://photon.komoot.io/api"
                    # Публичный API не поддерживает lang=ru
                    public_params = params.copy()
                    if "lang" in public_params:
                        del public_params["lang"]
                    public_params = {k: v for k, v in public_params.items() if v is not None}

                    response = await client.get(public_url, params=public_params)
                    response.raise_for_status()
                    data = response.json()
        except Exception as e:
            logger.error(f"Geocoding search failed: {str(e)}")
            return []

        results = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [0, 0])
            
            # Собираем читаемый адрес
            addr_parts = [
                props.get("name"),
                props.get("street"),
                props.get("housenumber"),
                props.get("city"),
                props.get("state"),
                props.get("country")
            ]
            address_full = ", ".join([p for p in addr_parts if p])

            results.append(GeocodingResult(
                name=props.get("name", "Unknown"),
                lat=coords[1],
                lon=coords[0],
                address_full=address_full,
                osm_id=props.get("osm_id"),
                osm_key=props.get("osm_key"),
                osm_value=props.get("osm_value")
            ))
        
        return results

    async def reverse(self, lat: float, lon: float, lang: str = "ru") -> Optional[GeocodingResult]:
        """Обратный геокодинг (по координатам)."""
        url = f"{self.url}/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "lang": lang
        }
        params = {k: v for k, v in params.items() if v is not None}

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                # Пытаемся использовать локальный API с защитой circuit breaker
                try:
                    async def _fetch_local_reverse() -> dict:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        return response.json()

                    data = await self.circuit_breaker.call(_fetch_local_reverse)
                except CircuitBreakerOpenError:
                    logger.warning(f"Circuit breaker open for Photon, using public API fallback")
                    # Fallback на публичный photon.komoot.io
                    public_url = "https://photon.komoot.io/reverse"
                    # Публичный API не поддерживает lang=ru
                    public_params = params.copy()
                    if "lang" in public_params:
                        del public_params["lang"]
                    public_params = {k: v for k, v in public_params.items() if v is not None}

                    response = await client.get(public_url, params=public_params)
                    response.raise_for_status()
                    data = response.json()
                except (httpx.ConnectError, httpx.HTTPStatusError):
                    # Fallback на публичный photon.komoot.io
                    public_url = "https://photon.komoot.io/reverse"
                    # Публичный API не поддерживает lang=ru
                    public_params = params.copy()
                    if "lang" in public_params:
                        del public_params["lang"]
                    public_params = {k: v for k, v in public_params.items() if v is not None}

                    response = await client.get(public_url, params=public_params)
                    response.raise_for_status()
                    data = response.json()
        except Exception as e:
            logger.error(f"Geocoding reverse failed: {str(e)}")
            return None

        features = data.get("features", [])
        if not features:
            return None

        feature = features[0]
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [lon, lat])
        
        addr_parts = [
            props.get("name"),
            props.get("street"),
            props.get("housenumber"),
            props.get("city"),
            props.get("country")
        ]
        address_full = ", ".join([p for p in addr_parts if p])

        return GeocodingResult(
            name=props.get("name", "Unknown"),
            lat=coords[1],
            lon=coords[0],
            address_full=address_full
        )
