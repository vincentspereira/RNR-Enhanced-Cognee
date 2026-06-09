#!/usr/bin/env python3
"""
Enhanced Cognee Soak Test
=========================
Long-duration, sustained-load test that surfaces what a short burst (the
100-user SLA profile in ``locustfile.py``) cannot: slow memory leaks and
latency drift over hours of continuous traffic.

What it does
------------
1. (optional) Boots the FastAPI HTTP server (``src.enhanced_cognee_mcp``) as a
   subprocess with dev-open auth and waits for ``/health`` to come up.
2. Drives a sustained, moderate load with Locust headless for ``--duration``.
3. Every ``--sample-interval`` seconds, samples:
     - server process-tree RSS (psutil)
     - each DB container's memory (``docker stats --no-stream``)
     - system available memory (psutil)
4. After the run, parses the Locust CSV for RPS / p95 / error-rate and fits a
   linear regression to the post-warmup RSS series to estimate the leak rate in
   MB/hour. Emits a PASS/FAIL verdict against ``--leak-threshold-mb-per-hr``.
5. Writes a JSON + Markdown report to ``tests/benchmarks/output/``.

ASCII-only output (Windows cp1252 safe). No Unicode symbols.

Run (server already up on :8080)::

    python tests/load/soak_test.py --duration 7200 --users 40 --no-server

Run (let the harness boot the server)::

    python tests/load/soak_test.py --duration 14400 --users 40
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import psutil

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv optional
    load_dotenv = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "tests" / "benchmarks" / "output"
LOCUSTFILE = REPO_ROOT / "tests" / "load" / "locustfile.py"

# DB containers sampled for memory growth (the running default stack).
DB_CONTAINERS = [
    "cognee-mcp-postgres",
    "cognee-mcp-qdrant",
    "cognee-mcp-valkey",
    "cognee-mcp-arcadedb",
]


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

@dataclass
class Sample:
    t_seconds: float
    server_rss_mb: float
    system_used_pct: float
    container_mb: Dict[str, float] = field(default_factory=dict)


def _proc_tree_rss_mb(pid: int) -> float:
    """Sum RSS (MB) of a process and all of its children."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return 0.0
    total = 0
    procs = [proc]
    try:
        procs += proc.children(recursive=True)
    except psutil.Error:
        pass
    for p in procs:
        try:
            total += p.memory_info().rss
        except psutil.Error:
            continue
    return total / (1024 * 1024)


def _parse_mem_usage(field_value: str) -> float:
    """Parse the left side of docker stats MemUsage ('123.4MiB / 7.5GiB') -> MB."""
    left = field_value.split("/")[0].strip()
    units = {"B": 1 / (1024 * 1024), "KIB": 1 / 1024, "MIB": 1.0,
             "GIB": 1024.0, "KB": 1 / 1000, "MB": 1.0, "GB": 1000.0}
    num = ""
    unit = ""
    for ch in left:
        if ch.isdigit() or ch == ".":
            num += ch
        else:
            unit += ch
    try:
        value = float(num)
    except ValueError:
        return 0.0
    return value * units.get(unit.strip().upper(), 1.0)


def _sample_containers(names: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    try:
        proc = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             "{{.Name}}\t{{.MemUsage}}", *names],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return out
    if proc.returncode != 0:
        return out
    for line in proc.stdout.splitlines():
        if "\t" not in line:
            continue
        name, mem = line.split("\t", 1)
        out[name.strip()] = round(_parse_mem_usage(mem), 1)
    return out


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

def _dev_open_env(port: int) -> Dict[str, str]:
    env = dict(os.environ)
    # Dev-open auth: no JWT secret / API key / prod env -> insecure defaults
    for key in ("ENHANCED_JWT_SECRET", "ENHANCED_API_KEY", "ENHANCED_ENV"):
        env.pop(key, None)
    env["ENHANCED_ALLOW_INSECURE_DEFAULTS"] = "true"
    env["ENHANCED_COGNEE_MODE"] = "true"  # init postgres_pool for /mcp/* routes
    env["ENHANCED_HTTPS_HOST"] = "127.0.0.1"
    env["ENHANCED_HTTPS_PORT"] = str(port)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _wait_for_health(host: str, port: int, timeout_s: int = 60) -> bool:
    import urllib.request

    deadline = time.monotonic() + timeout_s
    url = f"http://{host}:{port}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False


def boot_server(port: int, log_path: Path) -> subprocess.Popen:
    # Load .env into our own environment FIRST so DB creds (POSTGRES_PASSWORD,
    # etc.) are visible, THEN build the dev-open env -- _dev_open_env pops the
    # auth keys last, so any ENHANCED_ENV/ENHANCED_API_KEY coming from a
    # production .env is stripped (the load profiles send no auth headers).
    if load_dotenv is not None:
        load_dotenv(REPO_ROOT / ".env")
    env = _dev_open_env(port)
    log_fh = open(log_path, "w", encoding="utf-8")
    print(f"[soak] booting server on 127.0.0.1:{port} (log -> {log_path})")
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.enhanced_cognee_mcp"],
        cwd=str(REPO_ROOT), env=env, stdout=log_fh, stderr=subprocess.STDOUT,
    )
    return proc


def stop_server(proc: Optional[subprocess.Popen]) -> None:
    if proc is None or proc.poll() is not None:
        return
    print("[soak] stopping server")
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGINT)
        proc.wait(timeout=20)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Locust lifecycle
# ---------------------------------------------------------------------------

def start_locust(host: str, port: int, users: int, spawn_rate: int,
                 duration_s: int, csv_prefix: Path, log_path: Path
                 ) -> subprocess.Popen:
    log_fh = open(log_path, "w", encoding="utf-8")
    cmd = [
        sys.executable, "-m", "locust", "-f", str(LOCUSTFILE), "--headless",
        "--host", f"http://{host}:{port}",
        "--users", str(users), "--spawn-rate", str(spawn_rate),
        "--run-time", f"{duration_s}s",
        "--csv", str(csv_prefix), "--only-summary",
    ]
    print(f"[soak] starting locust: {users} users, {duration_s}s "
          f"(csv -> {csv_prefix}_stats.csv)")
    return subprocess.Popen(
        cmd, cwd=str(REPO_ROOT), stdout=log_fh, stderr=subprocess.STDOUT,
    )


def parse_locust_stats(csv_prefix: Path) -> Dict[str, object]:
    """Read the Locust _stats.csv 'Aggregated' row."""
    stats_file = Path(str(csv_prefix) + "_stats.csv")
    result: Dict[str, object] = {"found": False}
    if not stats_file.exists():
        return result
    with open(stats_file, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    agg = next((r for r in rows if r.get("Name") == "Aggregated"), None)
    if agg is None:
        return result

    def num(key: str) -> float:
        try:
            return float(agg.get(key, "0") or 0)
        except ValueError:
            return 0.0

    reqs = num("Request Count")
    fails = num("Failure Count")
    result.update({
        "found": True,
        "requests": int(reqs),
        "failures": int(fails),
        "error_rate_pct": round((fails / reqs * 100.0) if reqs else 0.0, 4),
        "rps": round(num("Requests/s"), 1),
        "p50_ms": int(num("50%")),
        "p95_ms": int(num("95%")),
        "p99_ms": int(num("99%")),
        "max_ms": int(num("Max Response Time")),
    })
    return result


# ---------------------------------------------------------------------------
# Leak analysis (linear regression, no numpy dependency)
# ---------------------------------------------------------------------------

def _linreg(xs: List[float], ys: List[float]) -> Dict[str, float]:
    """Ordinary least squares. Returns slope, intercept, r_squared."""
    n = len(xs)
    if n < 2:
        return {"slope": 0.0, "intercept": ys[0] if ys else 0.0, "r_squared": 0.0}
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if sxx == 0:
        return {"slope": 0.0, "intercept": mean_y, "r_squared": 0.0}
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return {"slope": slope, "intercept": intercept, "r_squared": r2}


def analyze_leak(samples: List[Sample], warmup_s: float,
                 threshold_mb_per_hr: float) -> Dict[str, object]:
    post = [s for s in samples if s.t_seconds >= warmup_s]
    if len(post) < 3:
        post = samples
    xs_hr = [s.t_seconds / 3600.0 for s in post]
    server_y = [s.server_rss_mb for s in post]
    fit = _linreg(xs_hr, server_y)
    slope = fit["slope"]
    r2 = fit["r_squared"]
    # Leak verdict: a sustained, consistent upward trend above threshold.
    is_leak = (slope > threshold_mb_per_hr) and (r2 > 0.5)

    container_trends: Dict[str, Dict[str, float]] = {}
    names = sorted({k for s in samples for k in s.container_mb})
    for name in names:
        ys = [s.container_mb.get(name, 0.0) for s in post]
        cfit = _linreg(xs_hr, ys)
        container_trends[name] = {
            "slope_mb_per_hr": round(cfit["slope"], 2),
            "r_squared": round(cfit["r_squared"], 3),
            "first_mb": round(ys[0], 1) if ys else 0.0,
            "last_mb": round(ys[-1], 1) if ys else 0.0,
        }

    return {
        "server_rss_first_mb": round(server_y[0], 1) if server_y else 0.0,
        "server_rss_last_mb": round(server_y[-1], 1) if server_y else 0.0,
        "server_rss_peak_mb": round(max(server_y), 1) if server_y else 0.0,
        "server_slope_mb_per_hr": round(slope, 2),
        "server_r_squared": round(r2, 3),
        "leak_threshold_mb_per_hr": threshold_mb_per_hr,
        "leak_detected": bool(is_leak),
        "container_trends": container_trends,
        "samples_analyzed": len(post),
        "warmup_seconds": warmup_s,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_reports(out_dir: Path, stamp: str, meta: Dict[str, object],
                  sla: Dict[str, object], leak: Dict[str, object],
                  samples: List[Sample]) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stamp}_soak.json"
    md_path = out_dir / f"{stamp}_soak.md"

    payload = {
        "meta": meta,
        "sla": sla,
        "leak_analysis": leak,
        "samples": [asdict(s) for s in samples],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    dur_h = float(meta["duration_seconds"]) / 3600.0  # type: ignore[arg-type]
    leak_verdict = "FAIL (leak suspected)" if leak["leak_detected"] else "PASS (no leak)"
    err_ok = "MET" if float(sla.get("error_rate_pct", 1)) == 0.0 else "MISSED"

    lines = [
        f"# Soak test -- {meta['users']} users, {dur_h:.1f}h ({stamp})",
        "",
        f"Sustained-load soak of `tests/load/locustfile.py` against the HTTP "
        f"server (`src/enhanced_cognee_mcp.py`) on the default stack. "
        f"Purpose: detect memory leaks / latency drift over a long run that "
        f"the short SLA burst cannot surface.",
        "",
        "## Run parameters",
        "",
        "| Parameter | Value |",
        "| --- | --- |",
        f"| Duration | {dur_h:.2f} h ({meta['duration_seconds']}s) |",
        f"| Concurrent users | {meta['users']} (spawn-rate {meta['spawn_rate']}) |",
        f"| Sample interval | {meta['sample_interval']}s |",
        f"| Samples captured | {len(samples)} |",
        f"| Auth | {meta['auth']} |",
        "",
        "## Throughput / latency (Locust aggregate)",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total requests | {sla.get('requests', 'n/a')} |",
        f"| Error rate | {sla.get('error_rate_pct', 'n/a')}% ({err_ok}) |",
        f"| Sustained RPS | {sla.get('rps', 'n/a')} |",
        f"| p50 | {sla.get('p50_ms', 'n/a')}ms |",
        f"| p95 | {sla.get('p95_ms', 'n/a')}ms |",
        f"| p99 | {sla.get('p99_ms', 'n/a')}ms |",
        "",
        "## Memory-leak analysis",
        "",
        f"**Verdict: {leak_verdict}**",
        "",
        "Linear regression on the post-warmup server-process RSS time series. "
        "A leak is flagged only when the slope exceeds the threshold AND the "
        "trend is consistent (R^2 > 0.5).",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Server RSS first | {leak['server_rss_first_mb']} MB |",
        f"| Server RSS last | {leak['server_rss_last_mb']} MB |",
        f"| Server RSS peak | {leak['server_rss_peak_mb']} MB |",
        f"| Server RSS slope | {leak['server_slope_mb_per_hr']} MB/h |",
        f"| Trend R^2 | {leak['server_r_squared']} |",
        f"| Leak threshold | {leak['leak_threshold_mb_per_hr']} MB/h |",
        "",
        "### DB container memory trends",
        "",
        "| Container | First MB | Last MB | Slope MB/h | R^2 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, t in leak["container_trends"].items():  # type: ignore[union-attr]
        lines.append(
            f"| {name} | {t['first_mb']} | {t['last_mb']} | "
            f"{t['slope_mb_per_hr']} | {t['r_squared']} |"
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- Single dev box (server + 4 DB containers + Locust co-resident); "
        "container memory slopes include normal cache/working-set growth, not "
        "only leaks. The server-process RSS slope is the primary leak signal.",
        "- Dev-open auth (locustfile sends no auth headers).",
        "",
        "## Reproduce",
        "",
        "```bash",
        f"python tests/load/soak_test.py --duration {meta['duration_seconds']} "
        f"--users {meta['users']} --no-server",
        "```",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Enhanced Cognee soak test")
    ap.add_argument("--duration", type=int, default=14400,
                    help="soak duration in seconds (default 14400 = 4h)")
    ap.add_argument("--users", type=int, default=40,
                    help="sustained concurrent users (default 40)")
    ap.add_argument("--spawn-rate", type=int, default=10)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--sample-interval", type=int, default=30,
                    help="seconds between resource samples (default 30)")
    ap.add_argument("--warmup", type=int, default=300,
                    help="seconds to exclude from leak regression (default 300)")
    ap.add_argument("--leak-threshold-mb-per-hr", type=float, default=25.0,
                    help="server RSS slope above which a leak is flagged")
    ap.add_argument("--no-server", action="store_true",
                    help="assume the server is already running; do not boot it")
    ap.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    ap.add_argument("--stamp", default=None,
                    help="report filename stamp (default: date_soak)")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp or time.strftime("%Y-%m-%d") + f"_{args.users}u_soak"
    csv_prefix = out_dir / f"{stamp}_locust"

    server_proc: Optional[subprocess.Popen] = None
    if not args.no_server:
        server_proc = boot_server(args.port, out_dir / f"{stamp}_server.log")

    if not _wait_for_health(args.host, args.port, timeout_s=90):
        print("[soak] ERR server /health did not come up in time")
        stop_server(server_proc)
        return 2
    print("[soak] OK server healthy")

    start = time.monotonic()
    locust_proc = start_locust(
        args.host, args.port, args.users, args.spawn_rate, args.duration,
        csv_prefix, out_dir / f"{stamp}_locust.log",
    )

    samples: List[Sample] = []
    server_pid = server_proc.pid if server_proc else None
    next_sample = 0.0
    print("[soak] sampling resources (server RSS + container memory)...")
    while locust_proc.poll() is None:
        now = time.monotonic() - start
        if now >= next_sample:
            rss = _proc_tree_rss_mb(server_pid) if server_pid else 0.0
            vm = psutil.virtual_memory()
            s = Sample(
                t_seconds=round(now, 1),
                server_rss_mb=round(rss, 1),
                system_used_pct=vm.percent,
                container_mb=_sample_containers(DB_CONTAINERS),
            )
            samples.append(s)
            if len(samples) % 10 == 1:
                print(f"[soak] t={now/60:.1f}m rss={s.server_rss_mb}MB "
                      f"sys={s.system_used_pct}% samples={len(samples)}")
            next_sample = now + args.sample_interval
        time.sleep(1.0)

    locust_rc = locust_proc.returncode
    print(f"[soak] locust exited rc={locust_rc}; captured {len(samples)} samples")

    sla = parse_locust_stats(csv_prefix)
    leak = analyze_leak(samples, float(args.warmup),
                        args.leak_threshold_mb_per_hr)

    meta = {
        "duration_seconds": args.duration,
        "users": args.users,
        "spawn_rate": args.spawn_rate,
        "sample_interval": args.sample_interval,
        "host": f"http://{args.host}:{args.port}",
        "auth": "dev-open (no headers)",
        "booted_server": not args.no_server,
        "stamp": stamp,
    }

    paths = write_reports(out_dir, stamp, meta, sla, leak, samples)
    stop_server(server_proc)

    print("\n=== SOAK SUMMARY ===")
    print(f"  duration       : {args.duration/3600:.2f}h")
    print(f"  requests       : {sla.get('requests', 'n/a')} "
          f"(errors {sla.get('error_rate_pct', 'n/a')}%)")
    print(f"  RPS            : {sla.get('rps', 'n/a')}")
    print(f"  p95            : {sla.get('p95_ms', 'n/a')}ms")
    print(f"  server RSS     : {leak['server_rss_first_mb']} -> "
          f"{leak['server_rss_last_mb']} MB "
          f"(slope {leak['server_slope_mb_per_hr']} MB/h, "
          f"R^2 {leak['server_r_squared']})")
    print(f"  leak verdict   : "
          f"{'FAIL (leak suspected)' if leak['leak_detected'] else 'PASS (no leak)'}")
    print(f"  report (md)    : {paths['md']}")
    print(f"  report (json)  : {paths['json']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
