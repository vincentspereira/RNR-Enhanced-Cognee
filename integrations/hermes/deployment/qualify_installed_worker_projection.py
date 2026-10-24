"""One NEW invented API scope proves delivery by the installed worker.

No model chat, profile edits or old-record replay. A new canonical record is
created/retracted, retaining history; running stores are exercised normally.
"""
from __future__ import annotations

import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from urllib.parse import unquote, urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
SOURCES = {
    "recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef",
    "provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "install_launch_cache_operator.py":"3084341ecd75655725542afbd673e41d6e99e28ad93a648b085ad5f5067f7741"}


def definitions(name):
    path = Path(__file__).with_name(name)
    fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd,"rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != SOURCES[name]:
        raise ValueError("reviewed_source_required")
    namespace = {"__name__":"verified_worker_projection_support"}
    exec(compile(raw,"<verified-worker-projection-support>","exec"),namespace)
    return namespace


def api(token,method,path,body=None):
    if not path.startswith("/v1/memories"):
        raise ValueError("fixed_memory_endpoint_required")
    connection = HTTPConnection("127.0.0.1",28080,timeout=5)
    try:
        connection.request(method,path,body=None if body is None else json.dumps(body),
            headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        response = connection.getresponse()
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("bounded_response_required")
        return response.status,json.loads(raw)
    finally:
        connection.close()


def record_cache_key(key,pipeline,project,ident):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}",pipeline):
        raise ValueError("fixed_pipeline_required")
    raw = json.dumps([pipeline,"record","qualification",project,ident],ensure_ascii=True,separators=(",",":")).encode()
    return "ec:"+pipeline+":"+hmac.new(key.encode(),raw,hashlib.sha256).hexdigest()


def projection_ready(ident,recall,graph,cached,text):
    return (isinstance(recall,dict) and recall.get("vector_index") == "queried"
        and any(isinstance(row,dict) and row.get("id") == ident for row in recall.get("results",[]))
        and isinstance(graph,dict) and bool(graph.get("paths")) and cached is not None
        and isinstance(json.loads(cached).get("payload"),str) and json.loads(cached)["payload"].startswith("enc2:")
        and text.encode() not in cached)


def public_index_settings():
    path = Path("/etc/enhanced-cognee/index.json")
    for parent in reversed(path.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("protected_index_settings_required")
    fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd,"rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or info.st_size > 16384:
            raise ValueError("protected_index_settings_required")
        return json.loads(stream.read(16385))


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    os.umask(0o077)
    support = definitions("recover_launch_graph_operator.py")
    read,write = support["read_file"],support["private_write"]
    switched = json.loads(read(BASE / "operator-evidence/controlled-runtime-switch/summary.json",0))
    if switched.get("complete") is not True or switched.get("worker_candidate_bound") is not True:
        raise ValueError("installed_worker_required")
    worker = json.loads(read(Path("/etc/enhanced-cognee/worker.json"),0))
    settings = public_index_settings()
    cache = definitions("install_launch_cache_operator.py")["cache_call"]
    uri = urlsplit(worker["INDEX_VALKEY_URL"])
    if uri.hostname not in {"localhost","127.0.0.1"} or uri.port != 28537 or uri.path not in {"","/0"}:
        raise ValueError("fixed_cache_binding_required")
    cache_user,cache_password = unquote(uri.username or "default"),unquote(uri.password or "")
    attempt = BASE / "operator-evidence/installed-worker-projection"
    attempt.mkdir(mode=0o700)  # Never replay an incomplete or finished attempt.
    issuer = definitions("provision_pilot_access.py")
    suffix = secrets.token_hex(8)
    project = "wp_"+suffix
    identity = {"sub":"worker_projection","agent_id":"worker_projection","tenant":"qualification",
                "project_id":project,"roles":["api_client"],"capture_policy":"selected"}
    now = int(time.time())
    key = issuer["load_signing_key"]()
    token = issuer["sign_claims"](dict(identity,iat=now,exp=now+600),key)
    peer = issuer["sign_claims"](dict(identity,project_id="peer_"+suffix,sub="worker_peer",iat=now,exp=now+600),key)
    del key
    result = {"complete":False,"evidence":str(attempt),"project":project,"installed_worker_projection_qualified":False,
        "new_invented_canonical_record_written":False,"profiles_changed":False,"model_chat_called":False,
        "fleet_launch_approved":False,"checkpoint":"new_scope"}
    try:
        code,status = api(token,"GET","/v1/memories/status")
        if code != 200 or status.get("project_id") != project or status.get("active_records") != 0:
            raise ValueError("new_scope_required")
        text = "Invented worker probe "+suffix+": Cedar references Birch."
        write(attempt / "before-create.json",json.dumps({"project":project,"idempotency_key":"worker-probe-"+suffix}).encode())
        result["checkpoint"] = "create_invented_record"
        code,record = api(token,"POST","/v1/memories",{"content":text,"idempotency_key":"worker-probe-"+suffix,
            "knowledge_links":[{"subject":"Cedar","predicate":"references","object":"Birch","span_start":0,"span_end":len(text)}]})
        ident = record.get("id")
        if code not in {200,201} or not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",ident) or record.get("version") != 1:
            raise ValueError("new_record_not_acknowledged")
        result.update(new_invented_canonical_record_written=True,record_id=ident,checkpoint="installed_worker_delivery")
        write(attempt / "record-created.json",json.dumps({"project":project,"record_id":ident}).encode())
        endpoint = "/v1/memories/"+ident
        if api(peer,"GET",endpoint)[0] != 404:
            raise ValueError("peer_scope_denial_failed")
        cache_key = record_cache_key(worker["ENHANCED_INDEX_KEY"],settings["pipeline"],project,ident)
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            rc,recall = api(token,"POST","/v1/memories/recall",{"query":"Cedar Birch","limit":5})
            gc,graph = api(token,"POST","/v1/memories/connections",{"entity":"Cedar","depth":1})
            kind,cached = cache(cache_user,cache_password,"GET",cache_key)
            if rc == gc == 200 and kind == "bulk" and projection_ready(ident,recall,graph,cached,text):
                break
            time.sleep(1)
        else:
            raise ValueError("installed_worker_projection_not_ready")
        result.update(semantic_graph_encrypted_cache_verified=True,peer_scope_denied=True,checkpoint="withdrawal")
        code,retracted = api(token,"POST",endpoint+"/retract",{"expected_version":1})
        if code != 200 or retracted.get("state") != "retracted" or retracted.get("version") != 2:
            raise ValueError("new_probe_retraction_not_acknowledged")
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            sc,status = api(token,"GET","/v1/memories/status")
            rc,recall = api(token,"POST","/v1/memories/recall",{"query":"Cedar Birch","limit":5})
            gc,graph = api(token,"POST","/v1/memories/connections",{"entity":"Cedar","depth":1})
            kind,cached = cache(cache_user,cache_password,"GET",cache_key)
            if sc == rc == gc == 200 and status.get("pending_change_events") == 0 and not recall.get("results") and not graph.get("paths") and kind == "bulk" and cached is None:
                break
            time.sleep(1)
        else:
            raise ValueError("installed_worker_withdrawal_not_ready")
        code,history = api(token,"GET",endpoint+"/history?limit=10")
        if code != 200 or {row.get("version") for row in history.get("versions",[])} != {1,2}:
            raise ValueError("new_probe_history_not_verified")
        result.update(complete=True,installed_worker_projection_qualified=True,actual_withdrawal_verified=True,
                      new_record_retracted_history_preserved=True,checkpoint="complete")
    except BaseException:
        result["category"] = "installed_worker_projection_incomplete_preserve_evidence"
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError):
        print('{"complete":false,"category":"installed_worker_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
