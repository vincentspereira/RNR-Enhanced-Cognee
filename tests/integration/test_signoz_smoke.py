"""Live SigNoz observability smoke test (PR 14).

Asserts that a trace emitted by ``src/tracing.py`` actually lands in
SigNoz's ClickHouse trace store, so the full Phase 4 observability
chain works end-to-end (MCP server -> OTel SDK -> SigNoz OTel
Collector -> ClickHouse -> SigNoz Query Service).

Skips when:
  - SigNoz isn't reachable on http://localhost:3301 (the SigNoz UI
    + Query Service port)
  - The ClickHouse `signoz_traces` schema is empty (collector hasn't
    received any spans yet)

CI runs this only on the `signoz-monitoring` profile (gated by env
var ``ENHANCED_RUN_SIGNOZ_SMOKE=1``) because booting the full
monitoring stack adds ~3 min and isn't worth it for every PR.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest


_REASON_NO_SIGNOZ = (
    "SigNoz smoke test skipped. Set ENHANCED_RUN_SIGNOZ_SMOKE=1 and "
    "boot the monitoring stack via "
    "`docker compose -f monitoring/docker-compose-monitoring.yml up -d` "
    "to exercise the end-to-end trace pipeline."
)


def _signoz_enabled() -> bool:
    return os.getenv("ENHANCED_RUN_SIGNOZ_SMOKE") == "1"


def _signoz_ui_reachable() -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(
            "http://localhost:3301/api/v1/health", timeout=2
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _signoz_enabled(), reason=_REASON_NO_SIGNOZ)
class TestSigNozTracePipeline:
    """End-to-end: emit a span, query SigNoz's API, assert it appears."""

    def setup_class(cls) -> None:  # noqa: N805
        if not _signoz_ui_reachable():
            pytest.skip(
                "SigNoz UI not reachable on http://localhost:3301; "
                "the monitoring stack isn't running."
            )

    def test_health_endpoint_responds(self):
        import urllib.request

        with urllib.request.urlopen(
            "http://localhost:3301/api/v1/health", timeout=5
        ) as resp:
            assert resp.status == 200

    def test_emitted_span_lands_in_clickhouse(self):
        """Emit a uniquely-tagged span via OTel and search for it via SigNoz's API."""
        from opentelemetry import trace

        # 1. Configure the OTel SDK to send to SigNoz's collector
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            SimpleSpanProcessor,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        provider = TracerProvider()
        exporter = OTLPSpanExporter(
            endpoint=os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            ),
            insecure=True,
        )
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        tracer = trace.get_tracer("enhanced-cognee-smoke-test")

        # 2. Emit a uniquely-tagged span
        marker = f"signoz_smoke_{uuid.uuid4().hex[:8]}"
        with tracer.start_as_current_span("smoke_test_span") as span:
            span.set_attribute("test.marker", marker)
            span.set_attribute("test.timestamp", time.time())

        # 3. Force flush
        provider.shutdown()

        # 4. Allow the collector ~5 seconds to ingest
        time.sleep(5)

        # 5. Query SigNoz's API for the span
        import urllib.request
        import json

        # SigNoz's traces query endpoint
        query_url = (
            "http://localhost:3301/api/v3/query_range"
        )
        body = {
            "compositeQuery": {
                "queryType": "builder",
                "panelType": "list",
                "builderQueries": {
                    "A": {
                        "queryName": "A",
                        "dataSource": "traces",
                        "filters": {
                            "items": [
                                {
                                    "key": {"key": "test.marker"},
                                    "op": "=",
                                    "value": marker,
                                }
                            ],
                            "op": "AND",
                        },
                        "expression": "A",
                    }
                },
            },
            "start": int((time.time() - 60) * 1000),
            "end": int(time.time() * 1000),
        }

        req = urllib.request.Request(
            query_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            pytest.fail(
                f"SigNoz query API call failed: {e}. The collector may not "
                "be wired correctly or ClickHouse hasn't received the span."
            )

        # SigNoz's response shape: {data: {result: [{rows: [...]}]}}
        result = payload.get("data", {}).get("result", [])
        assert len(result) > 0, (
            f"Span with marker={marker} did not appear in SigNoz within 5s. "
            "Check the OTel collector logs and ClickHouse retention config."
        )
