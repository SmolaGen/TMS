"""
Integration tests for health check endpoints and health check framework.
Tests cover the health check base classes, individual checkers, composite checkers,
and the HTTP endpoints.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import FrozenInstanceError

from src.core.health_check import (
    HealthStatus,
    HealthCheckResult,
    HealthCheckError,
    HealthChecker,
    SyncHealthChecker,
    CompositeHealthChecker,
)


# ============================================================================
# Tests for HealthStatus Enum
# ============================================================================


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """HealthStatus has correct string values."""
        assert HealthStatus.OK.value == "ok"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.FAILED.value == "failed"

    def test_health_status_members_count(self):
        """HealthStatus has exactly 3 members."""
        assert len(HealthStatus.__members__) == 3

    def test_health_status_is_string_enum(self):
        """HealthStatus is a string enum."""
        assert isinstance(HealthStatus.OK, str)
        assert HealthStatus.OK == "ok"


# ============================================================================
# Tests for HealthCheckResult Dataclass
# ============================================================================


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_default_values(self):
        """HealthCheckResult has correct default values."""
        result = HealthCheckResult(
            name="test_component",
            status=HealthStatus.OK,
        )
        assert result.name == "test_component"
        assert result.status == HealthStatus.OK
        assert result.message == "OK"
        assert result.details == {}
        assert result.response_time_ms == 0.0
        assert isinstance(result.timestamp, float)

    def test_custom_values(self):
        """HealthCheckResult accepts custom values."""
        result = HealthCheckResult(
            name="custom_check",
            status=HealthStatus.FAILED,
            message="Custom error message",
            details={"error_code": 500},
            timestamp=1234567890.0,
            response_time_ms=123.45,
        )
        assert result.name == "custom_check"
        assert result.status == HealthStatus.FAILED
        assert result.message == "Custom error message"
        assert result.details == {"error_code": 500}
        assert result.timestamp == 1234567890.0
        assert result.response_time_ms == 123.45

    def test_to_dict(self):
        """to_dict() returns correct dictionary representation."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.OK,
            message="All good",
            details={"key": "value"},
            timestamp=1234567890.0,
            response_time_ms=50.0,
        )
        result_dict = result.to_dict()

        assert result_dict["name"] == "test"
        assert result_dict["status"] == "ok"
        assert result_dict["message"] == "All good"
        assert result_dict["details"] == {"key": "value"}
        assert result_dict["timestamp"] == 1234567890.0
        assert result_dict["response_time_ms"] == 50.0

    def test_is_healthy(self):
        """is_healthy() returns True only for OK status."""
        ok_result = HealthCheckResult(name="test", status=HealthStatus.OK)
        degraded_result = HealthCheckResult(name="test", status=HealthStatus.DEGRADED)
        failed_result = HealthCheckResult(name="test", status=HealthStatus.FAILED)

        assert ok_result.is_healthy() is True
        assert degraded_result.is_healthy() is False
        assert failed_result.is_healthy() is False

    def test_is_failed(self):
        """is_failed() returns True only for FAILED status."""
        ok_result = HealthCheckResult(name="test", status=HealthStatus.OK)
        degraded_result = HealthCheckResult(name="test", status=HealthStatus.DEGRADED)
        failed_result = HealthCheckResult(name="test", status=HealthStatus.FAILED)

        assert ok_result.is_failed() is False
        assert degraded_result.is_failed() is False
        assert failed_result.is_failed() is True


# ============================================================================
# Tests for HealthCheckError Exception
# ============================================================================


class TestHealthCheckError:
    """Tests for HealthCheckError exception."""

    def test_health_check_error_is_exception(self):
        """HealthCheckError is an Exception subclass."""
        error = HealthCheckError("Test error")
        assert isinstance(error, Exception)

    def test_health_check_error_message(self):
        """HealthCheckError stores the message correctly."""
        error = HealthCheckError("Custom error message")
        assert str(error) == "Custom error message"

    def test_health_check_error_can_be_raised(self):
        """HealthCheckError can be raised and caught."""
        with pytest.raises(HealthCheckError, match="Test exception"):
            raise HealthCheckError("Test exception")


# ============================================================================
# Tests for HealthChecker Base Class
# ============================================================================


class ConcreteAsyncHealthChecker(HealthChecker):
    """Concrete implementation of HealthChecker for testing."""

    def __init__(self, name: str, should_fail: bool = False, raise_exception: bool = False):
        super().__init__(name=name)
        self.should_fail = should_fail
        self.raise_exception = raise_exception

    async def check(self) -> HealthCheckResult:
        if self.raise_exception:
            raise Exception("Simulated failure")
        if self.should_fail:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message="Check failed",
            )
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.OK,
            message="Check passed",
        )


class TestHealthChecker:
    """Tests for HealthChecker base class."""

    def test_initialization(self):
        """HealthChecker initializes correctly."""
        checker = ConcreteAsyncHealthChecker(name="test_checker")
        assert checker.name == "test_checker"
        assert checker.timeout == 5.0
        assert checker.last_result is None

    def test_custom_timeout(self):
        """HealthChecker accepts custom timeout."""
        checker = ConcreteAsyncHealthChecker(name="test")
        checker.timeout = 10.0
        assert checker.timeout == 10.0

    @pytest.mark.asyncio
    async def test_check_success(self):
        """check() returns successful result."""
        checker = ConcreteAsyncHealthChecker(name="test", should_fail=False)
        result = await checker.check()

        assert result.status == HealthStatus.OK
        assert result.message == "Check passed"

    @pytest.mark.asyncio
    async def test_check_failure(self):
        """check() returns failed result when configured to fail."""
        checker = ConcreteAsyncHealthChecker(name="test", should_fail=True)
        result = await checker.check()

        assert result.status == HealthStatus.FAILED
        assert result.message == "Check failed"

    @pytest.mark.asyncio
    async def test_perform_check_measures_response_time(self):
        """perform_check() measures response time."""
        checker = ConcreteAsyncHealthChecker(name="test")
        result = await checker.perform_check()

        assert result.response_time_ms >= 0.0
        assert checker.last_result is not None
        assert checker.last_result == result

    @pytest.mark.asyncio
    async def test_perform_check_handles_exceptions(self):
        """perform_check() handles exceptions gracefully."""
        checker = ConcreteAsyncHealthChecker(name="test", raise_exception=True)
        result = await checker.perform_check()

        assert result.status == HealthStatus.FAILED
        assert "Health check failed" in result.message
        assert checker.last_result == result


# ============================================================================
# Tests for SyncHealthChecker Base Class
# ============================================================================


class ConcreteSyncHealthChecker(SyncHealthChecker):
    """Concrete implementation of SyncHealthChecker for testing."""

    def __init__(self, name: str, should_fail: bool = False, raise_exception: bool = False):
        super().__init__(name=name)
        self.should_fail = should_fail
        self.raise_exception = raise_exception

    def check(self) -> HealthCheckResult:
        if self.raise_exception:
            raise Exception("Simulated sync failure")
        if self.should_fail:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message="Sync check failed",
            )
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.OK,
            message="Sync check passed",
        )


class TestSyncHealthChecker:
    """Tests for SyncHealthChecker base class."""

    def test_initialization(self):
        """SyncHealthChecker initializes correctly."""
        checker = ConcreteSyncHealthChecker(name="sync_test")
        assert checker.name == "sync_test"
        assert checker.timeout == 5.0
        assert checker.last_result is None

    def test_check_success(self):
        """check() returns successful result."""
        checker = ConcreteSyncHealthChecker(name="test", should_fail=False)
        result = checker.check()

        assert result.status == HealthStatus.OK
        assert result.message == "Sync check passed"

    def test_check_failure(self):
        """check() returns failed result when configured to fail."""
        checker = ConcreteSyncHealthChecker(name="test", should_fail=True)
        result = checker.check()

        assert result.status == HealthStatus.FAILED
        assert result.message == "Sync check failed"

    def test_perform_check_measures_response_time(self):
        """perform_check() measures response time."""
        checker = ConcreteSyncHealthChecker(name="test")
        result = checker.perform_check()

        assert result.response_time_ms >= 0.0
        assert checker.last_result is not None
        assert checker.last_result == result

    def test_perform_check_handles_exceptions(self):
        """perform_check() handles exceptions gracefully."""
        checker = ConcreteSyncHealthChecker(name="test", raise_exception=True)
        result = checker.perform_check()

        assert result.status == HealthStatus.FAILED
        assert "Health check failed" in result.message


# ============================================================================
# Tests for CompositeHealthChecker
# ============================================================================


class TestCompositeHealthChecker:
    """Tests for CompositeHealthChecker."""

    def test_initialization(self):
        """CompositeHealthChecker initializes correctly."""
        composite = CompositeHealthChecker(name="test_composite")
        assert composite.name == "test_composite"
        assert composite.checkers == {}
        assert composite.sync_checkers == {}

    def test_default_name(self):
        """CompositeHealthChecker has default name."""
        composite = CompositeHealthChecker()
        assert composite.name == "composite_health"

    def test_add_async_checker(self):
        """add_async_checker() adds an async checker."""
        composite = CompositeHealthChecker()
        checker = ConcreteAsyncHealthChecker(name="async_check")

        composite.add_async_checker(checker)

        assert "async_check" in composite.checkers
        assert composite.checkers["async_check"] == checker

    def test_add_sync_checker(self):
        """add_sync_checker() adds a sync checker."""
        composite = CompositeHealthChecker()
        checker = ConcreteSyncHealthChecker(name="sync_check")

        composite.add_sync_checker(checker)

        assert "sync_check" in composite.sync_checkers
        assert composite.sync_checkers["sync_check"] == checker

    @pytest.mark.asyncio
    async def test_check_all_healthy(self):
        """check() returns OK when all checkers are healthy."""
        composite = CompositeHealthChecker(name="all_healthy")
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="check1"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="check2"))

        result = await composite.check()

        assert result.status == HealthStatus.OK
        assert result.message == "All checks passed"
        assert "checks" in result.details

    @pytest.mark.asyncio
    async def test_check_one_failed(self):
        """check() returns FAILED when one checker fails."""
        composite = CompositeHealthChecker(name="one_failed")
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="healthy"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="unhealthy", should_fail=True))

        result = await composite.check()

        assert result.status == HealthStatus.FAILED
        assert "unhealthy" in result.message

    @pytest.mark.asyncio
    async def test_check_with_exception(self):
        """check() handles checker exceptions gracefully."""
        composite = CompositeHealthChecker(name="with_exception")
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="healthy"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="raises", raise_exception=True))

        result = await composite.check()

        assert result.status == HealthStatus.FAILED
        assert "raises" in result.message

    @pytest.mark.asyncio
    async def test_check_empty_composite(self):
        """check() returns OK for empty composite."""
        composite = CompositeHealthChecker()
        result = await composite.check()

        assert result.status == HealthStatus.OK

    @pytest.mark.asyncio
    async def test_check_mixed_sync_async(self):
        """check() handles mixed sync and async checkers."""
        composite = CompositeHealthChecker(name="mixed")
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="async_healthy"))
        composite.add_sync_checker(ConcreteSyncHealthChecker(name="sync_healthy"))

        result = await composite.check()

        assert result.status == HealthStatus.OK
        assert "async_healthy" in result.details["checks"]
        assert "sync_healthy" in result.details["checks"]

    def test_check_sync_only(self):
        """check_sync() runs only sync checkers."""
        composite = CompositeHealthChecker(name="sync_only")
        composite.add_sync_checker(ConcreteSyncHealthChecker(name="sync1"))
        composite.add_sync_checker(ConcreteSyncHealthChecker(name="sync2"))

        result = composite.check_sync()

        assert result.status == HealthStatus.OK
        assert "sync1" in result.details["checks"]
        assert "sync2" in result.details["checks"]

    def test_check_sync_with_failure(self):
        """check_sync() returns FAILED when sync checker fails."""
        composite = CompositeHealthChecker(name="sync_failed")
        composite.add_sync_checker(ConcreteSyncHealthChecker(name="healthy"))
        composite.add_sync_checker(ConcreteSyncHealthChecker(name="failed", should_fail=True))

        result = composite.check_sync()

        assert result.status == HealthStatus.FAILED


# ============================================================================
# Tests for Individual Health Checkers (with mocking)
# ============================================================================


class TestDatabaseHealthChecker:
    """Tests for DatabaseHealthChecker with mocked database."""

    @pytest.mark.asyncio
    async def test_database_health_check_success(self):
        """DatabaseHealthChecker returns OK on successful connection."""
        from src.api.endpoints.health import DatabaseHealthChecker

        checker = DatabaseHealthChecker()

        # Mock the engine.connect context manager
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.endpoints.health.engine') as mock_engine:
            mock_engine.connect.return_value = mock_context
            result = await checker.check()

        assert result.status == HealthStatus.OK
        assert "Database connection successful" in result.message

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """DatabaseHealthChecker returns FAILED on connection error."""
        from src.api.endpoints.health import DatabaseHealthChecker

        checker = DatabaseHealthChecker()

        with patch('src.api.endpoints.health.engine') as mock_engine:
            mock_engine.connect.side_effect = Exception("Connection refused")
            result = await checker.check()

        assert result.status == HealthStatus.FAILED
        assert "Database connection failed" in result.message


class TestRedisHealthChecker:
    """Tests for RedisHealthChecker with mocked Redis."""

    @pytest.mark.asyncio
    async def test_redis_health_check_success(self):
        """RedisHealthChecker returns OK on successful ping."""
        from src.api.endpoints.health import RedisHealthChecker

        checker = RedisHealthChecker()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()

        with patch('src.api.endpoints.health.aioredis') as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis
            result = await checker.check()

        assert result.status == HealthStatus.OK
        assert "Redis connection successful" in result.message
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self):
        """RedisHealthChecker returns FAILED on ping error."""
        from src.api.endpoints.health import RedisHealthChecker

        checker = RedisHealthChecker()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
        mock_redis.close = AsyncMock()

        with patch('src.api.endpoints.health.aioredis') as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis
            result = await checker.check()

        assert result.status == HealthStatus.FAILED
        assert "Redis connection failed" in result.message


class TestOSRMHealthChecker:
    """Tests for OSRMHealthChecker with mocked HTTP client."""

    @pytest.mark.asyncio
    async def test_osrm_health_check_success(self):
        """OSRMHealthChecker returns OK on successful response."""
        from src.api.endpoints.health_detailed import OSRMHealthChecker

        checker = OSRMHealthChecker()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.endpoints.health_detailed.httpx.AsyncClient', return_value=mock_client):
            result = await checker.check()

        assert result.status == HealthStatus.OK
        assert "OSRM service is available" in result.message

    @pytest.mark.asyncio
    async def test_osrm_health_check_failure(self):
        """OSRMHealthChecker returns FAILED on request error."""
        from src.api.endpoints.health_detailed import OSRMHealthChecker

        checker = OSRMHealthChecker()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.endpoints.health_detailed.httpx.AsyncClient', return_value=mock_client):
            result = await checker.check()

        assert result.status == HealthStatus.FAILED
        assert "OSRM service is unavailable" in result.message


class TestPhotonHealthChecker:
    """Tests for PhotonHealthChecker with mocked HTTP client."""

    @pytest.mark.asyncio
    async def test_photon_health_check_success(self):
        """PhotonHealthChecker returns OK on successful response."""
        from src.api.endpoints.health_detailed import PhotonHealthChecker

        checker = PhotonHealthChecker()

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.endpoints.health_detailed.httpx.AsyncClient', return_value=mock_client):
            result = await checker.check()

        assert result.status == HealthStatus.OK
        assert "Photon service is available" in result.message

    @pytest.mark.asyncio
    async def test_photon_health_check_failure(self):
        """PhotonHealthChecker returns FAILED on request error."""
        from src.api.endpoints.health_detailed import PhotonHealthChecker

        checker = PhotonHealthChecker()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('src.api.endpoints.health_detailed.httpx.AsyncClient', return_value=mock_client):
            result = await checker.check()

        assert result.status == HealthStatus.FAILED
        assert "Photon service is unavailable" in result.message


# ============================================================================
# Tests for Health Check HTTP Endpoints
# ============================================================================


class TestHealthEndpoint:
    """Tests for /health HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self):
        """Health endpoint returns 200 when all checks pass."""
        from fastapi import Response
        from src.api.endpoints import health as health_module

        # Create mock health checker that returns OK
        mock_result = HealthCheckResult(
            name="application",
            status=HealthStatus.OK,
            message="All checks passed",
            details={
                "checks": {
                    "database": HealthCheckResult(
                        name="database",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=10.0,
                    ),
                    "redis": HealthCheckResult(
                        name="redis",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=5.0,
                    ),
                }
            },
            response_time_ms=15.0,
        )

        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value=mock_result)

        with patch.object(health_module, '_health_checker', mock_health_checker):
            response = Response()
            result = await health_module.health_check(response)

        assert response.status_code == 200
        assert result["status"] == "ok"
        assert "timestamp" in result
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_503_on_failure(self):
        """Health endpoint returns 503 when checks fail."""
        from fastapi import Response
        from src.api.endpoints import health as health_module

        mock_result = HealthCheckResult(
            name="application",
            status=HealthStatus.FAILED,
            message="Failed checks: database",
            details={
                "checks": {
                    "database": HealthCheckResult(
                        name="database",
                        status=HealthStatus.FAILED,
                        message="Connection failed",
                        response_time_ms=100.0,
                    ),
                }
            },
            response_time_ms=100.0,
        )

        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value=mock_result)

        with patch.object(health_module, '_health_checker', mock_health_checker):
            response = Response()
            result = await health_module.health_check(response)

        assert response.status_code == 503
        assert result["status"] == "failed"


class TestDetailedHealthEndpoint:
    """Tests for /health/detailed HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint_returns_ok(self):
        """Detailed health endpoint returns 200 when all checks pass."""
        from fastapi import Response
        from src.api.endpoints import health_detailed as health_detailed_module

        mock_result = HealthCheckResult(
            name="detailed",
            status=HealthStatus.OK,
            message="All checks passed",
            details={
                "checks": {
                    "database": HealthCheckResult(
                        name="database",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=10.0,
                    ),
                    "redis": HealthCheckResult(
                        name="redis",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=5.0,
                    ),
                    "osrm": HealthCheckResult(
                        name="osrm",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=20.0,
                    ),
                    "photon": HealthCheckResult(
                        name="photon",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=15.0,
                    ),
                }
            },
            response_time_ms=50.0,
        )

        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value=mock_result)

        with patch.object(health_detailed_module, '_detailed_health_checker', mock_health_checker):
            response = Response()
            result = await health_detailed_module.detailed_health_check(response)

        assert response.status_code == 200
        assert result["status"] == "ok"
        assert "timestamp" in result
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint_returns_503_on_failure(self):
        """Detailed health endpoint returns 503 when any check fails."""
        from fastapi import Response
        from src.api.endpoints import health_detailed as health_detailed_module

        mock_result = HealthCheckResult(
            name="detailed",
            status=HealthStatus.FAILED,
            message="Failed checks: osrm",
            details={
                "checks": {
                    "database": HealthCheckResult(
                        name="database",
                        status=HealthStatus.OK,
                        message="OK",
                        response_time_ms=10.0,
                    ),
                    "osrm": HealthCheckResult(
                        name="osrm",
                        status=HealthStatus.FAILED,
                        message="Service unavailable",
                        response_time_ms=5000.0,
                    ),
                }
            },
            response_time_ms=5010.0,
        )

        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value=mock_result)

        with patch.object(health_detailed_module, '_detailed_health_checker', mock_health_checker):
            response = Response()
            result = await health_detailed_module.detailed_health_check(response)

        assert response.status_code == 503
        assert result["status"] == "failed"


# ============================================================================
# Tests for Overall Status Determination
# ============================================================================


class TestStatusDetermination:
    """Tests for overall status determination logic."""

    @pytest.mark.asyncio
    async def test_all_ok_returns_ok(self):
        """All OK checks result in overall OK status."""
        composite = CompositeHealthChecker()
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="check1"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="check2"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="check3"))

        result = await composite.check()
        assert result.status == HealthStatus.OK

    @pytest.mark.asyncio
    async def test_one_failed_returns_failed(self):
        """One failed check results in overall FAILED status."""
        composite = CompositeHealthChecker()
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="ok1"))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="failed", should_fail=True))
        composite.add_async_checker(ConcreteAsyncHealthChecker(name="ok2"))

        result = await composite.check()
        assert result.status == HealthStatus.FAILED

    @pytest.mark.asyncio
    async def test_response_body_structure(self):
        """Health check response has correct structure."""
        from fastapi import Response
        from src.api.endpoints import health as health_module

        mock_result = HealthCheckResult(
            name="application",
            status=HealthStatus.OK,
            message="All checks passed",
            details={
                "checks": {
                    "database": HealthCheckResult(
                        name="database",
                        status=HealthStatus.OK,
                        message="Database connection successful",
                        response_time_ms=10.5,
                    ),
                }
            },
            timestamp=1234567890.0,
            response_time_ms=10.5,
        )

        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value=mock_result)

        with patch.object(health_module, '_health_checker', mock_health_checker):
            response = Response()
            result = await health_module.health_check(response)

        # Verify response structure
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result

        # Verify check structure
        db_check = result["checks"]["database"]
        assert "status" in db_check
        assert "message" in db_check
        assert "response_time_ms" in db_check


# ============================================================================
# Tests for Response Time Measurement
# ============================================================================


class TestResponseTimeMeasurement:
    """Tests for response time measurement."""

    @pytest.mark.asyncio
    async def test_async_perform_check_measures_time(self):
        """perform_check() measures execution time for async checkers."""
        import asyncio

        class SlowAsyncChecker(HealthChecker):
            async def check(self) -> HealthCheckResult:
                await asyncio.sleep(0.05)  # 50ms delay
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.OK,
                )

        checker = SlowAsyncChecker(name="slow_async")
        result = await checker.perform_check()

        # Response time should be at least 50ms
        assert result.response_time_ms >= 40.0  # Allow some variance

    def test_sync_perform_check_measures_time(self):
        """perform_check() measures execution time for sync checkers."""
        import time as time_module

        class SlowSyncChecker(SyncHealthChecker):
            def check(self) -> HealthCheckResult:
                time_module.sleep(0.05)  # 50ms delay
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.OK,
                )

        checker = SlowSyncChecker(name="slow_sync")
        result = checker.perform_check()

        # Response time should be at least 50ms
        assert result.response_time_ms >= 40.0  # Allow some variance
