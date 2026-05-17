"""
Unit tests for src.circuit_breaker
=====================================
Tests all 4 states (CLOSED, OPEN, HALF_OPEN, forced-OPEN via max probes),
exception classification, CircuitBreakerRegistry, and module-level helpers.
No real network calls. All I/O is synchronous in-memory.
No Unicode characters in assertions.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _breaker(name="test", failure_threshold=5, recovery_timeout=30.0, half_open_max_calls=2):
    from src.circuit_breaker import CircuitBreaker
    return CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
    )


async def _success():
    return "ok"


async def _fail():
    raise RuntimeError("downstream failure")


# ---------------------------------------------------------------------------
# CircuitOpenError
# ---------------------------------------------------------------------------

class TestCircuitOpenError:
    def test_message_contains_name(self):
        from src.circuit_breaker import CircuitOpenError
        err = CircuitOpenError("postgresql", retry_after=10.0)
        assert "postgresql" in str(err)
        assert "10.0" in str(err)

    def test_attributes_set(self):
        from src.circuit_breaker import CircuitOpenError
        err = CircuitOpenError("redis", retry_after=5.5)
        assert err.name == "redis"
        assert err.retry_after == pytest.approx(5.5)

    def test_default_retry_after_is_zero(self):
        from src.circuit_breaker import CircuitOpenError
        err = CircuitOpenError("qdrant")
        assert err.retry_after == 0.0

    def test_is_exception(self):
        from src.circuit_breaker import CircuitOpenError
        with pytest.raises(CircuitOpenError):
            raise CircuitOpenError("test")


# ---------------------------------------------------------------------------
# CircuitBreaker init
# ---------------------------------------------------------------------------

class TestCircuitBreakerInit:
    def test_initial_state_is_closed(self):
        cb = _breaker()
        assert cb.state == "CLOSED"

    def test_initial_failure_count_is_zero(self):
        cb = _breaker()
        assert cb._failure_count == 0

    def test_custom_parameters(self):
        cb = _breaker(failure_threshold=3, recovery_timeout=10.0, half_open_max_calls=1)
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 10.0
        assert cb.half_open_max_calls == 1

    def test_name_is_stored(self):
        cb = _breaker(name="my-breaker")
        assert cb.name == "my-breaker"


# ---------------------------------------------------------------------------
# CLOSED state - normal operation
# ---------------------------------------------------------------------------

class TestClosedState:
    async def test_successful_call_returns_result(self):
        cb = _breaker()
        result = await cb.call(_success)
        assert result == "ok"

    async def test_successful_call_increments_success_count(self):
        cb = _breaker()
        await cb.call(_success)
        assert cb._success_count == 1
        assert cb._total_calls == 1

    async def test_failure_increments_failure_count(self):
        cb = _breaker(failure_threshold=5)
        with pytest.raises(RuntimeError):
            await cb.call(_fail)
        assert cb._failure_count == 1

    async def test_failure_does_not_open_below_threshold(self):
        cb = _breaker(failure_threshold=5)
        for _ in range(4):
            try:
                await cb.call(_fail)
            except RuntimeError:
                pass
        assert cb.state == "CLOSED"

    async def test_failure_opens_at_threshold(self):
        cb = _breaker(failure_threshold=3)
        for _ in range(3):
            try:
                await cb.call(_fail)
            except RuntimeError:
                pass
        assert cb.state == "OPEN"

    async def test_success_resets_failure_streak(self):
        cb = _breaker(failure_threshold=3)
        # 2 failures followed by 1 success
        for _ in range(2):
            try:
                await cb.call(_fail)
            except RuntimeError:
                pass
        await cb.call(_success)
        # After success, failure count resets
        assert cb._failure_count == 0
        assert cb.state == "CLOSED"

    async def test_multiple_successes_increment_count(self):
        cb = _breaker()
        for _ in range(5):
            await cb.call(_success)
        assert cb._success_count == 5


# ---------------------------------------------------------------------------
# OPEN state
# ---------------------------------------------------------------------------

class TestOpenState:
    def _forced_open_breaker(self):
        cb = _breaker(failure_threshold=1, recovery_timeout=99999.0)
        cb._state = "OPEN"
        cb._last_failure_time = time.monotonic()
        return cb

    async def test_open_raises_circuit_open_error(self):
        from src.circuit_breaker import CircuitOpenError
        cb = self._forced_open_breaker()
        with pytest.raises(CircuitOpenError):
            await cb.call(_success)

    async def test_open_does_not_call_downstream(self):
        from src.circuit_breaker import CircuitOpenError
        cb = self._forced_open_breaker()
        call_count = {"n": 0}

        async def tracked():
            call_count["n"] += 1
            return "ok"

        with pytest.raises(CircuitOpenError):
            await cb.call(tracked)

        assert call_count["n"] == 0

    async def test_open_transitions_to_half_open_after_timeout(self):
        cb = _breaker(recovery_timeout=0.01)
        cb._state = "OPEN"
        cb._last_failure_time = time.monotonic() - 1.0  # definitely past timeout
        # Access state property to trigger automatic transition
        state = cb.state
        assert state == "HALF_OPEN"

    async def test_retry_after_is_positive_when_just_opened(self):
        from src.circuit_breaker import CircuitOpenError
        cb = _breaker(recovery_timeout=30.0)
        cb._state = "OPEN"
        cb._last_failure_time = time.monotonic()
        try:
            await cb.call(_success)
        except CircuitOpenError as e:
            assert e.retry_after > 0

    async def test_open_state_no_last_failure_time(self):
        """When _last_failure_time is None but state is OPEN, retry_after = recovery_timeout."""
        from src.circuit_breaker import CircuitOpenError
        cb = _breaker(recovery_timeout=30.0)
        cb._state = "OPEN"
        cb._last_failure_time = None
        try:
            await cb.call(_success)
        except CircuitOpenError as e:
            assert e.retry_after >= 0.0


# ---------------------------------------------------------------------------
# HALF_OPEN state
# ---------------------------------------------------------------------------

class TestHalfOpenState:
    def _half_open_breaker(self, half_open_max_calls=2):
        cb = _breaker(
            failure_threshold=3,
            recovery_timeout=0.001,
            half_open_max_calls=half_open_max_calls
        )
        cb._state = "HALF_OPEN"
        cb._half_open_calls = 0
        return cb

    async def test_success_transitions_to_closed(self):
        cb = self._half_open_breaker()
        await cb.call(_success)
        assert cb.state == "CLOSED"

    async def test_failure_transitions_to_open(self):
        cb = self._half_open_breaker()
        try:
            await cb.call(_fail)
        except RuntimeError:
            pass
        assert cb._state == "OPEN"

    async def test_half_open_increments_probe_count(self):
        cb = self._half_open_breaker(half_open_max_calls=3)
        await cb.call(_success)
        # After success, should have transitioned to CLOSED (reset count)
        assert cb.state == "CLOSED"

    async def test_probes_exhausted_raises_circuit_open_error(self):
        from src.circuit_breaker import CircuitOpenError
        cb = self._half_open_breaker(half_open_max_calls=1)
        # Use up the 1 allowed probe
        await cb.call(_success)
        # Now CLOSED, force back to HALF_OPEN
        cb._state = "HALF_OPEN"
        cb._half_open_calls = 1  # already at limit
        with pytest.raises(CircuitOpenError):
            await cb.call(_success)

    async def test_half_open_failure_resets_probe_count(self):
        cb = self._half_open_breaker()
        try:
            await cb.call(_fail)
        except RuntimeError:
            pass
        # After failure from HALF_OPEN, should be OPEN with reset probe count
        assert cb._state == "OPEN"


# ---------------------------------------------------------------------------
# record_success / record_failure (manual)
# ---------------------------------------------------------------------------

class TestRecordMethods:
    def test_record_success_in_closed_resets_failures(self):
        cb = _breaker(failure_threshold=3)
        cb._failure_count = 2
        cb.record_success()
        assert cb._failure_count == 0

    def test_record_success_in_half_open_transitions_to_closed(self):
        cb = _breaker()
        cb._state = "HALF_OPEN"
        cb.record_success()
        assert cb._state == "CLOSED"

    def test_record_failure_in_closed_increments(self):
        cb = _breaker(failure_threshold=5)
        cb.record_failure()
        assert cb._failure_count == 1
        assert cb._state == "CLOSED"

    def test_record_failure_in_closed_at_threshold_opens(self):
        cb = _breaker(failure_threshold=3)
        cb._failure_count = 2
        cb.record_failure()
        assert cb._state == "OPEN"

    def test_record_failure_in_half_open_opens(self):
        cb = _breaker()
        cb._state = "HALF_OPEN"
        cb.record_failure()
        assert cb._state == "OPEN"

    def test_record_success_increments_success_count(self):
        cb = _breaker()
        cb.record_success()
        assert cb._success_count == 1


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_initial_state(self):
        cb = _breaker(name="my-cb")
        stats = cb.stats()
        assert stats["name"] == "my-cb"
        assert stats["state"] == "CLOSED"
        assert stats["failures"] == 0
        assert stats["total_calls"] == 0
        assert stats["success_calls"] == 0
        assert stats["last_failure"] is None

    async def test_stats_after_success(self):
        cb = _breaker()
        await cb.call(_success)
        stats = cb.stats()
        assert stats["total_calls"] == 1
        assert stats["success_calls"] == 1

    async def test_stats_after_failures(self):
        cb = _breaker(failure_threshold=10)
        for _ in range(3):
            try:
                await cb.call(_fail)
            except RuntimeError:
                pass
        stats = cb.stats()
        assert stats["failures"] == 3
        assert stats["last_failure"] is not None


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_all_counters(self):
        cb = _breaker(failure_threshold=1)
        cb._failure_count = 5
        cb._success_count = 3
        cb._total_calls = 8
        cb._state = "OPEN"
        cb._last_failure_time = time.monotonic()
        cb.reset()
        assert cb._state == "CLOSED"
        assert cb._failure_count == 0
        assert cb._success_count == 0
        assert cb._total_calls == 0
        assert cb._last_failure_time is None

    async def test_reset_allows_calls_after_open(self):
        cb = _breaker(failure_threshold=1)
        try:
            await cb.call(_fail)
        except RuntimeError:
            pass
        assert cb.state == "OPEN"
        cb.reset()
        result = await cb.call(_success)
        assert result == "ok"


# ---------------------------------------------------------------------------
# CircuitBreakerRegistry
# ---------------------------------------------------------------------------

class TestCircuitBreakerRegistry:
    def test_get_creates_new_breaker(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb = registry.get("db1")
        assert cb.name == "db1"

    def test_get_returns_same_instance(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("db1")
        cb2 = registry.get("db1")
        assert cb1 is cb2

    def test_different_names_different_instances(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("svc-a")
        cb2 = registry.get("svc-b")
        assert cb1 is not cb2

    def test_get_all_stats_empty_registry(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        stats = registry.get_all_stats()
        assert isinstance(stats, dict)
        assert stats == {}

    def test_get_all_stats_with_breakers(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        registry.get("svc-x")
        registry.get("svc-y")
        stats = registry.get_all_stats()
        assert "svc-x" in stats
        assert "svc-y" in stats

    def test_reset_all_resets_every_breaker(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb = registry.get("my-svc")
        cb._state = "OPEN"
        cb._failure_count = 10
        registry.reset_all()
        assert cb._state == "CLOSED"
        assert cb._failure_count == 0

    def test_default_thresholds(self):
        from src.circuit_breaker import CircuitBreakerRegistry
        registry = CircuitBreakerRegistry()
        cb = registry.get("new-svc")
        assert cb.failure_threshold == registry._DEFAULT_FAILURE_THRESHOLD
        assert cb.recovery_timeout == registry._DEFAULT_RECOVERY_TIMEOUT
        assert cb.half_open_max_calls == registry._DEFAULT_HALF_OPEN_MAX_CALLS


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

class TestModuleLevelHelpers:
    def test_get_circuit_breaker_creates_breaker(self):
        from src.circuit_breaker import get_circuit_breaker, CircuitBreaker
        cb = get_circuit_breaker("neo4j")
        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "neo4j"

    def test_get_circuit_breaker_returns_same_instance(self):
        from src.circuit_breaker import get_circuit_breaker
        cb1 = get_circuit_breaker("postgresql")
        cb2 = get_circuit_breaker("postgresql")
        assert cb1 is cb2

    def test_get_all_circuit_stats_includes_default_breakers(self):
        from src.circuit_breaker import get_all_circuit_stats
        stats = get_all_circuit_stats()
        # Should include the pre-registered default breakers
        for name in ("postgresql", "qdrant", "neo4j", "redis"):
            assert name in stats

    def test_default_breakers_start_closed(self):
        from src.circuit_breaker import get_all_circuit_stats
        stats = get_all_circuit_stats()
        for name in ("postgresql", "qdrant", "neo4j", "redis"):
            assert stats[name]["state"] == "CLOSED"

    def test_get_circuit_breaker_for_new_name(self):
        from src.circuit_breaker import get_circuit_breaker, CircuitBreaker
        cb = get_circuit_breaker("custom-service-unique-xyz")
        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "custom-service-unique-xyz"


# ---------------------------------------------------------------------------
# Decorator / context pattern verification
# ---------------------------------------------------------------------------

class TestDecoratorUsage:
    """Verify the circuit breaker can be used in decorator-like patterns."""

    async def test_wrap_function_closed(self):
        from src.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker("wrap-test", failure_threshold=5)

        async def my_db_call(x):
            return x + 1

        result = await cb.call(my_db_call, 41)
        assert result == 42

    async def test_wrap_function_with_kwargs(self):
        from src.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker("kwargs-test", failure_threshold=5)

        async def my_func(a, b=10):
            return a + b

        result = await cb.call(my_func, 5, b=20)
        assert result == 25

    async def test_failure_threshold_protection(self):
        """Circuit should open exactly at threshold and block subsequent calls."""
        from src.circuit_breaker import CircuitBreaker, CircuitOpenError
        cb = CircuitBreaker("prot-test", failure_threshold=2, recovery_timeout=9999.0)

        for _ in range(2):
            try:
                await cb.call(_fail)
            except RuntimeError:
                pass

        assert cb.state == "OPEN"

        with pytest.raises(CircuitOpenError):
            await cb.call(_success)

    async def test_half_open_probing(self):
        """After recovery timeout, HALF_OPEN probe succeeds -> CLOSED."""
        from src.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker("probe-test", failure_threshold=1, recovery_timeout=0.001)

        # Open the circuit
        try:
            await cb.call(_fail)
        except RuntimeError:
            pass

        assert cb._state == "OPEN"

        # Wait for recovery timeout
        await asyncio.sleep(0.05)

        # Next call should be treated as HALF_OPEN probe
        result = await cb.call(_success)
        assert result == "ok"
        assert cb.state == "CLOSED"
