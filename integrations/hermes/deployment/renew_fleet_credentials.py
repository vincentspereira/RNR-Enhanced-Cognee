"""Operator-owned fixed-policy renewal driver; no installation or activation.

No CLI signing choices. A root-owned allowlist selects ordinary identities.
Root never enters profile trees. Profile-owner children preserve settings and
renew atomically. Any incomplete operator attempt blocks later automatic runs
for that profile until an operator reviews the retained ledger. No retry loop.
The timer must remain disabled until native expiry/reload acceptance passes.
"""
from __future__ import annotations

import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import selectors
import stat
import subprocess
import time
import uuid


POLICY = Path("/etc/enhanced-cognee/fleet-credentials.json")
LEDGER = Path("/var/lib/enhanced-cognee-renewal")
SOURCES = {
    "provision_pilot_access.py": "f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "renew_pilot_access.py": "8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567",
    "fleet_credential_policy.py": "6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102",
    "fleet_credential_lifecycle.py": "f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62",
}
RECEIPT_FIELDS = {"complete", "credential_published", "preserved_settings_and_oauth", "preserved_previous_environment",
                  "interrupted_attempts_reconciled", "native_reload_qualified", "timer_activation_approved"}


def protected(path, *, final_link=False):
    for item in [path, *path.parents]:
        info = item.lstat()
        if info.st_uid != 0 or (stat.S_ISLNK(info.st_mode) and not (item == path and final_link)):
            raise ValueError("operator_path_protection")
        if not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022:
            raise ValueError("operator_path_protection")


def sources():
    result = {}
    for name, expected in SOURCES.items():
        fd = os.open(Path(__file__).with_name(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 65536:
                raise ValueError("operator_source_protection")
            raw = stream.read(65537)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("operator_source_hash")
        result[name] = raw
    return result


def definitions(raw, name):
    namespace = {"__name__": name}
    exec(compile(raw, "<verified-" + name + ">", "exec"), namespace)
    return namespace


def receipt(raw):
    if len(raw) > 16384:
        raise ValueError("child_receipt_budget")
    def unique(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError("duplicate_child_receipt_field")
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    if (not isinstance(value, dict) or set(value) != RECEIPT_FIELDS
            or any(type(value[key]) is not bool for key in RECEIPT_FIELDS - {"interrupted_attempts_reconciled"})
            or value["complete"] is not True or value["native_reload_qualified"] is not False
            or value["timer_activation_approved"] is not False
            or value["preserved_settings_and_oauth"] is not True or value["preserved_previous_environment"] is not True
            or type(value["interrupted_attempts_reconciled"]) is not int
            or not 0 <= value["interrupted_attempts_reconciled"] <= 128):
        raise ValueError("child_receipt_contract")
    return value


def child_main(core, renewal, lifecycle, entry, bundle):
    """Executes only after the caller has irreversibly dropped UID/groups."""
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if (account.pw_uid == 0 or account.pw_uid != entry["uid"] or account.pw_name != entry["user"]
            or account.pw_dir != entry["home"] or os.getgroups()
            or status.get("NoNewPrivs", "").strip() != "1"
            or any(status.get(k, "").strip() != "0000000000000000" for k in ("CapEff", "CapAmb"))):
        raise ValueError("child_identity_refused")
    core["IDENTITY"] = {"sub": entry["subject"], "agent_id": entry["agent_id"], "tenant": entry["tenant"],
                        "project_id": entry["project_id"], "roles": ["api_client"], "capture_policy": "selected"}
    fd = core["open_directory"](Path(entry["profile"]), {0, account.pw_uid})
    try:
        info = os.fstat(fd)
        if info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("profile_protection_refused")
        lock = os.open(".cognee-renewal.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                       0o600, dir_fd=fd)
        try:
            core["read_private_fd"](lock, account.pw_uid)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            original, _ = core["read_private_at"](fd, ".env", account.pw_uid)
            current = renewal["environment"](core, original)
            claims = renewal["token_claims"](core, current)
            if claims["exp"] - int(time.time()) > 21600:
                lifecycle["accepted_status"](core, current)
                result = {"complete": True, "credential_published": False, "preserved_settings_and_oauth": True,
                          "preserved_previous_environment": True, "interrupted_attempts_reconciled": 0,
                          "native_reload_qualified": False, "timer_activation_approved": False}
            else:
                result = lifecycle["publish"](core, renewal, fd, bundle, account.pw_uid)
        finally:
            os.close(lock)
    finally:
        os.close(fd)
    print(json.dumps(result))


def run_child(entry, bundle, source):
    account = pwd.getpwnam(entry["user"])
    if account.pw_uid != entry["uid"] or account.pw_dir != entry["home"]:
        raise ValueError("policy_account_binding_differs")
    groups = {grp.getgrgid(gid).gr_name for gid in os.getgrouplist(account.pw_name, account.pw_gid)}
    if groups & {"root", "sudo", "docker", "lxd", "incus-admin"}:
        raise ValueError("administrative_runtime_identity_refused")
    executable = Path(entry["executable"])
    protected(executable, final_link=True)
    protected(executable.resolve(strict=True))
    code = ("import json,sys\n"
            "def definitions(raw,name):\n n={'__name__':name};exec(compile(raw,'<verified-child>','exec'),n);return n\n"
            "core=definitions(" + repr(source["provision_pilot_access.py"]) + ",'issuer_child')\n"
            "renewal=definitions(" + repr(source["renew_pilot_access.py"]) + ",'renewal_child')\n"
            "lifecycle=definitions(" + repr(source["fleet_credential_lifecycle.py"]) + ",'lifecycle_child')\n"
            "driver=definitions(" + repr(Path(__file__).read_bytes()) + ",'driver_child')\n"
            "v=json.load(sys.stdin)\ndriver['child_main'](core,renewal,lifecycle,v['entry'],v['bundle'])\n")
    raw = json.dumps({"entry": entry, "bundle": bundle}).encode()
    if len(raw) > 8192:
        raise ValueError("child_input_budget")
    process = subprocess.Popen(["/usr/bin/setpriv", "--no-new-privs", "--", str(executable), "-I", "-B", "-c", code],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd="/",
        env={"PATH": "/usr/bin:/bin", "HOME": account.pw_dir, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
    output = bytearray()
    selector = selectors.DefaultSelector()
    try:
        os.set_blocking(process.stdin.fileno(), False)
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stdin, selectors.EVENT_WRITE)
        sent = 0
        deadline = time.monotonic() + 90
        eof = False
        while not eof:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("child_deadline")
            events = selector.select(remaining)
            if not events:
                raise ValueError("child_deadline")
            for selected, event in events:
                if selected.fileobj is process.stdin:
                    sent += os.write(process.stdin.fileno(), raw[sent:sent+4096])
                    if sent == len(raw):
                        selector.unregister(process.stdin)
                        process.stdin.close()
                else:
                    block = os.read(process.stdout.fileno(), 16385-len(output))
                    if not block:
                        eof = True
                        break
                    output.extend(block)
                    if len(output) > 16384:
                        raise ValueError("child_receipt_budget")
        if process.wait(timeout=max(0.01, deadline-time.monotonic())):
            raise ValueError("child_refused_review_retained_attempt")
        return receipt(output)
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()


def main():
    if os.geteuid() != 0:
        raise SystemExit("ERR: operator identity required")
    protected(Path(__file__).absolute())
    os.umask(0o077)
    source = sources()
    policy = definitions(source["fleet_credential_policy.py"], "policy_operator")["load"](POLICY)
    admitted = [entry for entry in policy["profiles"] if entry["enabled"]]
    if not admitted:
        print(json.dumps({"complete": True, "enabled_profiles": 0, "credentials_published": 0,
                          "native_reload_qualified": False, "timer_activation_approved": False}))
        return 0
    protected(LEDGER.parent)
    LEDGER.mkdir(mode=0o700, exist_ok=True)
    protected(LEDGER)
    lock = os.open(LEDGER / ".issuer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(lock)
        if info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError("operator_lock_protection")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        core = definitions(source["provision_pilot_access.py"], "issuer_operator")
        reports = []
        for entry in admitted:
            pending = list(LEDGER.glob(entry["name"] + "-*.started.json"))
            if len(pending) > 512 or any(not p.with_name(p.name.replace(".started.json", ".done.json")).exists() for p in pending):
                raise ValueError("incomplete_operator_attempt_requires_review")
            ident = entry["name"] + "-" + uuid.uuid4().hex
            started = LEDGER / (ident + ".started.json")
            with started.open("x", encoding="ascii") as stream:
                json.dump({"profile": entry["name"], "state": "started", "source_hashes": SOURCES}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(LEDGER, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            core["IDENTITY"] = {"sub": entry["subject"], "agent_id": entry["agent_id"], "tenant": entry["tenant"],
                                "project_id": entry["project_id"], "roles": ["api_client"], "capture_policy": "selected"}
            key = core["load_signing_key"]()
            bundle = core["make_bundle"](key, int(time.time()))
            del key
            report = run_child(entry, bundle, source)
            with (LEDGER / (ident + ".done.json")).open("x", encoding="ascii") as stream:
                json.dump(report, stream)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(LEDGER, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            reports.append(report)
        print(json.dumps({"complete": True, "enabled_profiles": len(admitted),
                          "credentials_published": sum(r["credential_published"] for r in reports),
                          "native_reload_qualified": False, "timer_activation_approved": False}))
        return 0
    finally:
        os.close(lock)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"complete": False, "category": "issuer_stopped_operator_review_required_no_automatic_retry",
                          "native_reload_qualified": False, "timer_activation_approved": False}))
        raise SystemExit(1) from None
