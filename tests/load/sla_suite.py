#!/usr/bin/env python3
"""
Enhanced Cognee SLA Suite
=========================
Runs the capacity-focused 100-user burst (the same profile that produced the
2026-06-04 dev-box baseline) and emits a hard PASS/FAIL verdict against the SLA
targets in ``locustfile.py``:

  - >= 100 RPS sustained
  - p95 latency < 200 ms
  - 0% error rate at 100 concurrent users

This is the script you run on a production-class host (see
``deploy/terraform/``) to re-confirm the SLA on real hardware. It reuses the
server-boot / locust helpers from ``soak_test.py`` so the two stay in lockstep.

ASCII-only output. Exit code 0 on PASS, 1 on FAIL, 2 on harness error.

Run (server already up)::

    python tests/load/sla_suite.py --no-server

Run (boot the server, default 100u/90s)::

    python tests/load/sla_suite.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

# Reuse the soak harness helpers (same directory on sys.path[0]).
from soak_test import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    boot_server,
    parse_locust_stats,
    start_locust,
    stop_server,
    _wait_for_health,
)

# SLA targets (mirror tests/load/locustfile.py docstring).
SLA_MIN_RPS = 100.0
SLA_MAX_P95_MS = 200
SLA_MAX_ERROR_PCT = 0.0


def evaluate(sla: dict) -> dict:
    rps = float(sla.get("rps", 0) or 0)
    p95 = int(sla.get("p95_ms", 10**9) or 10**9)
    err = float(sla.get("error_rate_pct", 100) or 100)
    checks = {
        "rps": {"value": rps, "target": f">= {SLA_MIN_RPS}",
                "met": rps >= SLA_MIN_RPS},
        "p95_ms": {"value": p95, "target": f"< {SLA_MAX_P95_MS}",
                   "met": p95 < SLA_MAX_P95_MS},
        "error_rate_pct": {"value": err, "target": f"== {SLA_MAX_ERROR_PCT}",
                           "met": err <= SLA_MAX_ERROR_PCT},
    }
    return {"checks": checks, "passed": all(c["met"] for c in checks.values())}


def write_report(out_dir: Path, stamp: str, meta: dict, sla: dict,
                 verdict: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{stamp}_sla.md"
    (out_dir / f"{stamp}_sla.json").write_text(
        json.dumps({"meta": meta, "sla": sla, "verdict": verdict}, indent=2),
        encoding="utf-8",
    )
    c = verdict["checks"]

    def row(label: str, key: str, unit: str) -> str:
        v = c[key]
        return (f"| {label} | {v['value']}{unit} | {v['target']} | "
                f"{'MET' if v['met'] else 'MISSED'} |")

    lines = [
        f"# SLA suite -- 100 users ({stamp})",
        "",
        f"Capacity burst of `tests/load/locustfile.py` against the HTTP server "
        f"on `{meta['host']}`. {meta['users']} users, spawn-rate "
        f"{meta['spawn_rate']}, {meta['run_time_s']}s. Auth: {meta['auth']}.",
        "",
        f"**Verdict: {'PASS' if verdict['passed'] else 'FAIL'}**",
        "",
        "| Target | Result | Threshold | Status |",
        "| --- | ---: | --- | --- |",
        row("Sustained RPS", "rps", ""),
        row("p95 latency", "p95_ms", "ms"),
        row("Error rate", "error_rate_pct", "%"),
        "",
        "## Full aggregate",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total requests | {sla.get('requests', 'n/a')} |",
        f"| Failures | {sla.get('failures', 'n/a')} |",
        f"| RPS | {sla.get('rps', 'n/a')} |",
        f"| p50 | {sla.get('p50_ms', 'n/a')}ms |",
        f"| p95 | {sla.get('p95_ms', 'n/a')}ms |",
        f"| p99 | {sla.get('p99_ms', 'n/a')}ms |",
        f"| max | {sla.get('max_ms', 'n/a')}ms |",
        "",
        "## Hardware / context",
        "",
        f"- Host: {meta['host']}",
        f"- Load generator: {meta['loadgen']}",
        "- Compare against tests/benchmarks/baselines/2026-06-04_sla_100users.md "
        "(dev box, co-resident). On dedicated-vCPU hardware p95 should improve.",
    ]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description="Enhanced Cognee SLA suite")
    ap.add_argument("--users", type=int, default=100)
    ap.add_argument("--spawn-rate", type=int, default=10)
    ap.add_argument("--run-time", type=int, default=90, dest="run_time")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-server", action="store_true",
                    help="assume server already running; do not boot it")
    ap.add_argument("--loadgen", default="on-box",
                    help="label describing where load is generated from")
    ap.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    ap.add_argument("--stamp", default=None)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp or time.strftime("%Y-%m-%d") + f"_{args.users}u_sla"
    csv_prefix = out_dir / f"{stamp}_locust"

    server_proc: Optional[object] = None
    if not args.no_server:
        server_proc = boot_server(args.port, out_dir / f"{stamp}_server.log")

    if not _wait_for_health(args.host, args.port, timeout_s=90):
        print("[sla] ERR server /health did not come up")
        stop_server(server_proc)  # type: ignore[arg-type]
        return 2
    print("[sla] OK server healthy; starting burst")

    proc = start_locust(args.host, args.port, args.users, args.spawn_rate,
                        args.run_time, csv_prefix, out_dir / f"{stamp}_locust.log")
    proc.wait()
    stop_server(server_proc)  # type: ignore[arg-type]

    sla = parse_locust_stats(csv_prefix)
    if not sla.get("found"):
        print("[sla] ERR no locust stats produced")
        return 2

    verdict = evaluate(sla)
    meta = {
        "host": f"http://{args.host}:{args.port}",
        "users": args.users,
        "spawn_rate": args.spawn_rate,
        "run_time_s": args.run_time,
        "auth": "dev-open (no headers)",
        "loadgen": args.loadgen,
        "stamp": stamp,
    }
    md = write_report(out_dir, stamp, meta, sla, verdict)

    print("\n=== SLA RESULT ===")
    for name, c in verdict["checks"].items():
        print(f"  {name:16s}: {c['value']} (target {c['target']}) "
              f"-> {'MET' if c['met'] else 'MISSED'}")
    print(f"  VERDICT: {'PASS' if verdict['passed'] else 'FAIL'}")
    print(f"  report : {md}")
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
