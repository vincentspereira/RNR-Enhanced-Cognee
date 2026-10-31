#!/usr/bin/env python3
"""Inspect the staged credential rotation (phase 1 of the executor).

Root-only, read-only: inventories the staged candidate directory under
/var/lib/enhanced-cognee-rotation - directory names, file names, sizes and
JSON KEY NAMES only. Never prints a value of any credential, current or
candidate. The owner pastes the sanitized inventory back so the apply
phase is written against the real staged layout instead of a guess.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path("/var/lib/enhanced-cognee-rotation")


def require(value, category="rotation_inspect_refused"):
    if not value:
        raise ValueError(category)


def key_names(path: Path):
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return ["<unparseable>"]
    if isinstance(value, dict):
        return sorted(value)[:32]
    if isinstance(value, list):
        return ["<list:%d>" % len(value)]
    return ["<%s>" % type(value).__name__]


def main():
    require(os.geteuid() == 0 and os.uname().nodename == "Ubuntu-Hermes",
            "root_on_gateway_host")
    require(ROOT.is_dir(), "staged_rotation_missing")
    inventory = {}
    for entry in sorted(ROOT.iterdir()):
        if entry.is_dir():
            children = {}
            for child in sorted(entry.iterdir()):
                children[child.name] = {
                    "bytes": child.stat().st_size,
                    "keys": key_names(child) if child.suffix == ".json"
                    else ["<%s>" % child.suffix or "file"],
                }
            inventory[entry.name] = {"kind": "dir", "children": children}
        else:
            inventory[entry.name] = {
                "kind": "file", "bytes": entry.stat().st_size,
                "keys": key_names(entry) if entry.suffix == ".json" else []}
    print(json.dumps({"complete": True, "staged_root": str(ROOT),
                      "inventory": inventory}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "rotation_inspect_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError)
                          else ""}), flush=True)
        raise SystemExit(1)
