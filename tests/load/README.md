# `tests/load/` -- Locust load-test scenarios

Workload definitions for performance / latency characterisation of the
Enhanced Cognee MCP server. Run them against a **live** stack -- they
are not unit tests and are not exercised by CI.

## Quick start

```bash
# 1. Bring up the stack
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
python src/enhanced_cognee_mcp.py &     # FastAPI MCP variant on :8080

# 2. Install Locust
pip install locust

# 3. Headless run, default mixed-workload (60s)
locust -f tests/load/locustfile.py \
       --host http://localhost:8080 \
       --headless --users 100 --spawn-rate 10 --run-time 60s \
       --html tests/load/report.html

# 4. Or interactive (Locust web UI at http://localhost:8089)
locust -f tests/load/locustfile.py --host http://localhost:8080
```

## Scenario classes

The file defines several `HttpUser` classes. Some are `weight > 0` and
participate in the default mix; others are `weight = 0` and need to be
selected explicitly on the command line.

### Default mix (weight > 0)

| Class | Weight | Wait | Workload |
| --- | --- | --- | --- |
| `ReadHeavyUser` | 3 | 0.1-0.5s | 90% `search_memories`, 10% `get_memories` |
| `WriteHeavyUser` | 2 | 0.2-1.0s | 70% `add_memory`, 30% `update_memory` |
| `MixedWorkloadUser` | 1 | 0.1-0.8s | 50% search, 30% add, 10% delete, 10% list |

Default user-count ratio: 6 users -> 3 ReadHeavy + 2 WriteHeavy + 1 Mixed.

### Opt-in classes (weight = 0)

Select with `<ClassName>` on the command line:

| Class | When to use |
| --- | --- |
| `HealthCheckUser` | Sanity-check the load harness itself (pings `/health`) |
| `SemanticSearchUser` | `search` over the cognified corpus -- LLM-backed pipeline |
| `KnowledgeGraphUser` | `remember` + `recall` -- direct KG ops, no cognify |
| `GDPRWorkflowUser` | Consent + export + erasure flows |
| `BackupVerifyUser` | Heaviest single MCP op -- serialises every DB |

Examples:

```bash
# Knowledge-graph scenario, 20 users for 2 minutes
locust -f tests/load/locustfile.py KnowledgeGraphUser \
       --headless --users 20 --spawn-rate 2 --run-time 2m \
       --host http://localhost:8080

# Backup stress test -- low users, long run, expect one-at-a-time ops
locust -f tests/load/locustfile.py BackupVerifyUser \
       --headless --users 1 --spawn-rate 1 --run-time 10m \
       --host http://localhost:8080
```

## Recommended SLAs (per HANDOVER section 5 H4)

These are *targets*, not CI gates. The scenarios are the workload spec;
the thresholds for "good enough" depend on your hardware and traffic
profile.

| Workload | p50 target | p95 target | p99 target | RPS target |
| --- | --- | --- | --- | --- |
| Read-heavy memory CRUD | < 50ms | < 200ms | < 500ms | > 100 RPS |
| Write-heavy memory CRUD | < 100ms | < 400ms | < 1000ms | > 50 RPS |
| Semantic search | < 500ms | < 2000ms | < 5000ms | > 5 RPS |
| Knowledge graph (remember/recall) | < 100ms | < 400ms | < 1000ms | > 30 RPS |
| GDPR (export / list_consents) | < 200ms | < 800ms | < 2000ms | > 10 RPS |
| GDPR (delete_user_data) | < 500ms | < 2000ms | < 5000ms | > 1 RPS |
| Backup | -- (one at a time) | < 30s for typical small DB | < 120s | -- |

## Per-provider runs

The MCP server's user-facing tool API is provider-agnostic, so the same
scenarios work against any `ENHANCED_*_PROVIDER` combination. To
compare e.g. ArcadeDB vs Apache AGE performance:

```bash
# Provider A: ArcadeDB (default)
docker compose ... up -d
python src/enhanced_cognee_mcp.py &
locust -f tests/load/locustfile.py ReadHeavyUser \
       --headless --users 50 --spawn-rate 5 --run-time 5m \
       --html report-arcadedb.html

# Provider B: Apache AGE
ENHANCED_GRAPH_PROVIDER=apache_age python src/enhanced_cognee_mcp.py &
locust -f tests/load/locustfile.py ReadHeavyUser \
       --headless --users 50 --spawn-rate 5 --run-time 5m \
       --html report-apache-age.html
```

Diff the HTML reports for the comparison.

## See also

- `examples/` -- the single-shot scripts that mirror these load scenarios
- `docs/PROFILES.md` -- which providers each scenario can exercise
- `docs/PHASE5_TODO.md` "Performance + benchmarks (H4)" -- the
  remaining work to wire perf-regression dashboards in SigNoz
