#!/usr/bin/env python3
"""Select the Enhanced Cognee memory provider for every fleet profile.

User-space helper (no root): for each gateway profile with a config.yaml,
sets memory.provider=enhanced_cognee with a comment-preserving line edit,
a timestamped backup of the original, and a YAML readback verification.
Profiles already set are reported and left untouched.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

HOME = Path("/home/vincentspereira/.hermes")
PROFILES = HOME / "profiles"
PROVIDER = "enhanced_cognee"
PROVIDER_LINE = "  provider: enhanced_cognee\n"
TOP_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:")
MEMORY_KEY = re.compile(r"^memory:\s*$")
PROVIDER_KEY = re.compile(r"^\s+provider\s*:")


def require(value, category="fleet_provider_select_refused"):
    if not value:
        raise ValueError(category)


def select_provider(text: str) -> str | None:
    """Return updated config text, or None when already selected.

    Comment-preserving: only the provider line inside the top-level memory
    block changes; a missing memory section is appended."""
    lines = text.splitlines(keepends=True)
    memory_index = None
    for index, line in enumerate(lines):
        if MEMORY_KEY.match(line):
            memory_index = index
            break
        if TOP_KEY.match(line) and not line.startswith("memory:"):
            continue
    if memory_index is None:
        if not text.endswith("\n") and text:
            text += "\n"
        return text + "\nmemory:\n  provider: enhanced_cognee\n"
    end = len(lines)
    for index in range(memory_index + 1, len(lines)):
        if TOP_KEY.match(lines[index]):
            end = index
            break
    block = lines[memory_index + 1:end]
    existing = [line for line in block if PROVIDER_KEY.match(line)]
    if len(existing) == 1 and PROVIDER in existing[0]:
        return None
    kept = [line for line in block if not PROVIDER_KEY.match(line)]
    updated = lines[:memory_index + 1] + [PROVIDER_LINE] + kept + lines[end:]
    return "".join(updated)


def verify(path: Path):
    import yaml
    config = yaml.safe_load(path.read_text())
    require(isinstance(config, dict) and isinstance(config.get("memory"), dict)
            and config["memory"].get("provider") == PROVIDER, "readback_failed:" + path.name)


def main():
    require(sys.argv[1:] == [] and PROFILES.is_dir())
    changed, already, missing = [], [], []
    for profile in sorted(PROFILES.iterdir()):
        config = profile / "config.yaml"
        if not profile.is_dir() or not config.is_file():
            missing.append(profile.name)
            continue
        original = config.read_text()
        updated = select_provider(original)
        if updated is None:
            already.append(profile.name)
            continue
        backup = config.with_name("config.yaml-before-enhanced-cognee-" + uuid.uuid4().hex[:12])
        shutil.copy2(config, backup)
        require(backup.read_text() == original, "backup_mismatch:" + profile.name)
        config.write_text(updated)
        verify(config)
        changed.append(profile.name)
    print(json.dumps({"complete": True, "provider_selected": changed,
                      "already_selected": already, "no_config": missing,
                      "changed": len(changed), "already": len(already)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "fleet_provider_select_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError) else ""},
                         sort_keys=True))
        raise SystemExit(1)
