"""Compare a fresh benchmark run against a committed baseline.

Reads two ``provider_comparison.json`` files (from
``tests/benchmarks/run_provider_comparison.py``) and a thresholds
JSON, and exits non-zero if any metric for any matching permutation
regressed beyond its allowed threshold.

Designed to be called from CI as the last step of a perf-regression
job:

    python -m tests.benchmarks.compare_to_baseline \
      --baseline tests/benchmarks/baselines/<YYYY-MM-DD>_default_stack.json \
      --new tests/benchmarks/output/provider_comparison.json \
      --thresholds tests/benchmarks/baselines/regression_thresholds.json

Per-metric semantics:

- ``rps``: regression = drop. Fails if ``(baseline - new) / baseline * 100 > rps_drop_pct_max``.
- ``p50_ms`` / ``p95_ms`` / ``p99_ms``: regression = growth. Fails if
  ``(new - baseline) / baseline * 100 > <metric>_growth_pct_max``.
- ``error_pct``: regression = absolute increase. Fails if
  ``new - baseline > error_pct_absolute_max``.

Output: human-readable summary plus exit code (0 OK, 1 regression,
2 missing data / config error).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_by_name(runs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {r["name"]: r for r in runs if "name" in r}


def _pct_change(baseline: float, new: float) -> float:
    if baseline == 0:
        return 0.0 if new == 0 else float("inf")
    return (new - baseline) / baseline * 100.0


def compare(
    baseline_runs: List[Dict[str, Any]],
    new_runs: List[Dict[str, Any]],
    thresholds: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Returns (ok, lines). `lines` is the human-readable report."""
    baseline_idx = _index_by_name(baseline_runs)
    new_idx = _index_by_name(new_runs)

    lines: List[str] = []
    overall_ok = True

    rps_max = thresholds.get("rps_drop_pct_max", 15.0)
    p50_max = thresholds.get("p50_ms_growth_pct_max", 25.0)
    p95_max = thresholds.get("p95_ms_growth_pct_max", 30.0)
    p99_max = thresholds.get("p99_ms_growth_pct_max", 50.0)
    err_abs = thresholds.get("error_pct_absolute_max", 0.5)

    for name in sorted(baseline_idx.keys() | new_idx.keys()):
        b = baseline_idx.get(name)
        n = new_idx.get(name)
        if b is None:
            lines.append(f"[NEW]   {name}: in new run but no baseline -- skipped")
            continue
        if n is None:
            lines.append(f"[GONE]  {name}: in baseline but not in new run -- skipped")
            continue

        perm_ok = True

        # RPS drop
        b_rps, n_rps = float(b["rps"]), float(n["rps"])
        rps_drop = (b_rps - n_rps) / b_rps * 100.0 if b_rps > 0 else 0.0
        rps_ok = rps_drop <= rps_max
        perm_ok &= rps_ok

        # Latency growth
        p50_growth = _pct_change(float(b["p50_ms"]), float(n["p50_ms"]))
        p95_growth = _pct_change(float(b["p95_ms"]), float(n["p95_ms"]))
        p99_growth = _pct_change(float(b["p99_ms"]), float(n["p99_ms"]))
        p50_ok = p50_growth <= p50_max
        p95_ok = p95_growth <= p95_max
        p99_ok = p99_growth <= p99_max
        perm_ok &= p50_ok and p95_ok and p99_ok

        # Error rate
        err_growth = float(n["error_pct"]) - float(b["error_pct"])
        err_ok = err_growth <= err_abs
        perm_ok &= err_ok

        status = "[OK]" if perm_ok else "[REGRESSION]"
        lines.append(f"{status} {name}")
        lines.append(
            f"    RPS: {b_rps:.1f} -> {n_rps:.1f} ({-rps_drop:+.1f}%; allowed drop {rps_max}%)"
        )
        lines.append(
            f"    p50: {b['p50_ms']:.0f}ms -> {n['p50_ms']:.0f}ms ({p50_growth:+.1f}%; max growth {p50_max}%)"
        )
        lines.append(
            f"    p95: {b['p95_ms']:.0f}ms -> {n['p95_ms']:.0f}ms ({p95_growth:+.1f}%; max growth {p95_max}%)"
        )
        lines.append(
            f"    p99: {b['p99_ms']:.0f}ms -> {n['p99_ms']:.0f}ms ({p99_growth:+.1f}%; max growth {p99_max}%)"
        )
        lines.append(
            f"    err: {b['error_pct']:.2f}% -> {n['error_pct']:.2f}% ({err_growth:+.2f} pp; max +{err_abs} pp)"
        )

        overall_ok &= perm_ok

    return overall_ok, lines


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--thresholds", required=True, type=Path)
    args = parser.parse_args(argv)

    if not args.baseline.exists():
        print(f"ERR baseline file not found: {args.baseline}", file=sys.stderr)
        return 2
    if not args.new.exists():
        print(f"ERR new-run file not found: {args.new}", file=sys.stderr)
        return 2
    if not args.thresholds.exists():
        print(f"ERR thresholds file not found: {args.thresholds}", file=sys.stderr)
        return 2

    baseline_runs = _load_json(args.baseline)
    new_runs = _load_json(args.new)
    thresholds = _load_json(args.thresholds)

    ok, lines = compare(baseline_runs, new_runs, thresholds)
    for line in lines:
        print(line)
    print()
    print("REGRESSION CHECK: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
