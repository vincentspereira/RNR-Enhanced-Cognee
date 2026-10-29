"""Actual age encryption, PostgreSQL restore, history and project-denial proof."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest
from cryptography.fernet import Fernet

from src.memory_backup import backup, validate_backup, restore
from src.memory_service import MemoryService, MemoryScope
from src.encryption_manager import EncryptionManager


@pytest.mark.asyncio
@pytest.mark.parametrize("text_model", [False, True], ids=["canonical", "text-model-recovery"])
async def test_actual_encrypted_dump_restore_and_wrong_key_denial(tmp_path, monkeypatch, text_model):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url or not shutil.which("age") or not shutil.which("age-keygen"):
        pytest.skip("Requires an explicitly disposable DB and free age tools")
    container = os.getenv("RNR_QUALIFICATION_PG_CONTAINER")
    docker = os.getenv("RNR_QUALIFICATION_DOCKER", "docker")
    if not container and not (shutil.which("pg_dump") and shutil.which("pg_restore")):
        pytest.skip("Requires PostgreSQL client tools or an explicitly disposable PG container")
    embedder = None
    if text_model:
        cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
        if not cache:
            pytest.skip("Requires the explicit prepared offline text-model cache")
        from src.local_embeddings import LocalEmbeddings, MODEL, MODEL_FILES
        embedder = LocalEmbeddings(MODEL, cache)
    suffix = uuid.uuid4().hex[:16]
    source_name, target_name = "memory_backup_src_" + suffix, "memory_restore_" + suffix
    uri = urlsplit(url)

    def database_url(name):
        return urlunsplit((uri.scheme, uri.netloc, "/" + name, uri.query, ""))

    operator = await asyncpg.connect(url)
    await operator.execute(f"CREATE DATABASE {source_name}")
    await operator.close()
    source_url = database_url(source_name)
    monkeypatch.setenv("ENHANCED_MEMORY_DATABASE_URL", source_url)
    monkeypatch.setenv("ENHANCED_BACKUP_SIGNING_KEY", "synthetic-backup-manifest-signing-key-32bytes")
    source = await asyncpg.create_pool(source_url, min_size=1, max_size=2)
    cipher = EncryptionManager(master_key=Fernet.generate_key().decode())
    scope = MemoryScope("backup_fixture", "source", "alice", "hermes")
    try:
        service = MemoryService(source, cipher, embedder)
        await service.initialize()
        record = await service.remember(scope, "Synthetic backup cedar fixture", idempotency_key="backup")
        await service.correct(scope, record["id"], expected_version=1, content="Synthetic backup birch fixture")
        if text_model:
            semantic = await service.remember(scope, "Recovery copies are retained for thirty days.", idempotency_key="semantic")
            await service.remember(scope, "Lunch is served in the garden at noon.", idempotency_key="distractor")
            recalled = await service.recall(scope, "How long do we keep backups?", limit=1)
            assert recalled["retrieval"] == "semantic"
            assert recalled["results"][0]["id"] == semantic["id"]
        identity, wrong = tmp_path / "identity.txt", tmp_path / "wrong.txt"
        for path in (identity, wrong):
            subprocess.run(["age-keygen", "-o", str(path)], check=True, capture_output=True)
        recipient = subprocess.check_output(["age-keygen", "-y", str(identity)]).decode().strip()
        dump = [docker, "exec", container, "pg_dump", "-U", "postgres", "-d", source_name,
                "--format=custom", "--no-owner", "--no-acl"] if container else None
        path = tmp_path / "fixture.dump.age"
        result = backup(str(path), recipient, dump_command=dump)
        assert result["complete"] and not result["plaintext_dump_written"]
        assert path.stat().st_mode & 0o077 == 0 and b"birch" not in path.read_bytes()
        with pytest.raises(ValueError, match="authentication"):
            validate_backup(str(path), str(wrong))
        damaged = tmp_path / "damaged.age"
        damaged.write_bytes(path.read_bytes()[:-20])
        Path(str(damaged) + ".json").write_text(json.dumps(result | {
            "ciphertext_sha256": hashlib.sha256(damaged.read_bytes()).hexdigest()}))
        with pytest.raises(ValueError, match="authentication"):
            validate_backup(str(damaged), str(identity))
        restore_command = [docker, "exec", "-i", container, "pg_restore", "-U", "postgres", "-d", target_name,
                           "--no-owner", "--no-acl", "--single-transaction", "--exit-on-error"] if container else None
        restored_result = await restore(str(path), str(identity), target_name, restore_command=restore_command)
        assert restored_result["restored"] and not restored_result["existing_databases_changed"]
        with pytest.raises(ValueError, match="already exists"):
            await restore(str(path), str(identity), target_name, restore_command=restore_command)
        target = await asyncpg.create_pool(database_url(target_name), min_size=1, max_size=2)
        try:
            if text_model:
                # Restore the model to a separate cache and start a fresh
                # engine; never reuse the original model/session object.
                restored_cache = tmp_path / "restored-model"
                restored_cache.mkdir()
                for name in MODEL_FILES:
                    shutil.copyfile(Path(cache) / name, restored_cache / name)
                embedder = LocalEmbeddings(MODEL, str(restored_cache))
            recovered = MemoryService(target, cipher, embedder)
            await recovered.check_schema()
            assert (await recovered.get(scope, record["id"]))["content"] == "Synthetic backup birch fixture"
            with pytest.raises(KeyError):
                await recovered.get(MemoryScope(scope.tenant, "other", "alice", "hermes"), record["id"])
            async with target.acquire() as conn:
                assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_versions") == (4 if text_model else 2)
            if text_model:
                recalled = await recovered.recall(scope, "How long do we keep backups?", limit=1)
                assert recalled["retrieval"] == "semantic"
                assert recalled["results"][0]["id"] == semantic["id"]
                assert (await recovered.recall(MemoryScope(scope.tenant, "other", "alice", "hermes"),
                    "How long do we keep backups?"))["results"] == []
        finally:
            await target.close()
    finally:
        await source.close()
