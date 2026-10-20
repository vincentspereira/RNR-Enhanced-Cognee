"""Operator-only streaming PostgreSQL backups encrypted with the age CLI.

No uploads, retention deletion, schedule installation or plaintext dump files.
Restore requires an authenticated complete backup and creates a fresh database.
Install pg_dump/pg_restore and the free age tools in the operator environment.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
from urllib.parse import urlsplit, unquote

from src.memory_admin import write_private_json


def _signature(manifest):
    key = os.environ["ENHANCED_BACKUP_SIGNING_KEY"].encode()
    if len(key) < 32:
        raise ValueError("A persistent backup signing key of at least 32 bytes is required")
    value = {k: v for k, v in manifest.items() if k != "signature"}
    return hmac.new(key, json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()


def _digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _environment(database=None):
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT"}}
    uri = urlsplit(os.environ.get("ENHANCED_MEMORY_DATABASE_URL", ""))
    if uri.scheme not in {"postgres", "postgresql"} or not uri.hostname or not uri.path.strip("/"):
        raise ValueError("Configure an explicit PostgreSQL operator URL")
    env.update(PGHOST=uri.hostname, PGPORT=str(uri.port or 5432), PGDATABASE=database or unquote(uri.path[1:]),
               PGUSER=unquote(uri.username or ""), PGPASSWORD=unquote(uri.password or ""))
    from urllib.parse import parse_qsl
    for key, value in parse_qsl(uri.query):
        if key in {"sslmode", "sslrootcert"}:
            env["PG" + key.upper()] = value
        else:
            raise ValueError("Unsupported backup connection option; configure it explicitly")
    return env


def _pipe(left, right, *, destination=None, left_env=None, right_env=None, timeout=600):
    """Bounded process lifetime and a streaming pipe; no shell or dump buffering."""
    processes = []
    try:
        first = subprocess.Popen(left, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=left_env)
        processes.append(first)
        second = subprocess.Popen(right, stdin=first.stdout, stdout=destination or subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, env=right_env)
        processes.append(second)
        first.stdout.close()
        second_status = second.wait(timeout=timeout)
        first_status = first.wait(timeout=30)
        if first_status or second_status:
            raise RuntimeError("Backup/restore stream did not complete")
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()


def backup(output: str, recipient: str, *, dump_command=None, age_command="age", env=None) -> dict:
    _signature({})  # Missing authentication configuration fails before any output.
    path = Path(output)
    if not path.is_absolute() or path.parent != path.parent.resolve(strict=True):
        raise ValueError("Use an absolute backup path without symlink parents")
    if not recipient or recipient.startswith("-") or len(recipient) > 200:
        raise ValueError("Configure a public age recipient")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        _pipe(dump_command or ["pg_dump", "--format=custom", "--no-owner", "--no-acl"],
              [age_command, "--encrypt", "--recipient", recipient], destination=handle,
              left_env=env if env is not None else _environment(),
              right_env={k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG"}})
        handle.flush()
        os.fsync(handle.fileno())
    manifest = {"format": "postgres-custom+age", "complete": True, "ciphertext_sha256": _digest(path),
                "created_utc": datetime.now(timezone.utc).isoformat(), "plaintext_dump_written": False,
                "signing_key_id": os.getenv("ENHANCED_BACKUP_SIGNING_KEY_ID", "backup_v1")}
    manifest["signature"] = _signature(manifest)
    write_private_json(str(path) + ".json", manifest)
    return manifest


def validate_backup(path: str, identity: str, *, age_command="age") -> None:
    manifest_path = Path(path + ".json")
    if manifest_path.stat().st_size > 4096:
        raise ValueError("Invalid backup completion manifest")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not isinstance(manifest.get("signature"), str):
        raise ValueError("Backup authentication failed; no signed manifest")
    if (manifest.get("signing_key_id") != os.getenv("ENHANCED_BACKUP_SIGNING_KEY_ID", "backup_v1")
            or not hmac.compare_digest(manifest["signature"], _signature(manifest))):
        raise ValueError("Backup authentication failed; manifest signature mismatch")
    if (manifest.get("format") != "postgres-custom+age" or manifest.get("complete") is not True
            or manifest.get("ciphertext_sha256") != _digest(path)):
        raise ValueError("Backup is incomplete or its ciphertext changed")
    result = subprocess.run([age_command, "--decrypt", "--identity", identity, path],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    if result.returncode:
        raise ValueError("Backup authentication failed; restore was not started")


async def restore(path: str, identity: str, new_database: str, *, restore_command=None) -> dict:
    import asyncpg
    if not re.fullmatch(r"memory_restore_[a-z0-9_]{1,40}", new_database):
        raise ValueError("Restore needs a fresh database named memory_restore_<unique-name>")
    await asyncio.to_thread(validate_backup, path, identity)
    conn = await asyncpg.connect(os.environ["ENHANCED_MEMORY_DATABASE_URL"])
    try:
        if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=$1)", new_database):
            raise ValueError("Restore target already exists; it will not be overwritten")
        await conn.execute(f"CREATE DATABASE {new_database}")
    finally:
        await conn.close()
    await asyncio.to_thread(_pipe, ["age", "--decrypt", "--identity", identity, path],
        restore_command or ["pg_restore", "--dbname", new_database, "--no-owner", "--no-acl", "--single-transaction", "--exit-on-error"],
        right_env=_environment(new_database))
    return {"database": new_database, "restored": True, "existing_databases_changed": False,
            "next_step": "Verify schema, decryption, project denial and retained history before real recovery"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--directory", required=True)
    create.add_argument("--recipient", required=True)
    recover = commands.add_parser("restore")
    recover.add_argument("--input", required=True)
    recover.add_argument("--identity", required=True)
    recover.add_argument("--new-database", required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            filename = datetime.now(timezone.utc).strftime("memory_%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8] + ".dump.age"
            result = backup(str(Path(args.directory) / filename), args.recipient)
        else:
            result = asyncio.run(restore(args.input, args.identity, args.new_database))
        print(json.dumps(result, ensure_ascii=True))
    except Exception:
        parser.exit(1, "Backup action stopped. Incomplete files/new restore databases are retained for review. No existing data was deleted.\n")


if __name__ == "__main__":
    main()
