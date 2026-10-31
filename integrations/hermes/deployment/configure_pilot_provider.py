"""Select the pilot MemoryProvider and check native authenticated reads only.

Execute the hash-verified blob as hermes-runtime under no-new-privileges using
the protected tools1 Python. Never run this helper as root. No chat/model route,
secret migration, memory-record write, gateway or fleet activation is performed.
"""
from __future__ import annotations

import contextlib
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import sys
import uuid


HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
ARTIFACT = Path("/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-29cb9fa3400a")
TOKEN_NAME = "ENHANCED_COGNEE_ACCESS_TOKEN"
SETTINGS = {"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}
FILES = {"enhanced_cognee.json": (json.dumps(SETTINGS, ensure_ascii=True, indent=2) + "\n").encode(),
         "config.yaml": b"memory:\n  provider: enhanced_cognee\n"}
HASHES = {
    "__init__.py": "b221c38baab2c2915f42683e0b8e764be0a42bc3d160f9ab786fd8ea64da6a0a",
    "client.py": "8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "plugin.yaml": "c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}


class ConfigurationError(RuntimeError):
    """Only fixed public diagnostics may leave the restricted check."""


def open_profile(uid):
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in (None, *PROFILE.parts[1:]):
            if name is not None:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            if info.st_uid not in {0, uid} or info.st_mode & 0o022:
                raise ConfigurationError("Pilot directory protection needs review.")
        info = os.fstat(fd)
        if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
            raise ConfigurationError("Pilot ownership/privacy needs review.")
        return fd
    except BaseException:
        os.close(fd)
        raise


def private_bytes(directory, name, uid):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or before.st_size > 65536):
            raise ConfigurationError("Pilot file protection needs review.")
        raw = handle.read(65537)
        after = os.fstat(handle.fileno())
        if (len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ConfigurationError("A pilot file changed during inspection.")
        return raw


def publish(directory, source, target):
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(directory, os.fsencode(source), directory, os.fsencode(target), 1) != 0:
        raise ConfigurationError("Configuration publication refused; all existing/prepared files retained.")


def check_existing(directory, uid):
    missing = []
    for name, expected in FILES.items():
        try:
            raw = private_bytes(directory, name, uid)
        except FileNotFoundError:
            missing.append(name)
            continue
        if raw != expected:
            raise ConfigurationError("Existing pilot configuration differs; preserved without overwrite.")
    return missing


def create_settings(directory, uid):
    # Inspect BOTH destinations before writing either. Matching interrupted
    # installations can resume, but later owner/model edits are never overwritten.
    missing = check_existing(directory, uid)
    created = []
    for name in missing:
        raw = FILES[name]
        stage = ".cognee-pilot-config-" + uuid.uuid4().hex
        fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if private_bytes(directory, stage, uid) != raw:
            raise ConfigurationError("Prepared pilot settings did not verify; retained.")
        publish(directory, stage, name)
        os.fsync(directory)
        created.append(name)
    if check_existing(directory, uid):
        raise ConfigurationError("Pilot settings publication is incomplete.")
    return created


def verify_artifact():
    for path in (ARTIFACT, *ARTIFACT.parents):
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                or os.access(path, os.W_OK, effective_ids=True)):
            raise ConfigurationError("Protected provider directory needs review.")
    if set(os.listdir(ARTIFACT)) != set(HASHES):
        raise ConfigurationError("Protected provider contents differ.")
    for name, expected in HASHES.items():
        fd = os.open(ARTIFACT / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022
                    or info.st_nlink != 1 or info.st_size > 65536
                    or os.access(ARTIFACT / name, os.W_OK, effective_ids=True)
                    or hashlib.sha256(handle.read(65537)).hexdigest() != expected):
                raise ConfigurationError("Protected provider payload differs.")
    link = PROFILE / "plugins/enhanced_cognee"
    info = link.lstat()
    if (not stat.S_ISLNK(info.st_mode) or info.st_uid != os.geteuid()
            or os.readlink(link) != str(ARTIFACT) or link.resolve(strict=True) != ARTIFACT):
        raise ConfigurationError("The pilot provider link differs; preserved.")


def qualify_provider(provider):
    status = json.loads(provider.handle_tool_call("enhanced_status", {}))
    if (not isinstance(status, dict) or status.get("ready") is not True
            or status.get("tenant_id") != "qualification" or status.get("project_id") != "hermes_pilot"
            or status.get("subject") != "hermes_pilot_runtime" or status.get("capture") != "selected"
            or status.get("notebook_mirroring") is not False or status.get("schema_version") != 3
            or status.get("encryption") != "AES-256-GCM" or type(status.get("active_records")) is not int
            or status["active_records"] != 0):
        raise ConfigurationError("Native provider authenticated status/scope differs.")
    recalled = json.loads(provider.handle_tool_call("enhanced_recall", {
        "query": "Invented pilot connector qualification fixture", "limit": 1}))
    if not isinstance(recalled, dict) or recalled.get("results") != [] or "error" in recalled:
        raise ConfigurationError("Native provider empty-scope recall did not pass.")


def main():
    phase = "identity"
    try:
        os.umask(0o077)
        account = pwd.getpwuid(os.geteuid())
        fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
        if (account.pw_name != "hermes-runtime" or account.pw_uid == 0 or Path(account.pw_dir) != HOME
                or os.environ.get("HERMES_HOME") != str(PROFILE)
                or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
                or fields.get("NoNewPrivs", "").strip() != "1"
                or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))
                or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
            raise ConfigurationError("Use the approved restricted tools1 launch.")
        os.chdir(HOME)
        phase = "profile_preflight"
        directory = open_profile(account.pw_uid)
        try:
            env_before = private_bytes(directory, ".env", account.pw_uid)
            check_existing(directory, account.pw_uid)
            phase = "artifact_verification"
            verify_artifact()
            # Capture framework chatter, not secrets, into bounded-lifetime local
            # streams. Only the fixed summary or phase reaches the operator.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                phase = "native_contract"
                sys.path.insert(0, str(RELEASE / "repo"))
                import hermes_bootstrap
                from hermes_constants import get_hermes_home
                import agent.memory_provider as api
                import agent.secret_scope as secrets
                import plugins.memory as loader
                if (Path(get_hermes_home()).resolve() != PROFILE
                        or any(not Path(module.__file__).resolve().is_relative_to(RELEASE / "repo")
                               for module in (api, secrets, loader))):
                    raise ConfigurationError("The native Hermes contract/profile differs.")
                phase = "credential_scope"
                token = secrets.load_env_file(PROFILE / ".env").get(TOKEN_NAME)
                if not isinstance(token, str) or not token or private_bytes(directory, ".env", account.pw_uid) != env_before:
                    raise ConfigurationError("The installed ordinary pilot credential needs review.")
                binding = secrets.set_secret_scope({TOKEN_NAME: token}, profile_home=str(PROFILE))
                try:
                    phase = "settings_publication"
                    created = create_settings(directory, account.pw_uid)
                    phase = "provider_selection"
                    if loader._get_active_memory_provider() != "enhanced_cognee":
                        raise ConfigurationError("Hermes did not select the configured pilot provider.")
                    found = loader.find_provider_dir("enhanced_cognee")
                    if found is None or found.resolve() != ARTIFACT:
                        raise ConfigurationError("Native provider discovery selected another source.")
                    provider = loader.load_memory_provider("enhanced_cognee", register_skills=False)
                    if not isinstance(provider, api.MemoryProvider) or provider.name != "enhanced_cognee":
                        raise ConfigurationError("Native provider loading failed.")
                    try:
                        phase = "provider_initialization"
                        provider.initialize("pilot_connector_qualification", hermes_home=str(PROFILE), agent_context="primary")
                        phase = "authenticated_provider_reads"
                        qualify_provider(provider)
                    finally:
                        provider.shutdown()
                finally:
                    secrets.reset_secret_scope(binding)
            phase = "readback"
            if check_existing(directory, account.pw_uid) or private_bytes(directory, ".env", account.pw_uid) != env_before:
                raise ConfigurationError("Pilot settings or credential file changed during qualification.")
        finally:
            os.close(directory)
    except Exception:
        print(json.dumps({"complete": False, "failure_stage": phase,
                          "existing_and_prepared_files_retained": True}, indent=2))
        raise SystemExit(1) from None
    print(json.dumps({"complete": True, "effective_user": account.pw_name, "profile": str(PROFILE),
                      "created_settings": created, "provider_selected": True,
                      "native_provider_initialized": True, "authenticated_provider_status_passed": True,
                      "empty_scope_recall_passed": True, "capture_policy": "selected",
                      "reviewed_sharing_enabled": True, "credential_file_unchanged": True,
                      "chat_model_called": False, "memory_records_written": False,
                      "runtime_qualified": False}, indent=2))


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified restricted operator command.")
