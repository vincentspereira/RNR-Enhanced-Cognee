"""MCP server security middleware (Phase 5 hardening).

Three layered protections for the MCP server's mutation surface:

1. **API-key authentication** -- `ENHANCED_API_KEY` env var defines the
   accepted key; mutating tools (`add_memory` / `update_memory` /
   `delete_memory` / `cognify` / `ingest_*`) check the
   `X-API-Key` header (HTTP variant) or the `api_key` kwarg (MCP
   stdio variant). Missing or wrong key raises `PermissionError`.
   When the env var is not set, auth is disabled and a warning is
   logged at startup -- the default development-mode behaviour.

2. **Rate limiting** -- token-bucket per agent_id on the
   `add_memory` tool. Default: 60 calls/min per agent (= 1/sec
   sustained, with burst up to 10). Configurable via
   `ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN`. Returns
   `RateLimitExceeded` (subclass of `RuntimeError`) when exceeded.

3. **Payload size cap** -- `add_memory` / `update_memory` /
   `cognify` content is rejected if it exceeds
   `ENHANCED_MAX_PAYLOAD_BYTES` (default 1_048_576 = 1 MiB).
   Returns `PayloadTooLarge` (subclass of `ValueError`).

All three are off by default unless their corresponding env var is
set. The intent is: dev environments stay frictionless, production
operators flip the right knobs at deploy time.

Usage in the MCP server entry points:

    from src.mcp_security import (
        require_api_key, check_rate_limit, check_payload_size
    )

    @mcp.tool()
    def add_memory(content: str, agent_id: str, api_key: str = None) -> str:
        require_api_key(api_key)
        check_rate_limit("add_memory", agent_id)
        check_payload_size(content)
        ...  # existing implementation

The helpers are state-light (the rate-limiter holds a per-tool
token-bucket dict in a module-level singleton) and have no
external dependencies beyond the standard library.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class RateLimitExceeded(RuntimeError):
    """Raised when an agent exceeds its per-tool call rate."""


class PayloadTooLarge(ValueError):
    """Raised when a content / payload arg exceeds the byte cap."""


# ---------------------------------------------------------------------------
# 1. API-key auth
# ---------------------------------------------------------------------------


def _expected_api_key() -> Optional[str]:
    return os.getenv("ENHANCED_API_KEY")


def require_api_key(provided: Optional[str]) -> None:
    """Reject the call if ``ENHANCED_API_KEY`` is set and ``provided``
    doesn't match. Disabled when the env var is empty / unset.
    """
    expected = _expected_api_key()
    if not expected:
        return
    if not provided or provided != expected:
        raise PermissionError(
            "Enhanced Cognee API: missing or invalid X-API-Key / api_key. "
            "Provide the ENHANCED_API_KEY value to call mutating MCP tools."
        )


# ---------------------------------------------------------------------------
# 2. Rate limiter -- per-(tool, agent_id) token bucket
# ---------------------------------------------------------------------------


_BUCKET_LOCK = threading.Lock()
_BUCKETS: Dict[Tuple[str, str], Tuple[float, float]] = {}
# Maps (tool_name, agent_id) -> (tokens, last_refill_ts)


def _bucket_config(tool: str) -> Tuple[float, float]:
    """Return (calls_per_minute, burst). Falls back to a permissive default."""
    env_name = f"ENHANCED_RATE_LIMIT_{tool.upper()}_PER_MIN"
    per_min_raw = os.getenv(env_name)
    if per_min_raw:
        try:
            per_min = float(per_min_raw)
        except ValueError:
            per_min = 60.0
    else:
        per_min = 60.0
    burst = max(1.0, per_min / 6.0)  # ~10 burst when per_min = 60
    return per_min, burst


def check_rate_limit(tool: str, agent_id: str, now: Optional[float] = None) -> None:
    """Consume one token from the (tool, agent_id) bucket.

    Refills proportionally to elapsed wall-clock. Raises
    ``RateLimitExceeded`` when the bucket is empty.

    Rate limiting is **disabled** when the per-tool env var
    (``ENHANCED_RATE_LIMIT_<TOOL>_PER_MIN``) is unset; the default 60/min
    only applies if the env var is set to a value the parser couldn't
    read.
    """
    env_name = f"ENHANCED_RATE_LIMIT_{tool.upper()}_PER_MIN"
    if env_name not in os.environ:
        return  # disabled

    per_min, burst = _bucket_config(tool)
    refill_per_sec = per_min / 60.0
    now = now or time.monotonic()

    key = (tool, agent_id or "_default_")
    with _BUCKET_LOCK:
        tokens, last = _BUCKETS.get(key, (burst, now))
        elapsed = max(0.0, now - last)
        tokens = min(burst, tokens + elapsed * refill_per_sec)
        if tokens < 1.0:
            _BUCKETS[key] = (tokens, now)
            raise RateLimitExceeded(
                f"Rate limit exceeded for tool {tool!r} agent_id "
                f"{agent_id!r}: {per_min:.0f} calls/min (burst {burst:.0f})."
            )
        _BUCKETS[key] = (tokens - 1.0, now)


def reset_rate_limits() -> None:
    """Test helper: clear every bucket. Production code should not call this."""
    with _BUCKET_LOCK:
        _BUCKETS.clear()


# ---------------------------------------------------------------------------
# 3. Payload size cap
# ---------------------------------------------------------------------------


def _payload_byte_cap() -> Optional[int]:
    raw = os.getenv("ENHANCED_MAX_PAYLOAD_BYTES")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def check_payload_size(content: Optional[str]) -> None:
    """Raise ``PayloadTooLarge`` if ``content`` (UTF-8 encoded) exceeds
    the byte cap. Disabled when ``ENHANCED_MAX_PAYLOAD_BYTES`` is unset.
    """
    if content is None:
        return
    cap = _payload_byte_cap()
    if cap is None:
        return
    size = len(content.encode("utf-8"))
    if size > cap:
        raise PayloadTooLarge(
            f"Payload size {size} bytes exceeds ENHANCED_MAX_PAYLOAD_BYTES "
            f"cap of {cap} bytes."
        )


# ---------------------------------------------------------------------------
# Startup banner (called from the MCP server entry point)
# ---------------------------------------------------------------------------


def log_security_status() -> None:
    """Emit a single INFO line summarising which knobs are active.

    Designed to run once at server startup so operators can see at
    a glance whether the production knobs are in effect.
    """
    auth_enabled = bool(_expected_api_key())
    cap = _payload_byte_cap()
    rate_tools = [
        e.split("_PER_MIN")[0].removeprefix("ENHANCED_RATE_LIMIT_").lower()
        for e in os.environ
        if e.startswith("ENHANCED_RATE_LIMIT_") and e.endswith("_PER_MIN")
    ]
    logger.info(
        "MCP security: auth=%s payload_cap=%s rate_limited_tools=%s",
        "on" if auth_enabled else "off",
        f"{cap}B" if cap is not None else "off",
        ",".join(rate_tools) if rate_tools else "none",
    )
