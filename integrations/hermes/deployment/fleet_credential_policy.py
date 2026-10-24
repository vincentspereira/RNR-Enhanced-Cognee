"""Strict operator-owned admission policy for future fleet credential renewal.

This is policy admission, not an installed issuer or proof of native reload.
No caller-supplied signing algorithm/key, role, origin or executable is admitted.
Profile paths are validated as strings; root never walks an agent profile tree.
The issuer and its disabled timer must still pass installed lifecycle acceptance.
"""
from __future__ import annotations

import json
import os
from pathlib import PurePosixPath
import re
import stat


EXECUTABLE = "/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python"
ORIGIN = "http://127.0.0.1:28080"
FIELDS = {"name", "enabled", "user", "uid", "home", "profile", "tenant", "project_id",
          "subject", "agent_id", "roles", "lifetime_seconds", "origin", "executable",
          "reload_qualified", "launch_binding_qualified", "backup_qualified", "os_boundary_qualified"}


def absolute(value):
    if not isinstance(value, str) or not value.isascii() or "\x00" in value:
        raise ValueError("invalid_policy_path")
    path = PurePosixPath(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts:
        raise ValueError("invalid_policy_path")
    return path


def validate(value):
    if (not isinstance(value, dict) or set(value) != {"schema", "profiles"}
            or type(value["schema"]) is not int or value["schema"] != 1
            or not isinstance(value["profiles"], list) or not 1 <= len(value["profiles"]) <= 256):
        raise ValueError("invalid_policy_schema")
    names, paths, identities, scopes = set(), set(), set(), set()
    for row in value["profiles"]:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("invalid_policy_fields")
        for field in ("name", "user", "subject", "agent_id"):
            if not isinstance(row[field], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", row[field]):
                raise ValueError("invalid_policy_identity")
        for field in ("tenant", "project_id"):
            if not isinstance(row[field], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", row[field]):
                raise ValueError("invalid_policy_scope")
        if type(row["uid"]) is not int or not 1 <= row["uid"] < 2**31:
            raise ValueError("invalid_policy_uid")
        home, profile = absolute(row["home"]), absolute(row["profile"])
        if home == PurePosixPath("/") or not profile.is_relative_to(home / ".hermes"):
            raise ValueError("profile_outside_explicit_home")
        if (type(row["lifetime_seconds"]) is not int or row["lifetime_seconds"] != 86400
                or row["roles"] != ["api_client"] or row["origin"] != ORIGIN
                or row["executable"] != EXECUTABLE):
            raise ValueError("unapproved_signing_or_launch_choices")
        flags = ("enabled", "reload_qualified", "launch_binding_qualified", "backup_qualified", "os_boundary_qualified")
        if any(type(row[key]) is not bool for key in flags):
            raise ValueError("invalid_policy_gate")
        if row["enabled"] and not all(row[key] for key in flags[1:]):
            raise ValueError("profile_gates_incomplete")
        identity = (row["tenant"], row["project_id"], row["subject"], row["agent_id"])
        scope = (row["tenant"], row["project_id"])
        if row["name"] in names or str(profile) in paths or identity in identities or scope in scopes:
            raise ValueError("duplicate_policy_binding")
        names.add(row["name"])
        paths.add(str(profile))
        identities.add(identity)
        scopes.add(scope)
    # Return an independent copy: changing the parsed input cannot alter a plan.
    return json.loads(json.dumps(value))


def load(path):
    """Admit a bounded root-only policy via pinned, protected ancestors."""
    selected = absolute(str(path))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in selected.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("unprotected_policy_ancestor")
        file_fd = os.open(selected.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(file_fd, "rb") as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_nlink != 1 or info.st_size > 65536):
                raise ValueError("unprotected_policy_file")
            raw = source.read(65537)
            after = os.fstat(source.fileno())
            named = os.stat(selected.name, dir_fd=fd, follow_symlinks=False)
            fields = ("st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
            if (len(raw) != info.st_size or any(getattr(info, key) != getattr(after, key) for key in fields)
                    or named.st_dev != after.st_dev or named.st_ino != after.st_ino):
                raise ValueError("policy_changed_during_read")
        def unique(pairs):
            result = dict(pairs)
            if len(result) != len(pairs):
                raise ValueError("duplicate_policy_field")
            return result
        return validate(json.loads(raw, object_pairs_hook=unique))
    finally:
        os.close(fd)
