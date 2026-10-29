"""Stage the pinned provider, then verify registration as hermes-runtime.

Only stdlib runs as root. No service keys are read; the child creates only a
pilot plugin link. No token, model configuration or active provider is selected.
Invoke through the reviewed four-file Git archive, not a mutable checkout import.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import uuid


RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
PARENT = Path("/opt/hermes-runtime/providers")
ARTIFACT_NAME = "enhanced-cognee-0.1.0-launch-fcc7be3d7659"
ARTIFACT = PARENT / ARTIFACT_NAME
HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
HASHES = {
    "__init__.py": "fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061",
    "client.py": "8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "plugin.yaml": "c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}
TOOLS = {"enhanced_recall", "enhanced_remember", "enhanced_get", "enhanced_correct",
         "enhanced_retract", "enhanced_status", "enhanced_clarify", "enhanced_connections"}
PHASES = {"identity", "artifact_protection", "profile_link", "native_contract",
          "provider_discovery", "provider_registration", "tool_schemas"}


class InstallError(RuntimeError):
    """Fixed public diagnostics only."""


def open_directory(path):
    if not path.is_absolute():
        raise InstallError("Use an absolute approved directory.")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def protected_directory(fd):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise InstallError("An add-on directory is not protected and root-owned.")


def child_directory(parent, name, *, create=False):
    if create:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent)
        except FileExistsError:
            pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        protected_directory(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def publish(parent, source, target):
    """Atomic publication without replacing any existing name, including links."""
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent, os.fsencode(source), parent, os.fsencode(target), 1) != 0:
        raise InstallError("Publication refused; the existing destination was preserved.")


def verify_payload(files):
    if not isinstance(files, dict) or set(files) != set(HASHES):
        raise InstallError("Supply exactly the three reviewed provider files.")
    for name, expected in HASHES.items():
        raw = files[name]
        if not isinstance(raw, bytes) or len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
            raise InstallError("A provider file differs from the reviewed payload.")
        if name.endswith(".py"):
            compile(raw, "reviewed-provider-" + name, "exec")


def verify_artifact(fd):
    if set(os.listdir(fd)) != set(HASHES):
        raise InstallError("Existing add-on contents differ; nothing was replaced.")
    for name, expected in HASHES.items():
        opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(opened, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022
                    or info.st_nlink != 1 or info.st_size > 65536
                    or hashlib.sha256(stream.read(65537)).hexdigest() != expected):
                raise InstallError("Existing add-on bytes or protection differ; nothing was replaced.")


def stage_artifact(files):
    verify_payload(files)
    # Root code never traverses or changes the agent-owned profile tree.
    fd = open_directory(Path("/"))
    try:
        protected_directory(fd)
        for name in ("opt", "hermes-runtime", "providers"):
            child = child_directory(fd, name, create=name == "providers")
            os.close(fd)
            fd = child
        try:
            existing = child_directory(fd, ARTIFACT_NAME)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            try:
                verify_artifact(existing)
            finally:
                os.close(existing)
            return False
        stage = ".preparing-" + uuid.uuid4().hex
        os.mkdir(stage, mode=0o755, dir_fd=fd)
        directory = child_directory(fd, stage)
        try:
            for name, raw in files.items():
                output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o644, dir_fd=directory)
                with os.fdopen(output, "wb") as stream:
                    stream.write(raw)
                    os.fchmod(stream.fileno(), 0o644)
                    stream.flush()
                    os.fsync(stream.fileno())
            verify_artifact(directory)
            os.fsync(directory)
        finally:
            os.close(directory)
        publish(fd, stage, ARTIFACT_NAME)
        os.fsync(fd)
        return True
    finally:
        os.close(fd)


# The same reviewed safe directory/publication primitives run only AFTER dropping
# uid/groups, with no-new-privileges, in the protected Hermes interpreter.
CHILD = r'''
import contextlib, io, json, os, pwd, stat, sys, uuid
from pathlib import Path
_phase = "identity"
home = Path("/var/lib/hermes-runtime")
profile = home / ".hermes/profiles/enhanced-cognee-pilot"
release = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
artifact = Path("/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659")
identity = pwd.getpwuid(os.geteuid())
fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
if (identity.pw_name != "hermes-runtime" or identity.pw_uid == 0
    or Path(identity.pw_dir) != home or Path.cwd() != home
    or set(os.getgroups()) | {os.getegid()} != {identity.pw_gid}
    or fields.get("NoNewPrivs", "").strip() != "1"
    or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
    raise RuntimeError("Restricted child identity failed")
_phase = "artifact_protection"
for path in (artifact, *(artifact / name for name in HASHES)):
    info = path.lstat()
    if info.st_uid != 0 or info.st_mode & 0o022 or os.access(path, os.W_OK, effective_ids=True):
        raise RuntimeError("Provider artifact is writable")
    if path != artifact and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        raise RuntimeError("Provider artifact type failed")
for path in artifact.parents:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or os.access(path, os.W_OK, effective_ids=True):
        raise RuntimeError("Provider ancestor protection failed")
_phase = "profile_link"
fd = open_directory(profile)
link_created = False
try:
    info = os.fstat(fd)
    if info.st_uid != identity.pw_uid or info.st_mode & 0o777 != 0o700:
        raise RuntimeError("Pilot ownership or privacy failed")
    try:
        os.mkdir("plugins", mode=0o700, dir_fd=fd)
    except FileExistsError:
        pass
    plugin_fd = os.open("plugins", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        info = os.fstat(plugin_fd)
        if info.st_uid != identity.pw_uid or info.st_mode & 0o022:
            raise RuntimeError("Pilot plugin parent protection failed")
        try:
            info = os.stat("enhanced_cognee", dir_fd=plugin_fd, follow_symlinks=False)
        except FileNotFoundError:
            name = ".enhanced-cognee-" + uuid.uuid4().hex
            os.symlink(str(artifact), name, dir_fd=plugin_fd)
            publish(plugin_fd, name, "enhanced_cognee")
            os.fsync(plugin_fd)
            link_created = True
        else:
            if (not stat.S_ISLNK(info.st_mode) or info.st_uid != identity.pw_uid
                or os.readlink("enhanced_cognee", dir_fd=plugin_fd) != str(artifact)):
                raise RuntimeError("Existing plugin differs; preserved")
    finally:
        os.close(plugin_fd)
finally:
    os.close(fd)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    _phase = "native_contract"
    sys.path.insert(0, str(release / "repo"))
    import hermes_bootstrap
    from hermes_constants import get_hermes_home
    import agent.memory_provider as api
    import plugins.memory as loader
    if Path(get_hermes_home()).resolve() != profile:
        raise RuntimeError("Active Hermes profile differs")
    if any(not Path(module.__file__).resolve().is_relative_to(release / "repo") for module in (api, loader)):
        raise RuntimeError("Hermes contract source differs")
    if loader._get_active_memory_provider() not in (None, "builtin"):
        raise RuntimeError("Pilot already selects an external memory provider; preserved")
    _phase = "provider_discovery"
    found = loader.find_provider_dir("enhanced_cognee")
    if found is None or found.resolve() != artifact:
        raise RuntimeError("Provider discovery selected another source")
    _phase = "provider_registration"
    provider = loader.load_memory_provider("enhanced_cognee", register_skills=False)
    if not isinstance(provider, api.MemoryProvider) or provider.name != "enhanced_cognee":
        raise RuntimeError("Native provider registration failed")
    try:
        _phase = "tool_schemas"
        schemas = provider.get_tool_schemas()
        if len(schemas) != 8 or {row["name"] for row in schemas} != TOOLS:
            raise RuntimeError("Native tool schemas differ")
    finally:
        provider.shutdown()
print(json.dumps({"profile_plugin_link_created": link_created, "native_loader_passed": True,
                  "registered_tools": sorted(TOOLS), "effective_user": identity.pw_name}))
'''


def run_native_child(account, source):
    # Reuse the exact verified in-memory helper, never introspect a nonexistent
    # source file or import a mutable checkout. __main__ is deliberately absent.
    code = ("import json\nnamespace={'__name__':'reviewed_pilot_primitives'}\n"
            "exec(compile(" + repr(source) + ",'reviewed-pilot-source','exec'),namespace)\n"
            "open_directory=namespace['open_directory']; publish=namespace['publish']\n"
            "HASHES=namespace['HASHES']; TOOLS=namespace['TOOLS']\n"
            "try:\n    exec(compile(namespace['CHILD'],'pilot-native-check','exec'),globals())\n"
            "except Exception:\n"
            "    print(json.dumps({'native_loader_passed':False,'failure_stage':globals().get('_phase','unknown')}))\n"
            "    raise SystemExit(1)\n")
    result = subprocess.run(
        ["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env", "-i",
         "HOME=" + str(HOME), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
         "HERMES_HOME=" + str(PROFILE), "PATH=/usr/bin:/bin", "LANG=C.UTF-8",
         "PYTHONDONTWRITEBYTECODE=1", str(RELEASE / "venv/bin/python"), "-I", "-B", "-c", code],
        user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd=HOME,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )
    if len(result.stdout) > 65536:
        raise InstallError("Native pilot provider verification did not pass; all new files are retained.")
    report = json.loads(result.stdout)
    if result.returncode:
        phase = report.get("failure_stage") if isinstance(report, dict) else None
        if isinstance(phase, str) and phase in PHASES:
            raise InstallError("Native pilot verification failed at " + phase + "; new artifacts are retained.")
        raise InstallError("Native pilot provider verification did not pass; all new files are retained.")
    if (not isinstance(report, dict) or set(report) != {
            "native_loader_passed", "registered_tools", "effective_user", "profile_plugin_link_created"}
            or type(report.get("profile_plugin_link_created")) is not bool
            or report.get("native_loader_passed") is not True
            or report.get("registered_tools") != sorted(TOOLS)
            or report.get("effective_user") != "hermes-runtime"):
        raise InstallError("Native provider verification returned an unexpected receipt.")
    return report


def main(files, source):
    try:
        if (os.geteuid() != 0 or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
                or os.environ.get("SUDO_USER") != "vincentspereira"):
            raise InstallError("Use the approved human Ubuntu-Hermes operator through sudo.")
        os.umask(0o022)
        if not isinstance(source, bytes) or len(source) > 65536:
            raise InstallError("Use the exact verified helper source.")
        account = pwd.getpwnam("hermes-runtime")
        if (account.pw_uid == 0 or Path(account.pw_dir) != HOME
                or set(os.getgrouplist(account.pw_name, account.pw_gid)) != {account.pw_gid}):
            raise InstallError("The approved restricted account needs review.")
        # System launcher and selected interpreter must be protected before exec.
        for path in (Path("/usr/bin/setpriv"), RELEASE / "venv/bin/python"):
            resolved = path.resolve(strict=True)
            info = resolved.stat()
            if (info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o6022
                    or (path != Path("/usr/bin/setpriv") and not resolved.is_relative_to(RELEASE))):
                raise InstallError("The protected child launcher needs review.")
        created = stage_artifact(files)
        report = run_native_child(account, source)
    except InstallError as error:
        raise SystemExit("STOP: " + str(error) + " No credential or provider selection was requested.") from None
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            SyntaxError, subprocess.SubprocessError):
        raise SystemExit("STOP: pilot staging/verification incomplete. No credential or provider selection was requested; artifacts retained.") from None
    print(json.dumps({"complete": True, "artifact": str(ARTIFACT), "artifact_created": created,
                      "profile": str(PROFILE), "plugin_version": "0.1.0", **report,
                      "provider_selected": False, "credentials_provisioned": False,
                      "memory_connected": False, "model_called": False,
                      "runtime_qualified": False}, indent=2))


if __name__ == "__main__":
    raise SystemExit("Use the exact published four-file archive and reviewed operator command.")
