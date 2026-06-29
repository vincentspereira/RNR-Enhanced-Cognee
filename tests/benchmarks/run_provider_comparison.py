"""Cross-provider benchmark runner.

Drives the existing Locust workload (`tests/load/locustfile.py`)
against multiple RNR Enhanced Cognee provider configurations and emits a
comparison report (Markdown + JSON). The point is to defend
provider-choice decisions with numbers, not just licence rationale.

How it works
============

For each provider permutation listed in ``PROVIDER_PERMUTATIONS``,
the runner:

1. Spawns the Locust process in headless mode against the MCP HTTP
   variant (``src.enhanced_cognee_mcp`` on http://localhost:8080) with
   the environment configured via ``ENHANCED_GRAPH_PROVIDER`` /
   ``ENHANCED_VECTOR_PROVIDER`` / ``ENHANCED_CACHE_PROVIDER`` /
   ``ENHANCED_RELATIONAL_PROVIDER``.
2. Parses Locust's ``--csv`` output for the per-endpoint p50/p95/p99
   latency and the aggregate RPS / error rate.
3. Aggregates the result into a single dict per permutation and writes
   ``provider_comparison.{json,md}`` next to this file.

Caveats
=======

- This runner does NOT spin up the databases. The caller is expected
  to have all the relevant services already running (see
  ``docker/docker-compose-enhanced-cognee.yml`` for the full stack,
  or use ``monitoring/docker-compose-monitoring.yml`` for the
  SigNoz observability side).
- The runner shells out to the ``locust`` CLI; ``pip install locust``
  in the environment first.
- Locust's headless mode writes CSVs to a temp dir; we collect the
  ``*_stats.csv`` file and ``*_stats_history.csv`` for per-second
  RPS data.

Run
===

  # From repo root, with the MCP server + databases already up:
  python -m tests.benchmarks.run_provider_comparison

  # Or with custom output path:
  python -m tests.benchmarks.run_provider_comparison --output-dir /tmp/bench

The output directory will contain:
  - provider_comparison.json
  - provider_comparison.md
  - <permutation>_stats.csv  (one per run)
  - <permutation>_stats_history.csv

Use the markdown file in PR descriptions or for the GH issue templates.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Permutations to compare
# ---------------------------------------------------------------------------

PROVIDER_PERMUTATIONS: List[Dict[str, str]] = [
    # name -> the env overrides for this run
    {
        "name": "default",
        "ENHANCED_GRAPH_PROVIDER": "arcadedb",
        "ENHANCED_VECTOR_PROVIDER": "qdrant",
        "ENHANCED_CACHE_PROVIDER": "valkey",
        "ENHANCED_RELATIONAL_PROVIDER": "postgres",
    },
    {
        "name": "lean",
        "ENHANCED_GRAPH_PROVIDER": "apache_age",
        "ENHANCED_VECTOR_PROVIDER": "pgvector",
        "ENHANCED_CACHE_PROVIDER": "in_memory",
        "ENHANCED_RELATIONAL_PROVIDER": "postgres",
    },
    {
        "name": "neo4j_stack",
        "ENHANCED_GRAPH_PROVIDER": "neo4j",
        "ENHANCED_VECTOR_PROVIDER": "qdrant",
        "ENHANCED_CACHE_PROVIDER": "redis",
        "ENHANCED_RELATIONAL_PROVIDER": "postgres",
    },
    {
        "name": "embedded",
        "ENHANCED_GRAPH_PROVIDER": "ladybug",
        "ENHANCED_VECTOR_PROVIDER": "lancedb",
        "ENHANCED_CACHE_PROVIDER": "in_memory",
        "ENHANCED_RELATIONAL_PROVIDER": "sqlite",
    },
    {
        "name": "memgraph_kuzu",
        "ENHANCED_GRAPH_PROVIDER": "memgraph",
        "ENHANCED_VECTOR_PROVIDER": "qdrant",
        "ENHANCED_CACHE_PROVIDER": "valkey",
        "ENHANCED_RELATIONAL_PROVIDER": "postgres",
    },
]


# ---------------------------------------------------------------------------
# Locust runner
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    name: str
    providers: Dict[str, str]
    total_requests: int = 0
    total_failures: int = 0
    rps: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    per_endpoint: List[Dict[str, str]] = field(default_factory=list)
    error_pct: float = 0.0


def _build_run_env(perm: Dict[str, str]) -> Dict[str, str]:
    env = os.environ.copy()
    for key, val in perm.items():
        if key == "name":
            continue
        env[key] = val
    # Make sure the MCP server itself has the same env -- the caller is
    # responsible for restarting it between runs (we do not manage the
    # MCP process here, see module docstring).
    return env


def _run_locust(
    perm: Dict[str, str],
    host: str,
    users: int,
    spawn_rate: int,
    duration: str,
    output_dir: Path,
) -> RunResult:
    name = perm["name"]
    csv_prefix = output_dir / name

    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--headless",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--csv", str(csv_prefix),
        "--only-summary",
    ]

    env = _build_run_env(perm)

    print(f"[bench] Running permutation {name!r} ...", flush=True)
    print(f"        {' '.join(cmd)}", flush=True)
    print(
        "        ENV: "
        + ", ".join(
            f"{k}={v}" for k, v in perm.items() if k != "name"
        ),
        flush=True,
    )

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[bench] locust returned {result.returncode}", flush=True)
        print(f"        stderr: {result.stderr[:500]}", flush=True)

    return _parse_locust_csv(name, perm, csv_prefix)


def _parse_locust_csv(
    name: str, perm: Dict[str, str], csv_prefix: Path
) -> RunResult:
    """Parse the ``<prefix>_stats.csv`` Locust emits."""
    stats_csv = csv_prefix.with_name(csv_prefix.name + "_stats.csv")
    if not stats_csv.exists():
        print(f"[bench] WARN: {stats_csv} not found -- run likely failed", flush=True)
        return RunResult(name=name, providers={k: v for k, v in perm.items() if k != "name"})

    per_endpoint: List[Dict[str, str]] = []
    aggregated: Optional[Dict[str, str]] = None

    with stats_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name", "").lower() == "aggregated":
                aggregated = row
            else:
                per_endpoint.append(row)

    if aggregated is None:
        return RunResult(name=name, providers={k: v for k, v in perm.items() if k != "name"})

    total_req = int(aggregated.get("Request Count", "0") or "0")
    fails = int(aggregated.get("Failure Count", "0") or "0")
    rps = float(aggregated.get("Requests/s", "0") or "0")
    p50 = float(aggregated.get("50%", "0") or "0")
    p95 = float(aggregated.get("95%", "0") or "0")
    p99 = float(aggregated.get("99%", "0") or "0")

    return RunResult(
        name=name,
        providers={k: v for k, v in perm.items() if k != "name"},
        total_requests=total_req,
        total_failures=fails,
        rps=rps,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        per_endpoint=per_endpoint,
        error_pct=(100.0 * fails / total_req) if total_req else 0.0,
    )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_reports(results: List[RunResult], output_dir: Path) -> None:
    json_path = output_dir / "provider_comparison.json"
    md_path = output_dir / "provider_comparison.md"

    json_path.write_text(
        json.dumps(
            [
                {
                    "name": r.name,
                    "providers": r.providers,
                    "rps": r.rps,
                    "p50_ms": r.p50_ms,
                    "p95_ms": r.p95_ms,
                    "p99_ms": r.p99_ms,
                    "total_requests": r.total_requests,
                    "total_failures": r.total_failures,
                    "error_pct": r.error_pct,
                }
                for r in results
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("# Cross-provider benchmark comparison")
    lines.append("")
    lines.append(
        "Generated by `tests/benchmarks/run_provider_comparison.py`. "
        "Each row is one provider permutation; columns are the "
        "Locust-reported metrics."
    )
    lines.append("")
    lines.append(
        "| Permutation | Graph | Vector | Cache | Relational | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error % |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for r in results:
        p = r.providers
        lines.append(
            "| {name} | {g} | {v} | {c} | {rel} | {rps:.1f} | "
            "{p50:.0f} | {p95:.0f} | {p99:.0f} | {err:.2f} |".format(
                name=r.name,
                g=p.get("ENHANCED_GRAPH_PROVIDER", "?"),
                v=p.get("ENHANCED_VECTOR_PROVIDER", "?"),
                c=p.get("ENHANCED_CACHE_PROVIDER", "?"),
                rel=p.get("ENHANCED_RELATIONAL_PROVIDER", "?"),
                rps=r.rps,
                p50=r.p50_ms,
                p95=r.p95_ms,
                p99=r.p99_ms,
                err=r.error_pct,
            )
        )

    lines.append("")
    lines.append("## Per-endpoint detail")
    lines.append("")
    for r in results:
        if not r.per_endpoint:
            continue
        lines.append(f"### Permutation: {r.name}")
        lines.append("")
        lines.append(
            "| Endpoint | Reqs | Fails | p50 | p95 | p99 | RPS |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in r.per_endpoint:
            lines.append(
                "| {name} | {req} | {fail} | {p50} | {p95} | {p99} | {rps} |".format(
                    name=row.get("Name", "?"),
                    req=row.get("Request Count", "0"),
                    fail=row.get("Failure Count", "0"),
                    p50=row.get("50%", "?"),
                    p95=row.get("95%", "?"),
                    p99=row.get("99%", "?"),
                    rps=row.get("Requests/s", "?"),
                )
            )
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[bench] Wrote {json_path}")
    print(f"[bench] Wrote {md_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Locust against multiple RNR Enhanced Cognee provider permutations."
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8080",
        help="MCP HTTP host the locustfile targets",
    )
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--spawn-rate", type=int, default=5)
    parser.add_argument(
        "--duration",
        default="60s",
        help="Locust --run-time value (e.g. '30s', '2m')",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/benchmarks/output",
        help="Directory for per-permutation CSVs + the comparison report",
    )
    parser.add_argument(
        "--permutations",
        nargs="*",
        default=None,
        help="Subset of permutation names to run (default: all)",
    )

    args = parser.parse_args(argv)

    if shutil.which("locust") is None:
        print(
            "ERR: `locust` CLI not on PATH. Run `pip install locust` first.",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected: List[Dict[str, str]] = (
        [p for p in PROVIDER_PERMUTATIONS if p["name"] in set(args.permutations)]
        if args.permutations
        else PROVIDER_PERMUTATIONS
    )

    results: List[RunResult] = []
    for perm in selected:
        result = _run_locust(
            perm,
            host=args.host,
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
            output_dir=output_dir,
        )
        results.append(result)
        # Give the MCP server / databases a beat to settle between runs.
        time.sleep(2)

    write_reports(results, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
