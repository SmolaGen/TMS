import time
from typing import Optional

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


# Create health checkers
_db_checker = DatabaseHealthChecker()
_redis_checker = RedisHealthChecker()

# Create composite health checker
_health_checker = CompositeHealthChecker(name="application")
_health_checker.add_async_checker(_db_checker)
_health_checker.add_async_checker(_redis_checker)


@router.get("/health", tags=["Health"])
async def health_check(response: Response) -> dict:
    """
    Performs a comprehensive health check on the application.
    Checks database and Redis connectivity.

    Returns:
        - 200: Application is healthy with all dependencies available
        - 503: One or more critical dependencies are unavailable

    Response:
        {
            "status": "ok" | "degraded" | "failed",
            "timestamp": <unix timestamp>,
            "checks": {
                "database": {"status": "ok", "message": "..."},
                "redis": {"status": "ok", "message": "..."}
            }
        }
    """
    result = await _health_checker.check()

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

    # Log the health check result
    logger.info(
        "health_check_completed",
        status=result.status.value,
        status_code=status_code,
        response_time_ms=result.response_time_ms,
    )

    return response_body
