"""
Graceful Degradation Module

Provides fallback behaviors when external services are unavailable:
- Registration of fallback handlers for services
- Automatic fallback execution when primary service fails
- Caching of last known good values for degraded service responses
- Integration with circuit breaker pattern
"""
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import (
    Dict,
    Any,
    Optional,
    Callable,
    TypeVar,
    Generic,
    Awaitable,
    Union,
)
import structlog

from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class DegradationLevel(str, Enum):
    """Уровни деградации сервиса."""
    NONE = "none"          # Сервис работает нормально
    PARTIAL = "partial"    # Сервис работает с ограничениями (кэш/fallback)
    COMPLETE = "complete"  # Сервис недоступен, только fallback


class FallbackStrategy(str, Enum):
    """Стратегии fallback поведения."""
    CACHE = "cache"              # Использовать кэшированное значение
    DEFAULT = "default"          # Использовать значение по умолчанию
    ALTERNATIVE = "alternative"  # Использовать альтернативный сервис
    NONE = "none"                # Нет fallback, вернуть ошибку


@dataclass
class DegradationState:
    """Состояние деградации сервиса."""
    service_name: str
    level: DegradationLevel = DegradationLevel.NONE
    reason: str = ""
    since: float = field(default_factory=time.time)
    fallback_used: int = 0
    last_success: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует состояние в словарь."""
        return {
            "service_name": self.service_name,
            "level": self.level.value,
            "reason": self.reason,
            "since": self.since,
            "fallback_used": self.fallback_used,
            "last_success": self.last_success,
            "duration_seconds": time.time() - self.since if self.level != DegradationLevel.NONE else 0,
        }


@dataclass
class FallbackConfig:
    """Конфигурация fallback для сервиса."""
    service_name: str
    strategy: FallbackStrategy
    default_value: Any = None
    alternative_handler: Optional[Callable[..., Any]] = None
    cache_ttl: int = 3600  # TTL кэша в секундах
    max_cache_size: int = 1000


class FallbackCache(Generic[T]):
    """
    Кэш для хранения последних успешных значений.

    Используется для graceful degradation - возвращает кэшированные
    значения когда основной сервис недоступен.
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Инициализация кэша fallback значений.

        Args:
            ttl_seconds: Время жизни кэша в секундах (по умолчанию 1 час)
            max_size: Максимальный размер кэша
        """
        self._cache: Dict[str, tuple[float, T]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, service: str, **kwargs) -> str:
        """Генерирует ключ кэша из параметров."""
        key_data = f"{service}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, service: str, allow_expired: bool = False, **kwargs) -> Optional[T]:
        """
        Получает значение из кэша.

        Args:
            service: Имя сервиса
            allow_expired: Разрешить возврат устаревших значений (для degradation)
            **kwargs: Параметры для ключа кэша

        Returns:
            Кэшированное значение или None
        """
        key = self._make_key(service, **kwargs)
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(
                    "Fallback cache hit",
                    service=service,
                    cache_key=key[:8],
                    fresh=True
                )
                return value
            elif allow_expired:
                logger.debug(
                    "Fallback cache hit (expired but allowed)",
                    service=service,
                    cache_key=key[:8],
                    fresh=False,
                    age_seconds=time.time() - timestamp
                )
                return value
            else:
                # Истёк срок - удаляем
                del self._cache[key]
        return None

    def set(self, service: str, value: T, **kwargs) -> None:
        """
        Сохраняет значение в кэш.

        Args:
            service: Имя сервиса
            value: Значение для кэширования
            **kwargs: Параметры для ключа кэша
        """
        # Очистка при превышении размера
        if len(self._cache) >= self._max_size:
            self._cleanup_expired()
            if len(self._cache) >= self._max_size:
                # Удаляем самые старые записи
                sorted_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][0]
                )
                for key in sorted_keys[:self._max_size // 4]:
                    del self._cache[key]

        key = self._make_key(service, **kwargs)
        self._cache[key] = (time.time(), value)
        logger.debug(
            "Fallback cache set",
            service=service,
            cache_key=key[:8]
        )

    def _cleanup_expired(self) -> None:
        """Удаляет истекшие записи."""
        now = time.time()
        expired_keys = [
            key for key, (ts, _) in self._cache.items()
            if now - ts >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    def clear(self, service: Optional[str] = None) -> None:
        """
        Очищает кэш.

        Args:
            service: Очистить только для конкретного сервиса (если указан)
        """
        if service is None:
            self._cache.clear()
        else:
            prefix = f"{service}:"
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(hashlib.md5(prefix.encode()).hexdigest()[:8])
            ]
            for key in keys_to_delete:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
        }


class GracefulDegradationManager:
    """
    Менеджер graceful degradation для управления fallback поведением.

    Особенности:
    - Регистрация fallback конфигураций для сервисов
    - Автоматическое переключение на fallback при отказе сервиса
    - Интеграция с circuit breaker
    - Кэширование последних успешных значений
    - Мониторинг состояния деградации
    """

    def __init__(
        self,
        cache_ttl: int = 3600,
        cache_size: int = 1000
    ):
        """
        Инициализация менеджера graceful degradation.

        Args:
            cache_ttl: TTL кэша в секундах (по умолчанию 1 час)
            cache_size: Максимальный размер кэша (по умолчанию 1000 записей)
        """
        self._configs: Dict[str, FallbackConfig] = {}
        self._states: Dict[str, DegradationState] = {}
        self._cache: FallbackCache[Any] = FallbackCache(
            ttl_seconds=cache_ttl,
            max_size=cache_size
        )
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        logger.info(
            "GracefulDegradationManager initialized",
            cache_ttl=cache_ttl,
            cache_size=cache_size
        )

    def register_service(
        self,
        service_name: str,
        strategy: FallbackStrategy = FallbackStrategy.CACHE,
        default_value: Any = None,
        alternative_handler: Optional[Callable[..., Any]] = None,
        cache_ttl: Optional[int] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ) -> None:
        """
        Регистрирует сервис для graceful degradation.

        Args:
            service_name: Имя сервиса
            strategy: Стратегия fallback (по умолчанию CACHE)
            default_value: Значение по умолчанию для стратегии DEFAULT
            alternative_handler: Альтернативный обработчик для стратегии ALTERNATIVE
            cache_ttl: TTL кэша для этого сервиса
            circuit_breaker: Circuit breaker для интеграции
        """
        self._configs[service_name] = FallbackConfig(
            service_name=service_name,
            strategy=strategy,
            default_value=default_value,
            alternative_handler=alternative_handler,
            cache_ttl=cache_ttl or self._cache._ttl,
        )

        self._states[service_name] = DegradationState(
            service_name=service_name
        )

        if circuit_breaker:
            self._circuit_breakers[service_name] = circuit_breaker

        logger.info(
            "Service registered for graceful degradation",
            service_name=service_name,
            strategy=strategy.value,
            has_circuit_breaker=circuit_breaker is not None
        )

    def get_state(self, service_name: str) -> Optional[DegradationState]:
        """
        Получает состояние деградации сервиса.

        Args:
            service_name: Имя сервиса

        Returns:
            DegradationState или None если сервис не зарегистрирован
        """
        return self._states.get(service_name)

    def get_all_states(self) -> Dict[str, DegradationState]:
        """Возвращает состояния всех зарегистрированных сервисов."""
        return self._states.copy()

    def is_degraded(self, service_name: str) -> bool:
        """
        Проверяет, находится ли сервис в состоянии деградации.

        Args:
            service_name: Имя сервиса

        Returns:
            True если сервис деградирован
        """
        state = self._states.get(service_name)
        return state is not None and state.level != DegradationLevel.NONE

    def record_success(
        self,
        service_name: str,
        value: Any = None,
        **cache_kwargs
    ) -> None:
        """
        Фиксирует успешный вызов сервиса.

        Args:
            service_name: Имя сервиса
            value: Значение для кэширования
            **cache_kwargs: Дополнительные параметры для ключа кэша
        """
        state = self._states.get(service_name)
        if state:
            if state.level != DegradationLevel.NONE:
                logger.info(
                    "Service recovered from degradation",
                    service_name=service_name,
                    previous_level=state.level.value,
                    degradation_duration=time.time() - state.since
                )
            state.level = DegradationLevel.NONE
            state.reason = ""
            state.last_success = time.time()

        # Кэшируем успешное значение
        if value is not None:
            self._cache.set(service_name, value, **cache_kwargs)

    def record_failure(
        self,
        service_name: str,
        reason: str = "",
        level: DegradationLevel = DegradationLevel.COMPLETE
    ) -> None:
        """
        Фиксирует отказ сервиса.

        Args:
            service_name: Имя сервиса
            reason: Причина отказа
            level: Уровень деградации
        """
        state = self._states.get(service_name)
        if state:
            if state.level == DegradationLevel.NONE:
                state.since = time.time()
                logger.warning(
                    "Service entering degradation",
                    service_name=service_name,
                    level=level.value,
                    reason=reason
                )
            state.level = level
            state.reason = reason

    def get_fallback(
        self,
        service_name: str,
        **cache_kwargs
    ) -> tuple[Any, bool]:
        """
        Получает fallback значение для сервиса.

        Args:
            service_name: Имя сервиса
            **cache_kwargs: Параметры для ключа кэша

        Returns:
            Кортеж (значение, успех). Успех=True если fallback найден.
        """
        config = self._configs.get(service_name)
        if not config:
            logger.warning(
                "No fallback config for service",
                service_name=service_name
            )
            return None, False

        state = self._states.get(service_name)
        if state:
            state.fallback_used += 1

        if config.strategy == FallbackStrategy.CACHE:
            cached = self._cache.get(
                service_name,
                allow_expired=True,
                **cache_kwargs
            )
            if cached is not None:
                logger.info(
                    "Using cached fallback value",
                    service_name=service_name,
                )
                return cached, True
            logger.warning(
                "No cached value available for fallback",
                service_name=service_name
            )
            return None, False

        elif config.strategy == FallbackStrategy.DEFAULT:
            logger.info(
                "Using default fallback value",
                service_name=service_name
            )
            return config.default_value, True

        elif config.strategy == FallbackStrategy.ALTERNATIVE:
            if config.alternative_handler:
                try:
                    result = config.alternative_handler(**cache_kwargs)
                    logger.info(
                        "Using alternative handler fallback",
                        service_name=service_name
                    )
                    return result, True
                except Exception as e:
                    logger.error(
                        "Alternative handler failed",
                        service_name=service_name,
                        error=str(e)
                    )
                    return None, False
            logger.warning(
                "No alternative handler configured",
                service_name=service_name
            )
            return None, False

        # FallbackStrategy.NONE
        return None, False

    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable[..., Awaitable[T]],
        cache_key_params: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> tuple[T, bool]:
        """
        Выполняет функцию с автоматическим fallback при ошибке.

        Args:
            service_name: Имя сервиса
            primary_func: Основная асинхронная функция
            cache_key_params: Параметры для ключа кэша
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции

        Returns:
            Кортеж (результат, is_primary). is_primary=True если результат от основной функции.
        """
        cache_kwargs = cache_key_params or {}

        # Проверяем circuit breaker если есть
        cb = self._circuit_breakers.get(service_name)
        if cb and cb.is_open():
            logger.warning(
                "Circuit breaker is open, using fallback",
                service_name=service_name,
                circuit_breaker_state=cb.get_state()
            )
            self.record_failure(
                service_name,
                reason="Circuit breaker open",
                level=DegradationLevel.COMPLETE
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise CircuitBreakerOpenError(
                f"Circuit breaker {service_name} is open and no fallback available"
            )

        try:
            result = await primary_func(*args, **kwargs)
            self.record_success(service_name, result, **cache_kwargs)
            return result, True

        except CircuitBreakerOpenError:
            self.record_failure(
                service_name,
                reason="Circuit breaker open",
                level=DegradationLevel.COMPLETE
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise

        except Exception as e:
            logger.warning(
                "Primary function failed, attempting fallback",
                service_name=service_name,
                error=str(e),
                error_type=type(e).__name__
            )
            self.record_failure(
                service_name,
                reason=str(e),
                level=DegradationLevel.PARTIAL
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise

    def execute_with_fallback_sync(
        self,
        service_name: str,
        primary_func: Callable[..., T],
        cache_key_params: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> tuple[T, bool]:
        """
        Синхронно выполняет функцию с автоматическим fallback при ошибке.

        Args:
            service_name: Имя сервиса
            primary_func: Основная синхронная функция
            cache_key_params: Параметры для ключа кэша
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции

        Returns:
            Кортеж (результат, is_primary). is_primary=True если результат от основной функции.
        """
        cache_kwargs = cache_key_params or {}

        # Проверяем circuit breaker если есть
        cb = self._circuit_breakers.get(service_name)
        if cb and cb.is_open():
            logger.warning(
                "Circuit breaker is open, using fallback",
                service_name=service_name,
                circuit_breaker_state=cb.get_state()
            )
            self.record_failure(
                service_name,
                reason="Circuit breaker open",
                level=DegradationLevel.COMPLETE
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise CircuitBreakerOpenError(
                f"Circuit breaker {service_name} is open and no fallback available"
            )

        try:
            result = primary_func(*args, **kwargs)
            self.record_success(service_name, result, **cache_kwargs)
            return result, True

        except CircuitBreakerOpenError:
            self.record_failure(
                service_name,
                reason="Circuit breaker open",
                level=DegradationLevel.COMPLETE
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise

        except Exception as e:
            logger.warning(
                "Primary function failed, attempting fallback",
                service_name=service_name,
                error=str(e),
                error_type=type(e).__name__
            )
            self.record_failure(
                service_name,
                reason=str(e),
                level=DegradationLevel.PARTIAL
            )
            fallback, success = self.get_fallback(service_name, **cache_kwargs)
            if success:
                return fallback, False
            raise

    def cache_value(
        self,
        service_name: str,
        value: Any,
        **cache_kwargs
    ) -> None:
        """
        Кэширует значение для использования в качестве fallback.

        Args:
            service_name: Имя сервиса
            value: Значение для кэширования
            **cache_kwargs: Параметры для ключа кэша
        """
        self._cache.set(service_name, value, **cache_kwargs)

    def get_cached_value(
        self,
        service_name: str,
        allow_expired: bool = True,
        **cache_kwargs
    ) -> Optional[Any]:
        """
        Получает кэшированное значение.

        Args:
            service_name: Имя сервиса
            allow_expired: Разрешить возврат устаревших значений
            **cache_kwargs: Параметры для ключа кэша

        Returns:
            Кэшированное значение или None
        """
        return self._cache.get(service_name, allow_expired=allow_expired, **cache_kwargs)

    def clear_cache(self, service_name: Optional[str] = None) -> None:
        """
        Очищает кэш.

        Args:
            service_name: Очистить только для конкретного сервиса (если указан)
        """
        self._cache.clear(service_name)
        logger.info(
            "Fallback cache cleared",
            service_name=service_name or "all"
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        return self._cache.get_stats()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики graceful degradation.

        Returns:
            Словарь с метриками
        """
        degraded_services = [
            name for name, state in self._states.items()
            if state.level != DegradationLevel.NONE
        ]

        total_fallbacks = sum(
            state.fallback_used for state in self._states.values()
        )

        return {
            "registered_services": list(self._configs.keys()),
            "degraded_services": degraded_services,
            "degraded_count": len(degraded_services),
            "total_fallbacks_used": total_fallbacks,
            "cache_stats": self.get_cache_stats(),
            "states": {
                name: state.to_dict()
                for name, state in self._states.items()
            },
        }

    def reset_service(self, service_name: str) -> None:
        """
        Сбрасывает состояние сервиса.

        Args:
            service_name: Имя сервиса
        """
        if service_name in self._states:
            self._states[service_name] = DegradationState(
                service_name=service_name
            )
            logger.info(
                "Service state reset",
                service_name=service_name
            )

    def reset_all(self) -> None:
        """Сбрасывает состояние всех сервисов."""
        for service_name in self._states:
            self._states[service_name] = DegradationState(
                service_name=service_name
            )
        logger.info("All service states reset")
