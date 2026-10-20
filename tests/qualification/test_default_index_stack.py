"""Opt-in real Qdrant, ArcadeDB and Valkey qualification with invented facts.

Every endpoint/credential is supplied explicitly. A new database/collection is
created only in the explicitly selected disposable services; fixtures are kept.
"""
import json
import os
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
async def test_real_default_stores_source_paths_correction_retraction_and_recovery(monkeypatch):
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
    pool = await asyncpg.create_pool(urlunsplit((parsed.scheme, parsed.netloc, "/" + name, parsed.query, "")),
                                     min_size=1, max_size=4)
    identity = IndexIdentity("synthetic-default-stack-index-key-32bytes", "q_" + suffix)
    sinks = DefaultIndexSinks(identity, qdrant_url=settings["qdrant_url"], arcade_url=settings["arcade_url"],
        arcade_database="q_" + suffix, arcade_user=settings["arcade_user"], arcade_password=settings["arcade_password"],
        cache_url=settings["cache_url"], dimensions=384, model="BAAI/bge-small-en-v1.5")
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()),
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
            cache_url=settings["cache_url"], dimensions=384, model=sinks.model)
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
        assert await sinks.neighbors(scope.tenant, "Cedar") == []
        points = await sinks._request("POST", sinks.qdrant_url + "/collections/" + sinks.collection + "/points",
                                      json={"ids": [first["id"]], "with_payload": True})
        assert points["result"] == []
        assert (await service.status(scope))["pending_change_events"] == 0
        assert len((await service.history(scope, first["id"]))["versions"]) == 3
        print(json.dumps({"actual_stores": ["PostgreSQL", "Qdrant", "ArcadeDB", "Valkey"],
            "source_grounded_hops": 2, "partial_delivery_recovered": True,
            "stale_graph_denied": True, "derived_retraction_cleaned": True,
            "graph_transaction_rollback": True, "fresh_namespace_rebuild": True,
            "history_retained": True, "fixtures_preserved": True}))
    finally:
        await sinks.close()
        await pool.close()
