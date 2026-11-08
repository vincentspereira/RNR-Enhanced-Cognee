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
import socket
import stat
import sys
import time
from urllib.parse import unquote, urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
SOURCES = {
    "recover_launch_graph_operator.py":"d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef",
    "provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "install_launch_cache_operator.py":"3084341ecd75655725542afbd673e41d6e99e28ad93a648b085ad5f5067f7741"}
INSPECTION_PHASE = "protected_preflight"


def cache_bulk_reply(stream):
    line = stream.readline(4097)
    if len(line) > 4096 or not line.endswith(b"\r\n"):
        raise ValueError("bounded_cache_response_required")
    if line.startswith(b"-"):
        return "refused",None
    if not line.startswith(b"$"):
        raise ValueError("cache_bulk_response_required")
    length = int(line[1:-2])
    if length == -1:
        return "bulk",None
    if not 0 <= length <= 262144:
        raise ValueError("bounded_cache_response_required")
    raw = stream.read(length+2)
    if len(raw) != length+2 or raw[-2:] != b"\r\n":
        raise ValueError("bounded_cache_response_required")
    return "bulk",raw[:-2]


def cache_get(username,password,key):
    if not re.fullmatch(r"ec:[a-z][a-z0-9_]{0,31}:[a-f0-9]{64}",key):
        raise ValueError("fixed_cache_key_required")
    command = definitions("install_launch_cache_operator.py")["command"]
    with socket.create_connection(("127.0.0.1",28537),timeout=3) as sock:
        with sock.makefile("rb") as stream:
            if command(sock,stream,"AUTH",username,password) != ("simple",b"OK"):
                return "refused",None
            raw = key.encode("ascii")
            sock.sendall(b"*2\r\n$3\r\nGET\r\n$"+str(len(raw)).encode()+b"\r\n"+raw+b"\r\n")
            return cache_bulk_reply(stream)


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


def inspect_existing(finish=False):
    global INSPECTION_PHASE
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    support = definitions("recover_launch_graph_operator.py")
    read = support["read_file"]
    attempt = BASE / "operator-evidence/installed-worker-projection"
    previous = json.loads(read(attempt / "summary.json",0))
    if previous.get("project") != "wp_10df177d41ceef89" or previous.get("record_id") != "c85b599e-69b4-46f4-ac8d-9f3848bc3d3b":
        raise ValueError("fixed_observed_probe_required")
    issuer = definitions("provision_pilot_access.py")
    now = int(time.time())
    key = issuer["load_signing_key"]()
    token = issuer["sign_claims"]({"sub":"worker_projection","agent_id":"worker_projection",
        "tenant":"qualification","project_id":previous["project"],"roles":["api_client"],
        "capture_policy":"selected","iat":now,"exp":now+300},key)
    del key
    result = {"stage":"read_only_installed_worker_probe_inspection","memory_written":False,
              "model_chat_called":False,"profiles_changed":False,"fleet_launch_approved":False}
    INSPECTION_PHASE = "status"
    code,status = api(token,"GET","/v1/memories/status")
    index = status.get("index",{}) if isinstance(status,dict) else {}
    state = index.get("worker_state")
    pending = status.get("pending_change_events")
    result.update(status_http=code,worker_available=index.get("worker_available") is True,
        worker_state=state if state in {"running","degraded","unavailable"} else "other",
        pending_change_events=pending if type(pending) is int and 0 <= pending <= 1000000 else None)
    INSPECTION_PHASE = "recall"
    code,recall = api(token,"POST","/v1/memories/recall",{"query":"Cedar Birch","limit":5})
    result.update(recall_http=code,vector_queried=recall.get("vector_index") == "queried",
        probe_in_recall=any(isinstance(row,dict) and row.get("id") == previous["record_id"] for row in recall.get("results",[])))
    INSPECTION_PHASE = "graph"
    code,graph = api(token,"POST","/v1/memories/connections",{"entity":"Cedar","depth":1})
    result.update(graph_http=code,graph_paths_present=bool(graph.get("paths")))
    worker = json.loads(read(Path("/etc/enhanced-cognee/worker.json"),0))
    settings = public_index_settings()
    uri = urlsplit(worker["INDEX_VALKEY_URL"])
    cache_key = record_cache_key(worker["ENHANCED_INDEX_KEY"],settings["pipeline"],previous["project"],previous["record_id"])
    INSPECTION_PHASE = "cache"
    cache_user,cache_password = unquote(uri.username or "default"),unquote(uri.password or "")
    kind,cached = cache_get(cache_user,cache_password,cache_key)
    result.update(cache_get_refused=kind == "refused",cache_value_present=cached is not None)
    result["cache_reply_bytes"] = len(cached) if cached is not None else 0
    if kind == "bulk" and cached is not None:
        parsed = json.loads(cached)
        result["cache_payload_encrypted"] = isinstance(parsed.get("payload"),str) and parsed["payload"].startswith("enc2:")
    if finish:
        if (not all(result.get(k) is True for k in ("worker_available","vector_queried","probe_in_recall",
                "graph_paths_present","cache_payload_encrypted")) or result.get("pending_change_events") != 0):
            result.update(complete=False,category="existing_probe_delivery_not_ready_preserve_record")
            print(json.dumps(result))
            return 1
        endpoint = "/v1/memories/"+previous["record_id"]
        code,row = api(token,"GET",endpoint)
        if code != 200 or row.get("version") != 1 or row.get("state") != "active" or row.get("project_id") != previous["project"]:
            raise ValueError("fixed_active_probe_version_required")
        support["private_write"](attempt / "finish-existing.started.json",json.dumps({"record_id":previous["record_id"],"expected_version":1}).encode())
        result.update(stage="finish_existing_installed_worker_probe",memory_written=True,checkpoint="probe_retraction")
        INSPECTION_PHASE = "probe_retraction"
        code,row = api(token,"POST",endpoint+"/retract",{"expected_version":1})
        if code != 200 or row.get("version") != 2 or row.get("state") != "retracted":
            raise ValueError("existing_probe_retraction_not_acknowledged")
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            sc,status = api(token,"GET","/v1/memories/status")
            rc,recall = api(token,"POST","/v1/memories/recall",{"query":"Cedar Birch","limit":5})
            gc,graph = api(token,"POST","/v1/memories/connections",{"entity":"Cedar","depth":1})
            kind,cached = cache_get(cache_user,cache_password,cache_key)
            if sc == rc == gc == 200 and status.get("pending_change_events") == 0 and not recall.get("results") and not graph.get("paths") and kind == "bulk" and cached is None:
                break
            time.sleep(1)
        else:
            raise ValueError("existing_probe_withdrawal_not_ready")
        code,history = api(token,"GET",endpoint+"/history?limit=10")
        if code != 200 or {r.get("version") for r in history.get("versions",[])} != {1,2}:
            raise ValueError("existing_probe_history_not_verified")
        result.update(complete=True,installed_worker_projection_qualified=True,actual_withdrawal_verified=True,
                      new_record_retracted_history_preserved=True,checkpoint="complete",evidence=str(attempt))
        support["private_write"](attempt / "finish-existing.summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    if sys.argv[1:] == ["--inspect"]:
        return inspect_existing()
    if sys.argv[1:] == ["--finish-existing"]:
        return inspect_existing(finish=True)
    post_rotation = sys.argv[1:] == ["--post-rotation"]
    post_retirement = sys.argv[1:] == ["--post-retirement"]
    if len(sys.argv) != 1 and not (post_rotation or post_retirement):
        raise ValueError("fixed_operator_mode_required")
    os.umask(0o077)
    support = definitions("recover_launch_graph_operator.py")
    read,write = support["read_file"],support["private_write"]
    if post_rotation or post_retirement:
        stage = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
        for name in ("postgres-service-rotation","derived-service-rotation-valid-probe","postgres-operator-backup-rotation"):
            if json.loads(read(stage / name / "summary.json",0)).get("complete") is not True:
                raise ValueError("completed_credential_rotations_required")
        if post_retirement:
            for name in ("application-signing-rotation","postgres-legacy-login-retirement","derived-legacy-login-retirement"):
                if json.loads(read(stage / name / "summary.json",0)).get("complete") is not True:
                    raise ValueError("completed_login_retirements_required")
    switched = json.loads(read(BASE / "operator-evidence/controlled-runtime-switch/summary.json",0))
    if switched.get("complete") is not True or switched.get("worker_candidate_bound") is not True:
        raise ValueError("installed_worker_required")
    worker = json.loads(read(Path("/etc/enhanced-cognee/worker.json"),0))
    settings = public_index_settings()
    uri = urlsplit(worker["INDEX_VALKEY_URL"])
    if uri.hostname not in {"localhost","127.0.0.1"} or uri.port != 28537 or uri.path not in {"","/0"}:
        raise ValueError("fixed_cache_binding_required")
    cache_user,cache_password = unquote(uri.username or "default"),unquote(uri.password or "")
    attempt_name = ("installed-worker-projection-after-retirement" if post_retirement else
        "installed-worker-projection-after-rotation" if post_rotation else "installed-worker-projection")
    attempt = BASE / "operator-evidence" / attempt_name
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
        "post_rotation_qualification":post_rotation,
        "post_retirement_qualification":post_retirement,
        "source_revision":BASE.name,"operator_helper_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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
            kind,cached = cache_get(cache_user,cache_password,cache_key)
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
            kind,cached = cache_get(cache_user,cache_password,cache_key)
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
    except Exception as error:
        allowed = {"bounded_cache_response_required","cache_bulk_response_required","fixed_cache_key_required",
            "fixed_observed_probe_required","reviewed_source_required","protected_ancestor_required","protected_file_required",
            "fixed_active_probe_version_required","existing_probe_retraction_not_acknowledged","existing_probe_withdrawal_not_ready",
            "existing_probe_history_not_verified"}
        reason = str(error) if type(error) is ValueError and str(error) in allowed else "protected_input_or_protocol_error"
        result = {"complete":False,"category":"installed_worker_probe_check_failed_preserve_evidence",
                  "phase":INSPECTION_PHASE,"reason":reason}
        if os.geteuid() == 0 and INSPECTION_PHASE == "probe_retraction":
            try:
                definitions("recover_launch_graph_operator.py")["private_write"](
                    BASE / "operator-evidence/installed-worker-projection" / ("finish-existing.failure-"+secrets.token_hex(6)+".json"),
                    json.dumps(result).encode())
            except Exception:
                pass
        print(json.dumps(result))
        raise SystemExit(1)
