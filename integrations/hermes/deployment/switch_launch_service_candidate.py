"""Controlled protected API/worker candidate switch, never fleet activation.

Verify installed wheel bytes and completed recovery receipts. Preserve configs
and units; rollback on failed bounded startup/authentication checks. No profile,
credential, encryption key, canonical memory or existing index namespace edits.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import time
import zipfile

REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
BASE = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
WHEEL_SHA256 = "9ba46a58f32adf29c378690041beaa96ff2f545d432df1265d62617caf5ba7d5"
ROLES = {"api":"api", "index":"worker"}
RECOVERY_RECEIPTS = {Path("/var/tmp/ec-launch-recovery-aja7p8j9/summary.json"),
                     Path("/var/tmp/ec-launch-index-recovery-sw3log4z/summary.json")}


def directory_guard(info, *, sticky=False, private=False):
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        raise ValueError("receipt_directory_protection_required")
    mode = stat.S_IMODE(info.st_mode)
    if ((sticky and mode != 0o1777) or (private and mode != 0o700)
            or (not sticky and not private and mode & 0o022)):
        raise ValueError("receipt_directory_protection_required")


def recovery_receipt(path):
    """Exact root-private receipts below the fixed root-owned sticky /var/tmp.

    Directory descriptors pin every component. Never generalize this shared
    parent exception to credentials, runtime files or arbitrary caller paths.
    """
    if path not in RECOVERY_RECEIPTS:
        raise ValueError("fixed_recovery_receipt_required")
    fd = os.open("/",os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        directory_guard(os.fstat(fd))
        for name in ("var","tmp",path.parent.name):
            child = os.open(name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd)
            fd = child
            directory_guard(os.fstat(fd),sticky=name == "tmp",private=name == path.parent.name)
        item = os.open("summary.json",os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(item,"rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 262144:
                raise ValueError("receipt_file_protection_required")
            raw = stream.read(262145)
            if len(raw) > 262144:
                raise ValueError("receipt_file_protection_required")
            return json.loads(raw)
    finally:
        os.close(fd)


def runtime_members(names):
    return [name for name in names if not name.endswith("/")
            and ".dist-info/" not in name]


def refusal_reason(error):
    allowed = {"local_root_operator_required", "reviewed_shared_source_required",
        "protected_candidate_required", "verified_staging_and_recovery_required",
        "wheel_size_required", "exact_wheel_required", "wheel_member_required",
        "installed_wheel_bytes_differ", "installed_package_inventory_required",
        "admitted_model_required", "existing_runtime_selection_preserved",
        "receipt_directory_protection_required", "fixed_recovery_receipt_required", "receipt_file_protection_required",
        "protected_ancestor_required", "protected_file_required", "input_budget",
        "bounded_service_control_failed"}
    return str(error) if type(error) is ValueError and str(error) in allowed else "protected_input_or_service_error"


def protected(path):
    for item in [*reversed(path.parents), path]:
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError("protected_candidate_required")


def dropin(role):
    if role not in {"api", "worker"}:
        raise ValueError("fixed_role_required")
    return ("[Service]\nWorkingDirectory="+str(BASE)+"\nExecStart=\nExecStart="+
            str(BASE / "runtime/bin/python")+" -m src.memory_daemon "+role+"\n").encode("ascii")


def configuration(raw):
    value = json.loads(raw)
    if value.get("ENHANCED_EMBEDDING_MODEL") != "BAAI/bge-small-en-v1.5":
        raise ValueError("admitted_model_required")
    value["ENHANCED_MODEL_CACHE"] = str(BASE / "model-cache")
    return json.dumps(value, ensure_ascii=True).encode()


def systemctl(*args):
    result = subprocess.run(["/usr/bin/systemctl", *args], capture_output=True,
        timeout=45, env={"PATH":"/usr/bin:/bin", "LC_ALL":"C"})
    if result.returncode:
        raise ValueError("bounded_service_control_failed")
    return result.stdout


def request(path, token=None):
    client = HTTPConnection("127.0.0.1", 28080, timeout=3)
    try:
        client.request("GET", path, headers={"Authorization":"Bearer "+token} if token else {})
        response = client.getresponse()
        raw = response.read(32769)
        if len(raw) > 32768:
            raise ValueError("bounded_status_required")
        return response.status, json.loads(raw)
    finally:
        client.close()


def token(key, scope, expired=False):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value,separators=(",",":"),ensure_ascii=True).encode()).rstrip(b"=")
    now = int(time.time())
    claims = dict(scope, iat=now-60 if expired else now, exp=now-1 if expired else now+300)
    content = encode({"alg":"HS256","typ":"JWT"})+b"."+encode(claims)
    return (content+b"."+base64.urlsafe_b64encode(hmac.new(key.encode(),content,hashlib.sha256).digest()).rstrip(b"=")).decode()


def ready():
    deadline = time.monotonic()+60
    while time.monotonic() < deadline:
        try:
            code, body = request("/health/ready")
            if code == 200 and body.get("ready") is True:
                return True
        except (OSError, ValueError):
            pass
        time.sleep(1)
    return False


def process_binding(unit):
    raw = systemctl("show",unit,"--property=MainPID","--value").strip()
    if not raw.isdigit() or int(raw) <= 0:
        return False
    process = Path("/proc") / raw.decode()
    return (process.joinpath("exe").resolve() == (BASE / "runtime/bin/python").resolve()
            and process.joinpath("cwd").resolve() == BASE)


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    os.umask(0o077)
    source = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != SHARED_SHA256:
        raise ValueError("reviewed_shared_source_required")
    shared = {"__name__":"verified_runtime_file_primitives"}
    exec(compile(source,"<verified-runtime-file-primitives>","exec"),shared)
    read, write, replace = (shared[k] for k in ("read_file","private_write","replace_file"))
    for path in (BASE, BASE / "runtime/bin/python", BASE / "model-cache"):
        protected(path)
    staging = json.loads(read(BASE / "operator-evidence/summary.json",0))
    canonical = recovery_receipt(Path("/var/tmp/ec-launch-recovery-aja7p8j9/summary.json"))
    derived = recovery_receipt(Path("/var/tmp/ec-launch-index-recovery-sw3log4z/summary.json"))
    if (staging.get("complete") is not True or staging.get("source_revision") != REVISION
            or canonical.get("canonical_recovery_qualified") is not True
            or derived.get("derived_store_recovery_qualified") is not True
            or derived.get("source_revision") != REVISION):
        raise ValueError("verified_staging_and_recovery_required")
    wheel = BASE / "artifacts/rnr_enhanced_cognee_memory-1.2.0-py3-none-any.whl"
    protected(wheel)
    if wheel.stat().st_size > 4194304:
        raise ValueError("wheel_size_required")
    data = wheel.read_bytes()
    if hashlib.sha256(data).hexdigest() != WHEEL_SHA256:
        raise ValueError("exact_wheel_required")
    checked = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in runtime_members(archive.namelist()):
            if ".." in Path(name).parts:
                raise ValueError("wheel_member_required")
            installed = BASE / "runtime/lib/python3.12/site-packages" / name
            protected(installed)
            if installed.read_bytes() != archive.read(name):
                raise ValueError("installed_wheel_bytes_differ")
            checked += 1
    if checked != 34:
        raise ValueError("installed_package_inventory_required")
    originals, paths = {}, {}
    for unit, role in ROLES.items():
        config = Path("/etc/enhanced-cognee") / (role+".json")
        originals[role] = read(config,0)
        configuration(originals[role])
        directory = Path("/etc/systemd/system/enhanced-cognee-"+unit+".service.d")
        protected(directory)
        paths[role] = directory / "20-launch-runtime.conf"
        if os.path.lexists(paths[role]):
            raise ValueError("existing_runtime_selection_preserved")
    attempt = BASE / "operator-evidence/controlled-runtime-switch"
    attempt.mkdir(mode=0o700)
    for role, raw in originals.items():
        write(attempt / (role+".before.json"),raw)
    for unit in ROLES:
        write(attempt / (unit+".unit.before.txt"),systemctl("cat","enhanced-cognee-"+unit+".service"))
    result = {"complete":False,"source_revision":REVISION,"evidence":str(attempt),
        "profiles_changed":False,"canonical_memory_edits":False,"credentials_rotated":False,
        "fleet_launch_approved":False,"installed_worker_projection_qualified":False}
    touched = False
    def interrupted(signum,frame):
        raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    try:
        write(attempt / "before-stop.json",b'{"controlled_switch_started":true}')
        touched = True
        systemctl("stop","enhanced-cognee-index.service","enhanced-cognee-api.service")
        for role, raw in originals.items():
            config = Path("/etc/enhanced-cognee") / (role+".json")
            if read(config,0) != raw:
                raise ValueError("service_configuration_changed_concurrently")
            replace(config,configuration(raw),0)
            write(paths[role],dropin(role))
        systemctl("daemon-reload")
        systemctl("start","enhanced-cognee-api.service","enhanced-cognee-index.service")
        if not ready() or not all(process_binding("enhanced-cognee-"+unit+".service") for unit in ROLES):
            raise ValueError("candidate_startup_or_process_binding_failed")
        scope = {"tenant":"qualification","project_id":"runtime_"+secrets.token_hex(8),
                 "sub":"runtime_acceptance","agent_id":"runtime_acceptance","roles":["api_client"],"capture_policy":"selected"}
        key = json.loads(originals["api"])["ENHANCED_JWT_SECRET"]
        code, body = request("/v1/memories/status",token(key,scope))
        if (code != 200 or body.get("ready") is not True or body.get("schema_version") != 3
                or body.get("encryption") != "AES-256-GCM" or body.get("tenant_id") != scope["tenant"]
                or body.get("project_id") != scope["project_id"] or body.get("subject") != scope["sub"]):
            raise ValueError("authenticated_candidate_scope_failed")
        if request("/v1/memories/status")[0] != 401 or request("/v1/memories/status",token(key,scope,True))[0] != 401:
            raise ValueError("candidate_authentication_refusal_failed")
        result.update(complete=True,installed_wheel_files_verified=checked,api_candidate_bound=True,
            worker_candidate_bound=True,authenticated_scope_status_verified=True,
            unauthenticated_and_expired_denied=True,service_runtime_changed=True,
            old_runtime_retained=True,model_cache_selected=True)
    except BaseException:
        result["category"] = "controlled_candidate_switch_failed_preserve_evidence"
        if touched:
            try:
                systemctl("stop","enhanced-cognee-index.service","enhanced-cognee-api.service")
                for role, raw in originals.items():
                    replace(Path("/etc/enhanced-cognee") / (role+".json"),raw,0)
                    if os.path.lexists(paths[role]):
                        os.rename(paths[role],paths[role].with_name(paths[role].name+".rollback-"+secrets.token_hex(6)))
                systemctl("daemon-reload")
                systemctl("start","enhanced-cognee-api.service","enhanced-cognee-index.service")
                result["rollback_api_ready"] = ready()
            except BaseException:
                result["rollback_api_ready"] = False
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print(json.dumps({"complete":False,"category":"candidate_switch_preflight_refused_no_secret_output",
                          "reason":refusal_reason(error)}))
        raise SystemExit(1)
