#!/usr/bin/env python3
"""Persistent model-budget ledger tools for the 2026-11-05 cutover.

Subcommands (stdlib only, ASCII output, never prints key material):

  verify         Stat + schema readback of the persistent ledger at
                 /var/lib/enhanced-cognee-llm-budget/tokens.sqlite3:
                 regular file, single link, mode 0600, owned by the API
                 service account, reservations table and budget_scope_day
                 index present.

  backup         Consistent sqlite snapshot (online backup API) encrypted
                 with age to the recipient from backup.json, plus an
                 HMAC-SHA256 signed manifest mirroring src/memory_backup.py.

  verify-backup  Signature, ciphertext digest, decrypt (restore path),
                 PRAGMA integrity_check and schema/row-count readback of an
                 encrypted ledger backup.

No service restarts, no credential values, no ledger mutations. Exit codes:
0 pass, 1 failed check, 2 configuration error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import sqlite3
import stat
import subprocess
import sys
import uuid

LEDGER = "/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3"
SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS reservations ("
    "id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL, "
    "day TEXT NOT NULL, tokens INTEGER NOT NULL CHECK(tokens >= 0), "
    "settled INTEGER NOT NULL DEFAULT 0 CHECK(settled IN (0,1)))",
    "CREATE INDEX IF NOT EXISTS budget_scope_day ON reservations(tenant,project,day)",
)


def _fail(name, message):
    print(json.dumps({"tool": name, "overall": "fail", "reason": message},
                     ensure_ascii=True))
    return 1


def _digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _signature(manifest: dict, key: bytes) -> str:
    if len(key) < 32:
        raise ValueError("A backup signing key of at least 32 bytes is required")
    value = {k: v for k, v in manifest.items() if k != "signature"}
    return hmac.new(key, json.dumps(value, sort_keys=True,
                                    separators=(",", ":")).encode(), hashlib.sha256).hexdigest()


def _load_credential(path: str) -> dict:
    with open(path, "rb") as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError("Backup credential exceeded its size limit")
    value = json.loads(raw)
    recipient = value.get("ENHANCED_BACKUP_RECIPIENT")
    key = value.get("ENHANCED_BACKUP_SIGNING_KEY")
    if (not isinstance(value, dict) or not isinstance(recipient, str)
            or not recipient or recipient.startswith("-") or len(recipient) > 200):
        raise ValueError("Configure a public age recipient")
    if not isinstance(key, str) or len(key.encode()) < 32:
        raise ValueError("A persistent backup signing key of at least 32 bytes is required")
    return {"recipient": recipient, "signing_key": key.encode(),
            "signing_key_id": value.get("ENHANCED_BACKUP_SIGNING_KEY_ID", "backup_v1")}


def _credential_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        raise ValueError("Pass --credential or run under systemd LoadCredential")
    return os.path.join(directory, "backup.json")


def _stat_checks(name: str, path: str, expect_uid: int) -> dict:
    info = os.lstat(path)
    mode = stat.S_IMODE(info.st_mode)
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or mode != 0o600 or info.st_uid != expect_uid):
        raise OSError("ledger is not a single-link 0600 file owned by uid %d" % expect_uid)
    return {"tool": name, "path": path, "uid": info.st_uid, "gid": info.st_gid,
            "mode": format(mode, "04o"), "nlink": info.st_nlink}


def _open_readonly(path: str) -> sqlite3.Connection:
    return sqlite3.connect("file:" + path + "?mode=ro", uri=True, timeout=5)


def _schema_facts(connection: sqlite3.Connection) -> dict:
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reservations'")]
    indexes = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='budget_scope_day'")]
    rows = connection.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    if not tables or not indexes:
        raise sqlite3.DatabaseError("ledger schema is incomplete")
    return {"table": "reservations", "index": "budget_scope_day", "rows": rows}


def _resolve_uid(name: str, explicit: int | None) -> int:
    if explicit:
        return explicit
    import pwd
    return pwd.getpwnam(name).pw_uid


def cmd_verify(args) -> int:
    try:
        report = _stat_checks("verify", args.ledger,
                              _resolve_uid(args.owner_name, args.expect_uid))
        with _open_readonly(args.ledger) as connection:
            report.update(_schema_facts(connection))
        report["overall"] = "pass"
        print(json.dumps(report, ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        return _fail("verify", str(exc))


def cmd_backup(args) -> int:
    try:
        credential = _load_credential(_credential_path(args.credential))
        _stat_checks("backup", args.ledger,
                     _resolve_uid(args.owner_name, args.expect_uid))
        source_digest = _digest(args.ledger)
        os.makedirs(args.output_dir, mode=0o700, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
        token = uuid.uuid4().hex[:8]
        snapshot = os.path.join(args.output_dir, "ledger-snapshot-%s-%s.sqlite3" % (stamp, token))
        fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        try:
            source = _open_readonly(args.ledger)
            destination = sqlite3.connect(snapshot)
            source.backup(destination)
            destination.close()
            source.close()
            output = os.path.join(args.output_dir,
                                  "ledger-%s-%s.sqlite3.age" % (stamp, token))
            out_fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(out_fd, "wb") as handle:
                with open(snapshot, "rb") as snapshot_handle:
                    result = subprocess.run([args.age_command, "--encrypt", "--recipient",
                                             credential["recipient"]], stdin=snapshot_handle,
                                            stdout=handle, stderr=subprocess.DEVNULL, timeout=600)
            if result.returncode:
                raise RuntimeError("age encryption failed")
            with _open_readonly(snapshot) as connection:
                rows = _schema_facts(connection)["rows"]
            manifest = {"format": "sqlite-snapshot+age", "complete": True,
                        "source_path": args.ledger, "source_sha256": source_digest,
                        "ciphertext_sha256": _digest(output), "rows": rows,
                        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "plaintext_snapshot_written": False,
                        "signing_key_id": credential["signing_key_id"]}
            manifest["signature"] = _signature(manifest, credential["signing_key"])
            manifest_path = output + ".json"
            manifest_fd = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                  | os.O_NOFOLLOW, 0o600)
            with os.fdopen(manifest_fd, "w", encoding="ascii") as handle:
                handle.write(json.dumps(manifest, ensure_ascii=True, sort_keys=True))
        finally:
            if os.path.lexists(snapshot):
                os.unlink(snapshot)
        print(json.dumps({"tool": "backup", "overall": "pass", "path": output,
                          "manifest": manifest_path,
                          "ciphertext_sha256": manifest["ciphertext_sha256"],
                          "rows": rows}, ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        return _fail("backup", str(exc))


def cmd_verify_backup(args) -> int:
    try:
        credential = _load_credential(_credential_path(args.credential))
        if os.lstat(args.backup + ".json").st_size > 4096:
            raise ValueError("Invalid backup completion manifest")
        with open(args.backup + ".json", "r", encoding="ascii") as handle:
            manifest = json.load(handle)
        if (not isinstance(manifest, dict)
                or manifest.get("signing_key_id") != credential["signing_key_id"]
                or not hmac.compare_digest(manifest.get("signature", ""),
                                           _signature(manifest, credential["signing_key"]))):
            raise ValueError("Backup authentication failed; manifest signature mismatch")
        if (manifest.get("format") != "sqlite-snapshot+age"
                or manifest.get("complete") is not True
                or manifest.get("ciphertext_sha256") != _digest(args.backup)):
            raise ValueError("Backup is incomplete or its ciphertext changed")
        decrypted = args.backup + ".verify-%s" % uuid.uuid4().hex[:8]
        fd = os.open(decrypted, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            result = subprocess.run([args.age_command, "--decrypt", "--identity",
                                     args.identity, args.backup], stdout=handle,
                                    stderr=subprocess.DEVNULL, timeout=600)
        try:
            if result.returncode:
                raise ValueError("Backup authentication failed; restore was not started")
            with _open_readonly(decrypted) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                facts = _schema_facts(connection)
            if integrity != "ok":
                raise ValueError("Decrypted ledger failed its integrity check")
            if manifest.get("rows") != facts["rows"]:
                raise ValueError("Decrypted ledger row count differs from the manifest")
        finally:
            if os.path.lexists(decrypted):
                os.unlink(decrypted)
        print(json.dumps({"tool": "verify-backup", "overall": "pass",
                          "path": args.backup, "integrity": "ok",
                          "rows": facts["rows"],
                          "ciphertext_sha256": manifest["ciphertext_sha256"]},
                         ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        return _fail("verify-backup", str(exc))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Enhanced Cognee ledger tools.").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(item):
        item.add_argument("--ledger", default=LEDGER)
        item.add_argument("--owner-name", default="enhanced-cognee-api")
        item.add_argument("--expect-uid", type=int, default=None)

    verify = sub.add_parser("verify", help="stat and schema readback")
    common(verify)
    verify.set_defaults(func=cmd_verify)

    backup = sub.add_parser("backup", help="snapshot + age-encrypt the ledger")
    common(backup)
    backup.add_argument("--output-dir", default="/var/backups/enhanced-cognee")
    backup.add_argument("--credential", default=None,
                        help="backup.json path (default: $CREDENTIALS_DIRECTORY)")
    backup.add_argument("--age-command", default="age")
    backup.set_defaults(func=cmd_backup)

    check = sub.add_parser("verify-backup", help="decrypt + verify a ledger backup")
    check.add_argument("--backup", required=True)
    check.add_argument("--identity", required=True,
                       help="root-only age identity file; read in-process")
    check.add_argument("--credential", default=None)
    check.add_argument("--age-command", default="age")
    check.set_defaults(func=cmd_verify_backup)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
