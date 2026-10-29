"""Opt-in HTTP-only synthetic fleet check; scoped tokens arrive through stdin.

This never installs a profile or calls a chat model. Run only against the
explicit synthetic host/tenant chosen by the operator. Tokens never reach logs.
"""
import asyncio
import json
import math
import sys
import time

import httpx


async def run(config):
    origin = config["origin"]
    if origin != "http://127.0.0.1:28080":
        raise ValueError("This installed qualification admits only the selected loopback API")
    tokens = config["tokens"]
    projects = ["controller"] + [f"bot_{i:02}" for i in range(41)]
    if set(tokens) != set(projects) or not config.get("reviewer"):
        raise ValueError("Use exactly 42 scoped synthetic identities and one separate reviewer")
    stats = {"requests": 0, "admission_retries": 0, "latencies_seconds": []}
    async with httpx.AsyncClient(base_url=origin, timeout=30, trust_env=False) as client:
        async def call(method, path, project="controller", *, reviewer=False, body=None):
            headers = {"Authorization": "Bearer " + (config["reviewer"] if reviewer else tokens[project])}
            for attempt in range(30):
                start = time.monotonic()
                response = await client.request(method, path, headers=headers, json=body)
                stats["requests"] += 1
                stats["latencies_seconds"].append(time.monotonic() - start)
                busy = response.status_code == 503 and response.json().get("detail", "").startswith("Service busy;")
                if response.status_code != 429 and not busy:
                    return response
                stats["admission_retries"] += 1
                await asyncio.sleep(min(.1 * (attempt + 1), 2))
            raise AssertionError("Bounded admission retries exhausted")

        gate = asyncio.Semaphore(8)
        async def create(project):
            async with gate:
                response = await call("POST", "/v1/memories", project, body={
                    "content": f"Private synthetic cedar working note for {project}.",
                    "idempotency_key": "initial-note", "fact_key": "working.note"})
                response.raise_for_status()
                return response.json()
        started = time.monotonic()
        values = await asyncio.gather(*(create(p) for p in projects))
        records = dict(zip(projects, values))
        assert len({r["id"] for r in values}) == 42
        write_seconds = time.monotonic() - started

        gate = asyncio.Semaphore(4)
        async def isolation(project, index):
            async with gate:
                response = await call("POST", "/v1/memories/recall", project, body={"query": "cedar"})
                response.raise_for_status()
                assert [r["id"] for r in response.json()["results"]] == [records[project]["id"]]
                other = records[projects[(index + 1) % 42]]["id"]
                assert (await call("GET", "/v1/memories/" + other, project)).status_code == 404
        await asyncio.gather(*(isolation(p, i) for i, p in enumerate(projects)))

        membership = {"library": "reviewed_portfolio", "member_project": "bot_00", "admitted": True}
        assert (await call("POST", "/v1/memories/library/membership", "bot_00", body=membership)).status_code == 403
        shared = await call("POST", "/v1/memories", body={
            "content": "Reviewed synthetic guidance uses a deployment checklist.",
            "idempotency_key": "reviewed-guidance"})
        shared.raise_for_status()
        shared_id = shared.json()["id"]
        for project in projects:
            response = await call("POST", "/v1/memories/library/membership", reviewer=True, body={
                "library": "reviewed_portfolio", "member_project": project,
                "admitted": True, "can_publish": project == "controller"})
            response.raise_for_status()
        response = await call("POST", "/v1/memories/" + shared_id + "/library", reviewer=True, body={
            "library": "reviewed_portfolio", "expected_version": 1})
        response.raise_for_status()
        for project in projects[1:]:
            response = await call("GET", "/v1/memories/" + shared_id, project)
            response.raise_for_status()
            assert response.json()["shared"]
        response = await call("POST", "/v1/memories/library/membership", reviewer=True,
                              body=membership | {"admitted": False})
        response.raise_for_status()
        assert (await call("GET", "/v1/memories/" + shared_id, "bot_00")).status_code == 404
        response = await call("PATCH", "/v1/memories/" + shared_id, body={
            "expected_version": 1, "content": "Updated synthetic guidance awaits a new review."})
        response.raise_for_status()
        for project in projects[1:]:
            assert (await call("GET", "/v1/memories/" + shared_id, project)).status_code == 404
            assert (await call("GET", "/v1/memories/" + records[project]["id"], project)).status_code == 200

        for _ in range(120):
            response = await call("GET", "/v1/memories/status")
            response.raise_for_status()
            status = response.json()
            if status["index"]["worker_available"] and status["index"]["pending_change_events"] == 0:
                break
            await asyncio.sleep(1)
        assert status["index"]["worker_available"] and status["index"]["pending_change_events"] == 0
        response = await call("POST", "/v1/memories/recall", body={"query": "cedar"})
        response.raise_for_status()
        assert response.json()["vector_index"] == "queried"
    latency = sorted(stats.pop("latencies_seconds"))
    return {
        "passed": True, "synthetic_identities": 42, "profile_installations": 0,
        "write_concurrency": 8, "recall_concurrency": 4,
        "write_batch_seconds": round(write_seconds, 3),
        "request_p50_seconds": round(latency[len(latency) // 2], 3),
        "request_p95_seconds": round(latency[math.ceil(.95 * len(latency)) - 1], 3),
        **stats, "private_cross_scope_denials": 42, "reviewed_shared_reads": 41,
        "membership_revocation_denied_immediately": True,
        "correction_withdrawn_from_all_bot_views": True, "private_records_preserved": True,
        "actual_vector_index_queried": True, "controller_pending_events": 0,
        "chat_model_calls": 0, "production_throughput_qualified": False,
    }


if __name__ == "__main__":
    try:
        result = asyncio.run(run(json.load(sys.stdin)))
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
    print(json.dumps(result))

