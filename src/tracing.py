"""
Phase 9 - 14.5: Distributed Tracing
======================================
Optional OpenTelemetry integration for per-tool spans.

When OpenTelemetry SDK is installed (`pip install opentelemetry-sdk
opentelemetry-exporter-otlp`) and OTEL_EXPORTER_OTLP_ENDPOINT is set,
every MCP tool call is wrapped in a span with:
  - span name: "enhanced-cognee.<tool_name>"
  - attributes: agent_id, tool_name, service.name
  - status: OK on success, ERROR on exception

When OpenTelemetry is NOT installed the module degrades silently and
all span context managers are no-ops.

ASCII-only: no Unicode in strings or log output.

Environment variables
---------------------
  OTEL_EXPORTER_OTLP_ENDPOINT - gRPC or HTTP endpoint (enables tracing)
  OTEL_SERVICE_NAME            - service name tag (default: enhanced-cognee)
  OTEL_TRACES_SAMPLER          - sampling strategy (default: parentbased_always_on)

Usage
-----
    from src.tracing import init_tracing, trace_tool

    # At server startup
    init_tracing()

    # In an MCP tool
    with trace_tool("add_memory", agent_id="claude-code") as span:
        # do work
        span.set_attribute("memory.size", len(content))
"""

import logging
import os
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import OpenTelemetry
# ---------------------------------------------------------------------------

_OTEL_AVAILABLE = False
_tracer = None

try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor as _BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource as _Resource
    _OTEL_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# No-op span context manager (fallback)
# ---------------------------------------------------------------------------

class _NoOpSpan:
    """Returned when OpenTelemetry is not available or tracing is disabled."""

    def set_attribute(self, key: str, value) -> None:
        pass

    def set_status(self, *args, **kwargs) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_tracing(
    service_name: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> bool:
    """
    Initialise OpenTelemetry tracing.

    Returns True if tracing was enabled successfully, False otherwise.
    """
    global _tracer

    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "enhanced-cognee")

    if not _OTEL_AVAILABLE:
        logger.info(
            "Tracing: OpenTelemetry SDK not installed. "
            "Install opentelemetry-sdk to enable distributed tracing."
        )
        return False

    if not endpoint:
        logger.info(
            "Tracing: OTEL_EXPORTER_OTLP_ENDPOINT not set. "
            "Tracing is disabled. Set the env var to enable."
        )
        return False

    try:
        resource = _Resource.create({"service.name": service_name})
        provider = _TracerProvider(resource=resource)

        # Choose exporter based on endpoint protocol
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter as _HTTPExporter,
            )
            exporter = _HTTPExporter(endpoint=endpoint)
        else:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter as _GRPCExporter,
            )
            exporter = _GRPCExporter(endpoint=endpoint)

        provider.add_span_processor(_BatchSpanProcessor(exporter))
        _otel_trace.set_tracer_provider(provider)
        _tracer = _otel_trace.get_tracer("enhanced-cognee", "1.0.9-enhanced")
        logger.info(f"OK Tracing initialized: service={service_name} endpoint={endpoint}")
        return True

    except Exception as exc:
        logger.warning(f"Tracing initialization failed (non-fatal): {exc}")
        return False


# ---------------------------------------------------------------------------
# Per-tool span context manager
# ---------------------------------------------------------------------------

@contextmanager
def trace_tool(tool_name: str, agent_id: str = "unknown", **extra_attrs):
    """
    Context manager that wraps a tool call in an OpenTelemetry span.

    When tracing is disabled or unavailable, yields a no-op span.

    Usage::

        with trace_tool("add_memory", agent_id=agent_id) as span:
            result = do_work()
            span.set_attribute("result.size", len(result))
    """
    if _tracer is None:
        yield _NoOpSpan()
        return

    try:
        with _tracer.start_as_current_span(f"enhanced-cognee.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("agent.id", agent_id)
            for k, v in extra_attrs.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                if _OTEL_AVAILABLE:
                    from opentelemetry.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
    except Exception as exc:
        # Tracing infrastructure failure must never break tool execution
        logger.debug(f"Span creation failed ({tool_name}): {exc}")
        yield _NoOpSpan()


def is_tracing_enabled() -> bool:
    """Return True if OpenTelemetry tracing is active."""
    return _tracer is not None
