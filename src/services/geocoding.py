"""
Geocoding Service with Circuit Breaker and Caching

Provides geocoding functionality with:
- Circuit breaker protection for local Photon API
- Automatic fallback to public Photon API
- In-memory caching for improved performance and graceful degradation
"""
from typing import List, Optional, Dict, Any
import time
import hashlib
import httpx
from src.schemas.geocoding import GeocodingResult
from src.config import settings
from src.core.logging import get_logger
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = get_logger(__name__)

# Public Photon API endpoint for fallback
PUBLIC_PHOTON_URL = "https://photon.komoot.io"

# Default headers for requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class GeocodingCache:
    """Simple in-memory cache for geocoding results with TTL."""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize geocoding cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 1 hour)
            max_size: Maximum number of entries in cache
        """
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        key_data = f"{prefix}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        key = self._make_key(prefix, **kwargs)
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug("Cache hit", cache_key=key[:8], prefix=prefix)
                return value
            else:
                # Expired - remove entry
                del self._cache[key]
        return None

    def set(self, prefix: str, value: Any, **kwargs) -> None:
        """Store value in cache."""
        # Cleanup if cache is too large
        if len(self._cache) >= self._max_size:
            self._cleanup_expired()
            if len(self._cache) >= self._max_size:
                # Remove oldest entries
                sorted_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][0]
                )
                for key in sorted_keys[:self._max_size // 4]:
                    del self._cache[key]

        key = self._make_key(prefix, **kwargs)
        self._cache[key] = (time.time(), value)
        logger.debug("Cache set", cache_key=key[:8], prefix=prefix)

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = time.time()
        expired_keys = [
            key for key, (ts, _) in self._cache.items()
            if now - ts >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl
        }


class GeocodingService:
    """
    Geocoding service using Photon API with circuit breaker protection.

    Features:
    - Circuit breaker for local Photon API protection
    - Automatic fallback to public Photon API
    - In-memory caching for performance and graceful degradation
    """

    def __init__(
        self,
        url: str = settings.PHOTON_URL,
        cache_ttl: int = 3600,
        cache_size: int = 1000
    ):
        """
        Initialize geocoding service.

        Args:
            url: Local Photon API URL
            cache_ttl: Cache TTL in seconds (default 1 hour)
            cache_size: Maximum cache size (default 1000 entries)
        """
        self.url = url.rstrip("/")
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            success_threshold=1,
            name="photon_geocoding"
        )
        self._cache = GeocodingCache(ttl_seconds=cache_ttl, max_size=cache_size)
        logger.info(
            "GeocodingService initialized",
            local_url=self.url,
            cache_ttl=cache_ttl,
            cache_size=cache_size
        )

    async def _fetch_from_api(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Dict[str, Any],
        source: str
    ) -> Dict[str, Any]:
        """
        Fetch data from geocoding API.

        Args:
            client: HTTP client
            url: API URL
            params: Request parameters
            source: Source identifier for logging

        Returns:
            JSON response data
        """
        response = await client.get(url, params=params)
        response.raise_for_status()
        logger.debug(
            "Geocoding API response",
            source=source,
            status_code=response.status_code,
            url=url
        )
        return response.json()

    async def _fetch_with_fallback(
        self,
        endpoint: str,
        params: Dict[str, Any],
        local_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch from local Photon API with circuit breaker and fallback to public API.

        Args:
            endpoint: API endpoint (e.g., '/api', '/reverse')
            params: Base request parameters
            local_params: Additional params for local API (e.g., lang=ru)

        Returns:
            JSON response data or None on failure
        """
        local_url = f"{self.url}{endpoint}"
        public_url = f"{PUBLIC_PHOTON_URL}{endpoint}"

        # Prepare params - local API supports additional params like lang
        full_local_params = {**params, **(local_params or {})}
        full_local_params = {k: v for k, v in full_local_params.items() if v is not None}

        # Public API params (no lang support)
        public_params = {k: v for k, v in params.items() if v is not None and k != "lang"}

        async with httpx.AsyncClient(timeout=5.0, headers=DEFAULT_HEADERS) as client:
            # Try local API with circuit breaker protection
            try:
                async def _fetch_local() -> Dict[str, Any]:
                    return await self._fetch_from_api(
                        client, local_url, full_local_params, "local_photon"
                    )

                return await self.circuit_breaker.call(_fetch_local)

            except CircuitBreakerOpenError:
                logger.warning(
                    "Circuit breaker open for Photon, using public API fallback",
                    circuit_breaker_state=self.circuit_breaker.get_state()
                )

            except (httpx.ConnectError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
                logger.warning(
                    "Local Photon API failed, trying public fallback",
                    error=str(e),
                    error_type=type(e).__name__
                )

            # Fallback to public API
            try:
                data = await self._fetch_from_api(
                    client, public_url, public_params, "public_photon"
                )
                return data
            except Exception as e:
                logger.error(
                    "Public Photon API also failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                return None

        return None

    def _parse_search_results(self, data: Dict[str, Any]) -> List[GeocodingResult]:
        """Parse geocoding search results from API response."""
        results = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [0, 0])

            # Build full address from components
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

    def _parse_reverse_result(
        self,
        data: Dict[str, Any],
        default_lat: float,
        default_lon: float
    ) -> Optional[GeocodingResult]:
        """Parse reverse geocoding result from API response."""
        features = data.get("features", [])
        if not features:
            return None

        feature = features[0]
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [default_lon, default_lat])

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

    async def search(
        self,
        query: str,
        limit: int = 10,
        lang: str = "ru"
    ) -> List[GeocodingResult]:
        """
        Forward geocoding - search by address string.

        Args:
            query: Address search query
            limit: Maximum number of results
            lang: Language for results (local API only)

        Returns:
            List of geocoding results
        """
        if not query or len(query) < 3:
            return []

        # Try cache first
        cached = self._cache.get("search", query=query, limit=limit, lang=lang)
        if cached is not None:
            logger.debug("Returning cached search results", query=query[:30])
            return cached

        params = {"q": query, "limit": limit}
        local_params = {"lang": lang}

        try:
            data = await self._fetch_with_fallback("/api", params, local_params)
            if data is None:
                # Return cached results if available (even if expired) for graceful degradation
                expired_cached = self._cache.get("search", query=query, limit=limit, lang=lang)
                if expired_cached:
                    logger.warning("Using potentially stale cache for graceful degradation")
                    return expired_cached
                return []

            results = self._parse_search_results(data)

            # Cache successful results
            if results:
                self._cache.set("search", results, query=query, limit=limit, lang=lang)

            return results

        except Exception as e:
            logger.error(
                "Geocoding search failed",
                error=str(e),
                query=query[:50]
            )
            return []

    async def reverse(
        self,
        lat: float,
        lon: float,
        lang: str = "ru"
    ) -> Optional[GeocodingResult]:
        """
        Reverse geocoding - get address from coordinates.

        Args:
            lat: Latitude
            lon: Longitude
            lang: Language for results (local API only)

        Returns:
            Geocoding result or None
        """
        # Round coordinates for cache key (to ~11m precision)
        cache_lat = round(lat, 4)
        cache_lon = round(lon, 4)

        # Try cache first
        cached = self._cache.get("reverse", lat=cache_lat, lon=cache_lon, lang=lang)
        if cached is not None:
            logger.debug("Returning cached reverse geocoding result", lat=lat, lon=lon)
            return cached

        params = {"lat": lat, "lon": lon}
        local_params = {"lang": lang}

        try:
            data = await self._fetch_with_fallback("/reverse", params, local_params)
            if data is None:
                # Return cached results for graceful degradation
                expired_cached = self._cache.get("reverse", lat=cache_lat, lon=cache_lon, lang=lang)
                if expired_cached:
                    logger.warning("Using potentially stale cache for graceful degradation")
                    return expired_cached
                return None

            result = self._parse_reverse_result(data, lat, lon)

            # Cache successful result
            if result:
                self._cache.set("reverse", result, lat=cache_lat, lon=cache_lon, lang=lang)

            return result

        except Exception as e:
            logger.error(
                "Geocoding reverse failed",
                error=str(e),
                lat=lat,
                lon=lon
            )
            return None

    def get_circuit_breaker_state(self) -> str:
        """Get current circuit breaker state."""
        return self.circuit_breaker.get_state()

    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return self.circuit_breaker.get_metrics()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def clear_cache(self) -> None:
        """Clear geocoding cache."""
        self._cache.clear()
        logger.info("Geocoding cache cleared")
