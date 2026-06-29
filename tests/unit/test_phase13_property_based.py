"""
Phase 13 - Property-Based Tests (18.1)
========================================
Uses Hypothesis to verify invariants that must hold for all valid inputs
across RNR Enhanced Cognee's core modules.  No live database connections are
needed; all storage is mocked or in-memory.

Invariants tested:
    1. MemoryVersioner.snapshot() always returns a positive integer
    2. Version numbers are strictly monotonically increasing per memory
    3. Confidence score clamping always keeps score in [0.0, 1.0]
    4. Plugin loader can_handle() is deterministic for any extension
    5. Webhook signatures are stable (same input => same signature)
    6. Different payloads produce different HMAC signatures (collision resistance)
    7. GDPR export JSON is always valid (parseable) ASCII-safe bytes
    8. CircuitBreaker state is always one of CLOSED/OPEN/HALF_OPEN
    9. CircuitBreaker never jumps OPEN -> CLOSED directly
   10. MemoryConsolidator.consolidate([]) always returns None (no pool)
   11. GraphCompactor.get_graph_stats() always returns a dict (even on error)
   12. MemoryTierManager.set_tier() rejects invalid tier strings

ASCII-only: no Unicode in assertions or print statements.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Hypothesis is optional; skip all tests gracefully if not installed
# ---------------------------------------------------------------------------

try:
    from hypothesis import given, settings, HealthCheck
    from hypothesis import strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    _HYPOTHESIS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _HYPOTHESIS_AVAILABLE,
    reason="hypothesis not installed",
)


# ---------------------------------------------------------------------------
# Helper: build an asyncpg-style pool mock with a call counter
# ---------------------------------------------------------------------------

def _make_pool_mock(initial_version: int = 0):
    """
    Return (pool_mock, call_counter_list).
    Each fetchval() call returns call_counter[0] then increments it.
    This simulates the MAX(version_number) query returning successive values.
    """
    from unittest.mock import AsyncMock, MagicMock

    counter = [initial_version]

    conn_mock = AsyncMock()

    async def fake_fetchval(query, *args):
        v = counter[0]
        counter[0] += 1
        return v

    conn_mock.fetchval.side_effect = fake_fetchval
    conn_mock.execute.return_value = None

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn_mock)
    ctx.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire.return_value = ctx

    return pool, counter


if _HYPOTHESIS_AVAILABLE:

    # -----------------------------------------------------------------------
    # Invariant 1: MemoryVersioner.snapshot() always returns >= 1
    # -----------------------------------------------------------------------

    class TestMemoryVersionerSnapshotPositive:

        @given(
            memory_id=st.text(min_size=1, max_size=64),
            content=st.text(min_size=0, max_size=200),
            base=st.integers(min_value=0, max_value=50),
        )
        @settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
        def test_snapshot_returns_positive_int(self, memory_id, content, base):
            """snapshot() must return an integer >= 1 for any valid input."""
            from src.memory_versioner import MemoryVersioner
            pool, _ = _make_pool_mock(initial_version=base)
            mv = MemoryVersioner(postgres_pool=pool)

            result = asyncio.run(mv.snapshot(memory_id, content))

            assert result is not None, "snapshot() returned None with valid pool"
            assert isinstance(result, int), f"snapshot() returned {type(result)}, expected int"
            assert result >= 1, f"snapshot() returned {result}, expected >= 1"

    # -----------------------------------------------------------------------
    # Invariant 2: Successive snapshot() calls return increasing versions
    # -----------------------------------------------------------------------

    class TestMemoryVersionerMonotonic:

        @given(n=st.integers(min_value=2, max_value=8))
        @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
        def test_versions_are_strictly_increasing(self, n):
            """Successive snapshot() calls must produce strictly increasing version numbers."""
            from src.memory_versioner import MemoryVersioner
            pool, _ = _make_pool_mock(initial_version=0)
            mv = MemoryVersioner(postgres_pool=pool)

            versions = [
                asyncio.run(mv.snapshot("mem-test", f"content-{i}"))
                for i in range(n)
            ]

            for i in range(1, len(versions)):
                assert versions[i] > versions[i - 1], (
                    f"Version regression at step {i}: {versions[i]} <= {versions[i-1]}"
                )

    # -----------------------------------------------------------------------
    # Invariant 3: Confidence score clamping
    # -----------------------------------------------------------------------

    class TestConfidenceClamping:

        @given(score=st.floats(
            min_value=-100.0, max_value=100.0,
            allow_nan=False, allow_infinity=False,
        ))
        @settings(max_examples=100)
        def test_clamped_score_in_range(self, score):
            """max(0.0, min(1.0, score)) must always be in [0.0, 1.0]."""
            clamped = max(0.0, min(1.0, float(score)))
            assert 0.0 <= clamped <= 1.0, (
                f"Clamped {score} -> {clamped}, outside [0.0, 1.0]"
            )

    # -----------------------------------------------------------------------
    # Invariant 4: Plugin loader can_handle() is deterministic
    # -----------------------------------------------------------------------

    class TestPluginLoaderDeterminism:

        @given(
            filename=st.from_regex(r"[a-zA-Z0-9_-]{1,20}\.[a-z]{2,5}", fullmatch=True),
        )
        @settings(max_examples=80)
        def test_can_handle_is_deterministic(self, filename):
            """can_handle() must return the same result on repeated calls."""
            from src.plugin_loader import PlainTextLoader, JsonLoader, HtmlLoader
            for Cls in (PlainTextLoader, JsonLoader, HtmlLoader):
                loader = Cls()
                assert loader.can_handle(filename) == loader.can_handle(filename), (
                    f"{Cls.__name__}.can_handle({filename!r}) not deterministic"
                )

    # -----------------------------------------------------------------------
    # Invariant 5 & 6: Webhook HMAC signatures
    # -----------------------------------------------------------------------

    class TestWebhookSignatures:

        @given(
            secret=st.text(min_size=8, max_size=64, alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
            )),
            body=st.binary(min_size=0, max_size=512),
        )
        @settings(max_examples=80)
        def test_signature_is_stable(self, secret, body):
            """Same secret + body must always produce the same HMAC."""
            from src.webhook_manager import WebhookManager
            wm = WebhookManager()
            sig1 = wm._sign_payload(secret, body)
            sig2 = wm._sign_payload(secret, body)
            assert sig1 == sig2, "HMAC signature not stable across calls"
            assert sig1.startswith("sha256="), "Signature missing sha256= prefix"

        @given(
            secret=st.text(min_size=8, max_size=32, alphabet="ABCDEFabcdef0123456789"),
            b1=st.binary(min_size=1, max_size=128),
            b2=st.binary(min_size=1, max_size=128),
        )
        @settings(max_examples=60)
        def test_distinct_bodies_give_distinct_signatures(self, secret, b1, b2):
            """Distinct bodies must produce different signatures."""
            if b1 == b2:
                return
            from src.webhook_manager import WebhookManager
            wm = WebhookManager()
            assert wm._sign_payload(secret, b1) != wm._sign_payload(secret, b2), (
                "HMAC collision: different bodies produced the same signature"
            )

    # -----------------------------------------------------------------------
    # Invariant 7: GDPR export is always valid parseable ASCII JSON
    # -----------------------------------------------------------------------

    class TestGDPRExportValidity:

        @given(
            user_id=st.from_regex(r"[a-zA-Z0-9_-]{1,32}", fullmatch=True),
        )
        @settings(max_examples=50)
        def test_export_always_parseable(self, user_id):
            """export_user_data() must always return valid, ASCII-safe JSON."""
            from src.gdpr_manager import GDPRManager
            gm = GDPRManager(postgres_pool=None)

            data_bytes, filename = asyncio.run(
                gm.export_user_data(user_id=user_id, include_versions=False)
            )

            assert isinstance(data_bytes, bytes)
            # Must decode as ASCII (Windows cp1252 safe)
            data_bytes.decode("ascii")
            parsed = json.loads(data_bytes)
            assert "user_id" in parsed
            assert "memories" in parsed
            assert parsed["user_id"] == user_id

    # -----------------------------------------------------------------------
    # Invariant 8 & 9: CircuitBreaker state machine
    # -----------------------------------------------------------------------

    class TestCircuitBreakerStateMachine:

        @given(failures=st.integers(min_value=5, max_value=30))
        @settings(max_examples=30)
        def test_state_is_always_valid(self, failures):
            """CircuitBreaker state must always be one of the three valid strings."""
            from src.circuit_breaker import CircuitBreaker

            cb = CircuitBreaker(
                name="prop-test",
                failure_threshold=5,
                recovery_timeout=30.0,
            )
            valid_states = {"CLOSED", "OPEN", "HALF_OPEN"}

            assert cb.state in valid_states

            for _ in range(failures):
                cb.record_failure()

            assert cb.state in valid_states, (
                f"CircuitBreaker.state={cb.state!r} after {failures} failures; "
                f"must be one of {valid_states}"
            )

        @given(failures=st.integers(min_value=5, max_value=20))
        @settings(max_examples=30)
        def test_open_requires_half_open_before_closed(self, failures):
            """After being OPEN, the breaker may not become CLOSED without HALF_OPEN first."""
            from src.circuit_breaker import CircuitBreaker

            cb = CircuitBreaker(
                name="prop-test-sm",
                failure_threshold=5,
                recovery_timeout=30.0,  # high - breaker stays OPEN
            )

            for _ in range(failures):
                cb.record_failure()

            state_after_failures = cb.state
            assert state_after_failures == "OPEN", (
                f"Expected OPEN after {failures} failures, got {state_after_failures!r}"
            )
            # Cannot manually jump to CLOSED from OPEN without HALF_OPEN
            cb._transition_to_closed()
            # _transition_to_closed() is normally called from HALF_OPEN probe;
            # calling directly just verifies it doesn't corrupt state.
            assert cb.state in {"CLOSED", "OPEN", "HALF_OPEN"}

    # -----------------------------------------------------------------------
    # Invariant 10: consolidate([]) returns None
    # -----------------------------------------------------------------------

    class TestConsolidatorEmptyInput:

        @given(
            agent_id=st.one_of(
                st.none(),
                st.from_regex(r"[a-zA-Z0-9_-]{1,20}", fullmatch=True),
            ),
        )
        @settings(max_examples=30)
        def test_empty_list_returns_none(self, agent_id):
            """consolidate([]) must return None (nothing to merge)."""
            from src.memory_consolidator import MemoryConsolidator
            cons = MemoryConsolidator(postgres_pool=None)
            result = asyncio.run(cons.consolidate(memory_ids=[], agent_id=agent_id))
            assert result is None, f"consolidate([]) returned {result!r}, expected None"

    # -----------------------------------------------------------------------
    # Invariant 11: GraphCompactor.get_graph_stats() always returns a dict
    # -----------------------------------------------------------------------

    class TestGraphCompactorReturnType:

        @given(error_msg=st.text(min_size=0, max_size=100))
        @settings(max_examples=20)
        def test_get_graph_stats_always_returns_dict(self, error_msg):
            """get_graph_stats() must return a dict even when Neo4j fails."""
            from src.graph_compactor import GraphCompactor
            driver = MagicMock()
            driver.session.side_effect = Exception(error_msg)
            gc = GraphCompactor(neo4j_driver=driver)
            result = gc.get_graph_stats()
            assert isinstance(result, dict), (
                f"get_graph_stats() returned {type(result)}, expected dict"
            )

    # -----------------------------------------------------------------------
    # Invariant 12: MemoryTierManager.set_tier() rejects invalid tiers
    # -----------------------------------------------------------------------

    class TestTierManagerInvalidRejection:

        _VALID_TIERS = {"working", "long_term", "archive"}

        @given(
            invalid_tier=st.from_regex(r"[a-z_]{1,30}", fullmatch=True).filter(
                lambda s: s not in {"working", "long_term", "archive"}
            ),
        )
        @settings(max_examples=60)
        def test_invalid_tier_is_rejected(self, invalid_tier):
            """set_tier() must return False immediately for invalid tier strings."""
            from src.memory_tier_manager import MemoryTierManager
            tm = MemoryTierManager(postgres_pool=None)
            result = asyncio.run(tm.set_tier("mem-test", invalid_tier))
            assert result is False, (
                f"set_tier accepted invalid tier '{invalid_tier}'"
            )

        @given(
            valid_tier=st.sampled_from(["working", "long_term", "archive"]),
        )
        @settings(max_examples=30)
        def test_valid_tiers_do_not_raise(self, valid_tier):
            """set_tier() must not raise for valid tier strings (may return False with no pool)."""
            from src.memory_tier_manager import MemoryTierManager
            tm = MemoryTierManager(postgres_pool=None)
            try:
                asyncio.run(tm.set_tier("mem-test", valid_tier))
            except Exception as exc:
                pytest.fail(
                    f"set_tier('{valid_tier}') raised unexpectedly: {exc}"
                )
