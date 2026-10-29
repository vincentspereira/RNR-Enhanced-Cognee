"""Rotate staged graph service logins, Qdrant keys and cache worker login.

Preserve existing graph/cache ACLs, all data, encryption keys and private
profiles. Snapshot configs, stop consumers, restart stores and validate before
selecting new consumer credentials. No legacy account removal or fleet launch.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import signal
import sys
import time
import uuid
from urllib.parse import quote, unquote, urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
SOURCES = {
    "recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef",
    "install_launch_cache_operator.py":"3084341ecd75655725542afbd673e41d6e99e28ad93a648b085ad5f5067f7741"}
UNITS = {"api":"enhanced-cognee-api.service","worker":"enhanced-cognee-index.service",
    "graph":"enhanced-cognee-graph.service","cache":"enhanced-cognee-cache.service","qdrant":"enhanced-cognee-qdrant.service"}


def support(name):
    raw = Path(__file__).with_name(name).read_bytes()
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != SOURCES[name]:
        raise ValueError("reviewed_support_required")
    namespace = {"__name__":"verified_derived_rotation_support"}
    exec(compile(raw,"<verified-derived-rotation-support>","exec"),namespace)
    return namespace


def staged_identity(row,kind):
    if (not isinstance(row,dict) or set(row) != {"username","password"}
            or not isinstance(row["username"],str) or not re.fullmatch("ec_"+kind+r"_[a-f0-9]{12}",row["username"])
            or not isinstance(row["password"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}",row["password"])):
        raise ValueError("generated_identity_required")
    return row["username"],row["password"]


def append_graph_users(raw,configs,candidates,hash_password):
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    names = [row["name"] for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("unique_graph_users_required")
    additions = []
    for kind in ("api","worker"):
        old_name = configs[kind]["INDEX_ARCADEDB_USER"]
        username,password = staged_identity(candidates[kind],kind)
        source = next((row for row in rows if row["name"] == old_name),None)
        if (source is None or old_name == "root" or username in names
                or not isinstance(source.get("databases"),dict) or "*" in source["databases"]):
            raise ValueError("restricted_existing_graph_service_grants_required")
        clone = dict(source,name=username,password=hash_password(password))
        additions.append(json.dumps(clone,ensure_ascii=True).encode()+b"\n")
    return raw+(b"\n" if raw and not raw.endswith(b"\n") else b"")+b"".join(additions)


def append_cache_worker(raw,old_user,old_password,candidate):
    username,password = staged_identity(candidate,"worker")
    selected = []
    for line in raw.decode("ascii").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        tokens = shlex.split(line,comments=False)
        if tokens[:2] == ["user",username]:
            raise ValueError("existing_cache_candidate_preserved")
        if tokens[:2] == ["user",old_user]:
            selected.append(line)
    if len(selected) != 1:
        raise ValueError("unique_existing_worker_acl_required")
    line = selected[0]
    hashes = re.findall(r"(?<!\S)#([a-f0-9]{64})(?=\s|$)",line)
    if len(hashes) != 1 or not hmac.compare_digest(hashes[0],hashlib.sha256(old_password.encode()).hexdigest()):
        raise ValueError("existing_worker_password_hash_not_verified")
    clone = re.sub(r"^(\s*user\s+)\S+",lambda match:match.group(1)+username,line,count=1)
    clone = clone.replace("#"+hashes[0],"#"+hashlib.sha256(password.encode()).hexdigest(),1)
    return raw+(b"\n" if raw and not raw.endswith(b"\n") else b"")+clone.encode()+b"\n"


def qdrant_configuration(original,candidates):
    updated = copy.deepcopy(original)
    if not isinstance(updated,dict) or not isinstance(updated.get("service"),dict):
        raise ValueError("existing_qdrant_service_configuration_required")
    for role,field in (("readonly","read_only_api_key"),("admin_write","api_key")):
        key = candidates[role]["api_key"]
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}",key):
            raise ValueError("generated_vector_key_required")
        updated["service"][field] = key
    return updated


def http_status(port,path,headers,method="GET",body=None):
    client = HTTPConnection("127.0.0.1",port,timeout=3)
    try:
        client.request(method,path,body=None if body is None else json.dumps(body),headers=headers)
        response = client.getresponse()
        response.read(16385)
        return response.status
    finally:
        client.close()


def await_check(check):
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        try:
            if check():
                return True
        except OSError:
            pass
        time.sleep(1)
    return False


def readonly_write_probe(admin_key,readonly_key):
    # This collection belongs to the retained successful disposable recovery,
    # not the live pipeline. Never target an existing point for denial tests.
    collection = "/collections/ec_lr_cc098bbed2b9424a"
    exists = http_status(28535,collection,{"api-key":admin_key})
    ident = str(uuid.uuid4())
    absent = http_status(28535,collection+"/points/"+ident,{"api-key":admin_key})
    result = {"collection_exists_http":exists,"absent_point_http":absent}
    if exists != 200 or absent != 404:
        return False,result
    code = http_status(28535,collection+"/points/delete?wait=true",
        {"api-key":readonly_key,"Content-Type":"application/json"},"POST",{"points":[ident]})
    result["readonly_delete_http"] = code
    return code in {401,403},result


def main():
    if os.geteuid() != 0 or Path(sys.prefix) != BASE / "runtime":
        raise ValueError("protected_operator_python_required")
    retry = sys.argv[1:] == ["--retry-after-verified-rollback"]
    if sys.argv[1:] and not retry:
        raise ValueError("fixed_rotation_action_required")
    import yaml
    os.umask(0o077)
    shared = support("recover_launch_graph_operator.py")
    cache = support("install_launch_cache_operator.py")
    read,write,replace = (shared[k] for k in ("read_file","private_write","replace_file"))
    pg = json.loads(read(STAGE / "postgres-service-rotation/summary.json",0))
    if pg.get("complete") is not True:
        raise ValueError("postgres_service_rotation_required")
    candidates = json.loads(read(STAGE / "replacement-logins.private.json",0))
    graph_owner = pwd.getpwnam("ecmem_graph").pw_uid
    paths = {"api":Path("/etc/enhanced-cognee/api.json"),"worker":Path("/etc/enhanced-cognee/worker.json"),
             "graph":Path("/var/lib/enhanced-cognee/arcade/config/server-users.jsonl"),
             "cache":Path("/etc/enhanced-cognee/valkey-users.acl"),"qdrant":Path("/etc/enhanced-cognee/qdrant.yaml")}
    owners = {name:graph_owner if name == "graph" else 0 for name in paths}
    original = {name:read(path,owners[name]) for name,path in paths.items()}
    if retry:
        previous = STAGE / "derived-service-rotation"
        receipt = json.loads(read(previous / "summary.json",0))
        if (receipt.get("complete") is not False or receipt.get("rollback_api_ready") is not True
                or receipt.get("reason") != "vector_readonly_write_boundary_failed"):
            raise ValueError("verified_specific_rollback_required")
        if any(read(previous / (name+".before.private"),0) != raw for name,raw in original.items()):
            raise ValueError("rollback_configurations_do_not_match")
    configs = {name:json.loads(original[name]) for name in ("api","worker")}
    uri = urlsplit(configs["worker"]["INDEX_VALKEY_URL"])
    if uri.hostname not in {"127.0.0.1","localhost"} or uri.port != 28537 or uri.path not in {"","/0"}:
        raise ValueError("fixed_cache_binding_required")
    vector = yaml.safe_load(original["qdrant"])
    if (vector.get("service",{}).get("api_key") != configs["worker"]["INDEX_QDRANT_API_KEY"]
            or vector.get("service",{}).get("read_only_api_key") != configs["api"]["INDEX_QDRANT_API_KEY"]):
        raise ValueError("active_vector_authority_binding_required")
    changed = {"graph":append_graph_users(original["graph"],configs,candidates["arcadedb"],shared["password_hash"]),
               "cache":append_cache_worker(original["cache"],unquote(uri.username or "default"),unquote(uri.password or ""),candidates["valkey"]["worker"]),
               "qdrant":json.dumps(qdrant_configuration(vector,candidates["qdrant"])).encode()}
    for kind in ("api","worker"):
        username,password = staged_identity(candidates["arcadedb"][kind],kind)
        configs[kind].update(INDEX_ARCADEDB_USER=username,INDEX_ARCADEDB_PASSWORD=password,
            INDEX_QDRANT_API_KEY=candidates["qdrant"]["readonly" if kind == "api" else "admin_write"]["api_key"])
    username,password = staged_identity(candidates["valkey"]["worker"],"worker")
    configs["worker"]["INDEX_VALKEY_URL"] = "redis://"+quote(username,safe="")+":"+quote(password,safe="")+"@127.0.0.1:28537/0"
    for kind in ("api","worker"):
        changed[kind] = json.dumps(configs[kind]).encode()
    attempt = STAGE / ("derived-service-rotation-valid-probe" if retry else "derived-service-rotation")
    attempt.mkdir(mode=0o700)
    for name,raw in original.items():
        write(attempt / (name+".before.private"),raw)
    result = {"complete":False,"evidence":str(attempt),"checkpoint":"store_selection","profiles_changed":False,
        "encryption_keys_changed":False,"application_signing_key_changed":False,"all_credentials_rotated":False,
        "old_graph_cache_users_retained":True,"fleet_launch_approved":False}
    touched = False
    def control(action,name):
        shared["UNIT"] = UNITS[name]
        shared["control"](action)
    def interrupted(signum,frame):
        raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    try:
        write(attempt / "before-stop.json",b'{"derived_service_rotation_started":true}')
        touched = True
        for name in ("worker","api","graph","qdrant","cache"):
            control("stop",name)
        for name,path in paths.items():
            if read(path,owners[name]) != original[name]:
                raise ValueError("store_configuration_changed_concurrently")
            replace(path,changed[name],owners[name])
        for name in ("graph","qdrant","cache"):
            control("start",name)
        for kind in ("api","worker"):
            name,password = staged_identity(candidates["arcadedb"][kind],kind)
            if not await_check(lambda:shared["graph_status"](name,password) == 200):
                raise ValueError("new_graph_service_authentication_failed")
        name,password = staged_identity(candidates["valkey"]["worker"],"worker")
        if not cache["ping"](name,password):
            raise ValueError("new_cache_worker_authentication_failed")
        for kind in ("readonly","admin_write"):
            key = candidates["qdrant"][kind]["api_key"]
            if not await_check(lambda:http_status(28535,"/collections",{"api-key":key}) == 200):
                raise ValueError("new_vector_key_authentication_failed")
        if any(http_status(28535,"/collections",{"api-key":vector["service"][field]}) not in {401,403}
               for field in ("api_key","read_only_api_key")):
            raise ValueError("old_vector_key_still_accepted")
        denied,probe = readonly_write_probe(candidates["qdrant"]["admin_write"]["api_key"],
                                           candidates["qdrant"]["readonly"]["api_key"])
        result["readonly_write_probe"] = probe
        if not denied:
            raise ValueError("vector_readonly_write_boundary_failed")
        result["checkpoint"] = "consumer_restart"
        control("start","api")
        control("start","worker")
        if not await_check(lambda:http_status(28080,"/health/ready",{}) == 200):
            raise ValueError("rotated_consumer_readiness_failed")
        result.update(complete=True,checkpoint="complete",new_graph_services_authenticated=True,
            new_valkey_worker_authenticated=True,new_qdrant_keys_authenticated=True,old_qdrant_keys_denied=True,
            qdrant_readonly_write_denied=True,api_ready=True,post_rotation_projection_qualified=False)
    except BaseException as error:
        result["category"] = "derived_service_rotation_incomplete_preserve_evidence"
        allowed = {"store_configuration_changed_concurrently","new_graph_service_authentication_failed",
            "new_cache_worker_authentication_failed","new_vector_key_authentication_failed",
            "old_vector_key_still_accepted","vector_readonly_write_boundary_failed","rotated_consumer_readiness_failed"}
        result["reason"] = str(error) if type(error) is ValueError and str(error) in allowed else "store_or_service_control_error"
        if touched:
            try:
                for name in ("worker","api","graph","qdrant","cache"):
                    control("stop",name)
                for name,path in paths.items():
                    replace(path,original[name],owners[name])
                for name in ("graph","qdrant","cache","api","worker"):
                    control("start",name)
                result["rollback_api_ready"] = await_check(lambda:http_status(28080,"/health/ready",{}) == 200)
            except BaseException:
                result["rollback_api_ready"] = False
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        allowed = {"protected_operator_python_required","reviewed_support_required","postgres_service_rotation_required",
            "generated_identity_required","unique_graph_users_required","restricted_existing_graph_service_grants_required",
            "existing_cache_candidate_preserved","unique_existing_worker_acl_required","existing_worker_password_hash_not_verified",
            "existing_qdrant_service_configuration_required","generated_vector_key_required","fixed_cache_binding_required",
            "active_vector_authority_binding_required","protected_ancestor_required","protected_file_required"}
        allowed.update({"fixed_rotation_action_required","verified_specific_rollback_required","rollback_configurations_do_not_match"})
        reason = str(error) if type(error) is ValueError and str(error) in allowed else "protected_input_or_configuration_error"
        print(json.dumps({"complete":False,"category":"derived_service_rotation_preflight_refused_no_secret_output","reason":reason}))
        raise SystemExit(1)
