#!/usr/bin/env python3
"""Backup / list / restore workflow.

Demonstrates RNR Enhanced Cognee's disaster-recovery primitives. The
default flow exports each of the four DBs (Postgres / Qdrant /
ArcadeDB / Valkey) to a snapshot directory; a restore replays them
back. Verify the backup before treating it as authoritative.

Run:
    python examples/05_backup_and_restore.py

This script does NOT call `restore_backup` on a real running stack,
since that would clobber whatever state you have. It performs the
backup + verify + list flow and prints the restore command you'd run
manually.
"""

from __future__ import annotations

import sys
from typing import Any

import requests

MCP_BASE = "http://localhost:8080"


def call(tool: str, **params: Any) -> Any:
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


def main() -> int:
    print("=== RNR Enhanced Cognee: backup + restore dry-run ===\n")

    # 1. Trigger a full-stack backup. Returns a backup_id we can
    #    refer to later.
    print("[1/4] Creating backup of all four databases...")
    backup = call("create_backup", description="Example script dry-run")
    backup_id = backup.get("backup_id") if isinstance(backup, dict) else backup
    print(f"      backup_id: {backup_id}")
    print(f"      details:   {str(backup)[:400]}")

    # 2. Verify the backup actually contains the data we expect.
    print(f"\n[2/4] Verifying backup {backup_id}...")
    verification = call("verify_backup", backup_id=backup_id)
    print(f"      {str(verification)[:400]}")

    # 3. List all known backups (history view, e.g. for a UI).
    print("\n[3/4] Listing all backups on file...")
    backups = call("list_backups")
    # Pretty-print just the count + most-recent
    if isinstance(backups, list):
        print(f"      total backups: {len(backups)}")
        if backups:
            most_recent = backups[0]
            print(f"      most recent:   {str(most_recent)[:200]}")
    else:
        print(f"      {str(backups)[:400]}")

    # 4. Show -- but don't run -- the restore call. In production this
    #    would clobber whatever's currently in the stack.
    print(f"\n[4/4] To restore from this backup, you would run:")
    print(f"\n      curl -X POST {MCP_BASE}/tools/restore_backup \\")
    print(f"           -H 'Content-Type: application/json' \\")
    print(f"           -d '{{\"backup_id\": \"{backup_id}\"}}'")
    print("\n      ...or call('restore_backup', backup_id=backup_id) from Python.")

    print("\nOK -- backup dry-run complete. No data was restored.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.ConnectionError:
        print(
            f"ERR could not connect to MCP server at {MCP_BASE}.",
            file=sys.stderr,
        )
        sys.exit(2)
