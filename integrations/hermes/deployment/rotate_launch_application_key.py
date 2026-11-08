"""Manual coordinated key rotation for the three existing qualification bindings.

Not an unattended issuer or fleet enrollment. Only owner-UID children enter
profiles; signing keys stay in root. Preserve scopes, lifetimes, unrelated .env
bytes, settings/OAuth and every failed attempt. Stop API during coordinated
publication, verify real authentication, restore prior selections on failure.
"""
from __future__ import annotations

import hashlib
import fcntl
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
EXECUTABLE = "/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python"
TOKEN = "ENHANCED_COGNEE_ACCESS_TOKEN"
OWNER_REASONS = {"restricted_owner_child_required","fixed_profile_phase_required","fixed_owner_profile_required",
    "profile_ancestor_owner_required","profile_ancestor_protection_required","profile_owner_required","private_profile_required",
    "owner_private_file_required","owner_file_changed_during_read","bounded_environment_required","single_valid_profile_token_required",
    "ordinary_token_shape_required","current_local_provider_binding_required","owner_settings_file_required",
    "profile_token_changed_before_prepare","expected_profile_token_required","unambiguous_profile_assignment_required",
    "unrelated_environment_preservation_failed","profile_renewal_lock_protection_required","unprepared_profile_changed",
    "concurrent_profile_change_requires_review","concurrent_environment_change_requires_review","profile_settings_changed_concurrently",
    "staged_environment_changed","published_environment_differs","profile_new_credential_refused"}
PINS = {"recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef",
    "provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "inventory_launch_token_bindings.py":"6392da7574e24f842ef6099e56502aed264c30f164e00eaea0185dd8c40fad96"}


def require(value,reason):
    if not value:
        raise ValueError(reason)


class OwnerPhaseRefused(ValueError):
    def __init__(self,reason):
        super().__init__("owner_phase_failed_preserve_evidence")
        self.safe_reason = reason if reason in OWNER_REASONS else "owner_process_or_input_error"


def definitions(name):
    raw = Path(__file__).with_name(name).read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == PINS[name],"reviewed_support_required")
    namespace = {"__name__":"verified_application_rotation_support"}
    exec(compile(raw,"<verified-application-rotation-support>","exec"),namespace)
    return namespace


def parse_token(raw):
    from dotenv.parser import parse_stream
    require(isinstance(raw,bytes) and len(raw) <= 65536 and b"\x00" not in raw,"bounded_environment_required")
    rows = list(parse_stream(io.StringIO(raw.decode("utf-8"))))
    selected = [row for row in rows if row.key == TOKEN]
    require(not any(row.error for row in rows) and len(selected) == 1,"single_valid_profile_token_required")
    value = selected[0].value
    require(isinstance(value,str) and len(value) <= 4096 and re.fullmatch(r"[A-Za-z0-9_.-]+",value),"ordinary_token_shape_required")
    return value,rows,selected[0]


def replacement_environment(raw,old,new):
    current,rows,selected = parse_token(raw)
    require(current == old and re.fullmatch(r"[A-Za-z0-9_.-]{1,4096}",new),"expected_profile_token_required")
    require(selected.original.string.count(old) == 1,"unambiguous_profile_assignment_required")
    updated = "".join(row.original.string.replace(old,new,1) if row is selected else row.original.string for row in rows).encode()
    value,after,_ = parse_token(updated)
    pairs = lambda values:[(row.key,row.value) for row in values if row.key not in {None,TOKEN}]
    require(value == new and pairs(rows) == pairs(after),"unrelated_environment_preservation_failed")
    return updated


def entry_guard(entry,account):
    home = Path(account.pw_dir)
    path = Path(entry["profile_home"])
    require(entry["user"] == account.pw_name and entry["uid"] == account.pw_uid and entry["home"] == str(home)
        and str(path) == entry["profile_home"] and ".." not in path.parts
        and (path == home / ".hermes" or path.parent == home / ".hermes/profiles"),"fixed_owner_profile_required")
    return path


def open_profile(entry,harden=False,readonly=False):
    account = pwd.getpwuid(os.geteuid())
    path = entry_guard(entry,account)
    fd = os.open("/",os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    current = Path("/")
    try:
        for name in path.parts[1:]:
            child = os.open(name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd)
            fd = child
            current = current / name
            info = os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0,account.pw_uid},"profile_ancestor_owner_required")
            if info.st_mode & 0o022:
                if harden and current == Path(account.pw_dir) / ".hermes/profiles" and info.st_uid == account.pw_uid:
                    os.fchmod(fd,stat.S_IMODE(info.st_mode) & ~0o022)
                else:
                    require(readonly and info.st_uid == account.pw_uid,"profile_ancestor_protection_required")
        require(os.fstat(fd).st_uid == account.pw_uid,"profile_owner_required")
        if harden:
            os.fchmod(fd,0o700)
        if not readonly:
            require(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700,"private_profile_required")
        return fd
    except BaseException:
        os.close(fd)
        raise


def owner_read(directory,name,uid,harden=False):
    fd = os.open(name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=directory)
    with os.fdopen(fd,"rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1 and info.st_size <= 65536,"owner_private_file_required")
        if harden:
            os.fchmod(stream.fileno(),0o600)
        before = os.fstat(stream.fileno())
        raw = stream.read(65537)
        after = os.fstat(stream.fileno())
        fields = ("st_dev","st_ino","st_size","st_mtime_ns","st_ctime_ns","st_mode","st_nlink","st_uid")
        require(len(raw) <= 65536 and len(raw) == before.st_size
            and all(getattr(before,k) == getattr(after,k) for k in fields),"owner_file_changed_during_read")
        return raw


def owner_write(directory,name,raw):
    fd = os.open(name,os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,0o600,dir_fd=directory)
    with os.fdopen(fd,"wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def settings_metadata(directory):
    result = {}
    for name in ("config.yaml","enhanced_cognee.json","auth.json"):
        try:
            info = os.stat(name,dir_fd=directory,follow_symlinks=False)
        except FileNotFoundError:
            result[name] = None
            continue
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid(),"owner_settings_file_required")
        result[name] = [info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_mode]
    return result


def api_status(token):
    client = HTTPConnection("127.0.0.1",28080,timeout=5)
    try:
        client.request("GET","/v1/memories/status",headers={"Authorization":"Bearer "+token})
        reply = client.getresponse()
        raw = reply.read(16385)
        require(len(raw) <= 16384,"bounded_api_status_required")
        return reply.status,json.loads(raw)
    finally:
        client.close()


def child(data):
    uid = os.geteuid()
    fields = dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
    require(uid != 0 and not os.getgroups() and fields["NoNewPrivs"].strip() == "1"
        and all(fields[x].strip() == "0000000000000000" for x in ("CapEff","CapAmb")),"restricted_owner_child_required")
    phase,entry,nonce = data["phase"],data["entry"],data["nonce"]
    require(phase in {"inspect","prepare","publish","verify","rollback"} and re.fullmatch(r"[a-f0-9]{16}",nonce),"fixed_profile_phase_required")
    directory = open_profile(entry,harden=phase == "prepare",readonly=phase == "inspect")
    backup,candidate,journal = ".env-before-issuer-"+nonce,".env-issuer-"+nonce,".issuer-"+nonce+".prepared.json"
    lock = None
    try:
        if phase != "inspect":
            lock = os.open(".cognee-renewal.lock",os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,0o600,dir_fd=directory)
            info = os.fstat(lock)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600,"profile_renewal_lock_protection_required")
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = owner_read(directory,".env",uid,harden=phase == "prepare")
        current,_,_ = parse_token(raw)
        if phase != "rollback":
            settings = json.loads(owner_read(directory,"enhanced_cognee.json",uid))
            uri = urlsplit(settings.get("base_url",""))
            require(uri.scheme == "http" and uri.hostname in {"127.0.0.1","localhost","::1"} and uri.port == 28080
                and not uri.username and not uri.password and uri.path in {"","/"},"current_local_provider_binding_required")
        if phase == "inspect":
            return {"complete":True,"ordinary_token_for_parent":current}
        if phase == "prepare":
            require(current == data["old"],"profile_token_changed_before_prepare")
            before = settings_metadata(directory)
            updated = replacement_environment(raw,data["old"],data["new"])
            owner_write(directory,backup,raw)
            owner_write(directory,candidate,updated)
            state = {"before":hashlib.sha256(raw).hexdigest(),"after":hashlib.sha256(updated).hexdigest(),"settings":before}
            owner_write(directory,journal,json.dumps(state).encode())
            os.fsync(directory)
            return {"complete":True,"environment_prepared":True}
        if phase == "rollback":
            try:
                original = owner_read(directory,backup,uid)
            except FileNotFoundError:
                require(current == data["old"],"unprepared_profile_changed")
                return {"complete":True,"profile_restored":True}
            require(current in {data["old"],data["new"]},"concurrent_profile_change_requires_review")
            if current == data["new"]:
                state = json.loads(owner_read(directory,journal,uid))
                require(hashlib.sha256(raw).hexdigest() == state["after"],"concurrent_environment_change_requires_review")
                owner_write(directory,".env-failed-issuer-"+nonce,raw)
                temporary = ".env-issuer-rollback-"+nonce
                owner_write(directory,temporary,original)
                os.replace(temporary,".env",src_dir_fd=directory,dst_dir_fd=directory)
                os.fsync(directory)
            return {"complete":True,"profile_restored":True}
        state = json.loads(owner_read(directory,journal,uid))
        require(settings_metadata(directory) == state["settings"],"profile_settings_changed_concurrently")
        if phase == "publish":
            require(hashlib.sha256(raw).hexdigest() == state["before"] and current == data["old"],"concurrent_environment_change_requires_review")
            staged = owner_read(directory,candidate,uid)
            require(hashlib.sha256(staged).hexdigest() == state["after"] and parse_token(staged)[0] == data["new"],"staged_environment_changed")
            os.replace(candidate,".env",src_dir_fd=directory,dst_dir_fd=directory)
            os.fsync(directory)
            owner_write(directory,".issuer-"+nonce+".published.json",b'{"published":true}')
            return {"complete":True,"credential_published":True}
        require(current == data["new"] and hashlib.sha256(raw).hexdigest() == state["after"],"published_environment_differs")
        code,status = api_status(current)
        binding = entry["verified_binding"]
        require(code == 200 and status.get("ready") is True and status.get("tenant_id") == binding["tenant"]
            and status.get("project_id") == binding["project_id"] and status.get("subject") == binding["sub"],"profile_new_credential_refused")
        return {"complete":True,"profile_new_credential_authenticated":True,"settings_and_oauth_preserved":True}
    finally:
        if lock is not None:os.close(lock)
        os.close(directory)


def run_child(entry,phase,nonce,old=None,new=None):
    account = pwd.getpwnam(entry["user"])
    require(account.pw_uid == entry["uid"] and account.pw_dir == entry["home"],"profile_account_binding_changed")
    source = Path(__file__).read_bytes()
    code = ("import json,sys\nn={'__name__':'verified_owner_key_rotation'}\nexec(compile("+repr(source)+",'<verified-owner-key-rotation>','exec'),n)\n"
        "try:\n print(json.dumps(n['child'](json.load(sys.stdin))))\n"
        "except Exception as e:\n reason=str(e) if type(e) is ValueError and str(e) in n['OWNER_REASONS'] else 'owner_process_or_input_error'\n"
        " print(json.dumps({'complete':False,'reason':reason}));sys.exit(1)\n")
    payload = json.dumps({"entry":entry,"phase":phase,"nonce":nonce,"old":old,"new":new}).encode()
    require(len(payload) <= 16384 and len(source) <= 65536 and len(code) <= 65536,"bounded_owner_input_required")
    process = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--",EXECUTABLE,"-I","-B","-c",code],
        input=payload,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,user=account.pw_uid,group=account.pw_gid,
        extra_groups=(),cwd="/",timeout=40,env={"PATH":"/usr/bin:/bin","HOME":account.pw_dir,"LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
    require(0 < len(process.stdout) <= 16384,"owner_phase_failed_preserve_evidence")
    result = json.loads(process.stdout)
    if process.returncode != 0 or result.get("complete") is not True:
        raise OwnerPhaseRefused(result.get("reason"))
    require(result.get("complete") is True,"owner_phase_incomplete")
    return result


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    shared,issuer,inventory = (definitions(name) for name in PINS)
    read,write,replace = (shared[k] for k in ("read_file","private_write","replace_file"))
    preflight = json.loads(read(BASE / "operator-evidence/issuer-preparation/summary.json",0))
    require(preflight.get("complete") is True and preflight.get("existing_qualification_bindings") == 3
            and preflight.get("credentials_issued") == 0,"protected_issuer_preparation_required")
    rows = json.loads(read(BASE / "operator-evidence/token-bindings-o7gaywzr/bindings.private.json",0))["rows"]
    entries = [row for row in rows if row.get("token_signature_valid") is True]
    require(len(entries) == 3 and len({row["profile_home"] for row in entries}) == 3
        and all(row.get("local_memory_configured") is True and row["verified_binding"]["tenant"] == "qualification" for row in entries),"exact_existing_qualification_bindings_required")
    originals = {name:read(Path("/etc/enhanced-cognee") / (name+".json"),0) for name in ("api","operator")}
    old_key = issuer["load_signing_key"]()
    candidate = json.loads(read(STAGE / "replacement-logins.private.json",0))["application"]["issuer"]["jwt_signing_key"]
    require(isinstance(candidate,str) and re.fullmatch(r"[A-Za-z0-9_-]{43,128}",candidate) and candidate.encode() != old_key,"staged_new_signing_key_required")
    nonce = secrets.token_hex(8)
    attempt = STAGE / "application-signing-rotation"
    attempt.mkdir(mode=0o700)
    for name,raw in originals.items():
        write(attempt / (name+".before.json"),raw)
    write(attempt / "coordination.private.json",json.dumps({"nonce":nonce,"profiles":entries,"staged_key_source":"replacement-logins.private.json"}).encode())
    result = {"complete":False,"evidence":str(attempt),"checkpoint":"owner_inspection","profiles_changed":False,
        "application_signing_key_changed":False,"encryption_keys_changed":False,"recovery_keys_changed":False,
        "credentials_issued":0,"running_gateway_reload_qualified":False,"unattended_issuer_qualified":False,
        "all_credentials_rotated":False,"fleet_launch_approved":False}
    values,prepared = [],[]
    touched = False
    shared["UNIT"] = "enhanced-cognee-api.service"
    def interrupted(signum,frame):raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    now = int(time.time())
    proof_claims = {"tenant":"qualification","project_id":"issuer_rotation_probe","sub":"issuer_rotation_probe",
        "agent_id":"issuer_rotation_probe","roles":["api_client"],"capture_policy":"selected","iat":now,"exp":now+900}
    old_proof = issuer["sign_claims"](proof_claims,old_key)
    try:
        require(api_status(old_proof)[0] == 200,"current_backend_key_not_verified")
        for index,entry in enumerate(entries):
            result["profile_index"] = index
            inspected = run_child(entry,"inspect",nonce)
            old = inspected.pop("ordinary_token_for_parent")
            claims = inventory["verified_claims"](old,old_key)
            require(claims is not None and {k:v for k,v in claims.items() if k not in {"iat","exp"}} == entry["verified_binding"],"profile_claims_changed_since_inventory")
            lifetime = claims["exp"]-claims["iat"]
            require(3600 <= lifetime <= 86400,"existing_profile_lifetime_requires_review")
            token = issuer["sign_claims"](dict(claims,iat=now,exp=now+lifetime),candidate.encode())
            values.append((entry,old,token))
        result["credentials_generated"] = len(values)
        result["checkpoint"] = "owner_preparation"
        result["permission_hardening_may_have_occurred"] = True
        for index,(entry,old,new) in enumerate(values):
            result["profile_index"] = index
            prepared.append((entry,old,new))
            run_child(entry,"prepare",nonce,old,new)
            result["profiles_changed"] = True
        result["checkpoint"] = "backend_publication"
        touched = True
        shared["control"]("stop")
        for name,raw in originals.items():
            path = Path("/etc/enhanced-cognee") / (name+".json")
            require(read(path,0) == raw,"backend_configuration_changed_concurrently")
            value = json.loads(raw)
            value["ENHANCED_JWT_SECRET"] = candidate
            replace(path,json.dumps(value).encode(),0)
        result["application_signing_key_changed"] = True
        result["checkpoint"] = "owner_publication"
        for index,(entry,old,new) in enumerate(values):
            result["profile_index"] = index
            run_child(entry,"publish",nonce,old,new)
        result["profiles_changed"] = True
        shared["control"]("start")
        result["checkpoint"] = "real_authentication"
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            try:
                if api_status(values[0][2])[0] == 200:break
            except OSError:pass
            time.sleep(1)
        else:raise ValueError("rotated_api_not_ready")
        require(api_status(old_proof)[0] == 401,"fresh_old_key_token_not_denied")
        for index,(entry,old,new) in enumerate(values):
            result["profile_index"] = index
            run_child(entry,"verify",nonce,old,new)
        require(issuer["load_signing_key"]() == candidate.encode(),"new_operator_api_key_binding_failed")
        result.update(complete=True,checkpoint="complete",credentials_issued=len(values),existing_bindings_reissued=len(values),
            scopes_roles_and_lifetimes_preserved=True,old_signing_key_fresh_token_denied=True,
            all_profile_credentials_authenticated=True,settings_and_oauth_preserved=True,
            permission_hardening_retained=True)
    except BaseException as error:
        result["category"] = "coordinated_application_rotation_incomplete_preserve_evidence"
        if isinstance(error,OwnerPhaseRefused):result["owner_phase_reason"] = error.safe_reason
        allowed = {"current_backend_key_not_verified","profile_claims_changed_since_inventory","existing_profile_lifetime_requires_review",
            "backend_configuration_changed_concurrently","rotated_api_not_ready","fresh_old_key_token_not_denied","new_operator_api_key_binding_failed"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
        restored = True
        for entry,old,new in reversed(prepared):
            try:run_child(entry,"rollback",nonce,old,new)
            except BaseException:restored = False
        result["profile_rollback_verified"] = restored
        if touched:
            result["application_signing_key_changed"] = None
            try:
                shared["control"]("stop")
                for name,raw in originals.items():
                    path = Path("/etc/enhanced-cognee") / (name+".json")
                    current = json.loads(read(path,0))
                    previous = json.loads(raw)
                    require(current.get("ENHANCED_JWT_SECRET") in {candidate,previous["ENHANCED_JWT_SECRET"]},"concurrent_backend_key_requires_review")
                    current["ENHANCED_JWT_SECRET"] = previous["ENHANCED_JWT_SECRET"]
                    replace(path,json.dumps(current).encode(),0)
                shared["control"]("start")
                result["backend_rollback_started"] = True
                require(issuer["load_signing_key"]() == old_key,"rollback_key_binding_not_verified")
                deadline = time.monotonic()+60
                while time.monotonic() < deadline:
                    try:
                        if api_status(old_proof)[0] == 200:break
                    except OSError:pass
                    time.sleep(1)
                else:raise ValueError("rollback_api_key_not_verified")
                result["application_signing_key_changed"] = False
                result["backend_rollback_verified"] = True
            except BaseException:
                result["backend_rollback_verified"] = False
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"application_rotation_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
