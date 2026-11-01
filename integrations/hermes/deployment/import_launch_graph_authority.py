"""Terminal-only import of existing local graph authority; no service calls.

Creates one new root-only file, never replaces an existing one. Does not read
an agent-owned .env, grant permissions, reset passwords or activate services.
"""
from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import stat
import sys

DESTINATION = Path("/etc/enhanced-cognee/launch-index-authority.json")


def authority_document(username, password):
    if (not isinstance(username, str) or not username or len(username) > 128
            or not username.isascii() or any(c.isspace() or c == ":" for c in username)
            or username in {"ARCADEDB_PASSWORD", "ARCADEDB_USER", "ARCADEDB_USERNAME",
                            "INDEX_ARCADEDB_USER", "INDEX_ARCADEDB_PASSWORD"}
            or not isinstance(password, str) or not password or len(password) > 4096
            or any(c in password for c in "\x00\r\n")):
        raise ValueError("invalid_local_graph_identity")
    return {"INDEX_ARCADEDB_USER": username, "INDEX_ARCADEDB_PASSWORD": password}


def main():
    if os.geteuid() != 0 or not sys.stdin.isatty():
        raise ValueError("root_operator_terminal_required")
    for parent in reversed(DESTINATION.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("protected_parent_required")
    if os.path.lexists(DESTINATION):
        raise ValueError("existing_authority_preserved_no_overwrite")
    username = input("Existing ArcadeDB username (matching the password; no guessing): ")
    password = getpass.getpass("Existing ARCADEDB_PASSWORD (hidden): ")
    document = authority_document(username, password)
    del password
    os.umask(0o077)
    fd = os.open(DESTINATION, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        json.dump(document, stream, ensure_ascii=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    del document
    directory = os.open(DESTINATION.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    print(json.dumps({"complete": True, "protected_operator_file_created": True,
        "credential_authenticated": False, "source_env_changed": False,
        "service_changed": False, "worker_privileges_changed": False,
        "credential_exposure_resolved": False, "fleet_launch_approved": False}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError):
        # Never stringify exceptions from credential processing or file writes.
        print('{"complete":false,"category":"operator_import_refused_preserve_existing"}')
        raise SystemExit(1)
