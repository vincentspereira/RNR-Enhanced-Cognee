# RNR Enhanced Cognee Fork Patches

Canonical record of RNR Enhanced Cognee's customizations to upstream
`topoteretes/cognee`. These MUST be re-applied after a full rebase onto a new
upstream tag (see `docs/UPSTREAM_SYNC_RUNBOOK.md`, section 8).

## Patches

### telemetry_opt_in.diff -> `cognee/shared/utils.py`
Privacy: product telemetry is made **OPT-IN**. `send_telemetry()` returns
immediately unless `COGNEE_TELEMETRY_ENABLED` is set, so RNR Enhanced Cognee never
phones home to `https://test.prometh.ai` by default -- in ANY context (general
use, MCP, API, or an air-gapped consuming app). The upstream `TELEMETRY_DISABLED`
and `ENV {test, dev}` gates are retained as defence-in-depth.

This is the SOLE telemetry mechanism. RNR Enhanced Cognee is deliberately left
general-purpose (cloud LLMs and HTTP requests remain enabled); any air-gap
configuration (local-only LLM, `ALLOW_HTTP_REQUESTS=False`, etc.) belongs INSIDE
the air-gapped consuming application (e.g. LSWA), not in RNR Enhanced Cognee.

Re-apply after every rebase of `cognee/`:

```bat
git apply .upstream-sync/enhanced-patches/telemetry_opt_in.diff
```

If the apply fails (context drift), re-apply manually: in
`cognee/shared/utils.py` -> `send_telemetry()`, add as the **first** gate, right
after the `additional_properties is None` normalization:

```python
    if not os.getenv("COGNEE_TELEMETRY_ENABLED"):
        return
```

The corresponding telemetry tests (`cognee/tests/test_telemetry.py`,
`cognee/tests/unit/shared/test_telemetry_tracking.py`) opt in via
`COGNEE_TELEMETRY_ENABLED=1` on their "enabled" path; re-apply those edits too
if upstream reverts them.

### Other forked files (canonical copies)
- `create_vector_engine.py`, `get_llm_client.py` (adds the `ZAI` provider),
  `OllamaEmbeddingEngine.py`, `QdrantAdapter.py`, `qdrant_init.py`,
  `search_api.py`, `search_methods.py`, `setup.py` - Enhanced provider/adapter
  customizations.

## Z.ai endpoint note (fixed 2026-06-18)
The `zai` templates/installers (`bin/install.py`, `docker/docker-compose-*.yml`,
`deploy/vps/README.md`) default to the Z.ai **Coding Plan** endpoint
`https://api.z.ai/api/coding/paas/v4` (owner is on the coding plan; verified
HTTP 200). Standard-plan users should switch to `https://api.z.ai/api/paas/v4`.
The previous default `https://api.z.ai/v1` 404s and must not be used.
