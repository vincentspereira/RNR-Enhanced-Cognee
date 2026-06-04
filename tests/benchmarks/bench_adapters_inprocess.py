"""In-process adapter micro-benchmark for the pluggable vector providers.

WHY THIS EXISTS (read tests/benchmarks/baselines/README.md first)
------------------------------------------------------------------
The HTTP Locust harness (`run_provider_comparison.py` + `tests/load/`) drives
the FastAPI `/mcp/*` routes, and those routes run entirely through Postgres
(raw SQL CRUD + `to_tsvector` full-text search). The vector and graph
providers are never on that request path, so the Locust harness CANNOT tell
`qdrant` from `lancedb` from `pgvector` -- every permutation clusters at the
same ~48 RPS because they share the Postgres CRUD path.

This script characterises the *vector tier* directly, the correct way: it
talks to each adapter through `src.db_factory.get_vector_client` and times the
operations that actually differ between providers -- `upsert` and `search` --
with no HTTP, no auth, no Postgres CRUD in the way.

Providers covered (one per stack profile):
  - qdrant   -> the `default` / `neo4j_stack` / `memgraph_kuzu` vector store
  - lancedb  -> the `embedded` profile vector store (in-process, filesystem)
  - pgvector -> the `lean` profile vector store (Postgres + pgvector ext)

Each provider that cannot connect/init is SKIPPED (not failed), so the script
runs wherever a subset of backends is available.

Usage:
    python -m tests.benchmarks.bench_adapters_inprocess \
        --dim 384 --points 1000 --queries 200 --limit 10 \
        --output-dir tests/benchmarks/output

Metrics reported per provider:
  - upsert throughput (points/sec) for a single batched upsert
  - search latency p50 / p95 / p99 / mean (ms) over N single-vector queries
  - search throughput (queries/sec)

These are ADAPTER-level numbers (single process, no concurrency) -- they
characterise per-op cost, not server capacity. For server capacity see the
Locust SLA run in `tests/benchmarks/baselines/`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# Profiles to exercise: (display name, vector provider, stack profile it maps to)
VECTOR_PROFILES = [
    ("qdrant", "qdrant", "default"),
    ("lancedb", "lancedb", "embedded"),
    ("pgvector", "pgvector", "lean"),
]


def _rand_vector(dim: int, rng: random.Random) -> List[float]:
    return [rng.uniform(-1.0, 1.0) for _ in range(dim)]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def _build_models() -> Any:
    """Return the qdrant_client.models module (the shared point/config shapes
    that every adapter accepts). All three adapters speak this surface.
    """
    from qdrant_client import models  # type: ignore

    return models


def _do_search(client: Any, provider: str, collection: str, vector: List[float], limit: int) -> None:
    """Issue one search. The pgvector/lancedb shims expose the legacy
    QdrantClient ``.search()`` surface; the real (newer) QdrantClient dropped
    ``.search()`` in favour of ``.query_points()``. Route accordingly.
    """
    if provider == "qdrant":
        client.query_points(collection_name=collection, query=vector, limit=limit)
    else:
        client.search(collection_name=collection, query_vector=vector, limit=limit)


def bench_provider(
    name: str,
    provider: str,
    profile: str,
    dim: int,
    n_points: int,
    n_queries: int,
    limit: int,
) -> Dict[str, Any]:
    """Benchmark one vector provider. Returns a result dict (status=ok|skipped)."""
    result: Dict[str, Any] = {
        "name": name,
        "provider": provider,
        "profile": profile,
        "status": "skipped",
    }

    # Each provider must be selected via the env var the factory reads.
    os.environ["ENHANCED_VECTOR_PROVIDER"] = provider

    try:
        from src.db_factory import get_vector_client

        models = _build_models()
    except Exception as exc:  # pragma: no cover - import guard
        result["skip_reason"] = f"import failed: {exc}"
        return result

    rng = random.Random(1234)  # fixed seed -> reproducible vectors
    collection = f"bench_{provider}_{dim}"

    # Build the client. lancedb is filesystem-backed; give it a scratch dir.
    try:
        kwargs: Dict[str, Any] = {}
        if provider == "lancedb":
            kwargs["url"] = os.getenv("LANCEDB_URI", "./bench_lancedb_data")
        if provider == "qdrant":
            # qdrant_client auto-enables HTTPS when an api_key is present
            # (QDRANT_API_KEY in .env); a local qdrant on the HTTP port then
            # fails with SSL WRONG_VERSION_NUMBER. Force plain HTTP for the
            # local bench.
            kwargs["https"] = False
            kwargs["api_key"] = None
        client = get_vector_client(**kwargs)
    except Exception as exc:
        result["skip_reason"] = f"client init failed: {exc}"
        return result

    # Create (or recreate) the collection.
    try:
        try:
            client.delete_collection(collection)  # type: ignore[attr-defined]
        except Exception:
            pass
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=dim, distance=models.Distance.COSINE
            ),
        )
    except Exception as exc:
        result["skip_reason"] = f"create_collection failed: {exc}"
        return result

    # Build points up front (excluded from timing).
    points = [
        models.PointStruct(
            id=i,
            vector=_rand_vector(dim, rng),
            payload={"agent_id": f"a{i % 8}", "n": i},
        )
        for i in range(n_points)
    ]
    queries = [_rand_vector(dim, rng) for _ in range(n_queries)]

    # --- upsert (single batched call) ---
    try:
        t0 = time.perf_counter()
        client.upsert(collection_name=collection, points=points)
        upsert_s = time.perf_counter() - t0
    except Exception as exc:
        result["skip_reason"] = f"upsert failed: {exc}"
        return result

    # --- search (per-query latency) ---
    latencies_ms: List[float] = []
    try:
        for q in queries:
            t0 = time.perf_counter()
            _do_search(client, provider, collection, q, limit)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    except Exception as exc:
        result["skip_reason"] = f"search failed: {exc}"
        return result

    total_search_s = sum(latencies_ms) / 1000.0
    result.update(
        {
            "status": "ok",
            "dim": dim,
            "points": n_points,
            "queries": n_queries,
            "limit": limit,
            "upsert_points_per_sec": round(n_points / upsert_s, 1) if upsert_s else None,
            "upsert_total_ms": round(upsert_s * 1000.0, 2),
            "search_p50_ms": round(_percentile(latencies_ms, 50), 3),
            "search_p95_ms": round(_percentile(latencies_ms, 95), 3),
            "search_p99_ms": round(_percentile(latencies_ms, 99), 3),
            "search_mean_ms": round(statistics.mean(latencies_ms), 3),
            "search_queries_per_sec": (
                round(n_queries / total_search_s, 1) if total_search_s else None
            ),
        }
    )

    # Best-effort cleanup.
    try:
        client.delete_collection(collection)  # type: ignore[attr-defined]
    except Exception:
        pass

    return result


def render_markdown(results: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
    lines = [
        "# Vector-tier adapter micro-benchmark",
        "",
        (
            f"Params: dim={params['dim']}, points={params['points']}, "
            f"queries={params['queries']}, limit={params['limit']}. "
            "Single process, no concurrency -- per-op adapter cost, NOT server "
            "capacity (see baselines/README.md)."
        ),
        "",
        "| Provider | Profile | Status | Upsert pts/s | Search p50 (ms) | Search p95 (ms) | Search p99 (ms) | Search q/s |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in results:
        if r.get("status") == "ok":
            lines.append(
                f"| `{r['name']}` | {r['profile']} | OK | "
                f"{r['upsert_points_per_sec']} | {r['search_p50_ms']} | "
                f"{r['search_p95_ms']} | {r['search_p99_ms']} | "
                f"{r['search_queries_per_sec']} |"
            )
        else:
            lines.append(
                f"| `{r['name']}` | {r['profile']} | SKIPPED | - | - | - | - | - |"
            )
    skipped = [r for r in results if r.get("status") != "ok"]
    if skipped:
        lines += ["", "## Skipped providers", ""]
        for r in skipped:
            lines.append(f"- `{r['name']}` ({r['profile']}): {r.get('skip_reason', 'unknown')}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dim", type=int, default=384)
    parser.add_argument("--points", type=int, default=1000)
    parser.add_argument("--queries", type=int, default=200)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--output-dir", default="tests/benchmarks/output", type=str
    )
    args = parser.parse_args(argv)

    # Load .env so the pgvector adapter gets POSTGRES_* (incl. the password).
    try:
        from dotenv import load_dotenv

        load_dotenv(".env")
    except Exception:
        pass
    # Allow the pgvector adapter's require_secret() to fall back to a dev
    # default if POSTGRES_PASSWORD is genuinely absent (local bench only).
    os.environ.setdefault("ENHANCED_ALLOW_INSECURE_DEFAULTS", "1")

    params = {
        "dim": args.dim,
        "points": args.points,
        "queries": args.queries,
        "limit": args.limit,
    }

    print(
        f"[bench] vector-tier micro-benchmark: dim={args.dim} points={args.points} "
        f"queries={args.queries} limit={args.limit}",
        flush=True,
    )

    results: List[Dict[str, Any]] = []
    for name, provider, profile in VECTOR_PROFILES:
        print(f"[bench] {name} ({profile}) ...", flush=True)
        r = bench_provider(
            name, provider, profile, args.dim, args.points, args.queries, args.limit
        )
        status = r.get("status")
        if status == "ok":
            print(
                f"        OK  upsert={r['upsert_points_per_sec']} pts/s  "
                f"search p50={r['search_p50_ms']}ms p95={r['search_p95_ms']}ms "
                f"q/s={r['search_queries_per_sec']}",
                flush=True,
            )
        else:
            print(f"        SKIPPED: {r.get('skip_reason')}", flush=True)
        results.append(r)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"params": params, "results": results}
    (out_dir / "vector_adapter_bench.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (out_dir / "vector_adapter_bench.md").write_text(
        render_markdown(results, params), encoding="utf-8"
    )
    print(f"[bench] wrote {out_dir / 'vector_adapter_bench.json'}", flush=True)
    print(f"[bench] wrote {out_dir / 'vector_adapter_bench.md'}", flush=True)

    ok = [r for r in results if r.get("status") == "ok"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
