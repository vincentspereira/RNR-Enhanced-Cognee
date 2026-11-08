"""Diagnose the retained gateway guard failure; no minting or expiry replay.

An owner child reads only the fixed prior synthetic fixture, copies its current
ordinary credential into a NEW disposable profile, and observes the same guard
through native construction/API/cache-change paths. Never output destinations,
tokens, raw logs or private stack paths. Original fixture stays read-only.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import socket
import subprocess
import sys
import time
import traceback
import uuid

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
ARTIFACT = BASE / "operator-gateway-renewal-probe"
EVIDENCE = BASE / "operator-evidence/gateway-renewal-v1"
ORIGINAL = ARTIFACT / "qualify_launch_gateway_renewal.py"
ORIGINAL_SHA256 = "40026aceba617ea663764ea0fee2b373b477c624d3aa69873dee15ccc110815d"
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
PHASE = "identity"
PHASES = {"identity","source_fixture_read","native_construction","memory_api_status","cache_change_control","invalid_memory_control","settle"}


def require(value,reason):
    if not value:raise ValueError(reason)


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest,"reviewed_source_required")
    namespace = {"__name__":"verified_gateway_network_diagnostic","__file__":str(path)}
    exec(compile(raw,"<verified-gateway-network-diagnostic>","exec"),namespace)
    return namespace


def guarded_network(release):
    counts,events = {"memory":0,"forbidden":0},[]
    original_connect,original_resolve = socket.socket.connect,socket.getaddrinfo
    def allowed(host,port):return host == "127.0.0.1" and port == 28080
    def blocked(operation,host,port,kind):
        counts["forbidden"] += 1
        frames = []
        for frame in traceback.extract_stack(limit=10):
            path = Path(frame.filename)
            if path.is_relative_to(release / "repo"):name = str(path.relative_to(release / "repo"))
            elif path.name in {"socket.py","request.py","client.py","connection.py","connectionpool.py","_client.py"}:name = path.name
            else:name = "other"
            frames.append(dict(file=name,line=frame.lineno))
        if len(events) < 8:
            events.append(dict(operation=operation,destination_kind=kind,host_is_memory=host == "127.0.0.1",
                port_is_memory=port == 28080,host_is_bytes=isinstance(host,bytes),port_is_text=isinstance(port,str),
                phase=PHASE,source_frames=frames))
        raise RuntimeError("non_memory_network_forbidden")
    def connect(sock,address):
        if not isinstance(address,tuple) or len(address) < 2:return blocked("connect",None,None,"non_tuple")
        if not allowed(address[0],address[1]):return blocked("connect",address[0],address[1],"tuple")
        counts["memory"] += 1
        return original_connect(sock,address)
    def resolve(host,port,*args,**kwargs):
        if not allowed(host,port):return blocked("resolve",host,port,"host_port")
        return original_resolve(host,port,*args,**kwargs)
    socket.socket.connect,socket.getaddrinfo = connect,resolve
    return counts,events


def child(data):
    global PHASE
    uid = os.geteuid()
    fields = dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
    require(uid == pwd.getpwnam("hermes-runtime").pw_uid and uid != 0 and not os.getgroups()
        and fields["NoNewPrivs"].strip() == "1" and all(fields[k].strip() == "0000000000000000" for k in ("CapEff","CapAmb")),"restricted_owner_required")
    old = definitions(ORIGINAL,ORIGINAL_SHA256)
    old["identity"](data["source_id"])
    old["identity"](data["diagnostic_id"])
    source = old["FIXTURES"] / ("gateway_"+data["source_id"])
    profile = old["FIXTURES"] / ("gateway_network_"+data["diagnostic_id"])
    require(Path(__file__).parent == ARTIFACT and os.environ.get("HOME") == str(profile)
        and os.environ.get("HERMES_HOME") == str(profile),"isolated_diagnostic_required")
    core,renewal,lifecycle = (old["definitions"](old["PACKAGE"] / name,digest) for name,digest in old["CORE"].items())
    core["IDENTITY"] = old["identity"](data["source_id"])
    PHASE = "source_fixture_read"
    source_fd = core["open_directory"](source,{0,uid})
    destination = core["open_directory"](profile,{0,uid})
    counts,events = guarded_network(old["RELEASE"])
    result = dict(complete=False,credentials_issued=0,original_fixture_changed=False,memory_records_written=False,model_called=False)
    try:
        snapshot = {name:core["read_private_at"](source_fd,name,uid)[0] for name in (".env","config.yaml","enhanced_cognee.json","auth.json")}
        expected = {"config.yaml":b"memory:\n  provider: enhanced_cognee\ngateway:\n  multiplex_profiles: true\n",
            "auth.json":b'{"synthetic_marker":"preserve"}',
            "enhanced_cognee.json":b'{"base_url":"http://127.0.0.1:28080","capture_policy":"selected","include_shared":true}'}
        require(all(snapshot[name] == raw for name,raw in expected.items()),"fixed_synthetic_settings_required")
        token = renewal["environment"](core,snapshot[".env"])
        lifecycle["accepted_status"](core,token)
        for name in ("config.yaml","enhanced_cognee.json","auth.json"):
            core["create_private_at"](destination,name,snapshot[name])
        environment = ("SYNTHETIC_NETWORK_DIAGNOSTIC=preserved\nENHANCED_COGNEE_ACCESS_TOKEN="+token+"\n").encode()
        core["create_private_at"](destination,".env",environment)
        (profile / "plugins").mkdir(mode=0o700)
        (profile / "plugins/enhanced_cognee").symlink_to(old["PROVIDER"])
        os.chdir(profile)
        sys.path.insert(0,str(old["RELEASE"] / "repo"))
        PHASE = "native_construction"
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig,Platform
        from gateway.session import SessionSource
        from gateway.turn_context import TurnContext
        from gateway.run_turn_runner import TurnRunner
        from run_agent import AIAgent
        runner = GatewayRunner(GatewayConfig(multiplex_profiles=True,sessions_dir=profile / "sessions"))
        context = TurnContext(source=SessionSource(platform=Platform.TELEGRAM,chat_id="diagnostic",user_id="diagnostic"),
            session_id="network_diagnostic",session_key="network_diagnostic",user_config={"memory":{"provider":"enhanced_cognee"},"gateway":{"multiplex_profiles":True}},
            enabled_toolsets=["memory"],AIAgent=AIAgent)
        turn = TurnRunner(runner,context)
        route = {"model":"gpt-6.1-sol","runtime":{"provider":"openai-codex","api_mode":"codex_responses",
            "api_key":"invented-unused-model-credential","base_url":"https://chatgpt.com/backend-api/codex","credential_pool":None}}
        def resolve():
            with runner._profile_scope_for_source(context.source):
                return turn._resolve_turn_agent(route,"telegram","",6,{"enabled":True,"effort":"low"},{})
        first,_ = resolve()
        PHASE = "memory_api_status"
        old["provider_of"](first)._client.request("GET","/v1/memories/status")
        PHASE = "cache_change_control"
        core["create_private_at"](destination,".env-before-network-control",environment)
        core["create_private_at"](destination,".env-network-control",b"ENHANCED_COGNEE_ACCESS_TOKEN=invented.invalid.control\n")
        os.replace(".env-network-control",".env",src_dir_fd=destination,dst_dir_fd=destination)
        second,reused = resolve()
        require(second is not first and not reused,"diagnostic_cache_change_missing")
        PHASE = "invalid_memory_control"
        try:old["provider_of"](second)._client.request("GET","/v1/memories/status")
        except Exception as error:require(getattr(error,"status_code",None) == 401,"invalid_control_not_denied")
        else:raise ValueError("invalid_control_accepted")
        PHASE = "settle"
        time.sleep(0.5)
        require(all(core["read_private_at"](source_fd,name,uid)[0] == raw for name,raw in snapshot.items()),"original_fixture_changed")
        result.update(complete=True,existing_credential_authenticated=True,invalid_control_denied=True,cache_change_observed=True)
    except Exception as error:
        result.update(phase=PHASE,error_kind=type(error).__name__ if type(error).__name__ in
            {"ValueError","RuntimeError","PermissionError","FileNotFoundError","MemoryTransportError","ProvisionError"} else "other")
    finally:
        os.close(source_fd)
        os.close(destination)
    result.update(network_counts=counts,blocked_events=events[:8])
    return result


def validate_diagnostic(value,release):
    base = {"complete","credentials_issued","original_fixture_changed","memory_records_written","model_called","network_counts","blocked_events"}
    success = {"existing_credential_authenticated","invalid_control_denied","cache_change_observed"}
    failure = {"phase","error_kind"}
    require(isinstance(value,dict) and type(value.get("complete")) is bool
        and set(value) == base | (success if value["complete"] else failure),"diagnostic_receipt_fields_required")
    require(type(value["credentials_issued"]) is int and value["credentials_issued"] == 0
        and all(value[k] is False for k in ("original_fixture_changed","memory_records_written","model_called")),"diagnostic_nonmutation_required")
    if value["complete"]:require(all(value[k] is True for k in success),"diagnostic_controls_required")
    else:require(value["phase"] in PHASES and value["error_kind"] in
        {"ValueError","RuntimeError","PermissionError","FileNotFoundError","MemoryTransportError","ProvisionError","other"},"fixed_diagnostic_failure_required")
    counts = value["network_counts"]
    require(isinstance(counts,dict) and set(counts) == {"memory","forbidden"}
        and all(type(n) is int and 0 <= n <= 1000 for n in counts.values()),"bounded_network_counts_required")
    events = value["blocked_events"]
    require(isinstance(events,list) and len(events) <= 8,"bounded_network_events_required")
    for event in events:
        require(isinstance(event,dict) and set(event) == {"operation","destination_kind","host_is_memory","port_is_memory",
            "host_is_bytes","port_is_text","phase","source_frames"},"fixed_network_event_required")
        require(event["operation"] in {"connect","resolve"} and event["destination_kind"] in {"non_tuple","tuple","host_port"}
            and event["phase"] in PHASES and all(type(event[k]) is bool for k in
                ("host_is_memory","port_is_memory","host_is_bytes","port_is_text")),"typed_network_event_required")
        require(isinstance(event["source_frames"],list) and len(event["source_frames"]) <= 10,"bounded_frames_required")
        for frame in event["source_frames"]:
            require(isinstance(frame,dict) and set(frame) == {"file","line"} and type(frame["line"]) is int
                and 0 < frame["line"] <= 1000000,"public_frame_metadata_required")
            name = frame["file"]
            safe = name in {"other","socket.py","request.py","client.py","connection.py","connectionpool.py","_client.py"}
            if not safe and isinstance(name,str) and len(name) <= 160 and re.fullmatch(r"[A-Za-z0-9_./-]+\.py",name):
                path = Path(name)
                safe = not path.is_absolute() and ".." not in path.parts and (release / "repo" / path).is_file()
            require(safe,"private_frame_path_refused")
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    shared = definitions(Path(__file__).with_name("recover_launch_graph_operator.py"),SHARED_SHA256)
    read,write = shared["read_file"],shared["private_write"]
    previous = json.loads(read(EVIDENCE / "summary.json",0))
    require(previous.get("complete") is False and previous.get("child_reason") == "network_boundary_failed"
        and previous.get("operator_helper_sha256") == ORIGINAL_SHA256,"specific_failed_probe_required")
    old = definitions(ORIGINAL,ORIGINAL_SHA256)
    driver = old["definitions"](old["PACKAGE"] / "renew_fleet_credentials.py","a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf")
    driver["protected"](ORIGINAL)
    for path,digest in [(old["RELEASE"] / "repo" / name,digest) for name,digest in old["NATIVE"].items()] + [(old["PROVIDER"] / name,digest) for name,digest in old["PROVIDER_FILES"].items()]:
        driver["protected"](path)
        require(path.stat().st_size <= 4194304 and hashlib.sha256(path.read_bytes()).hexdigest() == digest,"pinned_runtime_source_required")
    source = Path(previous["new_synthetic_profile"])
    source_id = source.name.removeprefix("gateway_")
    old["identity"](source_id)
    require(source == old["FIXTURES"] / ("gateway_"+source_id),"fixed_source_fixture_required")
    target = ARTIFACT / "diagnose_launch_gateway_network.py"
    write(target,Path(__file__).read_bytes())
    target.chmod(0o644)
    account = pwd.getpwnam("hermes-runtime")
    diagnostic_id = uuid.uuid4().hex[:16]
    profile = old["FIXTURES"] / ("gateway_network_"+diagnostic_id)
    profile.mkdir(mode=0o700)
    os.chown(profile,account.pw_uid,account.pw_gid)
    result = dict(complete=False,stage="retained_gateway_network_diagnostic",source_revision=BASE.name,credentials_issued=0,
        original_fixture_changed=False,services_changed=False,timers_changed=False,fleet_launch_approved=False,
        new_diagnostic_profile=str(profile),original_failure_preserved=True)
    process = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--",str(old["RELEASE"] / "venv/bin/python"),"-I","-B",str(target),"--child"],
        input=json.dumps(dict(source_id=source_id,diagnostic_id=diagnostic_id)).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        timeout=60,cwd="/",user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={"PATH":"/usr/bin:/bin","HOME":str(profile),"HERMES_HOME":str(profile),"LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
    require(0 < len(process.stdout) <= 16384,"bounded_diagnostic_required")
    value = validate_diagnostic(json.loads(process.stdout),old["RELEASE"])
    if process.returncode == 0 and value.get("complete") is True:result.update(complete=True,diagnostic=value)
    else:result.update(category="network_diagnostic_incomplete_preserve_evidence",diagnostic=value)
    write(EVIDENCE / "network-diagnostic-v1.summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--child"]:
        logging.disable(logging.CRITICAL)
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        try:
            raw = sys.stdin.buffer.read(4097)
            require(len(raw) <= 4096,"bounded_owner_packet_required")
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):value = child(json.loads(raw))
            print(json.dumps(value))
        except Exception as error:
            kind = type(error).__name__
            value = dict(complete=False,phase=PHASE if PHASE in PHASES else "identity",error_kind=kind if kind in
                {"ValueError","RuntimeError","PermissionError","FileNotFoundError","MemoryTransportError","ProvisionError"} else "other",
                credentials_issued=0,original_fixture_changed=False,memory_records_written=False,model_called=False,
                network_counts={"memory":0,"forbidden":0},blocked_events=[])
            print(json.dumps(value))
            raise SystemExit(1)
    else:
        try:raise SystemExit(main())
        except Exception:
            print('{"complete":false,"category":"network_diagnostic_preflight_refused_no_secret_output"}')
            raise SystemExit(1)
