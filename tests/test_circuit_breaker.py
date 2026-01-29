"""
Unit tests for CircuitBreaker implementation.
Tests cover state transitions, metrics tracking, sync/async calls, and recovery behavior.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerError,
    CircuitBreakerMetrics,
)


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker with default settings."""
    return CircuitBreaker(
        failure_threshold=3,
        timeout=1.0,
        success_threshold=2,
        name="test_circuit_breaker"
    )


@pytest.fixture
def quick_circuit_breaker():
    """Create a circuit breaker with quick timeout for testing recovery."""
    return CircuitBreaker(
        failure_threshold=2,
        timeout=0.1,
        success_threshold=1,
        name="quick_cb"
    )


class TestCircuitBreakerInitialization:
    """Tests for circuit breaker initialization."""

    def test_default_state_is_closed(self, circuit_breaker):
        """Circuit breaker starts in CLOSED state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_default_parameters(self):
        """Default parameters are set correctly."""
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.timeout == 60
        assert cb.success_threshold == 1
        assert cb.name == "circuit_breaker"

    def test_custom_parameters(self, circuit_breaker):
        """Custom parameters are applied correctly."""
        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.timeout == 1.0
        assert circuit_breaker.success_threshold == 2
        assert circuit_breaker.name == "test_circuit_breaker"

    def test_initial_metrics(self, circuit_breaker):
        """Initial metrics are all zeros."""
        metrics = circuit_breaker.metrics
        assert metrics.total_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.rejected_calls == 0
        assert metrics.last_failure_time is None


class TestCircuitBreakerStateChecks:
    """Tests for state check methods."""

    def test_is_open_when_closed(self, circuit_breaker):
        """is_open() returns False when state is CLOSED."""
        assert circuit_breaker.is_open() is False

    def test_is_open_when_open(self, circuit_breaker):
        """is_open() returns True when state is OPEN."""
        circuit_breaker.state = CircuitBreakerState.OPEN
        circuit_breaker._last_state_change_time = time.time()
        assert circuit_breaker.is_open() is True

    def test_is_half_open_when_closed(self, circuit_breaker):
        """is_half_open() returns False when state is CLOSED."""
        assert circuit_breaker.is_half_open() is False

    def test_is_half_open_when_half_open(self, circuit_breaker):
        """is_half_open() returns True when state is HALF_OPEN."""
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        assert circuit_breaker.is_half_open() is True

    def test_get_state_returns_string(self, circuit_breaker):
        """get_state() returns state as string."""
        assert circuit_breaker.get_state() == "closed"

        circuit_breaker.state = CircuitBreakerState.OPEN
        circuit_breaker._last_state_change_time = time.time()
        assert circuit_breaker.get_state() == "open"


class TestCircuitBreakerMetricsRecording:
    """Tests for recording success, failure, and rejection."""

    def test_record_success_increments_counters(self, circuit_breaker):
        """record_success() increments success and total counters."""
        circuit_breaker.record_success()
        assert circuit_breaker.metrics.successful_calls == 1
        assert circuit_breaker.metrics.total_calls == 1
        assert circuit_breaker.metrics.failed_calls == 0

    def test_record_failure_increments_counters(self, circuit_breaker):
        """record_failure() increments failure and total counters."""
        circuit_breaker.record_failure()
        assert circuit_breaker.metrics.failed_calls == 1
        assert circuit_breaker.metrics.total_calls == 1
        assert circuit_breaker.metrics.last_failure_time is not None

    def test_record_rejection_increments_counters(self, circuit_breaker):
        """record_rejection() increments rejection and total counters."""
        circuit_breaker.record_rejection()
        assert circuit_breaker.metrics.rejected_calls == 1
        assert circuit_breaker.metrics.total_calls == 1

    def test_success_resets_failure_count_in_closed_state(self, circuit_breaker):
        """Successful calls reset failure count when in CLOSED state."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.metrics.failed_calls == 2

        circuit_breaker.record_success()
        assert circuit_breaker.metrics.failed_calls == 0

    def test_get_metrics_returns_dict(self, circuit_breaker):
        """get_metrics() returns comprehensive metrics dictionary."""
        circuit_breaker.record_success()
        circuit_breaker.record_failure()
        circuit_breaker.record_rejection()

        metrics = circuit_breaker.get_metrics()

        assert metrics["state"] == "closed"
        assert metrics["name"] == "test_circuit_breaker"
        assert metrics["total_calls"] == 3
        assert metrics["failed_calls"] == 1
        assert metrics["successful_calls"] == 1
        assert metrics["rejected_calls"] == 1
        assert "failure_rate" in metrics
        assert "last_failure_time" in metrics

    def test_failure_rate_calculation(self, circuit_breaker):
        """Failure rate is calculated correctly."""
        circuit_breaker.record_success()
        circuit_breaker.record_failure()

        metrics = circuit_breaker.get_metrics()
        # Note: success resets failure count, so this checks current metrics
        assert metrics["failure_rate"] == pytest.approx(0.5, rel=0.01)

    def test_failure_rate_zero_when_no_calls(self, circuit_breaker):
        """Failure rate is zero when there are no calls."""
        metrics = circuit_breaker.get_metrics()
        assert metrics["failure_rate"] == 0.0


class TestCircuitBreakerStateTransitions:
    """Tests for state transitions."""

    def test_transition_to_open_on_failure_threshold(self, circuit_breaker):
        """Transitions to OPEN when failure threshold is reached."""
        for _ in range(3):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_no_transition_below_failure_threshold(self, circuit_breaker):
        """Does not transition to OPEN below failure threshold."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_transition_to_half_open_after_timeout(self, quick_circuit_breaker):
        """Transitions to HALF_OPEN after timeout expires."""
        # Trigger OPEN state
        quick_circuit_breaker.record_failure()
        quick_circuit_breaker.record_failure()
        assert quick_circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Check state (is_open triggers transition check)
        assert quick_circuit_breaker.is_open() is False
        assert quick_circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_get_state_triggers_half_open_transition(self, quick_circuit_breaker):
        """get_state() triggers transition to HALF_OPEN after timeout."""
        quick_circuit_breaker.record_failure()
        quick_circuit_breaker.record_failure()

        time.sleep(0.15)

        state = quick_circuit_breaker.get_state()
        assert state == "half_open"

    def test_transition_to_closed_after_success_in_half_open(self, quick_circuit_breaker):
        """Transitions to CLOSED after success threshold in HALF_OPEN."""
        quick_circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        quick_circuit_breaker._half_open_success_count = 0

        quick_circuit_breaker.record_success()

        assert quick_circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_transition_to_open_on_failure_in_half_open(self, circuit_breaker):
        """Transitions back to OPEN on failure in HALF_OPEN state."""
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN

        circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_success_threshold_in_half_open(self):
        """Requires multiple successes if success_threshold > 1."""
        cb = CircuitBreaker(
            failure_threshold=2,
            timeout=0.1,
            success_threshold=3,
            name="multi_success_cb"
        )
        cb.state = CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerReset:
    """Tests for reset functionality."""

    def test_reset_returns_to_closed_state(self, circuit_breaker):
        """reset() returns circuit breaker to CLOSED state."""
        # Trigger OPEN state
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_reset_clears_metrics(self, circuit_breaker):
        """reset() clears all metrics."""
        circuit_breaker.record_failure()
        circuit_breaker.record_success()
        circuit_breaker.record_rejection()

        circuit_breaker.reset()

        assert circuit_breaker.metrics.total_calls == 0
        assert circuit_breaker.metrics.failed_calls == 0
        assert circuit_breaker.metrics.successful_calls == 0
        assert circuit_breaker.metrics.rejected_calls == 0

    def test_reset_clears_half_open_success_count(self, circuit_breaker):
        """reset() clears half-open success counter."""
        circuit_breaker._half_open_success_count = 5

        circuit_breaker.reset()

        assert circuit_breaker._half_open_success_count == 0


class TestCircuitBreakerAsyncCall:
    """Tests for async call method."""

    @pytest.mark.asyncio
    async def test_async_call_success(self, circuit_breaker):
        """Async call succeeds and records success."""
        async def success_func():
            return "result"

        result = await circuit_breaker.call(success_func)

        assert result == "result"
        assert circuit_breaker.metrics.successful_calls == 1

    @pytest.mark.asyncio
    async def test_async_call_with_args(self, circuit_breaker):
        """Async call passes arguments correctly."""
        async def add_func(a, b, multiplier=1):
            return (a + b) * multiplier

        result = await circuit_breaker.call(add_func, 2, 3, multiplier=10)

        assert result == 50

    @pytest.mark.asyncio
    async def test_async_call_failure_records_and_reraises(self, circuit_breaker):
        """Async call records failure and re-raises exception."""
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await circuit_breaker.call(failing_func)

        assert circuit_breaker.metrics.failed_calls == 1

    @pytest.mark.asyncio
    async def test_async_call_rejected_when_open(self, circuit_breaker):
        """Async call is rejected when circuit breaker is open."""
        # Trigger OPEN state
        for _ in range(3):
            circuit_breaker.record_failure()

        async def any_func():
            return "should not be called"

        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(any_func)

        assert circuit_breaker.metrics.rejected_calls == 1

    @pytest.mark.asyncio
    async def test_async_call_allowed_in_half_open(self, quick_circuit_breaker):
        """Async call is allowed in HALF_OPEN state."""
        quick_circuit_breaker.state = CircuitBreakerState.HALF_OPEN

        async def success_func():
            return "recovered"

        result = await quick_circuit_breaker.call(success_func)

        assert result == "recovered"
        assert quick_circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerSyncCall:
    """Tests for sync call method."""

    def test_sync_call_success(self, circuit_breaker):
        """Sync call succeeds and records success."""
        def success_func():
            return "result"

        result = circuit_breaker.call_sync(success_func)

        assert result == "result"
        assert circuit_breaker.metrics.successful_calls == 1

    def test_sync_call_with_args(self, circuit_breaker):
        """Sync call passes arguments correctly."""
        def multiply_func(a, b, offset=0):
            return a * b + offset

        result = circuit_breaker.call_sync(multiply_func, 3, 4, offset=2)

        assert result == 14

    def test_sync_call_failure_records_and_reraises(self, circuit_breaker):
        """Sync call records failure and re-raises exception."""
        def failing_func():
            raise RuntimeError("Sync error")

        with pytest.raises(RuntimeError, match="Sync error"):
            circuit_breaker.call_sync(failing_func)

        assert circuit_breaker.metrics.failed_calls == 1

    def test_sync_call_rejected_when_open(self, circuit_breaker):
        """Sync call is rejected when circuit breaker is open."""
        # Trigger OPEN state
        for _ in range(3):
            circuit_breaker.record_failure()

        def any_func():
            return "should not be called"

        with pytest.raises(CircuitBreakerOpenError):
            circuit_breaker.call_sync(any_func)

        assert circuit_breaker.metrics.rejected_calls == 1

    def test_sync_call_allowed_in_half_open(self, quick_circuit_breaker):
        """Sync call is allowed in HALF_OPEN state."""
        quick_circuit_breaker.state = CircuitBreakerState.HALF_OPEN

        def success_func():
            return "recovered"

        result = quick_circuit_breaker.call_sync(success_func)

        assert result == "recovered"
        assert quick_circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerRecoveryScenarios:
    """Tests for full recovery scenarios."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_closed_to_open_to_half_open_to_closed(self, quick_circuit_breaker):
        """Test complete lifecycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        # Start in CLOSED
        assert quick_circuit_breaker.state == CircuitBreakerState.CLOSED

        # Generate failures to trigger OPEN
        async def failing_func():
            raise Exception("Service unavailable")

        for _ in range(2):
            with pytest.raises(Exception):
                await quick_circuit_breaker.call(failing_func)

        assert quick_circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next call attempt should trigger HALF_OPEN
        async def success_func():
            return "OK"

        result = await quick_circuit_breaker.call(success_func)

        # Should now be CLOSED after successful call in HALF_OPEN
        assert result == "OK"
        assert quick_circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_returns_to_open(self, quick_circuit_breaker):
        """Failure in HALF_OPEN state returns to OPEN."""
        # Set up HALF_OPEN state
        quick_circuit_breaker.state = CircuitBreakerState.HALF_OPEN

        async def failing_func():
            raise Exception("Still failing")

        with pytest.raises(Exception):
            await quick_circuit_breaker.call(failing_func)

        assert quick_circuit_breaker.state == CircuitBreakerState.OPEN

    def test_intermittent_failures_dont_trigger_open(self, circuit_breaker):
        """Intermittent failures with successes don't trigger OPEN."""
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        circuit_breaker.record_success()  # Resets failure count

        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        # Still CLOSED because success reset the count
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_rejected_calls_dont_affect_state_transitions(self, circuit_breaker):
        """Rejected calls increment counter but don't affect state transitions."""
        # Trigger OPEN
        for _ in range(3):
            circuit_breaker.record_failure()

        # Record some rejections
        for _ in range(5):
            try:
                await circuit_breaker.call(AsyncMock())
            except CircuitBreakerOpenError:
                pass

        assert circuit_breaker.metrics.rejected_calls == 5
        # State should still be OPEN (not affected by rejections)
        assert circuit_breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerExceptions:
    """Tests for exception classes."""

    def test_circuit_breaker_error_base_class(self):
        """CircuitBreakerError is a base exception class."""
        error = CircuitBreakerError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_circuit_breaker_open_error_inheritance(self):
        """CircuitBreakerOpenError inherits from CircuitBreakerError."""
        error = CircuitBreakerOpenError("CB is open")
        assert isinstance(error, CircuitBreakerError)
        assert isinstance(error, Exception)
        assert str(error) == "CB is open"


class TestCircuitBreakerMetricsDataclass:
    """Tests for CircuitBreakerMetrics dataclass."""

    def test_default_values(self):
        """CircuitBreakerMetrics has correct default values."""
        metrics = CircuitBreakerMetrics()
        assert metrics.total_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.rejected_calls == 0
        assert metrics.last_failure_time is None

    def test_custom_values(self):
        """CircuitBreakerMetrics accepts custom values."""
        metrics = CircuitBreakerMetrics(
            total_calls=100,
            failed_calls=10,
            successful_calls=85,
            rejected_calls=5,
            last_failure_time=1234567890.0
        )
        assert metrics.total_calls == 100
        assert metrics.failed_calls == 10
        assert metrics.successful_calls == 85
        assert metrics.rejected_calls == 5
        assert metrics.last_failure_time == 1234567890.0


class TestCircuitBreakerTimingBehavior:
    """Tests for timing-related behavior."""

    def test_open_state_respects_timeout(self, quick_circuit_breaker):
        """Circuit breaker remains OPEN until timeout expires."""
        quick_circuit_breaker.record_failure()
        quick_circuit_breaker.record_failure()

        # Immediately after opening, should still be open
        assert quick_circuit_breaker.is_open() is True
        assert quick_circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait partial timeout
        time.sleep(0.05)
        assert quick_circuit_breaker.is_open() is True

        # Wait for full timeout
        time.sleep(0.1)
        assert quick_circuit_breaker.is_open() is False
        assert quick_circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_state_change_time_updated_on_transitions(self, quick_circuit_breaker):
        """_last_state_change_time is updated on state transitions."""
        initial_time = quick_circuit_breaker._last_state_change_time

        time.sleep(0.01)
        quick_circuit_breaker.record_failure()
        quick_circuit_breaker.record_failure()

        # Time should be updated after transition to OPEN
        assert quick_circuit_breaker._last_state_change_time > initial_time
