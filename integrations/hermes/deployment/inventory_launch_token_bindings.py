"""Read-only owner-child memory-token bindings for signing-key coordination.

Root never walks profiles. Ordinary tokens cross a bounded pipe into root
memory for signature verification, never a persisted log or terminal output.
No key goes to children; no profile, API memory, model or launch state changes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
EXECUTABLE = "/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python"
ISSUER_SHA256 = "f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6"


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate_object_fields")
    return result


def verified_claims(token,key):
    if not isinstance(token,str) or not token.isascii() or len(token) > 4096:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    def decode(value):
        return base64.b64decode(value+"="*((4-len(value)%4)%4),altchars=b"-_",validate=True)
    try:
        header = json.loads(decode(parts[0]),object_pairs_hook=unique_object)
        claims = json.loads(decode(parts[1]),object_pairs_hook=unique_object)
        expected = hmac.new(key,(parts[0]+"."+parts[1]).encode(),hashlib.sha256).digest()
        if not isinstance(header,dict) or header.get("alg") != "HS256" or not hmac.compare_digest(decode(parts[2]),expected):
            return None
        fields = {"sub","agent_id","tenant","project_id","roles","capture_policy","iat","exp"}
        if not isinstance(claims,dict) or set(claims) != fields:
            return None
        if (any(not isinstance(claims[x],str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}",claims[x])
                for x in ("sub","agent_id","tenant","project_id"))
                or len(claims["tenant"]) > 32 or len(claims["project_id"]) > 32
                or claims["roles"] not in (["api_client"],["readonly"])
                or claims["capture_policy"] not in {"selected","explicit"}
                or type(claims["iat"]) is not int or type(claims["exp"]) is not int):
            return None
        return claims
    except (ValueError,UnicodeError,TypeError):
        return None


def read_owner_file(directory,name,uid):
    try:
        fd = os.open(name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=directory)
    except FileNotFoundError:
        return None
    with os.fdopen(fd,"rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_size > 65536:
            raise ValueError("profile_file_refused")
        raw = stream.read(65537)
        after = os.fstat(stream.fileno())
        if len(raw) > 65536 or (info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns) != (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError("profile_file_changed")
        return raw


def owner_child():
    uid = os.geteuid()
    if uid == 0 or os.getgroups():
        raise ValueError("restricted_owner_child_required")
    from dotenv.parser import parse_stream
    home = Path(pwd.getpwuid(uid).pw_dir) / ".hermes"
    fd = os.open("/",os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in home.parts[1:]:
            child = os.open(name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid not in {0,uid} or info.st_mode & 0o022:
                raise ValueError("owner_home_protection_required")
        profiles = [("main",str(home),os.dup(fd))]
        excluded = 0
        try:
            directory = os.open("profiles",os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
        except FileNotFoundError:
            directory = None
        if directory is not None:
            try:
                if os.fstat(directory).st_uid != uid:
                    raise ValueError("profiles_owner_mismatch")
                names = os.listdir(directory)
                if len(names) > 256:
                    raise ValueError("profile_inventory_budget")
                for name in sorted(names):
                    if "lswa" in name.casefold() or "legal-social-frameworks" in name.casefold():
                        excluded += 1
                        continue
                    info = os.stat(name,dir_fd=directory,follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode) and info.st_uid == uid:
                        opened = os.open(name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=directory)
                        profiles.append((name,str(home / "profiles" / name),opened))
            finally:
                os.close(directory)
        rows = []
        try:
            for name,profile_home,profile in profiles:
                row = {"profile":name,"profile_home":profile_home,"private_mode":stat.S_IMODE(os.fstat(profile).st_mode) == 0o700}
                try:
                    raw = read_owner_file(profile,"enhanced_cognee.json",uid)
                    settings = json.loads(raw) if raw is not None else {}
                    uri = urlsplit(settings.get("base_url", ""))
                    row["local_memory_configured"] = (uri.scheme == "http" and uri.hostname in {"127.0.0.1","localhost","::1"}
                        and uri.port == 28080 and not uri.username and not uri.password and uri.path in {"","/"})
                    raw = read_owner_file(profile,".env",uid)
                    token = None
                    if raw is not None:
                        selected = [x for x in parse_stream(io.StringIO(raw.decode("utf-8"))) if x.key == "ENHANCED_COGNEE_ACCESS_TOKEN"]
                        if len(selected) == 1 and not selected[0].error:
                            token = selected[0].value
                    row["memory_token_present"] = bool(token)
                    if isinstance(token,str) and len(token) <= 4096:
                        row["ordinary_token_for_parent_verification"] = token
                except (OSError,ValueError,UnicodeError,AttributeError):
                    row["binding_inspection_refused"] = True
                rows.append(row)
        finally:
            for _,_,profile in profiles:
                os.close(profile)
    finally:
        os.close(fd)
    raw = json.dumps({"rows":rows,"excluded_profiles":excluded},ensure_ascii=True).encode()
    if len(raw) > 262144:
        raise ValueError("binding_receipt_budget")
    sys.stdout.buffer.write(raw)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise ValueError("root_fixed_inventory_required")
    os.umask(0o077)
    raw = Path(__file__).with_name("provision_pilot_access.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != ISSUER_SHA256:
        raise ValueError("reviewed_issuer_source_required")
    issuer = {"__name__":"verified_binding_signature_reader"}
    exec(compile(raw,"<verified-binding-signature-reader>","exec"),issuer)
    key = issuer["load_signing_key"]()
    source = Path(__file__).read_bytes()
    evidence = Path(tempfile.mkdtemp(prefix="token-bindings-",dir=BASE / "operator-evidence"))
    rows = []
    complete = True
    for username in ("vincentspereira","hermes-runtime"):
        account = pwd.getpwnam(username)
        code = "import sys\nn={'__name__':'verified_binding_child'}\nexec(compile(sys.stdin.buffer.read(),'<verified-binding-child>','exec'),n)\nn['owner_child']()\n"
        child = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--",EXECUTABLE,"-I","-B","-c",code],
            input=source,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,user=account.pw_uid,group=account.pw_gid,
            extra_groups=(),cwd="/",timeout=90,env={"PATH":"/usr/bin:/bin","HOME":account.pw_dir,
                "LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
        if child.returncode or len(child.stdout) > 262144:
            complete = False
            rows.append({"user":username,"inventory_complete":False})
            continue
        document = json.loads(child.stdout)
        if document.get("excluded_profiles"):
            rows.append({"user":username,"excluded_profile_count":document["excluded_profiles"],"admission":"excluded"})
        for item in document["rows"]:
            token = item.pop("ordinary_token_for_parent_verification",None)
            claims = verified_claims(token,key)
            row = dict(item,user=username,uid=account.pw_uid,home=account.pw_dir,
                       token_signature_valid=claims is not None,admission="pending",credentials_issued=False)
            if claims is not None:
                row["verified_binding"] = {k:v for k,v in claims.items() if k not in {"iat","exp"}}
                row["token_expired"] = claims["exp"] <= int(time.time())
            rows.append(row)
        # Never persist or print the child's credential-bearing transport.
        del child
    del key
    with (evidence / "bindings.private.json").open("x",encoding="ascii") as stream:
        json.dump({"rows":rows},stream,ensure_ascii=True,indent=2)
    summary = {"complete":complete,"evidence":str(evidence),"profiles_inspected":sum("profile" in r for r in rows),
        "local_memory_configs":sum(r.get("local_memory_configured") is True for r in rows),
        "profiles_with_memory_tokens":sum(r.get("memory_token_present") is True for r in rows),
        "verified_token_bindings":sum(r.get("token_signature_valid") is True for r in rows),
        "excluded_profile_count":sum(r.get("excluded_profile_count",0) for r in rows),
        "unresolved_profile_bindings":sum(r.get("binding_inspection_refused") is True
            or r.get("memory_token_present") is True and r.get("token_signature_valid") is not True for r in rows),
        "profiles_changed":False,"signing_key_changed":False,"credentials_issued":0,"fleet_launch_approved":False}
    with (evidence / "summary.json").open("x",encoding="ascii") as stream:
        json.dump(summary,stream)
    print(json.dumps(summary))
    return 0 if complete else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"binding_inventory_refused_no_secret_output"}')
        raise SystemExit(1)
