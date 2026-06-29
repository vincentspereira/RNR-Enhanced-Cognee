"""
RNR Enhanced Cognee - Phase 9 Production Hardening: Circuit Breaker
================================================================
Implements the circuit-breaker pattern to protect downstream database
connections from cascading failures.

States
------
CLOSED    Normal operation.  All calls are forwarded to the downstream
          service.  Failures are counted.
OPEN      The failure threshold has been exceeded.  All calls immediately
          raise ``CircuitOpenError`` without touching the downstream service.
          After ``recovery_timeout`` seconds the breaker moves to HALF_OPEN.
HALF_OPEN The breaker is testing whether the downstream service has
          recovered.  A limited number of calls are forwarded.  A
          successful call transitions back to CLOSED; a failure
          transitions back to OPEN.

ASCII-only: no Unicode in string literals, comments, or log messages.

Author: RNR Enhanced Cognee Team
Version: 1.0.0 (Phase 9)
"""

import logging
import time
from typing import Any, Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel constants for state names
# ---------------------------------------------------------------------------

_STATE_CLOSED: str = "CLOSED"
_STATE_OPEN: str = "OPEN"
_STATE_HALF_OPEN: str = "HALF_OPEN"

# Default breaker names to pre-register at import time
_DEFAULT_BREAKER_NAMES = ("postgresql", "qdrant", "neo4j", "redis")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CircuitOpenError(Exception):
    """
    Raised when a call is rejected because the circuit breaker is OPEN.

    Attributes:
        name:       Name of the circuit breaker that rejected the call.
        retry_after: Approximate seconds until the breaker enters HALF_OPEN.
    """

    def __init__(self, name: str, retry_after: float = 0.0) -> None:
        self.name = name
        self.retry_after = retry_after
        message = (
            "Circuit breaker '{}' is OPEN. "
            "Retry after {:.1f}s.".format(name, retry_after)
        )
        super().__init__(message)


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """
    Single-service circuit breaker with configurable thresholds.

    Thread-safety note: This implementation is designed for use with
    asyncio.  Concurrent coroutines sharing one event loop are safe
    because Python's GIL protects the integer/float attribute updates.
    For multi-threaded use, add locking around state transitions.

    Example usage::

        from src.circuit_breaker import get_circuit_breaker

        pg_breaker = get_circuit_breaker("postgresql")

        async def fetch_data():
            return await pg_breaker.call(my_db_coroutine, arg1, key=val)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 2,
    ) -> None:
        """
        Initialise the circuit breaker.

        Args:
            name:                 Unique identifier for this breaker
                                  (used in logs and stats).
            failure_threshold:    Number of consecutive failures required
                                  to open the circuit.  Defaults to 5.
            recovery_timeout:     Seconds to wait in OPEN state before
                                  moving to HALF_OPEN.  Defaults to 30.0.
            half_open_max_calls:  Maximum calls forwarded while HALF_OPEN
                                  before forcing a CLOSED or OPEN decision.
                                  Defaults to 2.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # Internal state
        self._state: str = _STATE_CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._total_calls: int = 0
        self._half_open_calls: int = 0
        self._last_failure_time: Optional[float] = None

    # ------------------------------------------------------------------
    # State property
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """
        Current state string: "CLOSED", "OPEN", or "HALF_OPEN".

        Automatically transitions OPEN -> HALF_OPEN when the recovery
        timeout has elapsed.
        """
        if self._state == _STATE_OPEN:
            if (
                self._last_failure_time is not None
                and (time.monotonic() - self._last_failure_time) >= self.recovery_timeout
            ):
                self._transition_to_half_open()
        return self._state

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    def _transition_to_open(self) -> None:
        """Move the breaker to the OPEN state and log the event."""
        self._state = _STATE_OPEN
        self._last_failure_time = time.monotonic()
        logger.warning(
            "Circuit breaker '%s' OPENED after %d failures. "
            "Recovery check in %.1fs.",
            self.name,
            self._failure_count,
            self.recovery_timeout,
        )

    def _transition_to_half_open(self) -> None:
        """Move the breaker to the HALF_OPEN state and reset probe counter."""
        self._state = _STATE_HALF_OPEN
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker '%s' -> HALF_OPEN: probing downstream service.",
            self.name,
        )

    def _transition_to_closed(self) -> None:
        """Move the breaker to the CLOSED state and reset counters."""
        self._state = _STATE_CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker '%s' -> CLOSED: downstream service recovered.",
            self.name,
        )

    # ------------------------------------------------------------------
    # Public call interface
    # ------------------------------------------------------------------

    async def call(
        self,
        coro_fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute *coro_fn* if the circuit is CLOSED or HALF_OPEN.

        Records success or failure and drives state transitions.

        Args:
            coro_fn: An async callable (coroutine function) to execute.
            *args:   Positional arguments forwarded to *coro_fn*.
            **kwargs: Keyword arguments forwarded to *coro_fn*.

        Returns:
            The return value of *coro_fn*.

        Raises:
            CircuitOpenError: When the circuit is OPEN and the recovery
                              timeout has not yet elapsed.
            Exception:        Any exception raised by *coro_fn* is re-raised
                              after recording the failure.
        """
        current_state = self.state  # Triggers automatic OPEN->HALF_OPEN check

        if current_state == _STATE_OPEN:
            elapsed = (
                time.monotonic() - self._last_failure_time
                if self._last_failure_time is not None
                else self.recovery_timeout
            )
            retry_after = max(0.0, self.recovery_timeout - elapsed)
            raise CircuitOpenError(self.name, retry_after)

        if current_state == _STATE_HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                # All probe slots used; treat remaining as OPEN
                raise CircuitOpenError(self.name, 0.0)
            self._half_open_calls += 1

        self._total_calls += 1

        try:
            result = await coro_fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    # ------------------------------------------------------------------
    # Manual recording (useful for wrappers that catch exceptions early)
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        """
        Record a successful call outcome.

        Transitions HALF_OPEN -> CLOSED when called in HALF_OPEN state.
        """
        self._success_count += 1
        if self._state == _STATE_HALF_OPEN:
            self._transition_to_closed()
        elif self._state == _STATE_CLOSED:
            # Reset failure streak on any success
            self._failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed call outcome.

        Transitions CLOSED -> OPEN when the failure count reaches the
        threshold, or HALF_OPEN -> OPEN immediately on any failure.
        """
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == _STATE_HALF_OPEN:
            # Single failure while probing sends us straight back to OPEN
            self._transition_to_open()
        elif self._state == _STATE_CLOSED and self._failure_count >= self.failure_threshold:
            self._transition_to_open()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """
        Return a snapshot of the breaker's current metrics.

        Returns:
            Dict with keys:
            - name (str): Breaker name.
            - state (str): Current state string.
            - failures (int): Cumulative failure count.
            - total_calls (int): Total calls dispatched through the breaker.
            - success_calls (int): Total successful calls.
            - last_failure (float | None): Monotonic timestamp of last failure,
              or None if no failure has been recorded.
        """
        return {
            "name": self.name,
            "state": self.state,
            "failures": self._failure_count,
            "total_calls": self._total_calls,
            "success_calls": self._success_count,
            "last_failure": self._last_failure_time,
        }

    def reset(self) -> None:
        """
        Manually reset the breaker to CLOSED state and clear all counters.

        Intended for testing or operator-driven recovery.
        """
        self._state = _STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._half_open_calls = 0
        self._last_failure_time = None
        logger.info("Circuit breaker '%s' manually reset to CLOSED.", self.name)


# ---------------------------------------------------------------------------
# CircuitBreakerRegistry
# ---------------------------------------------------------------------------


class CircuitBreakerRegistry:
    """
    Central registry for named circuit breakers.

    Breakers are created on first access with project-wide defaults and
    reused on subsequent calls.  The registry is not thread-safe; it is
    designed for use within a single asyncio event loop.
    """

    _DEFAULT_FAILURE_THRESHOLD: int = 5
    _DEFAULT_RECOVERY_TIMEOUT: float = 30.0
    _DEFAULT_HALF_OPEN_MAX_CALLS: int = 2

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        """
        Get or create a named circuit breaker.

        If no breaker with *name* exists it is created with the project
        defaults.

        Args:
            name: Unique breaker identifier (e.g. "postgresql").

        Returns:
            The CircuitBreaker instance for *name*.
        """
        if name not in self._breakers:
            breaker = CircuitBreaker(
                name=name,
                failure_threshold=self._DEFAULT_FAILURE_THRESHOLD,
                recovery_timeout=self._DEFAULT_RECOVERY_TIMEOUT,
                half_open_max_calls=self._DEFAULT_HALF_OPEN_MAX_CALLS,
            )
            self._breakers[name] = breaker
            logger.debug("Circuit breaker registered: '%s'", name)
        return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Return stats snapshots for every registered breaker.

        Returns:
            Dict mapping breaker name -> stats dict (same shape as
            ``CircuitBreaker.stats()``).
        """
        return {name: breaker.stats() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """
        Reset every registered breaker to CLOSED state.

        Useful in test teardown to ensure a clean slate between test
        cases that share the module-level registry.
        """
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset to CLOSED.")


# ---------------------------------------------------------------------------
# Module-level singleton registry and pre-registered default breakers
# ---------------------------------------------------------------------------

_registry = CircuitBreakerRegistry()

# Pre-register breakers for the four RNR Enhanced Cognee databases so that
# callers get a ready-to-use breaker without an explicit registration step.
for _name in _DEFAULT_BREAKER_NAMES:
    _registry.get(_name)

logger.debug(
    "Default circuit breakers pre-registered: %s",
    ", ".join(_DEFAULT_BREAKER_NAMES),
)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Return the named circuit breaker from the module-level registry.

    Creates a new breaker with default settings if one does not exist.

    Args:
        name: Breaker identifier (e.g. "postgresql", "qdrant").

    Returns:
        CircuitBreaker instance.
    """
    return _registry.get(name)


def get_all_circuit_stats() -> Dict[str, Dict[str, Any]]:
    """
    Return stats for every breaker registered in the module-level registry.

    Returns:
        Dict mapping breaker name -> stats dict.
    """
    return _registry.get_all_stats()
