import time
from typing import Optional

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Response
from sqlalchemy import text

from src.config import settings
from src.core.health_check import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    CompositeHealthChecker,
)
from src.core.logging import get_logger
from src.database.connection import engine

logger = get_logger(__name__)

router = APIRouter()


class DatabaseHealthChecker(HealthChecker):
    """Проверяет здоровье подключения к базе данных."""

    def __init__(self, timeout: float = settings.HEALTH_CHECK_TIMEOUT):
        super().__init__(name="database", timeout=timeout)

    async def check(self) -> HealthCheckResult:
        """
        Проверяет подключение к базе данных.

        Returns:
            HealthCheckResult с статусом подключения к БД

        Raises:
            HealthCheckError: Если проверка не удалась
        """
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.OK,
                    message="Database connection successful",
                )
        except Exception as e:
            logger.error(
                f"Database health check failed",
                name=self.name,
                error=str(e),
            )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Database connection failed: {str(e)}",
            )


class RedisHealthChecker(HealthChecker):
    """Проверяет здоровье подключения к Redis."""

    def __init__(self, timeout: float = settings.HEALTH_CHECK_TIMEOUT):
        super().__init__(name="redis", timeout=timeout)

    async def check(self) -> HealthCheckResult:
        """
        Проверяет подключение к Redis.

        Returns:
            HealthCheckResult с статусом подключения к Redis

        Raises:
            HealthCheckError: Если проверка не удалась
        """
        redis_client: Optional[aioredis.Redis] = None
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.OK,
                message="Redis connection successful",
            )
        except Exception as e:
            logger.error(
                f"Redis health check failed",
                name=self.name,
                error=str(e),
            )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Redis connection failed: {str(e)}",
            )
        finally:
            if redis_client:
                await redis_client.close()


class OSRMHealthChecker(HealthChecker):
    """Проверяет здоровье подключения к OSRM сервису."""

    def __init__(self, timeout: float = settings.HEALTH_CHECK_TIMEOUT):
        super().__init__(name="osrm", timeout=timeout)

    async def check(self) -> HealthCheckResult:
        """
        Проверяет доступность OSRM сервиса.

        Returns:
            HealthCheckResult с статусом подключения к OSRM

        Raises:
            HealthCheckError: Если проверка не удалась
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # OSRM возвращает 200 на /status endpoint или информацию о версии
                response = await client.get(f"{settings.OSRM_URL}/status")
                response.raise_for_status()
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.OK,
                    message="OSRM service is available",
                )
        except Exception as e:
            logger.error(
                f"OSRM health check failed",
                name=self.name,
                error=str(e),
            )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"OSRM service is unavailable: {str(e)}",
            )


class PhotonHealthChecker(HealthChecker):
    """Проверяет здоровье подключения к Photon (геокодинг)."""

    def __init__(self, timeout: float = settings.HEALTH_CHECK_TIMEOUT):
        super().__init__(name="photon", timeout=timeout)

    async def check(self) -> HealthCheckResult:
        """
        Проверяет доступность Photon сервиса.

        Returns:
            HealthCheckResult с статусом подключения к Photon

        Raises:
            HealthCheckError: Если проверка не удалась
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Photon возвращает 400 на /api без параметров, но это нормально
                # Нам главное - проверить доступность endpoint
                response = await client.get(f"{settings.PHOTON_URL}/api", params={"q": "test"})
                # Принимаем любой статус - главное что сервис отвечает
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.OK,
                    message="Photon service is available",
                )
        except Exception as e:
            logger.error(
                f"Photon health check failed",
                name=self.name,
                error=str(e),
            )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Photon service is unavailable: {str(e)}",
            )


# Create health checkers for detailed check
_db_checker = DatabaseHealthChecker()
_redis_checker = RedisHealthChecker()
_osrm_checker = OSRMHealthChecker()
_photon_checker = PhotonHealthChecker()

# Create composite health checker for detailed check
_detailed_health_checker = CompositeHealthChecker(name="detailed")
_detailed_health_checker.add_async_checker(_db_checker)
_detailed_health_checker.add_async_checker(_redis_checker)
_detailed_health_checker.add_async_checker(_osrm_checker)
_detailed_health_checker.add_async_checker(_photon_checker)


@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check(response: Response) -> dict:
    """
    Performs a comprehensive health check on all external services and dependencies.
    Checks database, Redis, OSRM, and Photon connectivity.

    Returns:
        - 200: All external services are available
        - 503: One or more external services are unavailable

    Response:
        {
            "status": "ok" | "degraded" | "failed",
            "timestamp": <unix timestamp>,
            "checks": {
                "database": {"status": "ok", "message": "...", "response_time_ms": ...},
                "redis": {"status": "ok", "message": "...", "response_time_ms": ...},
                "osrm": {"status": "ok", "message": "...", "response_time_ms": ...},
                "photon": {"status": "ok", "message": "...", "response_time_ms": ...}
            }
        }
    """
    result = await _detailed_health_checker.check()

    # Determine HTTP status code based on health check result
    status_code = 200 if result.status == HealthStatus.OK else 503
    response.status_code = status_code

    response_body = {
        "status": result.status.value,
        "timestamp": result.timestamp,
        "checks": {
            check_name: {
                "status": check_result.status.value,
                "message": check_result.message,
                "response_time_ms": check_result.response_time_ms,
            }
            for check_name, check_result in result.details.get("checks", {}).items()
        },
    }

    # Log the detailed health check result
    logger.info(
        "detailed_health_check_completed",
        status=result.status.value,
        status_code=status_code,
        response_time_ms=result.response_time_ms,
    )

    return response_body
