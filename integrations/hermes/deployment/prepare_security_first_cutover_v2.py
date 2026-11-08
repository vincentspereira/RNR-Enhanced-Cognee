"""Stage-only security-first API package. No install or activation feature.

Owner use requires a separately reviewed, protected installation of this file.
Use /usr/bin/python3 -I -S -B; never run a checkout copy as root.
All paths and payload hashes are embedded: no sibling inputs are imported/read.
"""
import hashlib
import json
import re
import shlex
import os
import stat
from pathlib import Path
import subprocess
import sys


class Refusal(Exception):
    """Only fixed reason codes may cross the CLI boundary."""


BASE = "/opt/enhanced-cognee-memory"
CANDIDATE = BASE + "/candidates/audit-c14f595c-20261101"
OLD = BASE + "/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529"
BUNDLE = BASE + "/cutover/security-first-c14f595c-20261101-v2"
INSTALLED_HELPER = BASE + "/security-first-helper-v2/prepare_security_first_cutover_v2.py"
UNIT = "enhanced-cognee-api.service"
SOURCE = "/etc/systemd/system/" + UNIT
SOURCES = (SOURCE, SOURCE + ".d/10-protected-stores.conf",
           SOURCE + ".d/20-launch-runtime.conf", SOURCE + ".d/30-llm.conf")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def proposed_dropin():
    return ("[Service]\nWorkingDirectory=" + CANDIDATE + "\nExecStart=\nExecStart="
            + CANDIDATE + "/runtime/bin/python -I -B -m src.memory_daemon api\n"
            "LoadCredential=\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n"
            "LoadCredential=index.json:/etc/enhanced-cognee/index.json\n").encode("ascii")


SAFE_ENV = frozenset({"ENHANCED_ENV=production", "ENHANCED_LOAD_DOTENV=0",
    "COGNEE_TELEMETRY_ENABLED=0", "COGNEE_LOG_FILE=false", "HF_HUB_OFFLINE=1",
    "PYTHONDONTWRITEBYTECODE=1", "PYTHONUNBUFFERED=1"})
SECTIONS = {
    "Unit": set("Description After Requires".split()),
    "Install": {"WantedBy"},
    "Service": set("Type DynamicUser LoadCredential WorkingDirectory ExecStart Restart RestartSec TimeoutStopSec UMask NoNewPrivileges PrivateTmp PrivateDevices ProtectHome ProtectSystem ProtectKernelTunables ProtectKernelModules ProtectControlGroups RestrictSUIDSGID RestrictNamespaces RestrictAddressFamilies CapabilityBoundingSet AmbientCapabilities MemoryMax CPUQuota TasksMax User Group Environment".split()),
}
LAUNCH_KEYS = {"User", "Group", "WorkingDirectory", "ExecStart", "Environment"}


def parse_unit(raw, *, launch=False):
    """Deliberately small systemd subset; do not approximate complex syntax."""
    def refuse():
        raise Refusal("unit_syntax_or_directive_refused")
    if len(raw) > 65536 or any(c < 32 and c != 10 or c > 126 for c in raw) or b"\\" in raw:
        refuse()
    section = None
    seen_sections = set()
    result = {}
    for line in raw.decode("ascii").split("\n"):
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            if section not in SECTIONS or section in seen_sections or launch and section != "Service":
                refuse()
            seen_sections.add(section)
            continue
        if section is None or line != line.strip() or "=" not in line:
            refuse()
        key, value = line.split("=", 1)
        if key not in SECTIONS[section] or launch and key not in LAUNCH_KEYS:
            refuse()
        previous = result.setdefault(key, [])
        if previous and not (launch and key == "ExecStart" and previous == [""] and value):
            refuse()
        if not value and key not in {"ExecStart", "CapabilityBoundingSet", "AmbientCapabilities"}:
            refuse()
        if key in {"User", "Group"} and value != "enhanced-cognee-api":
            refuse()
        if key == "Environment":
            try:
                pairs = shlex.split(value)
            except ValueError:
                refuse()
            if not pairs or len(pairs) != len(set(pairs)) or set(pairs) - SAFE_ENV:
                refuse()
        previous.append(value)
    if not result:
        refuse()
    if launch:
        expected = {"WorkingDirectory": [OLD],
                    "ExecStart": ["", OLD + "/runtime/bin/python -m src.memory_daemon api"]}
        if any(result.get(key) != value for key, value in expected.items()):
            refuse()
    return result


SOURCE_HASHES = {
    SOURCES[0]: "af979af033e64fee0dde16a1484ac5eb00ca75282c3478f382599027ec35dba2",
    SOURCES[1]: "6ae6c5ebf3ac141c5bd03c8ac6970c308eee4fe5220606b800c2e11f698cee06",
    SOURCES[3]: "12f118dd78e34477736a3e4a9db2d5d29bcafb199a77386f58b8cc45b5e60f33",
}
MODULE_HASHES = {
    "src/ingestion.py": "b814d10674a13ac6e7ed8f1be7de5eec5ae215109dafd85bf524d6f6ba94c32b",
    "src/llm_summarize.py": "e78c3c7fae47afe6c6228d6cab7b45387fb375f8c07ca37261a606e79a4010ae",
    "src/llm_budget.py": "81a4ddc2ef5aee073b814a428a112cabe3536f4e83cbd7a0e15c83522b8d10a7",
    "src/memory_api.py": "4f125fb6d01719440a0b6c614a7767bbe386c73756b19e232e1fd481a7b64dda",
    "src/memory_daemon.py": "c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20",
    "src/memory_library.py": "9ca8bec14760ca2793b175bf69d088ed1a78eb9a5a06a94a744929ec3aa4ef2f",
    "src/memory_queries.py": "be051d645535239d57677a8a9d05bf47929d9c80f5e49d3e3884ea47e9c275a3",
    "src/security/enterprise_auth.py": "78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e",
}
EXPECTED_LOADED = {
    "Id": UNIT, "Names": UNIT, "LoadState": "loaded", "ActiveState": "active",
    "FragmentPath": SOURCE, "SourcePath": "", "DropInPaths": " ".join(SOURCES[1:]),
    "NeedDaemonReload": "no", "User": "enhanced-cognee-api", "Group": "enhanced-cognee-api",
    "DynamicUser": "yes", "ProtectSystem": "strict", "StateDirectory": "",
    "StateDirectoryMode": "0755", "UMask": "0077", "PrivateUsers": "no", "RootDirectory": "",
    "WorkingDirectory": OLD, "ExecStart": OLD + "/runtime/bin/python -m src.memory_daemon api",
}


def plan_from_snapshot(snapshot):
    """Pure validation. Only hashes, fixed paths and known properties survive."""
    if (snapshot["inventory"] != list(SOURCES) or set(snapshot["source_bytes"]) != set(SOURCES)
            or snapshot["loaded"] != EXPECTED_LOADED or snapshot["candidate"] != CANDIDATE
            or snapshot["candidate_hashes"] != MODULE_HASHES):
        raise Refusal("inventory_or_loaded_or_candidate_drift")
    hashes = {p: digest(snapshot["source_bytes"][p]) for p in SOURCES}
    if any(hashes[p] != value for p, value in SOURCE_HASHES.items()):
        raise Refusal("source_hash_drift")
    credentials = []
    identity = {}
    dynamic = []
    for index, path in enumerate(SOURCES):
        parsed = parse_unit(snapshot["source_bytes"][path], launch=index == 2)
        credentials += parsed.get("LoadCredential", [])
        dynamic += parsed.get("DynamicUser", [])
        for key in ("User", "Group"):
            if key in parsed:
                identity[key] = parsed[key][0]
    # DynamicUser defaults apply to the whole effective unit, not each drop-in.
    # Every explicit identity was checked above, including overwritten values.
    user = identity.get("User")
    if user is None:
        user = UNIT[:-8] if UNIT.endswith(".service") else ""
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,30}", user) is None:
            raise Refusal("source_identity_drift")
    group = identity.get("Group", user)
    if (not dynamic or any(value != "yes" for value in dynamic)
            or snapshot["loaded"]["DynamicUser"] != "yes"
            or user != "enhanced-cognee-api" or group != "enhanced-cognee-api"
            or snapshot["loaded"]["User"] != user or snapshot["loaded"]["Group"] != group):
        raise Refusal("source_identity_drift")
    if credentials != [name + ":/etc/enhanced-cognee/" + name for name in ("api.json", "index.json", "llm.json")]:
        raise Refusal("credential_inventory_drift")
    return {
        "schema": 1, "phase": "A-stage-only", "bundle": BUNDLE,
        "candidate": CANDIDATE, "candidate_hashes": dict(MODULE_HASHES),
        "source_sha256": hashes, "loaded": dict(EXPECTED_LOADED),
        "helper_sha256": snapshot["helper_sha256"],
        "startup_interpreter": dict(snapshot["startup_interpreter"]),
        "dropin_sha256": digest(proposed_dropin()),
        "retained_credentials": ["api.json", "index.json"], "omitted_credentials": ["llm.json"],
        "activated": False, "services_restarted": False, "ledger_created": False,
        "credentials_issued": 0, "model_analysis_expected_enabled": False,
        "installation_pending": True, "model_usage_reset": False, "state_directory_proposed": False,
    }


def trusted_path(path, *, kind="file", allow_alias=False, private=False, executable=False,
                 stat_fn=os.lstat, readlink=os.readlink, _depth=0):
    """No symlink ancestors; only interpreter leaf aliases can be followed."""
    path = str(path)
    if (not path.startswith("/") or os.path.normpath(path) != path
            or path.startswith("//") or _depth > 16 or kind not in {"file", "directory"}):
        raise Refusal("unsafe_path")
    chain = list(reversed(Path(path).parents)) + [Path(path)]
    for index, item in enumerate(chain):
        info = stat_fn(str(item))
        leaf = index == len(chain) - 1
        if info.st_uid != 0 or info.st_gid != 0:
            raise Refusal("unsafe_path_owner")
        if stat.S_ISLNK(info.st_mode):
            if not (leaf and allow_alias and kind == "file" and info.st_nlink == 1):
                raise Refusal("unsafe_path_link")
            target = readlink(str(item))
            if not target.startswith("/"):
                target = os.path.join(str(item.parent), target)
            # Check each lexical directory before a later '..' can erase it.
            ancestor = "/"
            for component in target.split("/")[1:-1]:
                ancestor = os.path.normpath(os.path.join(ancestor, component))
                trusted_path(ancestor, kind="directory", stat_fn=stat_fn,
                             readlink=readlink, _depth=_depth + 1)
            return trusted_path(os.path.normpath(target), kind=kind, allow_alias=True,
                                private=private, executable=executable, stat_fn=stat_fn, readlink=readlink, _depth=_depth + 1)
        if info.st_mode & 0o022:
            raise Refusal("unsafe_path_mode")
        if leaf and kind == "file":
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or executable and not info.st_mode & 0o111:
                raise Refusal("unsafe_path_type_or_links")
        elif not stat.S_ISDIR(info.st_mode):
            raise Refusal("unsafe_path_type_or_links")
        if leaf and private and stat.S_IMODE(info.st_mode) != (0o700 if kind == "directory" else 0o600):
            raise Refusal("unsafe_private_mode")
    return path


def write_new(directory_fd, name, data):
    """Exclusive, no-follow file creation; errors intentionally leave evidence."""
    if "/" in name or name in {"", ".", ".."}:
        raise Refusal("unsafe_artifact_name")
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_bundle(path, files, *, guard=trusted_path, writer=write_new):
    """The parent must already be private. Never create parents or clean up."""
    if tuple(files) != ("40-audit-security-first.conf", "manifest.json", "receipt.json"):
        raise Refusal("artifact_inventory_refused")
    parent, name = os.path.split(path)
    guard(parent, kind="directory", private=True)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        bundle_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=parent_fd)
        try:
            guard(path, kind="directory", private=True)
            for filename, data in files.items():
                writer(bundle_fd, filename, data)
                guard(path + "/" + filename, private=True)
                fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                             dir_fd=bundle_fd)
                with os.fdopen(fd, "rb") as handle:
                    info = os.fstat(handle.fileno())
                    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                            or handle.read(len(data) + 1) != data):
                        raise Refusal("artifact_readback_failed")
            os.fsync(bundle_fd)
        finally:
            os.close(bundle_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def read_protected(path, *, guard=trusted_path, limit=32 * 1024 * 1024):
    guard(path)
    before = os.lstat(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info != before:
            raise Refusal("source_open_race_or_type")
        data = handle.read(limit + 1)
        if len(data) > limit or os.fstat(handle.fileno()) != info or os.lstat(path) != info:
            raise Refusal("source_read_race_or_size")
    return data


UNIT_ROOTS = (
    "/etc/systemd/system.control", "/run/systemd/system.control", "/run/systemd/transient",
    "/run/systemd/generator.early", "/etc/systemd/system", "/etc/systemd/system.attached",
    "/run/systemd/system", "/run/systemd/system.attached", "/run/systemd/generator",
    "/usr/local/lib/systemd/system", "/usr/lib/systemd/system", "/run/systemd/generator.late",
)


def show_properties(unit, keys, *, run=subprocess.run, guard=trusted_path):
    guard("/usr/bin/systemctl", allow_alias=True)
    args = ["/usr/bin/systemctl", "--no-pager", "--full", "show"]
    if unit:
        args.append(unit)
    args += ["--property=" + key for key in keys]
    result = run(args, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"},
                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                 timeout=20, check=False, shell=False)
    if result.returncode != 0 or len(result.stdout) > 65536:
        raise Refusal("loaded_state_inspection_failed")
    properties = {}
    for line in result.stdout.decode("ascii").splitlines():
        if "=" not in line:
            raise Refusal("loaded_state_format_refused")
        key, value = line.split("=", 1)
        if key not in keys or key in properties:
            raise Refusal("loaded_state_format_refused")
        properties[key] = value
    if set(properties) != set(keys):
        raise Refusal("loaded_state_format_refused")
    return properties


def read_loaded(*, run=subprocess.run, guard=trusted_path):
    properties = show_properties(UNIT, EXPECTED_LOADED, run=run, guard=guard)
    # Strip only known volatile execution-result metadata, not argv or commands.
    expected = re.escape("{ path=" + OLD + "/runtime/bin/python ; argv[]=" + EXPECTED_LOADED["ExecStart"]
                         + " ; ignore_errors=no ; start_time=")
    tail = r"[^;\n]* ; stop_time=[^;\n]* ; pid=[0-9]+ ; code=[A-Za-z0-9()_-]+ ; status=[A-Za-z0-9/()_-]+ }"
    if re.fullmatch(expected + tail, properties["ExecStart"]) is None:
        raise Refusal("loaded_command_drift")
    properties["ExecStart"] = EXPECTED_LOADED["ExecStart"]
    return properties


def inventory_sources(*, roots=None, exists=os.path.lexists, children=os.listdir, guard=trusted_path):
    if roots is None:
        value = show_properties(None, ("UnitPath",))["UnitPath"]
        roots = tuple(value.split(" "))
    if tuple(roots) != UNIT_ROOTS:
        raise Refusal("unit_search_path_drift")
    found = []
    for root in roots:
        if not exists(root):
            continue
        guard(root, kind="directory")
        unit = root + "/" + UNIT
        if exists(unit):
            guard(unit)
            found.append(unit)
        for suffix in ("service.d", "enhanced-.service.d", "enhanced-cognee-.service.d", UNIT + ".d"):
            directory = root + "/" + suffix
            if not exists(directory):
                continue
            guard(directory, kind="directory")
            names = sorted(children(directory))
            if directory != SOURCE + ".d" and names:
                raise Refusal("unanticipated_dropin_directory")
            for name in names:
                path = directory + "/" + name
                if path not in SOURCES[1:]:
                    raise Refusal("unanticipated_unit_source")
                guard(path)
                found.append(path)
    if sorted(found) != sorted(SOURCES):
        raise Refusal("unit_source_inventory_drift")
    return list(SOURCES)


def collect_snapshot(*, reader=read_protected, guard=trusted_path,
                     inventory=inventory_sources, loaded=read_loaded):
    first_inventory, first_loaded = inventory(), loaded()
    guard(CANDIDATE, kind="directory")
    lexical = CANDIDATE + "/runtime/bin/python"
    resolved = guard(lexical, allow_alias=True, executable=True)
    if resolved != lexical and re.fullmatch(r"/usr/bin/python3(?:\.[0-9]+)?", resolved) is None:
        raise Refusal("startup_interpreter_target_refused")
    snapshot = {
        "inventory": first_inventory, "loaded": first_loaded,
        "source_bytes": {path: reader(path) for path in SOURCES},
        "candidate": CANDIDATE,
        "candidate_hashes": {path: digest(reader(CANDIDATE + "/runtime/lib/python3.12/site-packages/" + path)) for path in MODULE_HASHES},
        "helper_sha256": digest(reader(INSTALLED_HELPER)),
        "startup_interpreter": {"lexical": lexical, "resolved": resolved, "sha256": digest(reader(resolved))},
    }
    if inventory() != first_inventory or loaded() != first_loaded:
        raise Refusal("snapshot_changed_during_inspection")
    return snapshot


def runtime_guard(*, euid=os.geteuid, egid=os.getegid, flags=None, helper=None,
                  executable=None, guard=trusted_path):
    flags = sys.flags if flags is None else flags
    helper = __file__ if helper is None else helper
    executable = sys.executable if executable is None else executable
    if (euid() != 0 or egid() != 0 or helper != INSTALLED_HELPER or executable != "/usr/bin/python3"
            or not all(getattr(flags, key, False) for key in
                       ("isolated", "no_site", "dont_write_bytecode", "safe_path"))):
        raise Refusal("protected_root_runtime_required")
    guard(INSTALLED_HELPER)
    guard("/usr/bin/python3", allow_alias=True)


def check_output(path=BUNDLE, *, guard=trusted_path):
    guard(str(Path(path).parent), kind="directory", private=True)
    if os.path.lexists(path):
        raise Refusal("output_already_exists")


def main(argv=None, *, runtime=runtime_guard, collector=collect_snapshot,
         output_guard=check_output, writer=write_bundle):
    """Injected Python seams are test-only; CLI has no path or safety overrides."""
    try:
        args = list(sys.argv[1:] if argv is None else argv)
        prepare = len(args) == 3 and args[:2] == ["--prepare", "--expected-plan-sha256"]
        if args != ["--plan"] and not (prepare and re.fullmatch(r"[0-9a-f]{64}", args[2])):
            raise Refusal("arguments_refused")
        runtime()
        output_guard()
        plan = plan_from_snapshot(collector())
        plan_hash = digest(canonical(plan))
        if not prepare:
            print(canonical({"plan": plan, "plan_sha256": plan_hash}).decode("ascii"), end="")
            return 0
        if args[2] != plan_hash or digest(canonical(plan_from_snapshot(collector()))) != plan_hash:
            raise Refusal("approved_plan_changed")
        runtime()
        output_guard()
        files = {"40-audit-security-first.conf": proposed_dropin(), "manifest.json": canonical(plan)}
        receipt = {
            "complete": True, "plan_sha256": plan_hash,
            "artifact_sha256": {name: digest(data) for name, data in files.items()},
            **{key: plan[key] for key in ("activated", "services_restarted", "ledger_created", "credentials_issued",
                 "model_analysis_expected_enabled", "installation_pending", "model_usage_reset")},
        }
        files["receipt.json"] = canonical(receipt)
        writer(BUNDLE, files)
        print(canonical(receipt).decode("ascii"), end="")
        return 0
    except Exception:
        # Never stringify exceptions: parsers, OS errors and subprocesses may carry secrets.
        print("ERR stage_only_refused", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
