"""Tests for src/mcp_security.py (PR 13).

Covers:
  - require_api_key: off by default, on with env var, rejects wrong key
  - check_rate_limit: disabled by default, token-bucket refill, per-agent isolation
  - check_payload_size: disabled by default, accepts under cap, rejects over
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src import mcp_security
from src.mcp_security import (
    PayloadTooLarge,
    RateLimitExceeded,
    check_payload_size,
    check_rate_limit,
    require_api_key,
    reset_rate_limits,
)


# ---------------------------------------------------------------------------
# API key auth
# ---------------------------------------------------------------------------


class TestRequireAPIKey:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_API_KEY", raising=False)
        # No exception even when no key provided
        require_api_key(None)
        require_api_key("")
        require_api_key("anything")

    def test_missing_key_rejected_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret-123")
        with pytest.raises(PermissionError, match="missing or invalid"):
            require_api_key(None)
        with pytest.raises(PermissionError):
            require_api_key("")

    def test_wrong_key_rejected(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret-123")
        with pytest.raises(PermissionError):
            require_api_key("sk-wrong-456")

    def test_matching_key_passes(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret-123")
        # No exception
        require_api_key("sk-secret-123")


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TestRateLimit:
    def setup_method(self):
        reset_rate_limits()

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(
            "ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", raising=False
        )
        # 1000 calls all succeed
        for _ in range(1000):
            check_rate_limit("add_memory", "agent-1")

    def test_burst_then_block(self, monkeypatch):
        # 60/min -> burst of 10
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", "60")
        now = 1000.0
        for _ in range(10):
            check_rate_limit("add_memory", "agent-x", now=now)

        with pytest.raises(RateLimitExceeded, match="agent-x"):
            check_rate_limit("add_memory", "agent-x", now=now)

    def test_refill_after_time(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", "60")
        now = 2000.0
        for _ in range(10):
            check_rate_limit("add_memory", "agent-y", now=now)
        # Now blocked
        with pytest.raises(RateLimitExceeded):
            check_rate_limit("add_memory", "agent-y", now=now)
        # Advance time by 5 seconds (= 5 tokens refilled at 1/sec sustained)
        later = now + 5.0
        for _ in range(5):
            check_rate_limit("add_memory", "agent-y", now=later)
        with pytest.raises(RateLimitExceeded):
            check_rate_limit("add_memory", "agent-y", now=later)

    def test_per_agent_isolation(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", "60")
        now = 3000.0
        # Burn agent-a's bucket
        for _ in range(10):
            check_rate_limit("add_memory", "agent-a", now=now)
        # agent-b is unaffected
        for _ in range(10):
            check_rate_limit("add_memory", "agent-b", now=now)
        # agent-a still blocked
        with pytest.raises(RateLimitExceeded, match="agent-a"):
            check_rate_limit("add_memory", "agent-a", now=now)

    def test_per_tool_isolation(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", "60")
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_SEARCH_MEMORIES_PER_MIN", "60")
        now = 4000.0
        for _ in range(10):
            check_rate_limit("add_memory", "agent-z", now=now)
        # search_memories bucket is separate
        for _ in range(10):
            check_rate_limit("search_memories", "agent-z", now=now)


# ---------------------------------------------------------------------------
# Payload size cap
# ---------------------------------------------------------------------------


class TestPayloadSize:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_MAX_PAYLOAD_BYTES", raising=False)
        check_payload_size("x" * 10_000_000)  # 10 MiB, no cap

    def test_under_cap_accepted(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "1024")
        check_payload_size("x" * 1000)  # 1000 bytes < 1024

    def test_over_cap_rejected(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "1024")
        with pytest.raises(PayloadTooLarge, match="exceeds"):
            check_payload_size("x" * 2000)

    def test_utf8_multibyte_counted_correctly(self, monkeypatch):
        # ~24 bytes for 6 emoji (each is 4 bytes in UTF-8)
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "20")
        with pytest.raises(PayloadTooLarge):
            check_payload_size("😀😀😀😀😀😀")

    def test_invalid_cap_disables_silently(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "not-a-number")
        # No exception even with huge payload
        check_payload_size("x" * 10_000_000)

    def test_none_content_passes(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "1024")
        check_payload_size(None)


# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------


class TestSecurityStatusBanner:
    def test_logs_all_three_states(self, monkeypatch, caplog):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk")
        monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "1024")
        monkeypatch.setenv("ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN", "60")

        with caplog.at_level("INFO", logger="src.mcp_security"):
            mcp_security.log_security_status()

        msg = caplog.records[-1].getMessage()
        assert "auth=on" in msg
        assert "payload_cap=1024B" in msg
        assert "add_memory" in msg

    def test_logs_off_when_nothing_set(self, monkeypatch, caplog):
        for v in (
            "ENHANCED_API_KEY",
            "ENHANCED_MAX_PAYLOAD_BYTES",
            "ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN",
        ):
            monkeypatch.delenv(v, raising=False)

        with caplog.at_level("INFO", logger="src.mcp_security"):
            mcp_security.log_security_status()

        msg = caplog.records[-1].getMessage()
        assert "auth=off" in msg
        assert "payload_cap=off" in msg
        assert "rate_limited_tools=none" in msg


# ---------------------------------------------------------------------------
# Benchmark baseline comparison
# ---------------------------------------------------------------------------


class TestBenchmarkComparison:
    def test_clean_run_passes(self):
        from tests.benchmarks.compare_to_baseline import compare

        baseline = [
            {
                "name": "default",
                "rps": 100.0,
                "p50_ms": 20.0,
                "p95_ms": 60.0,
                "p99_ms": 150.0,
                "error_pct": 0.0,
            }
        ]
        new = [
            {
                "name": "default",
                "rps": 102.0,
                "p50_ms": 19.0,
                "p95_ms": 60.0,
                "p99_ms": 140.0,
                "error_pct": 0.0,
            }
        ]
        thresholds = {
            "rps_drop_pct_max": 15.0,
            "p50_ms_growth_pct_max": 25.0,
            "p95_ms_growth_pct_max": 30.0,
            "p99_ms_growth_pct_max": 50.0,
            "error_pct_absolute_max": 0.5,
        }
        ok, _lines = compare(baseline, new, thresholds)
        assert ok is True

    def test_rps_drop_fails(self):
        from tests.benchmarks.compare_to_baseline import compare

        baseline = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 0}]
        new = [{"name": "x", "rps": 50, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 0}]
        thresholds = {
            "rps_drop_pct_max": 15.0,
            "p50_ms_growth_pct_max": 25.0,
            "p95_ms_growth_pct_max": 30.0,
            "p99_ms_growth_pct_max": 50.0,
            "error_pct_absolute_max": 0.5,
        }
        ok, _ = compare(baseline, new, thresholds)
        assert ok is False

    def test_p95_growth_fails(self):
        from tests.benchmarks.compare_to_baseline import compare

        baseline = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 0}]
        # p95 doubles
        new = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 40, "p99_ms": 30, "error_pct": 0}]
        thresholds = {
            "rps_drop_pct_max": 15.0,
            "p50_ms_growth_pct_max": 25.0,
            "p95_ms_growth_pct_max": 30.0,
            "p99_ms_growth_pct_max": 50.0,
            "error_pct_absolute_max": 0.5,
        }
        ok, _ = compare(baseline, new, thresholds)
        assert ok is False

    def test_error_spike_fails(self):
        from tests.benchmarks.compare_to_baseline import compare

        baseline = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 0.0}]
        new = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 2.0}]
        thresholds = {
            "rps_drop_pct_max": 15.0,
            "p50_ms_growth_pct_max": 25.0,
            "p95_ms_growth_pct_max": 30.0,
            "p99_ms_growth_pct_max": 50.0,
            "error_pct_absolute_max": 0.5,
        }
        ok, _ = compare(baseline, new, thresholds)
        assert ok is False

    def test_missing_baseline_skipped(self):
        from tests.benchmarks.compare_to_baseline import compare

        baseline = []
        new = [{"name": "x", "rps": 100, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30, "error_pct": 0}]
        ok, lines = compare(baseline, new, {})
        # Nothing to compare against -> trivially OK
        assert ok is True
        assert any("[NEW]" in line for line in lines)
