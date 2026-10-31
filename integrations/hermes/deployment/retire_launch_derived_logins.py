"""Retire old graph passwords/cache login, preserving accounts, grants and data.

Restart graph/cache and their consumers once. Retain private snapshots; restore
only our exact file selections on failure. No profile access or key changes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shlex
import signal
import sys
import time
from urllib.parse import unquote,urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
PINS = {"recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef",
        "install_launch_cache_operator.py":"3084341ecd75655725542afbd673e41d6e99e28ad93a648b085ad5f5067f7741",
        "rotate_launch_derived_services.py":"8571d3ea79cc9453797afe9453bd618969e21eab6cb27eb478a4a6137f572499"}
UNITS = {"api":"enhanced-cognee-api.service","worker":"enhanced-cognee-index.service",
         "graph":"enhanced-cognee-graph.service","cache":"enhanced-cognee-cache.service"}


def require(value,reason):
    if not value:raise ValueError(reason)


def definitions(name):
    raw = Path(__file__).with_name(name).read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == PINS[name],"reviewed_support_required")
    namespace = {"__name__":"verified_derived_retirement_support"}
    exec(compile(raw,"<verified-derived-retirement-support>","exec"),namespace)
    return namespace


def cache_binding(value):
    uri = urlsplit(value)
    require(uri.scheme == "redis" and uri.hostname in {"127.0.0.1","localhost"} and uri.port == 28537
        and uri.path in {"","/0"} and uri.username and uri.password,"fixed_cache_binding_required")
    return unquote(uri.username),unquote(uri.password)


def graph_replacement(raw,old,current,hash_password,matches):
    previous = {row["INDEX_ARCADEDB_USER"]:row["INDEX_ARCADEDB_PASSWORD"] for row in old.values()}
    selected = {row["INDEX_ARCADEDB_USER"] for row in current.values()}
    require(len(previous) == 2 and len(selected) == 2 and "root" not in previous
        and not set(previous) & selected,"distinct_superseded_graph_identities_required")
    lines = raw.splitlines(keepends=True)
    rows = [json.loads(line) for line in lines if line.strip()]
    names = [row["name"] for row in rows]
    require(len(names) == len(set(names)) and set(previous) <= set(names) and selected <= set(names),"unique_existing_graph_users_required")
    for row in rows:
        if row["name"] in previous:
            require(matches(previous[row["name"]],row["password"]),"old_graph_hash_binding_required")
    output = []
    for line in lines:
        if line.strip():
            row = json.loads(line)
            if row["name"] in previous:
                # Unissued random replacements retire the old passwords without
                # deleting users or changing any database grants.
                row["password"] = hash_password(secrets.token_urlsafe(48))
                line = json.dumps(row,ensure_ascii=True).encode()+b"\n"
        output.append(line)
    return b"".join(output)


def cache_replacement(raw,old_user,old_password,current_user,operator_user):
    require(old_user not in {current_user,operator_user} and current_user != operator_user,"superseded_cache_identity_required")
    lines = raw.decode("ascii").splitlines(keepends=True)
    selected = []
    names = []
    for index,line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):continue
        tokens = shlex.split(line,comments=False)
        require(len(tokens) >= 3 and tokens[0] == "user","reviewed_cache_acl_required")
        names.append(tokens[1])
        if tokens[1] == old_user:selected.append((index,tokens))
    require(len(names) == len(set(names)) and len(selected) == 1
        and {current_user,operator_user} <= set(names),"unique_existing_cache_users_required")
    index,tokens = selected[0]
    require("#"+hashlib.sha256(old_password.encode()).hexdigest() in tokens,"old_cache_hash_binding_required")
    # Last flags win: off disallows authentication and resetpass removes old
    # password hashes. Preserve the account and its namespace/command rules.
    lines[index] = lines[index].rstrip("\r\n")+" off resetpass\n"
    return "".join(lines).encode("ascii")


def run_selection(shared,read,replace,paths,owners,original,changed,control,check,unchanged,result):
    touched = False
    try:
        unchanged()
        touched = True
        result["checkpoint"] = "controlled_store_restart"
        for name in ("worker","api","graph","cache"):control("stop",name)
        unchanged()
        for name,path in paths.items():
            require(read(path,owners[name]) == original[name],"store_file_changed_concurrently")
            replace(path,changed[name],owners[name])
        for name in ("graph","cache"):control("start",name)
        check(True)
        for name in ("api","worker"):control("start",name)
        require(shared["await_check"](lambda:shared["http_status"](28080,"/health/ready",{}) == 200),"api_not_ready")
        unchanged()
        result.update(complete=True,checkpoint="complete",retired_graph_password_count=2,retired_cache_login_count=1,
            old_graph_passwords_denied=True,old_cache_login_denied=True,replacement_logins_authenticated=True,
            graph_users_and_grants_retained=True,cache_user_and_rules_retained=True,api_ready=True,
            post_retirement_projection_qualified=False)
    except BaseException as error:
        result["category"] = "derived_login_retirement_incomplete_preserve_evidence"
        allowed = {"store_file_changed_concurrently","protected_configuration_changed_concurrently","api_not_ready",
            "current_graph_authentication_failed","current_cache_authentication_failed","old_graph_password_still_accepted",
            "old_cache_login_still_accepted"}
        result["reason"] = str(error) if type(error) is ValueError and str(error) in allowed else "store_or_service_control_error"
        if touched:
            try:
                for name in ("worker","api","graph","cache"):control("stop",name)
                conflict = False
                for name,path in paths.items():
                    current = read(path,owners[name])
                    if current == changed[name]:replace(path,original[name],owners[name])
                    elif current != original[name]:conflict = True
                for name in ("graph","cache"):control("start",name)
                for name in ("api","worker"):control("start",name)
                check(False)
                ready = shared["await_check"](
                    lambda:shared["http_status"](28080,"/health/ready",{}) == 200)
                result["rollback_current_logins_and_api_verified"] = ready and not conflict
                if conflict:result["concurrent_store_file_preserved"] = True
            except BaseException:result["rollback_current_logins_and_api_verified"] = False


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    graph,cache,service = (definitions(name) for name in PINS)
    read,write,replace = (graph[k] for k in ("read_file","private_write","replace_file"))
    for name in ("derived-service-rotation-valid-probe","application-signing-rotation","postgres-legacy-login-retirement"):
        require(json.loads(read(STAGE / name / "summary.json",0)).get("complete") is True,"prior_credential_gate_required")
    selected = {kind:read(Path("/etc/enhanced-cognee") / (kind+".json"),0) for kind in ("api","worker")}
    current = {kind:json.loads(value) for kind,value in selected.items()}
    old = {kind:json.loads(read(STAGE / "derived-service-rotation-valid-probe" / (kind+".before.private"),0)) for kind in selected}
    old_cache = cache_binding(old["worker"]["INDEX_VALKEY_URL"])
    active_cache = cache_binding(current["worker"]["INDEX_VALKEY_URL"])
    operator_cache = cache_binding(json.loads(read(Path("/etc/enhanced-cognee/launch-cache-authority.json"),0))["INDEX_VALKEY_URL"])
    operator_graph = json.loads(read(Path("/etc/enhanced-cognee/launch-index-authority.json"),0))
    candidates = json.loads(read(STAGE / "replacement-logins.private.json",0))
    for kind,row in current.items():
        expected = candidates["arcadedb"][kind]
        require((row["INDEX_ARCADEDB_USER"],row["INDEX_ARCADEDB_PASSWORD"]) == (expected["username"],expected["password"]),
                "staged_current_graph_binding_required")
    expected = candidates["valkey"]["worker"]
    require(active_cache == (expected["username"],expected["password"]),"staged_current_cache_binding_required")
    paths = {"graph":Path("/var/lib/enhanced-cognee/arcade/config/server-users.jsonl"),"cache":Path("/etc/enhanced-cognee/valkey-users.acl")}
    owners = {"graph":pwd.getpwnam("ecmem_graph").pw_uid,"cache":0}
    original = {name:read(path,owners[name]) for name,path in paths.items()}
    changed = {"graph":graph_replacement(original["graph"],old,current,graph["password_hash"],graph["matches"]),
        "cache":cache_replacement(original["cache"],*old_cache,active_cache[0],operator_cache[0])}
    for row in old.values():
        require(graph["graph_status"](row["INDEX_ARCADEDB_USER"],row["INDEX_ARCADEDB_PASSWORD"]) == 200,"old_graph_positive_control_required")
    require(cache["cache_call"](*old_cache,"PING") == ("simple",b"PONG"),"old_cache_positive_control_required")
    def unchanged():
        require(all(read(Path("/etc/enhanced-cognee") / (kind+".json"),0) == value for kind,value in selected.items()),"protected_configuration_changed_concurrently")
    def check(retired):
        for row in (*current.values(),operator_graph):
            require(service["await_check"](lambda:graph["graph_status"](row["INDEX_ARCADEDB_USER"],row["INDEX_ARCADEDB_PASSWORD"]) == 200),"current_graph_authentication_failed")
        for identity in (active_cache,operator_cache):
            require(cache["ping"](*identity),"current_cache_authentication_failed")
        if retired:
            for row in old.values():
                require(graph["graph_status"](row["INDEX_ARCADEDB_USER"],row["INDEX_ARCADEDB_PASSWORD"]) in {401,403},"old_graph_password_still_accepted")
            require(cache["cache_call"](*old_cache,"PING") == ("refused",None),"old_cache_login_still_accepted")
    check(False)
    attempt = STAGE / "derived-legacy-login-retirement"
    attempt.mkdir(mode=0o700)
    for name,value in original.items():write(attempt / (name+".before.private"),value)
    result = dict(complete=False,evidence=str(attempt),source_revision=BASE.name,checkpoint="protected_preflight",
        profiles_changed=False,canonical_memory_edits=False,keys_changed=False,all_credentials_rotated=False,fleet_launch_approved=False)
    write(attempt / "started.json",json.dumps(result).encode())
    def control(action,name):
        graph["UNIT"] = UNITS[name]
        graph["control"](action)
    def interrupted(signum,frame):raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    run_selection(service,read,replace,paths,owners,original,changed,control,check,unchanged,result)
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"derived_retirement_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
