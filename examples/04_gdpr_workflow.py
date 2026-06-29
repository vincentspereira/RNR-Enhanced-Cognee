#!/usr/bin/env python3
"""GDPR primitives: consent / export / erasure.

Demonstrates the right-to-erasure flow that RNR Enhanced Cognee exposes for
compliance with GDPR Articles 15 (access) and 17 (erasure). The MCP
server emits tenant-scoped operations so a single RNR Enhanced Cognee
instance can serve many isolated users.

Run:
    python examples/04_gdpr_workflow.py
"""

from __future__ import annotations

import json
import sys
import uuid
from typing import Any

import requests

MCP_BASE = "http://localhost:8080"


def call(tool: str, **params: Any) -> Any:
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


def main() -> int:
    print("=== RNR Enhanced Cognee: GDPR right-to-erasure workflow ===\n")

    # Use a fresh user_id so each run is independent.
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    print(f"Acting as user_id={user_id}\n")

    # 1. Record explicit consent. Without consent, downstream personal-data
    #    ingestion should be refused or scrubbed.
    print("[1/5] Recording consent (GDPR Art. 6 lawful basis)...")
    call(
        "gdpr_record_consent",
        user_id=user_id,
        purpose="memory-storage",
        granted=True,
        metadata=json.dumps({"source": "example-script"}),
    )
    print("      consent recorded.")

    # 2. List the consents on file (for the user-facing privacy dashboard).
    print("\n[2/5] Listing consents on file...")
    consents = call("gdpr_list_consents", user_id=user_id)
    print(f"      {str(consents)[:300]}")

    # 3. Verify tenant isolation -- the MCP server enforces that this
    #    user_id can only see their own data.
    print("\n[3/5] Verifying tenant isolation...")
    isolation = call("gdpr_verify_tenant_isolation", user_id=user_id)
    print(f"      {str(isolation)[:300]}")

    # 4. Add a couple of memories under the user, then export everything
    #    (GDPR Art. 15 -- right of access).
    print("\n[4/5] Adding 2 memories then exporting all user data...")
    call(
        "add_memory",
        content="User prefers email digests at 09:00 UTC.",
        user_id=user_id,
        agent_id="example-agent-04",
    )
    call(
        "add_memory",
        content="User's primary timezone is Europe/Berlin.",
        user_id=user_id,
        agent_id="example-agent-04",
    )
    export = call("gdpr_export_user_data", user_id=user_id)
    print(f"      export payload preview: {str(export)[:400]}")

    # 5. Right-to-erasure -- delete every trace of the user.
    print("\n[5/5] Deleting all user data (GDPR Art. 17)...")
    deletion = call("gdpr_delete_user_data", user_id=user_id)
    print(f"      deletion result: {str(deletion)[:300]}")

    # Confirm: a subsequent export should be empty / not-found.
    print("\n      confirming erasure -- re-export should be empty:")
    try:
        empty_export = call("gdpr_export_user_data", user_id=user_id)
        print(f"      {str(empty_export)[:200]}")
    except Exception as exc:
        print(f"      (expected) {exc}")

    print("\nOK -- GDPR workflow complete.")
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
