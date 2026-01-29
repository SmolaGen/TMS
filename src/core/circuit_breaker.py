import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, Any, Awaitable
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    """Состояния circuit breaker."""
    CLOSED = "closed"          # Работает нормально, запросы проходят
    OPEN = "open"              # Отказывает, запросы отклоняются
    HALF_OPEN = "half_open"    # Тестирует восстановление


class CircuitBreakerError(Exception):
    """Базовое исключение circuit breaker."""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Circuit breaker открыт, запрос отклонён."""
    pass


@dataclass
class CircuitBreakerMetrics:
    """Метрики circuit breaker."""
    total_calls: int = 0
    failed_calls: int = 0
    successful_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit breaker паттерн для защиты от каскадных отказов при обращении к внешним сервисам.

    Проходит через три состояния:
    - CLOSED: Нормальная работа, все запросы проходят
    - OPEN: Слишком много ошибок, запросы отклоняются сразу
    - HALF_OPEN: Тестирование восстановления сервиса

    При достижении порога ошибок (failure_threshold) переходит в OPEN.
    После истечения timeout переходит в HALF_OPEN для проверки восстановления.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60,
        success_threshold: int = 1,
        name: str = "circuit_breaker"
    ):
        """
        Инициализация circuit breaker.

        Args:
            failure_threshold: Количество ошибок, после которого открыть CB (по умолчанию 5)
            timeout: Время в секундах, после которого перейти из OPEN в HALF_OPEN (по умолчанию 60)
            success_threshold: Количество успешных запросов в HALF_OPEN для закрытия CB (по умолчанию 1)
            name: Имя circuit breaker для логирования
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name

        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._last_state_change_time = time.time()
        self._half_open_success_count = 0

    def is_open(self) -> bool:
        """Проверяет, открыт ли circuit breaker (отклоняет запросы)."""
        if self.state == CircuitBreakerState.OPEN:
            # Проверяем, истёк ли timeout для перехода в HALF_OPEN
            elapsed = time.time() - self._last_state_change_time
            if elapsed >= self.timeout:
                self._transition_to_half_open()
                return False
            return True
        return False

    def is_half_open(self) -> bool:
        """Проверяет, находится ли circuit breaker в режиме тестирования (HALF_OPEN)."""
        return self.state == CircuitBreakerState.HALF_OPEN

    def record_success(self) -> None:
        """Фиксирует успешный вызов."""
        self.metrics.successful_calls += 1
        self.metrics.total_calls += 1

        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Сбрасываем счётчик ошибок при нормальной работе
            if self.metrics.failed_calls > 0:
                logger.debug(
                    f"Circuit breaker {self.name} resetting failure count",
                    failed_calls=self.metrics.failed_calls,
                    state=self.state.value
                )
                self.metrics.failed_calls = 0

    def record_failure(self) -> None:
        """Фиксирует неудачный вызов."""
        self.metrics.failed_calls += 1
        self.metrics.total_calls += 1
        self.metrics.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker {self.name} recorded failure",
            failed_calls=self.metrics.failed_calls,
            threshold=self.failure_threshold,
            state=self.state.value
        )

        if self.state == CircuitBreakerState.CLOSED:
            if self.metrics.failed_calls >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # При ошибке в HALF_OPEN сразу возвращаемся в OPEN
            self._transition_to_open()

    def record_rejection(self) -> None:
        """Фиксирует отклонённый запрос (когда CB открыт)."""
        self.metrics.rejected_calls += 1
        self.metrics.total_calls += 1

        logger.debug(
            f"Circuit breaker {self.name} rejected request",
            rejected_calls=self.metrics.rejected_calls,
            state=self.state.value
        )

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Вызывает асинхронную функцию с защитой circuit breaker.

        Args:
            func: Асинхронная функция для вызова
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции

        Returns:
            Результат вызова функции

        Raises:
            CircuitBreakerOpenError: Если circuit breaker открыт
        """
        if self.is_open():
            self.record_rejection()
            logger.warning(
                f"Circuit breaker {self.name} is open, rejecting call",
                state=self.state.value,
                elapsed_since_open=time.time() - self._last_state_change_time
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is open"
            )

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def call_sync(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Вызывает синхронную функцию с защитой circuit breaker.

        Args:
            func: Синхронная функция для вызова
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции

        Returns:
            Результат вызова функции

        Raises:
            CircuitBreakerOpenError: Если circuit breaker открыт
        """
        if self.is_open():
            self.record_rejection()
            logger.warning(
                f"Circuit breaker {self.name} is open, rejecting call",
                state=self.state.value,
                elapsed_since_open=time.time() - self._last_state_change_time
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is open"
            )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def reset(self) -> None:
        """Сбрасывает circuit breaker в исходное состояние CLOSED."""
        logger.info(
            f"Circuit breaker {self.name} reset",
            previous_state=self.state.value,
            failed_calls=self.metrics.failed_calls
        )
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._half_open_success_count = 0
        self._last_state_change_time = time.time()

    def get_state(self) -> str:
        """Возвращает текущее состояние circuit breaker."""
        # Обновляем состояние перед возвращением (проверяем, не истёк ли timeout)
        if self.state == CircuitBreakerState.OPEN:
            elapsed = time.time() - self._last_state_change_time
            if elapsed >= self.timeout:
                self._transition_to_half_open()

        return self.state.value

    def get_metrics(self) -> dict:
        """Возвращает метрики circuit breaker."""
        return {
            "state": self.state.value,
            "name": self.name,
            "total_calls": self.metrics.total_calls,
            "failed_calls": self.metrics.failed_calls,
            "successful_calls": self.metrics.successful_calls,
            "rejected_calls": self.metrics.rejected_calls,
            "failure_rate": (
                self.metrics.failed_calls / self.metrics.total_calls
                if self.metrics.total_calls > 0
                else 0.0
            ),
            "last_failure_time": self.metrics.last_failure_time,
        }

    def _transition_to_open(self) -> None:
        """Переходит в состояние OPEN."""
        logger.error(
            f"Circuit breaker {self.name} transitioning to OPEN",
            previous_state=self.state.value,
            failed_calls=self.metrics.failed_calls,
            threshold=self.failure_threshold
        )
        self.state = CircuitBreakerState.OPEN
        self._last_state_change_time = time.time()
        self._half_open_success_count = 0

    def _transition_to_half_open(self) -> None:
        """Переходит в состояние HALF_OPEN."""
        logger.info(
            f"Circuit breaker {self.name} transitioning to HALF_OPEN",
            previous_state=self.state.value,
            elapsed_time=time.time() - self._last_state_change_time
        )
        self.state = CircuitBreakerState.HALF_OPEN
        self._last_state_change_time = time.time()
        self._half_open_success_count = 0

    def _transition_to_closed(self) -> None:
        """Переходит в состояние CLOSED."""
        logger.info(
            f"Circuit breaker {self.name} transitioning to CLOSED",
            previous_state=self.state.value,
            successful_calls_in_half_open=self._half_open_success_count
        )
        self.state = CircuitBreakerState.CLOSED
        self._last_state_change_time = time.time()
        self.metrics = CircuitBreakerMetrics()
        self._half_open_success_count = 0
