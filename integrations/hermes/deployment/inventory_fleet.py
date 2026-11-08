"""Read only profile metadata as its owning user; never inspect secret values.

Run separately under each launch identity. Root is deliberately refused: the
operator must not traverse agent-owned profile trees. Output contains private
profile names and belongs in a new private evidence file, outside publication.
No profile is qualified or enrolled by this inventory.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat


LIMIT = 256
MARKERS = ("config.yaml", "enhanced_cognee.json", ".env", "auth.json",
           "state.db", "state.db-wal", "state.db-shm", "workspace")


def open_home(path: Path, uid: int) -> int:
    """Pin each ancestor without following redirects; inspect only our home."""
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute_home_required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            if info.st_uid not in {0, uid} or (info.st_mode & 0o022 and not sticky_root):
                raise ValueError("unsafe_home_ancestor")
        if os.fstat(fd).st_uid != uid:
            raise ValueError("home_owner_mismatch")
        return fd
    except BaseException:
        os.close(fd)
        raise


def profile_metadata(fd: int, name: str, uid: int) -> dict:
    info = os.fstat(fd)
    markers = {}
    for marker in MARKERS:
        try:
            item = os.stat(marker, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            markers[marker] = {"present": False}
            continue
        markers[marker] = {"present": True, "uid": item.st_uid,
                           "mode": format(stat.S_IMODE(item.st_mode), "04o"),
                           "symlink": stat.S_ISLNK(item.st_mode),
                           "regular": stat.S_ISREG(item.st_mode),
                           "directory": stat.S_ISDIR(item.st_mode)}
    return {"profile": name, "uid": info.st_uid,
            "mode": format(stat.S_IMODE(info.st_mode), "04o"),
            "owner_matches_launch_user": info.st_uid == uid,
            "markers": markers, "admission": "pending",
            "scope_mapping": None, "launch_binding_verified": False,
            "backup_membership_verified": False, "credential_reload_verified": False}


def inventory(home: Path) -> dict:
    uid = os.geteuid()
    if uid == 0:
        raise ValueError("run_as_profile_owner_not_root")
    fd = open_home(home, uid)
    try:
        profiles = [profile_metadata(fd, "main", uid)]
        unresolved = []
        try:
            directory = os.open("profiles", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        except FileNotFoundError:
            directory = None
        if directory is not None:
            try:
                info = os.fstat(directory)
                if info.st_uid != uid:
                    raise ValueError("unsafe_profiles_directory")
                if info.st_mode & 0o022:
                    # Metadata-only inspection may continue. This directory is
                    # never admitted as a protected credential publication path.
                    unresolved.append({"entry": "profiles", "category": "writable_profiles_directory"})
                names = os.listdir(directory)
                if len(names) > LIMIT:
                    raise ValueError("profile_inventory_budget_exceeded")
                for name in sorted(names):
                    item = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if stat.S_ISLNK(item.st_mode):
                        unresolved.append({"entry": name, "category": "symlink_not_followed"})
                        continue
                    if not stat.S_ISDIR(item.st_mode):
                        continue
                    if item.st_uid != uid:
                        unresolved.append({"entry": name, "category": "other_owner_not_entered"})
                        continue
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        after = os.fstat(child)
                        if (item.st_dev, item.st_ino, item.st_uid) != (after.st_dev, after.st_ino, after.st_uid):
                            raise ValueError("profile_changed_during_inventory")
                        profiles.append(profile_metadata(child, name, uid))
                    finally:
                        os.close(child)
            finally:
                os.close(directory)
        return {"schema": 1, "uid": uid, "profile_directory_count": len(profiles),
                "profiles": profiles, "unresolved_entries": unresolved,
                "unresolved_launch_mechanisms": ["gateway", "cron", "system_timers",
                    "user_timers", "persistent_sessions", "other_accounts"],
                "fleet_inventory_complete": False, "fleet_launch_approved": False}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.home)
    # Refuse replacement, links and output in an unprotected evidence directory.
    directory = open_home(args.output.absolute().parent, os.geteuid())
    try:
        if stat.S_IMODE(os.fstat(directory).st_mode) != 0o700:
            raise ValueError("private_evidence_directory_required")
        fd = os.open(args.output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            json.dump(result, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(directory)
    finally:
        os.close(directory)
    print(json.dumps({"profile_directory_count": result["profile_directory_count"],
                      "unresolved_entries": len(result["unresolved_entries"]),
                      "fleet_inventory_complete": False, "fleet_launch_approved": False}))


if __name__ == "__main__":
    main()
