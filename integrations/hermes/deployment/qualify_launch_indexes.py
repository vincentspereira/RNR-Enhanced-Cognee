"""Restore-derived NEW namespaces on actual local stores; preserve live indexes.

Use the protected candidate Python as operator. Only the already restored
disposable database is writable. New graph database/vector collection/cache
prefixes are retained on success and failure. No service/profile switch.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import uuid
from urllib.parse import urlsplit, urlunsplit


REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
BASE = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
RECOVERY = Path("/var/tmp/ec-launch-recovery-aja7p8j9/summary.json")
RETAINED = Path("/root/cognee-protected-continuation-20261020T190055Z")


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


def settings_protection(path):
    """Bounded metadata only; stop before entering an untrusted ancestor."""
    report = {"accepted": False, "configured_path": str(path)}
    if not path.is_absolute() or ".." in path.parts:
        return dict(report, reason="noncanonical_or_relative_path")
    if not any(path.is_relative_to(root) for root in (
            Path("/etc/enhanced-cognee"), Path("/opt/enhanced-cognee-memory"))):
        return dict(report, reason="outside_reviewed_operator_roots")
    for item in [*reversed(path.parents), path]:
        try:
            info = item.lstat()
        except OSError:
            return dict(report, reason="metadata_unavailable", component=str(item))
        reason = ("symlink" if stat.S_ISLNK(info.st_mode) else
                  "non_root_owner" if info.st_uid != 0 else
                  "group_or_other_writable" if info.st_mode & 0o022 else None)
        if reason:
            return dict(report, reason=reason, component=str(item), uid=info.st_uid,
                        mode=format(stat.S_IMODE(info.st_mode), "04o"))
        if item != path and not stat.S_ISDIR(info.st_mode):
            return dict(report, reason="ancestor_not_directory", component=str(item))
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
        return dict(report, reason="settings_type_or_size")
    return dict(report, accepted=True, reason="protected")


def protected_settings(path):
    if not settings_protection(path)["accepted"]:
        raise ValueError("protected_index_settings_required")


def credential_source(configured, binding):
    """Translate only the exact reviewed mount using effective systemd metadata."""
    mounted = Path("/run/credentials/enhanced-cognee-index.service/index.json")
    source = Path("/etc/enhanced-cognee/index.json")
    if configured != mounted:
        raise ValueError("service_index_credential_binding_unverified")
    if (not isinstance(binding, dict) or set(binding) != {"type", "data"}
            or binding["type"] != "a(ss)" or not isinstance(binding["data"], list)
            or len(binding["data"]) > 32
            or any(not isinstance(row, list) or len(row) != 2
                   or any(not isinstance(v, str) or len(v) > 4096 for v in row)
                   for row in binding["data"])):
        raise ValueError("service_index_credential_binding_unverified")
    selected = [row for row in binding["data"] if row[0] == "index.json"]
    if selected != [["index.json", str(source)]]:
        raise ValueError("service_index_credential_binding_unverified")
    return source


def operator_settings_path(configured):
    if configured.is_relative_to(Path("/run/credentials")):
        result = subprocess.run(["/usr/bin/busctl", "--system", "--json=short", "get-property",
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1/unit/enhanced_2dcognee_2dindex_2eservice",
            "org.freedesktop.systemd1.Service", "LoadCredential"], capture_output=True,
            timeout=10, check=False, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        if result.returncode or len(result.stdout) > 16384:
            raise ValueError("service_index_credential_binding_unverified")
        return credential_source(configured, json.loads(result.stdout))
    return configured


def retained_json(path):
    if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(RETAINED):
        raise ValueError("retained_authority_path_refused")
    for item in [*reversed(path.parents), path]:
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError("retained_authority_path_refused")
        if item != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError("retained_authority_path_refused")
    return private_json(path)


def authority_fields(settings, active):
    """Accept the existing real-store qualification contract, never guessed keys."""
    required = {"arcade_user", "arcade_password", "cache_url", "qdrant_url", "arcade_url"}
    if (not isinstance(settings, dict) or not required <= settings.keys()
            or any(not isinstance(settings[k], str) or not settings[k] for k in required)):
        raise ValueError("retained_authority_contract_unavailable")
    if any(settings[k].rstrip("/") != active[k].rstrip("/") for k in ("qdrant_url", "arcade_url")):
        raise ValueError("retained_authority_store_binding_differs")
    local(settings["qdrant_url"], {"http", "https"}, 28535)
    local(settings["arcade_url"], {"http", "https"}, 28536)
    local(settings["cache_url"], {"redis", "rediss"}, 28537)
    return {"INDEX_ARCADEDB_USER": settings["arcade_user"],
            "INDEX_ARCADEDB_PASSWORD": settings["arcade_password"],
            "INDEX_VALKEY_URL": settings["cache_url"]}


def unique_authority(candidates, active, result):
    matches = []
    for path, settings in candidates:
        try:
            value = authority_fields(settings, active)
        except (ValueError, KeyError, TypeError):
            continue
        matches.append((path, value))
    result["retained_authority_candidate_paths"] = [str(path) for path, _ in matches]
    # Compare in protected memory only. Never emit secret hashes or try multiple
    # credentials against a service to decide which one works.
    variants = {tuple(sorted(value.items())) for _, value in matches}
    if len(variants) != 1:
        raise ValueError("retained_authority_missing_or_ambiguous")
    result["store_authority_source"] = "unique_protected_retained_store_settings"
    return matches[0][1]


def discover_retained_authority(active, result):
    """Bounded config-only inspection of the observed deployment/fleet archive."""
    candidates = []
    pending = [(RETAINED, 0), (RETAINED / "fleet-223416", 0)]
    seen = set()
    inspected = 0
    skipped = 0
    protection_skips = []
    while pending:
        directory, depth = pending.pop()
        if directory in seen:
            continue
        seen.add(directory)
        try:
            info = directory.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            skipped += 1
            continue
        # Check trusted ancestors before listing; never enter an agent-owned
        # directory. The known private root is the scope of this search.
        for parent in [*reversed(directory.parents), directory]:
            metadata = parent.lstat()
            if metadata.st_uid != 0 or metadata.st_mode & 0o022 or stat.S_ISLNK(metadata.st_mode):
                raise ValueError("retained_authority_path_refused")
        entries = list(directory.iterdir())
        if len(entries) > 256 or len(seen) > 16:
            raise ValueError("retained_authority_search_budget")
        for path in sorted(entries):
            item = path.lstat()
            if (stat.S_ISDIR(item.st_mode) and directory.is_relative_to(RETAINED / "fleet-223416")
                    and depth < 2 and item.st_uid == 0 and not item.st_mode & 0o022
                    and any(word in path.name.lower() for word in ("index", "settings", "config"))):
                pending.append((path, depth + 1))
            if (not stat.S_ISREG(item.st_mode) or path.suffix != ".json"
                    or not any(word in path.name.lower() for word in ("index", "settings", "config", "environment"))):
                continue
            inspected += 1
            if inspected > 128:
                raise ValueError("retained_authority_search_budget")
            if item.st_uid != 0 or item.st_mode & 0o077 or item.st_size > 65536:
                skipped += 1
                protection_skips.append({"path": str(path), "uid": item.st_uid,
                    "mode": format(stat.S_IMODE(item.st_mode), "04o"), "size": item.st_size})
                continue
            try:
                document = retained_json(path)
            except (ValueError, OSError):
                skipped += 1
                continue
            candidates.append((path, document))
    result["retained_settings_files_inspected"] = inspected
    result["retained_settings_entries_skipped"] = skipped
    result["retained_settings_protection_skips"] = protection_skips
    return unique_authority(candidates, active, result)


def retained_authority(active, result):
    document = retained_json(RETAINED / "qualification-environment.json")
    if not isinstance(document, dict):
        raise ValueError("retained_authority_contract_unavailable")
    # Only structure/field names are diagnostic; values remain in root memory.
    result["retained_authority_field_names"] = sorted(k for k in document
        if isinstance(k, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,100}", k))
    environment = document
    for wrapper in ("environment", "env"):
        if wrapper in document:
            if not isinstance(document[wrapper], dict):
                raise ValueError("retained_authority_contract_unavailable")
            environment = document[wrapper]
            break
    selected = environment
    for name in ("RNR_QUALIFICATION_INDEX_SETTINGS", "index_settings_path", "index_settings"):
        if name in environment:
            reference = environment[name]
            if isinstance(reference, str):
                selected = retained_json(Path(reference))
            elif name == "index_settings" and isinstance(reference, dict):
                selected = reference
            else:
                raise ValueError("retained_authority_contract_unavailable")
            break
    try:
        authority = authority_fields(selected, active)
        result["store_authority_source"] = "protected_retained_real_store_qualification"
    except ValueError as error:
        if str(error) != "retained_authority_contract_unavailable":
            raise
        authority = discover_retained_authority(active, result)
    result["worker_permissions_changed"] = False
    return authority


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
    configured_path = Path(worker_config["ENHANCED_INDEX_CONFIG"])
    settings_path = operator_settings_path(configured_path)
    protected_settings(settings_path)
    result["operator_index_settings_source_verified"] = True
    settings = json.loads(settings_path.read_text())
    if settings.get("model") != MODEL or settings.get("dimensions") != 384:
        raise ValueError("admitted_model_required")
    # Prefer the protected operator identity. A worker lacking permission to
    # create new namespaces must fail; no ACL/grant is altered to make it pass.
    combined = dict(worker_config, **operator)
    if not all(k in operator for k in ("INDEX_ARCADEDB_USER", "INDEX_ARCADEDB_PASSWORD", "INDEX_VALKEY_URL")):
        combined.update(retained_authority(settings, result))
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
                    failed = await conn.fetchval("""SELECT EXISTS(SELECT 1 FROM shared_memory.index_deliveries
                        WHERE pipeline=$1 AND completed_at IS NULL AND error_code IS NOT NULL)""", pipeline)
                if failed:
                    raise ValueError("new_pipeline_has_unready_deliveries")
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
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    inspection = parser.add_mutually_exclusive_group()
    inspection.add_argument("--inspect-settings", action="store_true",
                        help="Read protection metadata only; no store connection or replay")
    inspection.add_argument("--inspect-store-authority", action="store_true",
                            help="Report protected config field/file names only; no secret values or store calls")
    args = parser.parse_args()
    if os.geteuid() != 0 or Path(sys.prefix) != BASE / "runtime":
        raise SystemExit("ERR: use the staged protected Python as operator")
    helper_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.inspect_store_authority:
        try:
            operator = private_json(Path("/etc/enhanced-cognee/operator.json"))
            worker = private_json(Path("/etc/enhanced-cognee/worker.json"))
            directory = Path("/etc/enhanced-cognee")
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                raise ValueError("operator_input_protection")
            names = list(directory.iterdir())
            if len(names) > 128:
                raise ValueError("operator_input_protection")
            report = {"operator_field_names": sorted(operator), "worker_field_names": sorted(worker),
                      "protected_json_file_names": sorted(p.name for p in names if p.suffix == ".json"),
                      "protected_file_names": sorted(p.name for p in names),
                      "operator_has_graph_identity_fields": all(k in operator for k in
                          ("INDEX_ARCADEDB_USER", "INDEX_ARCADEDB_PASSWORD")),
                      "operator_graph_identity_differs_from_worker":
                          operator.get("INDEX_ARCADEDB_USER") is not None and
                          operator.get("INDEX_ARCADEDB_USER") != worker.get("INDEX_ARCADEDB_USER")}
            # Historical reports locate preparation under /root/cognee-*.
            # List only matching deployment-directory metadata, never unrelated
            # root files, profile trees, file contents or recovery key values.
            retained = []
            for candidate in Path("/root").iterdir():
                if not candidate.name.startswith(("cognee-", "enhanced-cognee-")):
                    continue
                info = candidate.lstat()
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                    continue
                if len(retained) >= 32:
                    raise ValueError("operator_input_protection")
                entries = list(candidate.iterdir())
                if len(entries) > 256:
                    raise ValueError("operator_input_protection")
                retained.append({"directory": str(candidate),
                                 "entry_names": sorted(p.name for p in entries)})
            report["retained_deployment_directory_metadata"] = retained
        except Exception:
            report = {"category": "protected_authority_metadata_unavailable"}
        print(json.dumps({"stage": "store_authority_metadata_inspection", **report,
                          "secret_values_printed": False, "store_connections": False,
                          "live_state_changed": False}))
        return 0
    if args.inspect_settings:
        try:
            config = private_json(Path("/etc/enhanced-cognee/worker.json"))
            configured = Path(config["ENHANCED_INDEX_CONFIG"])
            selected = operator_settings_path(configured)
            report = dict(settings_protection(selected), configured_service_path=str(configured),
                          effective_systemd_source_verified=selected != configured)
        except Exception:
            report = {"accepted": False, "reason": "protected_config_metadata_unavailable"}
        print(json.dumps({"stage": "settings_protection_inspection", "settings_protection": report,
                          "store_connections": False, "replay_started": False, "live_state_changed": False}))
        return 0
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    evidence = Path(tempfile.mkdtemp(prefix="ec-launch-index-recovery-", dir="/var/tmp"))
    result = {"source_revision": REVISION, "evidence": str(evidence), "complete": False,
              "operator_helper_sha256": helper_sha256,
              "derived_store_recovery_qualified": False, "live_indexes_changed": False,
              "live_canonical_edits": False, "service_runtime_changed": False,
              "fleet_launch_approved": False, "checkpoint": "protected_preflight"}
    try:
        asyncio.run(asyncio.wait_for(qualify(result), timeout=600))
    except BaseException as error:
        categories = {"operator_input_protection", "local_store_binding_required", "completed_disposable_recovery_required",
            "protected_index_settings_required", "service_index_credential_binding_unverified",
            "admitted_model_required", "operator_store_credentials_incomplete",
            "retained_authority_path_refused", "retained_authority_contract_unavailable",
            "retained_authority_store_binding_differs",
            "retained_authority_missing_or_ambiguous", "retained_authority_search_budget",
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
