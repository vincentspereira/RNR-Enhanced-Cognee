"""Restore-derived NEW namespaces on actual local stores; preserve live indexes.

Use the protected candidate Python as operator. Only the already restored
disposable database is writable. New graph database/vector collection/cache
prefixes are retained on success and failure. No service/profile switch.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid
from urllib.parse import urlsplit, urlunsplit


REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
BASE = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
RECOVERY = Path("/var/tmp/ec-launch-recovery-aja7p8j9/summary.json")


def private_json(path, *, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077
                or info.st_size > limit):
            raise ValueError("operator_input_protection")
        return json.loads(source.read(limit + 1))


def local(value, scheme, port):
    uri = urlsplit(value)
    if uri.scheme not in scheme or uri.hostname not in {"127.0.0.1", "localhost", "::1"} or uri.port != port:
        raise ValueError("local_store_binding_required")
    return value


def protected_settings(path):
    if (not path.is_absolute() or not any(path.is_relative_to(root) for root in (
            Path("/etc/enhanced-cognee"), Path("/opt/enhanced-cognee-memory")))
            or path != path.resolve(strict=True)):
        raise ValueError("protected_index_settings_required")
    for item in [path, *path.parents]:
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError("protected_index_settings_required")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
        raise ValueError("protected_index_settings_required")


async def qualify(result):
    import asyncpg
    from src.index_contracts import IndexIdentity
    from src.index_outbox import IndexWorker
    from src.index_sinks import DefaultIndexSinks
    from src.local_embeddings import LocalEmbeddings, MODEL
    from src.memory_keys import canonical_cipher_from_environment
    from src.memory_service import MemoryService, MemoryScope
    from src.recall_service import DerivedRecall

    receipt = private_json(RECOVERY)
    target_name = receipt.get("new_disposable_database", "")
    if (receipt.get("complete") is not True or receipt.get("canonical_recovery_qualified") is not True
            or receipt.get("source_revision") != REVISION
            or not re.fullmatch(r"memory_restore_launch_[a-f0-9]{16}", target_name)):
        raise ValueError("completed_disposable_recovery_required")
    operator = private_json(Path("/etc/enhanced-cognee/operator.json"))
    worker_config = private_json(Path("/etc/enhanced-cognee/worker.json"))
    settings_path = Path(worker_config["ENHANCED_INDEX_CONFIG"])
    protected_settings(settings_path)
    settings = json.loads(settings_path.read_text())
    if settings.get("model") != MODEL or settings.get("dimensions") != 384:
        raise ValueError("admitted_model_required")
    # Prefer the protected operator identity. A worker lacking permission to
    # create new namespaces must fail; no ACL/grant is altered to make it pass.
    combined = dict(worker_config, **operator)
    required = {"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_INDEX_KEY", "INDEX_ARCADEDB_USER",
                "INDEX_ARCADEDB_PASSWORD", "INDEX_VALKEY_URL", "INDEX_QDRANT_API_KEY"}
    if not required <= combined.keys():
        result["missing_operator_field_names"] = sorted(required - combined.keys())
        raise ValueError("operator_store_credentials_incomplete")
    os.environ.clear()
    os.environ.update(PATH="/usr/local/bin:/usr/bin:/bin", LANG="C.UTF-8",
                      HF_HUB_OFFLINE="1", COGNEE_LOG_FILE="false", ENHANCED_LOAD_DOTENV="0")
    os.environ.update(operator)
    cipher = canonical_cipher_from_environment()
    suffix = uuid.uuid4().hex[:16]
    pipeline = "lr_" + suffix
    result.update(new_pipeline=pipeline, new_graph_database=pipeline,
                  new_qdrant_collection="ec_" + pipeline, restored_database=target_name)
    identity = IndexIdentity(combined["ENHANCED_INDEX_KEY"], pipeline)
    sinks = DefaultIndexSinks(identity, model=MODEL, dimensions=384,
        qdrant_url=local(settings["qdrant_url"], {"http", "https"}, 28535),
        arcade_url=local(settings["arcade_url"], {"http", "https"}, 28536), arcade_database=pipeline,
        arcade_user=combined["INDEX_ARCADEDB_USER"], arcade_password=combined["INDEX_ARCADEDB_PASSWORD"],
        cache_url=local(combined["INDEX_VALKEY_URL"], {"redis", "rediss"}, 28537),
        qdrant_key=combined["INDEX_QDRANT_API_KEY"])
    parsed = urlsplit(operator["ENHANCED_MEMORY_DATABASE_URL"])
    fixture_url = urlunsplit((parsed.scheme, parsed.netloc, "/" + target_name, parsed.query, ""))
    pool = await asyncpg.create_pool(fixture_url, min_size=1, max_size=3, command_timeout=30)
    try:
        embedder = LocalEmbeddings(MODEL, str(BASE / "model-cache"))
        service = MemoryService(pool, cipher, embedder, derived=DerivedRecall(sinks))
        await service.check_schema()
        result["checkpoint"] = "new_actual_store_namespaces"
        await sinks.provision(create_graph_database=True)
        result["actual_store_namespaces_provisioned"] = True
        worker = IndexWorker(service, sinks)
        async def drain():
            attempts = 0
            while await worker.run_once():
                attempts += 1
                if attempts > 2000:
                    raise ValueError("bounded_replay_budget_exceeded")
            async with pool.acquire() as conn:
                pending = await conn.fetchval("""SELECT count(*) FROM shared_memory.record_outbox o
                    LEFT JOIN shared_memory.index_deliveries d ON d.event_id=o.id AND d.pipeline=$1
                    WHERE d.completed_at IS NULL""", pipeline)
            if pending:
                raise ValueError("new_pipeline_has_unready_deliveries")
            return attempts
        result["checkpoint"] = "restored_outbox_replay"
        result["replayed_events"] = await drain()
        result["restored_outbox_replayed_to_actual_stores"] = True
        # All new edits are confined to a NEW invented scope in the disposable
        # database, never the completed historical test or any live record.
        scope = MemoryScope("qualification", "ix_" + suffix, "launch_recovery", "launch_recovery")
        peer = MemoryScope(scope.tenant, "peer_" + suffix, "launch_peer", "launch_peer")
        reviewer = MemoryScope(scope.tenant, scope.project, "launch_reviewer", "launch_reviewer", admin=True)
        text = "Invented launch recovery Cedar references Birch."
        result["checkpoint"] = "invented_disposable_scope"
        record = await service.remember(scope, text, idempotency_key="new-invented-recovery-" + suffix,
            knowledge_links=[{"subject": "Cedar", "predicate": "references", "object": "Birch",
                              "span_start": 0, "span_end": len(text)}])
        await drain()
        recalled = await service.recall(scope, "Cedar Birch")
        if recalled.get("vector_index") != "queried" or not any(r["id"] == record["id"] for r in recalled["results"]):
            raise ValueError("actual_vector_recall_failed")
        graph = await service.connections(scope, "Cedar", depth=1)
        if not graph.get("paths"):
            raise ValueError("actual_graph_recall_failed")
        cache_key = "ec:" + pipeline + ":" + identity.record(scope.tenant, scope.project, record["id"])
        cached = await sinks.cache.get(cache_key)
        if not cached or not json.loads(cached)["payload"].startswith("enc2:") or text in cached:
            raise ValueError("actual_cache_encryption_failed")
        try:
            await service.get(peer, record["id"])
        except KeyError:
            pass
        else:
            raise ValueError("restored_peer_scope_denial_failed")
        result["checkpoint"] = "reviewed_sharing_and_revocation"
        await service.share(reviewer, record["id"], target_project=peer.project, expected_version=1)
        await service.get(peer, record["id"])
        await service.share(reviewer, record["id"], target_project=peer.project, expected_version=1, revoke=True)
        try:
            await service.get(peer, record["id"])
        except KeyError:
            result["reviewed_sharing_and_revocation_passed"] = True
        else:
            raise ValueError("reviewed_sharing_revocation_failed")
        result["checkpoint"] = "disposable_record_withdrawal"
        await service.correct(scope, record["id"], expected_version=1, retract=True)
        await drain()
        if (await service.recall(scope, "Cedar Birch"))["results"] or (await service.connections(scope, "Cedar"))["paths"]:
            raise ValueError("actual_index_withdrawal_failed")
        if await sinks.cache.get(cache_key) is not None:
            raise ValueError("actual_cache_withdrawal_failed")
        result.update(complete=True, derived_store_recovery_qualified=True,
                      actual_qdrant_arcadedb_valkey_verified=True, actual_withdrawal_verified=True,
                      checkpoint="complete")
    finally:
        await pool.close()
        await sinks.close()


def main():
    import sys
    if os.geteuid() != 0 or Path(sys.prefix) != BASE / "runtime":
        raise SystemExit("ERR: use the staged protected Python as operator")
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    evidence = Path(tempfile.mkdtemp(prefix="ec-launch-index-recovery-", dir="/var/tmp"))
    result = {"source_revision": REVISION, "evidence": str(evidence), "complete": False,
              "derived_store_recovery_qualified": False, "live_indexes_changed": False,
              "live_canonical_edits": False, "service_runtime_changed": False,
              "fleet_launch_approved": False, "checkpoint": "protected_preflight"}
    try:
        asyncio.run(asyncio.wait_for(qualify(result), timeout=600))
    except BaseException as error:
        categories = {"operator_input_protection", "local_store_binding_required", "completed_disposable_recovery_required",
            "protected_index_settings_required", "admitted_model_required", "operator_store_credentials_incomplete",
            "bounded_replay_budget_exceeded", "new_pipeline_has_unready_deliveries", "actual_vector_recall_failed",
            "actual_graph_recall_failed", "actual_cache_encryption_failed", "restored_peer_scope_denial_failed",
            "reviewed_sharing_revocation_failed", "actual_index_withdrawal_failed", "actual_cache_withdrawal_failed"}
        result["category"] = str(error) if type(error) is ValueError and str(error) in categories else "actual_store_recovery_failed_preserve_evidence"
        status = getattr(getattr(error, "response", None), "status_code", None)
        if type(status) is int and 100 <= status <= 599:
            result["store_http_status"] = status
    (evidence / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
