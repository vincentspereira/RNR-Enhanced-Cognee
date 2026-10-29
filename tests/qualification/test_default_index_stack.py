"""Opt-in real Qdrant, ArcadeDB and Valkey qualification with invented facts.

Every endpoint/credential is supplied explicitly. A new database/collection is
created only in the explicitly selected disposable services; fixtures are kept.
"""
import json
import asyncio
import os
import time
import math
import httpx
import jwt
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import uuid

import asyncpg
from cryptography.fernet import Fernet
import pytest

from src.encryption_manager import EncryptionManager
from src.index_contracts import IndexIdentity
from src.index_outbox import IndexWorker
from src.index_sinks import DefaultIndexSinks
from src.local_embeddings import LocalEmbeddings
from src.memory_service import MemoryService, MemoryScope
from src.recall_service import DerivedRecall
from src.security.enterprise_auth import AuthError


@pytest.mark.asyncio
async def test_real_default_stores_source_paths_correction_retraction_and_recovery(monkeypatch, tmp_path):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    settings_path = os.getenv("RNR_QUALIFICATION_INDEX_SETTINGS")
    cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
    if not url or not settings_path or not cache:
        pytest.skip("Select explicit disposable index services, database and prepared search model")
    settings = json.loads(Path(settings_path).read_text())
    suffix = uuid.uuid4().hex[:16]
    name = "index_stack_" + suffix
    operator = await asyncpg.connect(url)
    await operator.execute(f"CREATE DATABASE {name}")
    await operator.close()
    parsed = urlsplit(url)
    fixture_url = urlunsplit((parsed.scheme, parsed.netloc, "/" + name, parsed.query, ""))
    pool = await asyncpg.create_pool(fixture_url,
                                     min_size=1, max_size=4)
    identity = IndexIdentity("synthetic-default-stack-index-key-32bytes", "q_" + suffix)
    sinks = DefaultIndexSinks(identity, qdrant_url=settings["qdrant_url"], arcade_url=settings["arcade_url"],
        arcade_database="q_" + suffix, arcade_user=settings["arcade_user"], arcade_password=settings["arcade_password"],
        cache_url=settings["cache_url"], dimensions=384, model="BAAI/bge-small-en-v1.5",
        qdrant_key=settings.get("qdrant_api_key", ""))
    encryption_key = Fernet.generate_key().decode()
    service = MemoryService(pool, EncryptionManager(master_key=encryption_key),
        LocalEmbeddings(sinks.model, cache), derived=DerivedRecall(sinks))
    scope = MemoryScope("stack_fixture", "project_one", "owner", "hermes")
    try:
        await service.initialize()
        await sinks.provision(create_graph_database=True)
        worker = IndexWorker(service, sinks)

        async def remember(content, subject, obj, key):
            return await service.remember(scope, content, idempotency_key=key,
                evidence={"kind": "fact", "source_id": "synthetic:" + key},
                knowledge_links=[{"subject": subject, "predicate": "related to", "object": obj,
                                  "span_start": 0, "span_end": len(content)}])

        first = await remember("Cedar depends on Birch.", "Cedar", "Birch", "one")
        second = await remember("Birch stores its backups in Lisbon.", "Birch", "Lisbon", "two")
        assert await worker.run_once() and await worker.run_once()
        result = await service.connections(scope, "Cedar", depth=2)
        assert result["paths"][-1][-1]["object"] == "Lisbon" and len(result["paths"][-1]) == 2
        assert {edge["record_id"] for edge in result["paths"][-1]} == {first["id"], second["id"]}
        reader = DefaultIndexSinks(identity, qdrant_url=settings["qdrant_url"], arcade_url=settings["arcade_url"],
            arcade_database=sinks.database, arcade_user=settings["arcade_user"], arcade_password=settings["arcade_password"],
            dimensions=384, model=sinks.model, readonly=True,
            qdrant_key=settings.get("qdrant_read_api_key", settings.get("qdrant_api_key", "")))
        try:
            assert reader.cache is None
            with pytest.raises(PermissionError):
                await reader.provision()
            with pytest.raises(PermissionError):
                await reader.project({}, {}, [], active=True)
            with pytest.raises(PermissionError):
                await reader.sql("SELECT FROM ECEntity")
            assert (await DerivedRecall(reader).connections(service, scope, "Cedar", depth=2))["paths"][-1][-1]["object"] == "Lisbon"
            assert await reader.search(scope.tenant, await service.embedder.embed("Cedar"), [first["id"]], 1)
        finally:
            await reader.close()
        # Actual API startup must choose a read-only index client and require
        # no cache credential. Exercise its real authenticated graph route.
        from src.memory_api import create_app
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"pipeline": identity.pipeline, "model": sinks.model, "dimensions": 384,
            "qdrant_url": settings["qdrant_url"], "arcade_url": settings["arcade_url"], "arcade_database": sinks.database}))
        secret = "synthetic-index-api-verifier-key-at-least-32-bytes"
        environment = {"ENHANCED_ENV": "production", "ENHANCED_REQUIRE_TENANT": "1",
            "ENHANCED_JWT_SECRET": secret, "ENCRYPTION_MASTER_KEY": encryption_key,
            "ENHANCED_MEMORY_DATABASE_URL": fixture_url, "ENHANCED_EMBEDDING_MODEL": sinks.model,
            "ENHANCED_MODEL_CACHE": cache, "ENHANCED_INDEX_CONFIG": str(index_path),
            "ENHANCED_INDEX_KEY": "synthetic-default-stack-index-key-32bytes",
            "INDEX_ARCADEDB_USER": settings["arcade_user"], "INDEX_ARCADEDB_PASSWORD": settings["arcade_password"],
            "INDEX_QDRANT_API_KEY": settings.get("qdrant_read_api_key", settings.get("qdrant_api_key", ""))}
        for key, value in environment.items():
            monkeypatch.setenv(key, value)
        for key in ("INDEX_VALKEY_URL", "ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
            monkeypatch.delenv(key, raising=False)
        app = create_app()
        token = jwt.encode({"sub": scope.subject, "tenant": scope.tenant, "project_id": scope.project,
            "agent_id": scope.agent, "roles": ["api_client"], "exp": int(time.time())+300}, secret, algorithm="HS256")
        async with app.router.lifespan_context(app):
            assert app.state.memory_service.derived.sinks.readonly
            assert app.state.memory_service.derived.sinks.cache is None
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost",
                                         headers={"Authorization": "Bearer "+token}) as http:
                linked = await http.post("/v1/memories/connections", json={"entity": "Cedar", "depth": 2})
                assert linked.status_code == 200 and linked.json()["paths"][-1][-1]["object"] == "Lisbon"
        recall = await service.recall(scope, "Where are Birch recovery copies kept?")
        assert recall["vector_index"] == "queried" and recall["results"][0]["id"] == second["id"]
        assert (await service.connections(MemoryScope(scope.tenant, "other", "reader", "agent"), "Cedar"))["paths"] == []
        graph_rows = await sinks.sql("SELECT FROM ECLink LIMIT 64")
        assert len(graph_rows) == 2
        assert "Cedar" not in json.dumps(graph_rows) and "Lisbon" not in json.dumps(graph_rows)
        cache_key = "ec:" + identity.pipeline + ":" + identity.record(scope.tenant, scope.project, first["id"])
        cached = json.loads(await sinks.cache.get(cache_key))
        assert cached["payload"].startswith("enc2:") and "Cedar" not in cached["payload"]

        # A mid-transaction error must restore the previous complete edge set.
        original_sql = sinks.sql

        async def fail_after_graph_delete(command, *args, **kwargs):
            if command.startswith("CREATE EDGE"):
                raise ConnectionError("Synthetic graph transaction interruption")
            return await original_sql(command, *args, **kwargs)

        monkeypatch.setattr(sinks, "sql", fail_after_graph_delete)
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM shared_memory.records WHERE id=$1", first["id"])
        with pytest.raises(ConnectionError):
            await sinks.project(row, service._payload(row), await service.embedder.embed("Cedar depends on Birch."), active=True)
        monkeypatch.setattr(sinks, "sql", original_sql)
        assert len(await sinks.sql("SELECT FROM ECLink LIMIT 64")) == 2

        # Rebuild into a new explicit namespace, even though the original
        # outbox events are already processed. No source/history is rewritten.
        rebuilt = DefaultIndexSinks(IndexIdentity("synthetic-default-stack-index-key-32bytes", "r_" + suffix),
            qdrant_url=settings["qdrant_url"], arcade_url=settings["arcade_url"], arcade_database="r_"+suffix,
            arcade_user=settings["arcade_user"], arcade_password=settings["arcade_password"],
            cache_url=settings["cache_url"], dimensions=384, model=sinks.model,
            qdrant_key=settings.get("qdrant_api_key", ""))
        try:
            await rebuilt.provision(create_graph_database=True)
            new_worker = IndexWorker(service, rebuilt)
            assert await new_worker.run_once() and await new_worker.run_once()
            recovered_paths = await DerivedRecall(rebuilt).connections(service, scope, "Cedar", depth=2)
            assert recovered_paths["paths"][-1][-1]["object"] == "Lisbon"
        finally:
            await rebuilt.close()

        # Interrupt after Qdrant accepted the newer version, before graph/cache
        # delivery. The current canonical read must reject the old graph edge.
        content = "Cedar depends on Maple."
        await service.correct(scope, first["id"], expected_version=1, content=content,
            knowledge_links=[{"subject": "Cedar", "predicate": "depends on", "object": "Maple",
                              "span_start": 0, "span_end": len(content)}])
        assert (await service.connections(scope, "Cedar"))["paths"] == []
        original = sinks.sql

        async def offline_graph(*args, **kwargs):
            raise ConnectionError("Synthetic interrupted graph transport")

        monkeypatch.setattr(sinks, "sql", offline_graph)
        assert await worker.run_once()
        monkeypatch.setattr(sinks, "sql", original)
        with pytest.raises(AuthError) as denied:
            await service.connections(scope, "Cedar")
        assert denied.value.status_code == 503
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.index_deliveries WHERE error_code IS NOT NULL") == 1
            await conn.execute("UPDATE shared_memory.index_deliveries SET retry_at=now() WHERE completed_at IS NULL")
        assert await IndexWorker(service, sinks).run_once()
        paths = (await service.connections(scope, "Cedar"))["paths"]
        assert len(paths) == 1 and paths[0][0]["object"] == "Maple" and paths[0][0]["version"] == 2
        assert json.loads(await sinks.cache.get(cache_key))["version"] == 2
        await service.correct(scope, first["id"], expected_version=2, retract=True)
        assert (await service.connections(scope, "Cedar"))["paths"] == []
        assert await worker.run_once()
        assert await sinks.cache.get(cache_key) is None
        assert await sinks.neighbors(scope.tenant, "Cedar", identifiers=[first["id"]]) == []
        points = await sinks._request("POST", sinks.qdrant_url + "/collections/" + sinks.collection + "/points",
                                      headers=sinks._qdrant_headers,
                                      json={"ids": [first["id"]], "with_payload": True})
        assert points["result"] == []
        assert (await service.status(scope))["pending_change_events"] == 0
        assert len((await service.history(scope, first["id"]))["versions"]) == 3
        filtered = MemoryScope(scope.tenant, "filtered_owner", "owner", "hermes")
        hidden = MemoryScope(scope.tenant, "unapproved_other", "owner", "hermes")
        filter_records = []
        for item, target in ((filtered, "Harbor"), (hidden, "Meadow")):
            content = f"Cedar keeps its archives in {target}."
            filter_records.append(await service.remember(item, content, idempotency_key="candidate-filter",
                knowledge_links=[{"subject": "Cedar", "predicate": "archives in", "object": target,
                                  "span_start": 0, "span_end": len(content)}]))
        async with asyncio.timeout(15):
            while True:
                worked = await worker.run_once()
                states = await asyncio.gather(*(service.status(item) for item in (filtered, hidden)))
                if all(item["pending_change_events"] == 0 for item in states):
                    break
                if not worked:
                    await asyncio.sleep(.05)
        eligible = await sinks.neighbors(scope.tenant, "Cedar", identifiers=[filter_records[0]["id"]])
        assert len(eligible) == 1 and eligible[0]["record_id"] == filter_records[0]["id"]
        assert (await service.connections(filtered, "Cedar"))["paths"][0][0]["object"] == "Harbor"
        assert (await service.connections(scope, "Cedar"))["paths"] == []
        # Optional bounded concurrent workload on the actual default stores.
        # This records its exact duration/load, not a production capacity claim.
        seconds = int(os.getenv("RNR_QUALIFICATION_SOAK_SECONDS", "0"))
        if not 0 <= seconds <= 1800:
            raise ValueError("Synthetic soak duration must be between zero and 1800 seconds")
        load = {"enabled": bool(seconds)}
        if seconds:
            projects = int(os.getenv("RNR_QUALIFICATION_SOAK_PROJECTS", "4"))
            if not 2 <= projects <= 42:
                raise ValueError("Select between two and 42 synthetic concurrent spaces")
            scopes = [MemoryScope(scope.tenant, f"load_{i}", "owner", "hermes") for i in range(projects)]
            async def storage():
                async with pool.acquire() as connection:
                    return dict(await connection.fetchrow("""SELECT
                        pg_database_size(current_database()) AS database_bytes,
                        (SELECT count(*) FROM shared_memory.records) AS current_records,
                        (SELECT count(*) FROM shared_memory.record_versions) AS retained_versions"""))
            before = await storage()
            model_calls = 0
            original_embed = service.embedder.embed

            async def measured_embed(content):
                nonlocal model_calls
                model_calls += 1
                return await original_embed(content)

            monkeypatch.setattr(service.embedder, "embed", measured_embed)
            records = []
            for i, item in enumerate(scopes):
                records.append(await service.remember(item, f"Cedar keeps its recovery copies in Harbor{i}.",
                                                      idempotency_key="load-one"))
            started, rounds, times = time.monotonic(), 0, []
            while time.monotonic()-started < seconds:
                tick = time.monotonic()
                generation = rounds+2

                async def change(i):
                    content = f"Cedar keeps generation {generation} recovery copies in Harbor{i}."
                    records[i] = await service.correct(scopes[i], records[i]["id"],
                        expected_version=records[i]["version"], content=content,
                        knowledge_links=[{"subject": "Cedar", "predicate": "stores in", "object": f"Harbor{i}",
                                          "span_start": 0, "span_end": len(content)}])

                await asyncio.gather(*(change(i) for i in range(projects)))
                # Quiescent indexing checkpoint for this batch; no new write
                # is accepted as a graph hit merely because an event exists.
                async with asyncio.timeout(15):
                    while True:
                        worked = await worker.run_once()
                        states = await asyncio.gather(*(service.status(item) for item in scopes))
                        if all(item["pending_change_events"] == 0 for item in states):
                            break
                        # No currently claimable job does not imply an empty
                        # queue (leases, retries and wall-clock adjustments).
                        if not worked:
                            await asyncio.sleep(.05)

                async def check(i):
                    found = await service.recall(scopes[i], "Where are the recovery copies stored?")
                    assert len(found["results"]) == 1 and found["results"][0]["id"] == records[i]["id"]
                    assert found["results"][0]["version"] == records[i]["version"]
                    paths = (await service.connections(scopes[i], "Cedar"))["paths"]
                    assert len(paths) == 1 and paths[0][0]["object"] == f"Harbor{i}"
                    assert paths[0][0]["version"] == records[i]["version"]
                    assert (await service.status(scopes[i]))["pending_change_events"] == 0

                await asyncio.gather(*(check(i) for i in range(projects)))
                assert (await service.recall(MemoryScope(scope.tenant, "unapproved", "reader", "agent"), "Cedar"))["results"] == []
                times.append((time.monotonic()-tick)*1000)
                rounds += 1
            load.update(requested_seconds=seconds, actual_seconds=round(time.monotonic()-started, 2),
                concurrent_projects=projects, completed_rounds=rounds, corrected_records=rounds*projects,
                semantic_queries=rounds*(projects+1), graph_queries=rounds*projects, scope_leaks=0,
                round_p95_ms=round(sorted(times)[math.ceil(.95*len(times))-1], 2),
                pending_events=0, retained_history=True, failures=0,
                local_embedding_method_calls=model_calls, chat_model_calls=0,
                storage_before=before, storage_after=await storage())
        print(json.dumps({"actual_stores": ["PostgreSQL", "Qdrant", "ArcadeDB", "Valkey"],
            "source_grounded_hops": 2, "partial_delivery_recovered": True,
            "stale_graph_denied": True, "derived_retraction_cleaned": True,
            "graph_transaction_rollback": True, "fresh_namespace_rebuild": True,
            "history_retained": True, "fixtures_preserved": True, "bounded_load": load}))
    finally:
        await sinks.close()
        await pool.close()
