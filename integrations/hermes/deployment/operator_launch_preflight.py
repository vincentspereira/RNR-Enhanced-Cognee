"""Fixed read-only operator inventory. No installation, signing or model call.

Run with the system Python in isolated mode. Retain private receipts in a new
root-owned directory. The root parent never walks agent-owned profile trees;
the profile owner runs the hash-pinned metadata helper in a restricted child.
Only counts/flags and the private evidence location go to the terminal.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import tempfile


INVENTORY_SHA256 = "4ab67697f2a057d2182bb820b7d6b9c4ef686028360b9ae6f0685a473f3ccd75"
UNITS = ("enhanced-cognee-api.service", "enhanced-cognee-index.service",
         "enhanced-cognee-backup.service", "enhanced-cognee-backup.timer",
         "enhanced-cognee-profile-backup.service", "enhanced-cognee-profile-backup.timer")


def metadata(path):
    try:
        item = path.lstat()
    except FileNotFoundError:
        return {"present": False}
    return {"present": True, "uid": item.st_uid, "gid": item.st_gid,
            "mode": format(stat.S_IMODE(item.st_mode), "04o"),
            "symlink": stat.S_ISLNK(item.st_mode)}


def main():
    if os.geteuid() != 0:
        raise SystemExit("ERR: local operator authentication required")
    os.umask(0o077)
    evidence = Path(tempfile.mkdtemp(prefix="ec-launch-operator-", dir="/var/tmp"))
    result = {"source_revision": "21abf4857ca8dce8e0a3aafc725266c8d3754529",
              "installed_host_qualified": False, "fleet_launch_approved": False,
              "service_changed": False, "profiles_changed": False,
              "keys_read": False, "units": {}, "protected_files": {}}
    for name in UNITS:
        command = ["/usr/bin/systemctl", "show", name,
                   "--property=User,Group,ActiveState,SubState,FragmentPath,Result,LastTriggerUSec,NextElapseUSecRealtime"]
        process = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False,
                                 env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
        result["units"][name] = {"exit_code": process.returncode,
                                 "properties": dict(line.split("=", 1) for line in process.stdout.splitlines() if "=" in line)}
    for name in ("api.json", "worker.json", "operator.json", "backup.json"):
        result["protected_files"][name] = metadata(Path("/etc/enhanced-cognee") / name)
    # Inspect protection only; never load configuration or key values.
    api_path = Path("/etc/enhanced-cognee/api.json")
    info = api_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 65536:
        result["model_config_protection_valid"] = False
    else:
        # Keys remain in protected custody; do not read a config containing
        # signing material just to discover a model. Source metadata alone is
        # insufficient, so report the actual admitted-model gate unresolved.
        result["model_config_protection_valid"] = True
    result["configured_model_verified"] = False
    runtime = Path("/opt/enhanced-cognee-memory/runtime/lib/python3.12/site-packages")
    result["installed_memory_distributions"] = sorted(p.name for p in runtime.glob("rnr_enhanced_cognee_memory-*.dist-info"))
    result["backup_directories"] = {name: metadata(Path(name)) for name in (
        "/var/backups/enhanced-cognee", "/var/backups/enhanced-cognee-profiles")}
    helper = Path(__file__).with_name("inventory_fleet.py").read_bytes()
    if hashlib.sha256(helper).hexdigest() != INVENTORY_SHA256:
        raise SystemExit("ERR: metadata helper hash differs; no child started")
    account = pwd.getpwnam("hermes-runtime")
    child_output = evidence / "runtime-fleet.json"
    # Drop all groups/UID/GID before any agent path is inspected. There is no
    # signing key in stdin, argv or environment. Output has a strict size bound.
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(read_fd)
            os.setgroups([])
            os.setgid(account.pw_gid)
            os.setuid(account.pw_uid)
            os.chdir("/")
            os.environ.clear()
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
                os._exit(3)
            namespace = {"__name__": "fleet_metadata_child"}
            exec(compile(helper, "<verified-fleet-metadata>", "exec"), namespace)
            report = namespace["inventory"](Path(account.pw_dir) / ".hermes")
            raw = json.dumps(report, ensure_ascii=True).encode("ascii")
            if len(raw) > 1048576:
                os._exit(2)
            with os.fdopen(write_fd, "wb") as stream:
                stream.write(raw)
            os._exit(0)
        except BaseException:
            os._exit(1)
    os.close(write_fd)
    # poll bounds child time and accumulated bytes, retaining partial evidence.
    import select
    import time
    chunks = bytearray()
    deadline = time.monotonic() + 15
    complete = False
    while time.monotonic() < deadline and len(chunks) <= 1048576:
        if not select.select([read_fd], [], [], max(0, deadline - time.monotonic()))[0]:
            break
        raw = os.read(read_fd, 65536)
        if not raw:
            complete = True
            break
        chunks.extend(raw)
    os.close(read_fd)
    if not complete or len(chunks) > 1048576:
        import signal
        os.kill(pid, signal.SIGKILL)
    _, status = os.waitpid(pid, 0)
    child_output.write_bytes(chunks)
    result["runtime_inventory_complete"] = complete and status == 0
    if result["runtime_inventory_complete"]:
        receipt = json.loads(chunks)
        result["runtime_profile_directory_count"] = receipt["profile_directory_count"]
        result["runtime_unresolved_entries"] = len(receipt["unresolved_entries"])
    (evidence / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(json.dumps({"complete": result["runtime_inventory_complete"], "evidence": str(evidence),
                      "runtime_profile_directory_count": result.get("runtime_profile_directory_count"),
                      "configured_model_verified": False, "service_changed": False,
                      "fleet_launch_approved": False}))


if __name__ == "__main__":
    main()
