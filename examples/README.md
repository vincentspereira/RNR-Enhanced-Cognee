# Enhanced Cognee Examples

End-to-end Python scripts demonstrating the most common Enhanced Cognee
workflows. Each script is self-contained and runnable -- copy, edit
the agent IDs / queries to fit your case, and you have a working
starting point.

These examples talk to a **live** Enhanced Cognee MCP server (default
endpoint `http://localhost:8080`) -- bring the stack up first:

```bash
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
python bin/enhanced_cognee_mcp_server.py &
```

## What's here

| Script | Demonstrates | Run time |
|---|---|---|
| `01_basic_memory_crud.py` | `add_memory` / `get_memory` / `search_memories` / `update_memory` / `delete_memory` -- the standard memory MCP interface | ~5s |
| `02_semantic_search.py` | `cognify` / `search` -- transforming free text into a knowledge graph then searching it semantically | ~30s |
| `03_knowledge_graph.py` | Direct knowledge-graph operations: `remember` / `recall` / `forget_memory` / `improve` / `get_related` | ~10s |
| `04_gdpr_workflow.py` | GDPR primitives: `gdpr_record_consent` / `gdpr_export_user_data` / `gdpr_delete_user_data` -- the right-to-erasure flow | ~5s |
| `05_backup_and_restore.py` | `create_backup` / `list_backups` / `restore_backup` -- disaster-recovery dry-run | ~15s |

## Prerequisites

- Enhanced Cognee MCP server running locally (default `http://localhost:8080`)
- Python 3.11+
- The `enhanced-cognee-client` PyPI package, OR a direct MCP client
  (these examples use plain `requests` against the MCP server's
  HTTP wrapper for clarity)

```bash
pip install requests   # the examples here use requests directly
```

For more advanced patterns (per-agent memory segregation, cross-agent
sharing, undo/redo) see the MCP tool catalogue in
[`docs/api/MCP_TOOLS.md`](../docs/api/MCP_TOOLS.md) (if present) or
the inline docstrings in `bin/enhanced_cognee_mcp_server.py`.

## Common shape

Every script in this folder follows the same skeleton:

```python
#!/usr/bin/env python3
"""<short description of what this script demonstrates>"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import requests

MCP_BASE = "http://localhost:8080"


def call(tool: str, **params: Any) -> Any:
    """Invoke an MCP tool and return its result, raising on error."""
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


def main() -> int:
    # ... script body ...
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

The `call()` helper isolates the HTTP plumbing from the
"what-the-example-does" body so each script reads top-to-bottom.

## Adapting to a different provider

These examples work against the default `production` profile
(postgres + qdrant + arcadedb + valkey). They also work against any
other profile because the MCP server hides the provider choice
behind its tool surface. If you want to verify a specific provider:

```bash
ENHANCED_GRAPH_PROVIDER=apache_age \
  python bin/enhanced_cognee_mcp_server.py &
python examples/01_basic_memory_crud.py
```

See [`docs/PROFILES.md`](../docs/PROFILES.md) for the full provider
matrix.
