import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Awaitable, Callable, TypeVar
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class HealthStatus(str, Enum):
    """Статусы здоровья компонента."""
    OK = "ok"              # Компонент работает нормально
    DEGRADED = "degraded"  # Компонент работает, но с проблемами
    FAILED = "failed"      # Компонент не работает


class HealthCheckError(Exception):
    """Базовое исключение для health check."""
    pass


@dataclass
class HealthCheckResult:
    """Результат проверки здоровья компонента."""
    name: str
    status: HealthStatus
    message: str = "OK"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    response_time_ms: float = 0.0

    def to_dict(self) -> dict:
        """Преобразует результат в словарь."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "response_time_ms": self.response_time_ms,
        }

    def is_healthy(self) -> bool:
        """Проверяет, здоров ли компонент."""
        return self.status == HealthStatus.OK

    def is_failed(self) -> bool:
        """Проверяет, потерпел ли отказ компонент."""
        return self.status == HealthStatus.FAILED


class HealthChecker(ABC):
    """
    Абстрактный базовый класс для проверки здоровья компонентов.

    Подклассы должны реализовать метод `check()` для специфичной логики
    проверки здоровья конкретного компонента.
    """

    def __init__(self, name: str, timeout: float = 5.0):
        """
        Инициализация health checker.

        Args:
            name: Имя компонента для проверки
            timeout: Таймаут для проверки в секундах (по умолчанию 5.0)
        """
        self.name = name
        self.timeout = timeout
        self.last_result: Optional[HealthCheckResult] = None

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """
        Выполняет проверку здоровья компонента.

        Returns:
            HealthCheckResult с результатом проверки

        Raises:
            HealthCheckError: Если при проверке произошла ошибка
        """
        pass

    async def perform_check(self) -> HealthCheckResult:
        """
        Выполняет проверку с мерой времени и логированием.

        Returns:
            HealthCheckResult с результатом проверки
        """
        start_time = time.time()
        try:
            result = await self.check()
            response_time = (time.time() - start_time) * 1000

            result.response_time_ms = response_time

            logger.debug(
                f"Health check {self.name} completed",
                name=self.name,
                status=result.status.value,
                response_time_ms=response_time,
            )

            self.last_result = result
            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(
                f"Health check {self.name} failed",
                name=self.name,
                error=str(e),
                response_time_ms=response_time,
            )

            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
            )
            self.last_result = result
            return result


class SyncHealthChecker(ABC):
    """
    Абстрактный базовый класс для синхронной проверки здоровья компонентов.

    Подклассы должны реализовать метод `check()` для специфичной логики
    проверки здоровья конкретного компонента.
    """

    def __init__(self, name: str, timeout: float = 5.0):
        """
        Инициализация sync health checker.

        Args:
            name: Имя компонента для проверки
            timeout: Таймаут для проверки в секундах (по умолчанию 5.0)
        """
        self.name = name
        self.timeout = timeout
        self.last_result: Optional[HealthCheckResult] = None

    @abstractmethod
    def check(self) -> HealthCheckResult:
        """
        Выполняет проверку здоровья компонента (синхронно).

        Returns:
            HealthCheckResult с результатом проверки

        Raises:
            HealthCheckError: Если при проверке произошла ошибка
        """
        pass

    def perform_check(self) -> HealthCheckResult:
        """
        Выполняет проверку с мерой времени и логированием.

        Returns:
            HealthCheckResult с результатом проверки
        """
        start_time = time.time()
        try:
            result = self.check()
            response_time = (time.time() - start_time) * 1000

            result.response_time_ms = response_time

            logger.debug(
                f"Health check {self.name} completed",
                name=self.name,
                status=result.status.value,
                response_time_ms=response_time,
            )

            self.last_result = result
            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(
                f"Health check {self.name} failed",
                name=self.name,
                error=str(e),
                response_time_ms=response_time,
            )

            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
            )
            self.last_result = result
            return result


class CompositeHealthChecker:
    """
    Композитный health checker, объединяющий результаты нескольких checkers.

    Определяет общий статус на основе статусов компонентов:
    - OK: все компоненты OK
    - DEGRADED: некоторые компоненты DEGRADED
    - FAILED: один или несколько компонентов FAILED
    """

    def __init__(self, name: str = "composite_health"):
        """
        Инициализация composite health checker.

        Args:
            name: Имя для композитной проверки
        """
        self.name = name
        self.checkers: Dict[str, HealthChecker] = {}
        self.sync_checkers: Dict[str, SyncHealthChecker] = {}

    def add_async_checker(self, checker: HealthChecker) -> None:
        """
        Добавляет асинхронный health checker.

        Args:
            checker: HealthChecker для добавления
        """
        self.checkers[checker.name] = checker

    def add_sync_checker(self, checker: SyncHealthChecker) -> None:
        """
        Добавляет синхронный health checker.

        Args:
            checker: SyncHealthChecker для добавления
        """
        self.sync_checkers[checker.name] = checker

    async def check(self) -> HealthCheckResult:
        """
        Выполняет все асинхронные проверки здоровья.

        Returns:
            Композитный HealthCheckResult с общим статусом
        """
        results = {}

        # Выполняем все асинхронные проверки
        for name, checker in self.checkers.items():
            try:
                results[name] = await checker.perform_check()
            except Exception as e:
                logger.error(
                    f"Async health check {name} failed with exception",
                    name=name,
                    error=str(e),
                )
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.FAILED,
                    message=f"Health check failed: {str(e)}",
                )

        # Выполняем все синхронные проверки
        for name, checker in self.sync_checkers.items():
            try:
                results[name] = checker.perform_check()
            except Exception as e:
                logger.error(
                    f"Sync health check {name} failed with exception",
                    name=name,
                    error=str(e),
                )
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.FAILED,
                    message=f"Health check failed: {str(e)}",
                )

        # Определяем общий статус
        overall_status = self._determine_overall_status(results)

        return HealthCheckResult(
            name=self.name,
            status=overall_status,
            message=self._get_status_message(results),
            details={"checks": {k: v.to_dict() for k, v in results.items()}},
        )

    def check_sync(self) -> HealthCheckResult:
        """
        Выполняет все синхронные проверки здоровья.

        Returns:
            Композитный HealthCheckResult с общим статусом
        """
        results = {}

        # Выполняем все синхронные проверки
        for name, checker in self.sync_checkers.items():
            try:
                results[name] = checker.perform_check()
            except Exception as e:
                logger.error(
                    f"Sync health check {name} failed with exception",
                    name=name,
                    error=str(e),
                )
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.FAILED,
                    message=f"Health check failed: {str(e)}",
                )

        # Определяем общий статус
        overall_status = self._determine_overall_status(results)

        return HealthCheckResult(
            name=self.name,
            status=overall_status,
            message=self._get_status_message(results),
            details={"checks": {k: v.to_dict() for k, v in results.items()}},
        )

    def _determine_overall_status(
        self, results: Dict[str, HealthCheckResult]
    ) -> HealthStatus:
        """
        Определяет общий статус на основе статусов компонентов.

        Args:
            results: Словарь результатов проверок

        Returns:
            Общий HealthStatus
        """
        if not results:
            return HealthStatus.OK

        # Если есть хотя бы один FAILED, общий статус FAILED
        if any(r.status == HealthStatus.FAILED for r in results.values()):
            return HealthStatus.FAILED

        # Если есть хотя бы один DEGRADED, общий статус DEGRADED
        if any(r.status == HealthStatus.DEGRADED for r in results.values()):
            return HealthStatus.DEGRADED

        # Если все OK, общий статус OK
        return HealthStatus.OK

    def _get_status_message(self, results: Dict[str, HealthCheckResult]) -> str:
        """
        Получает сообщение о статусе на основе результатов.

        Args:
            results: Словарь результатов проверок

        Returns:
            Сообщение о статусе
        """
        failed = [k for k, v in results.items() if v.status == HealthStatus.FAILED]
        degraded = [k for k, v in results.items() if v.status == HealthStatus.DEGRADED]

        if failed:
            return f"Failed checks: {', '.join(failed)}"
        elif degraded:
            return f"Degraded checks: {', '.join(degraded)}"
        else:
            return "All checks passed"
