"""Version 2 gateway renewal with connect and connect_ex enforcement.

The original probe and its failed receipt remain unchanged.
Persistent headless native gateway renewal; new invented scope, no chat.

Real GatewayRunner/TurnRunner/AIAgent objects, actual memory API expiry and
native multiplex profile scopes. No platform adapter starts, model/OAuth use,
existing profile edits, memory writes or fleet enrollment. Standalone and actual
fleet launch bindings remain unqualified. Root keys never enter the child.
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
import resource
import socket
import stat
import subprocess
import sys
import time
import uuid

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
PACKAGE = BASE / "operator-issuer-candidate-v2"
ARTIFACT = BASE / "operator-gateway-renewal-probe-v2"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
PROVIDER = Path("/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659")
FIXTURES = Path("/var/lib/hermes-renewal-qualification")
CORE = {"provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "renew_pilot_access.py":"8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567",
    "fleet_credential_lifecycle.py":"f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62"}
NATIVE = {"hermes_bootstrap.py":"f242036b2d35b92283b9a7e97c7059e537607fc4b02026f657a6d00cb4683f69","gateway/run.py":"a98407aeb888003a2dcb75287291ecc33c8509a24ff8ef6576c00bca4e28de9c",
    "gateway/session_execution.py":"7c1e294795003b329cc9639fe27e9b8b8fdfbd9b1e3106fcfbd6c8e06f670a60",
    "gateway/run_turn_runner.py":"6cf9f1acdd64d69f5c613be214695b33dafe215eeced68cebe53f5d0c5e4cbc9",
    "agent/secret_scope.py":"dce64ce99a6966836108e202e1db41c4be97bd3dad41a79e357f39b8d7e90dec",
    "run_agent.py":"33c7195fc6efa9122f1a6700d416fd283f9634712189af3fd72feb01bcea054f",
    "gateway/run_turn.py":"323b21f4878623bac8764c14f9abc530e16b452a747769c6a0171889a8428167",
    "gateway/run_agent_cache.py":"c9a58d54a2efd7ff8fb674ecc041472f0401b33831e3eb8a41c92f0b6aad4aa5",
    "agent/agent_init.py":"1e29225039534583ef0f3e7ae0d7a02b091e03792f8170c880ba83fff9c977cd"}
PROVIDER_FILES = {"__init__.py":"fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061",
    "client.py":"8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "plugin.yaml":"c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48"}
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
PHASE = "identity"
SAFE_REASONS = {"non_memory_network_forbidden","real_memory_provider_required","pinned_provider_required",
    "old_provider_binding_failed","unchanged_cache_not_reused","initialization_expiry_margin_insufficient",
    "old_expiry_denial_not_verified","old_credential_still_accepted","renewed_agent_not_rebuilt",
    "new_provider_binding_failed","renewed_scope_not_verified","synthetic_settings_changed","network_boundary_failed","platform_adapter_started",
    "multiplex_launch_mode_required","native_scope_home_mismatch"}
GOOD_FLAGS = {"complete","gateway_runner_retained","real_gatewayrunner_and_agents_used","unchanged_agent_reused",
    "old_credential_expiry_denied","replacement_authenticated","renewed_agent_rebuilt","provider_tokens_bound",
    "profile_settings_auth_preserved","native_multiplex_scope_used"}
FALSE_FLAGS = {"chat_model_called","model_credentials_read","existing_profiles_changed","canonical_memory_edits","fleet_gateway_bindings_qualified"}


def require(value,reason):
    if not value:raise ValueError(reason)


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest,"reviewed_source_required")
    namespace = {"__name__":"verified_gateway_renewal_support","__file__":str(path)}
    exec(compile(raw,"<verified-gateway-renewal-support>","exec"),namespace)
    return namespace


def identity(ident):
    require(isinstance(ident,str) and len(ident) == 16 and all(c in "0123456789abcdef" for c in ident),"fixed_fixture_identifier_required")
    return dict(sub="gateway_"+ident,agent_id="gateway_renewal",tenant="qualification",project_id="gateway_"+ident,
                roles=["api_client"],capture_policy="selected")


def network_guard():
    counts = {"memory":0,"forbidden":0}
    original_connect,original_connect_ex,original_resolve = socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo
    def allowed(host,port):return host == "127.0.0.1" and port == 28080
    def check_address(address):
        if not isinstance(address,tuple) or len(address) < 2 or not allowed(address[0],address[1]):
            counts["forbidden"] += 1
            raise RuntimeError("non_memory_network_forbidden")
        counts["memory"] += 1
    def connect(sock,address):
        check_address(address)
        return original_connect(sock,address)
    def connect_ex(sock,address):
        # Native hermes_bootstrap uses nonblocking connect_ex after imports.
        check_address(address)
        return original_connect_ex(sock,address)
    def resolve(host,port,*args,**kwargs):
        if not allowed(host,port):
            counts["forbidden"] += 1
            raise RuntimeError("non_memory_network_forbidden")
        return original_resolve(host,port,*args,**kwargs)
    socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo = connect,connect_ex,resolve
    return counts


def provider_of(agent):
    values = [p for p in getattr(agent._memory_manager,"_providers",[]) if p.name == "enhanced_cognee"]
    require(len(values) == 1,"real_memory_provider_required")
    require(Path(sys.modules[type(values[0]).__module__].__file__).resolve() == PROVIDER / "__init__.py","pinned_provider_required")
    return values[0]


def child(data):
    global PHASE
    fields = dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
    uid = os.geteuid()
    require(uid == pwd.getpwnam("hermes-runtime").pw_uid and uid != 0 and not os.getgroups()
        and fields["NoNewPrivs"].strip() == "1" and all(fields[k].strip() == "0000000000000000" for k in ("CapEff","CapAmb")),"restricted_owner_required")
    require(Path(__file__).parent == ARTIFACT,"protected_child_source_required")
    claims = identity(data["run_id"])
    profile = FIXTURES / ("gateway_"+data["run_id"])
    require(os.environ.get("HOME") == str(profile) and os.environ.get("HERMES_HOME") == str(profile),"isolated_home_required")
    info = profile.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700,"private_fixture_required")
    os.chdir(profile)
    core,renewal,lifecycle = (definitions(PACKAGE / name,digest) for name,digest in CORE.items())
    core["IDENTITY"] = claims
    old_claims = renewal["token_claims"](core,data["old"])
    require(old_claims["exp"] == data["expires_at"],"fixed_expiry_binding_required")
    PHASE = "fixture_files"
    directory = core["open_directory"](profile,{0,uid})
    preserved = {"config.yaml":b"memory:\n  provider: enhanced_cognee\ngateway:\n  multiplex_profiles: true\n",
        "auth.json":b'{"synthetic_marker":"preserve"}',
        "enhanced_cognee.json":b'{"base_url":"http://127.0.0.1:28080","capture_policy":"selected","include_shared":true}'}
    try:
        for name,raw in preserved.items():core["create_private_at"](directory,name,raw)
        core["create_private_at"](directory,".env",("SYNTHETIC_UNRELATED=preserved\nENHANCED_COGNEE_ACCESS_TOKEN="+data["old"]+"\n").encode())
        (profile / "plugins").mkdir(mode=0o700)
        (profile / "plugins/enhanced_cognee").symlink_to(PROVIDER)
        counts = network_guard()
        PHASE = "native_imports"
        sys.path.insert(0,str(RELEASE / "repo"))
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig,Platform
        from gateway.session import SessionSource
        from gateway.turn_context import TurnContext
        from gateway.run_turn_runner import TurnRunner
        from agent.secret_scope import current_secret_scope_home
        from run_agent import AIAgent
        PHASE = "initial_gateway_agent"
        runner = GatewayRunner(GatewayConfig(multiplex_profiles=True,sessions_dir=profile / "sessions"))
        require(runner.config.multiplex_profiles is True,"multiplex_launch_mode_required")
        source = SessionSource(platform=Platform.TELEGRAM,chat_id="qualification",user_id="qualification")
        ctx = TurnContext(source=source,session_id="gateway_"+data["run_id"],session_key="gateway_"+data["run_id"],
            user_config={"memory":{"provider":"enhanced_cognee"},"gateway":{"multiplex_profiles":True}},
            enabled_toolsets=["memory"],disabled_toolsets=None,AIAgent=AIAgent)
        turn = TurnRunner(runner,ctx)
        # Constructor-only route matching the prior native qualification. The
        # placeholder is never used: non-memory DNS/connects are forbidden.
        route = {"model":"gpt-6.1-sol","runtime":{"provider":"openai-codex","api_mode":"codex_responses",
            "api_key":"invented-unused-model-credential","base_url":"https://chatgpt.com/backend-api/codex","credential_pool":None}}
        def resolve():
            with runner._profile_scope_for_source(source):
                require(current_secret_scope_home() == str(profile),"native_scope_home_mismatch")
                return turn._resolve_turn_agent(route,"telegram","",6,{"enabled":True,"effort":"low"},{})
        first,reused = resolve()
        require(not reused and isinstance(first,AIAgent),"first_native_agent_required")
        old_provider = provider_of(first)
        require(old_provider._client.token == data["old"],"old_provider_binding_failed")
        lifecycle["accepted_status"](core,data["old"])
        again,reused = resolve()
        require(reused and again is first,"unchanged_cache_not_reused")
        require(data["expires_at"]-int(time.time()) >= 15,"initialization_expiry_margin_insufficient")
        PHASE = "owner_transactional_renewal"
        lock = os.open(".cognee-renewal.lock",os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,0o600,dir_fd=directory)
        try:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = lifecycle["publish"](core,renewal,directory,data["bundle"],uid)
            require(report["credential_published"] is True,"credential_publication_required")
        finally:os.close(lock)
        PHASE = "real_wall_clock_expiry"
        deadline = time.monotonic()+120
        while int(time.time()) <= data["expires_at"]:
            require(time.monotonic() < deadline,"expiry_deadline_exceeded")
            time.sleep(1)
        try:old_provider._client.request("GET","/v1/memories/status")
        except Exception as error:require(type(error).__name__ == "MemoryTransportError" and getattr(error,"status_code",None) == 401,"old_expiry_denial_not_verified")
        else:raise ValueError("old_credential_still_accepted")
        PHASE = "renewed_gateway_resolution"
        renewed,reused = resolve()
        require(not reused and renewed is not first and isinstance(renewed,AIAgent),"renewed_agent_not_rebuilt")
        new_provider = provider_of(renewed)
        require(new_provider._client.token == data["bundle"]["token"],"new_provider_binding_failed")
        status = new_provider._client.request("GET","/v1/memories/status")
        require(status.get("ready") is True and all(status.get(field) == claims[key] for field,key in
            (("tenant_id","tenant"),("project_id","project_id"),("subject","sub"))),"renewed_scope_not_verified")
        require(all(core["read_private_at"](directory,name,uid)[0] == raw for name,raw in preserved.items()),"synthetic_settings_changed")
        require(counts["forbidden"] == 0 and 0 < counts["memory"] <= 100,"network_boundary_failed")
        require(not runner.adapters,"platform_adapter_started")
        result = {key:True for key in GOOD_FLAGS}
        result.update({key:False for key in FALSE_FLAGS})
        result.update(forbidden_network_attempts=counts["forbidden"],memory_api_connections=counts["memory"])
        return result
    finally:os.close(directory)


def validate_child(value):
    require(isinstance(value,dict) and set(value) == GOOD_FLAGS | FALSE_FLAGS | {"forbidden_network_attempts","memory_api_connections"},"fixed_child_receipt_required")
    require(all(value[key] is True for key in GOOD_FLAGS) and all(value[key] is False for key in FALSE_FLAGS)
        and type(value["forbidden_network_attempts"]) is int and value["forbidden_network_attempts"] == 0
        and type(value["memory_api_connections"]) is int and 0 < value["memory_api_connections"] <= 100,"gateway_receipt_contract_failed")
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    support = definitions(Path(__file__).with_name("recover_launch_graph_operator.py"),SHARED_SHA256)
    read,write = support["read_file"],support["private_write"]
    accepted = json.loads(read(BASE / "operator-evidence/issuer-publication-v2/finish-existing.summary.json",0))
    require(accepted.get("complete") is True and accepted.get("scheduled_publication_component_qualified") is True,"scheduled_publication_pass_required")
    driver_source = PACKAGE / "renew_fleet_credentials.py"
    driver = definitions(driver_source,"a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf")
    for path,digest in [(RELEASE / "repo" / name,digest) for name,digest in NATIVE.items()] + [(PROVIDER / name,digest) for name,digest in PROVIDER_FILES.items()]:
        driver["protected"](path)
        require(path.stat().st_size <= 4194304 and hashlib.sha256(path.read_bytes()).hexdigest() == digest,"pinned_runtime_source_required")
    for name,digest in CORE.items():
        driver["protected"](PACKAGE / name)
        definitions(PACKAGE / name,digest)
    driver["protected"](FIXTURES)
    driver["protected"](RELEASE / "venv/bin/python",final_link=True)
    driver["protected"]((RELEASE / "venv/bin/python").resolve())
    evidence = BASE / "operator-evidence/gateway-renewal-v2"
    evidence.mkdir(mode=0o700)
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    raw = Path(__file__).read_bytes()
    require(len(raw) <= 65536,"bounded_probe_source_required")
    target = ARTIFACT / Path(__file__).name
    write(target,raw)
    target.chmod(0o644)
    result = dict(complete=False,evidence=str(evidence),source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(raw).hexdigest(),native_source_hashes=NATIVE,provider_source_hashes=PROVIDER_FILES,
        existing_profiles_changed=False,keys_changed=False,services_changed=False,timer_enabled=False,
        model_called=False,memory_records_written=False,running_gateway_reload_qualified=False,
        actual_fleet_boundaries_qualified=False,fleet_launch_approved=False)
    write(evidence / "started.json",json.dumps(result).encode())
    try:
        ident = uuid.uuid4().hex[:16]
        profile = FIXTURES / ("gateway_"+ident)
        profile.mkdir(mode=0o700)
        account = pwd.getpwnam("hermes-runtime")
        os.chown(profile,account.pw_uid,account.pw_gid)
        result["new_synthetic_profile"] = str(profile)
        core = definitions(PACKAGE / "provision_pilot_access.py",CORE["provision_pilot_access.py"])
        core["IDENTITY"] = identity(ident)
        key = core["load_signing_key"]()
        now = int(time.time())
        expires = now+90
        old = core["sign_claims"](dict(core["IDENTITY"],iat=expires-86400,exp=expires),key)
        bundle = core["make_bundle"](key,now)
        del key
        result["qualification_credentials_issued"] = 2
        data = json.dumps(dict(run_id=ident,old=old,bundle=bundle,expires_at=expires)).encode()
        require(len(data) <= 16384,"bounded_owner_packet_required")
        process = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--",str(RELEASE / "venv/bin/python"),"-I","-B",str(target),"--child"],
            input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd="/",timeout=160,user=account.pw_uid,group=account.pw_gid,extra_groups=(),
            env={"PATH":"/usr/bin:/bin","HOME":str(profile),"HERMES_HOME":str(profile),"LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
        require(0 < len(process.stdout) <= 8192,"bounded_child_output_required")
        value = json.loads(process.stdout)
        if process.returncode == 0:
            result.update(complete=True,running_synthetic_gateway_reload_qualified=True,
                qualification_surface="persistent_headless_multiplex_gateway",native_result=validate_child(value),
                new_synthetic_profile=str(profile),qualification_credentials_issued=2,
                root_keys_withheld_from_children=True,chat_model_route_verified=False,standalone_gateway_qualified=False)
        else:
            result["category"] = "native_gateway_renewal_incomplete_preserve_evidence"
            if value.get("phase") in {"identity","fixture_files","native_imports","initial_gateway_agent","owner_transactional_renewal",
                    "real_wall_clock_expiry","renewed_gateway_resolution"}:result["child_phase"] = value["phase"]
            if value.get("error_kind") in {"ValueError","RuntimeError","PermissionError","FileNotFoundError","MemoryTransportError","ProvisionError"}:
                result["child_error_kind"] = value["error_kind"]
            if type(value.get("errno")) is int and 0 < value["errno"] < 4096:result["child_errno"] = value["errno"]
            if value.get("reason") in SAFE_REASONS:result["child_reason"] = value["reason"]
    except Exception:
        result["category"] = "gateway_renewal_probe_incomplete_preserve_evidence"
    write(evidence / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--child"]:
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        logging.disable(logging.CRITICAL)
        try:
            raw = sys.stdin.buffer.read(16385)
            require(len(raw) <= 16384,"bounded_owner_packet_required")
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):value = child(json.loads(raw))
            print(json.dumps(value))
        except Exception as error:
            value = dict(complete=False,phase=PHASE,error_kind=type(error).__name__ if type(error).__name__ in
                {"ValueError","RuntimeError","PermissionError","FileNotFoundError","MemoryTransportError","ProvisionError"} else "other")
            number = getattr(error,"errno",None)
            if type(number) is int and 0 < number < 4096:value["errno"] = number
            if type(error) in {ValueError,RuntimeError} and str(error) in SAFE_REASONS:value["reason"] = str(error)
            print(json.dumps(value))
            raise SystemExit(1)
    else:
        try:raise SystemExit(main())
        except Exception:
            print('{"complete":false,"category":"gateway_renewal_preflight_refused_no_secret_output"}')
            raise SystemExit(1)
