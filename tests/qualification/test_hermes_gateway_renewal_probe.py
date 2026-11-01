"""Transport, source and fixed-scope boundaries; no host credential use."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_gateway_renewal.py"
spec = importlib.util.spec_from_file_location("gateway_renewal_probe",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def good():
    return dict({key:True for key in helper.GOOD_FLAGS},**{key:False for key in helper.FALSE_FLAGS},
        forbidden_network_attempts=0,memory_api_connections=8)


def test_reviewed_public_source_pins_match_exact_current_modules():
    for name,digest in helper.CORE.items():assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest
    for name,digest in helper.NATIVE.items():assert hashlib.sha256((helper.RELEASE / "repo" / name).read_bytes()).hexdigest() == digest
    for name,digest in helper.PROVIDER_FILES.items():assert hashlib.sha256((SOURCE.parents[1] / "enhanced_cognee" / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("ident",["../private","a"*15,"g"*16,123,None])
def test_no_caller_selected_scopes_paths_or_roles(ident):
    with pytest.raises(ValueError):helper.identity(ident)


def test_synthetic_identity_is_fixed_ordinary_and_qualification_only():
    value = helper.identity("a"*16)
    assert value["tenant"] == "qualification" and value["roles"] == ["api_client"]
    assert value["capture_policy"] == "selected" and value["project_id"] == "gateway_"+"a"*16


@pytest.mark.parametrize("key,value",[("complete","true"),("renewed_agent_rebuilt",False),
    ("chat_model_called",True),("forbidden_network_attempts",False),("forbidden_network_attempts",1),
    ("memory_api_connections",0),("memory_api_connections",101),("unexpected_private_field","invented")])
def test_receipt_refuses_false_widened_or_unbounded_claims(key,value):
    report = good()
    report[key] = value
    with pytest.raises(ValueError):helper.validate_child(report)


def test_good_receipt_keeps_actual_fleet_and_model_acceptance_false():
    assert helper.validate_child(good())["fleet_gateway_bindings_qualified"] is False
    assert helper.validate_child(good())["model_credentials_read"] is False


def test_network_guard_blocks_model_hosts_other_ports_and_unix_sockets_before_resolution(monkeypatch):
    calls = []
    monkeypatch.setattr(helper.socket.socket,"connect",lambda sock,address:calls.append(("connect",address)))
    monkeypatch.setattr(helper.socket,"getaddrinfo",lambda host,port,*a,**kw:calls.append(("resolve",host,port)))
    counts = helper.network_guard()
    helper.socket.getaddrinfo("127.0.0.1",28080)
    helper.socket.socket.connect(None,("127.0.0.1",28080))
    for address in (("model.invalid",443),("127.0.0.1",28081),"/invented/socket"):
        with pytest.raises(RuntimeError):helper.socket.socket.connect(None,address)
    with pytest.raises(RuntimeError):helper.socket.getaddrinfo("model.invalid",443)
    assert counts == {"memory":1,"forbidden":4}
    assert calls == [("resolve","127.0.0.1",28080),("connect",("127.0.0.1",28080))]


def test_root_child_and_unprivileged_parent_refused_before_fixture_access(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:SimpleNamespace(pw_uid=993))
    with pytest.raises(ValueError,match="restricted_owner_required"):helper.child({})
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()


def test_parent_never_transports_signing_key_or_inherited_environment(monkeypatch,tmp_path,capsys):
    base = tmp_path / "base"
    (base / "operator-evidence").mkdir(parents=True)
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setattr(helper,"BASE",base)
    monkeypatch.setattr(helper,"ARTIFACT",base / "public-probe")
    monkeypatch.setattr(helper,"FIXTURES",fixtures)
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper.os,"chown",lambda *args:None)
    monkeypatch.setattr(helper.os,"umask",lambda *args:None)
    monkeypatch.setattr(helper.resource,"setrlimit",lambda *args:None)
    monkeypatch.setattr(helper.sys,"argv",[str(SOURCE)])
    account = SimpleNamespace(pw_uid=993,pw_gid=993)
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:account)
    root_key = b"invented-root-signing-key-not-owner-input"
    core = dict(load_signing_key=lambda:root_key,sign_claims=lambda claims,key:"invented.old.token",
        make_bundle=lambda key,now:{"token":"invented.new.token"})
    shared = dict(read_file=lambda *args:json.dumps(dict(complete=True,scheduled_publication_component_qualified=True)).encode(),
        private_write=lambda path,raw:path.write_bytes(raw))
    def definitions(path,digest):
        if path.name == "recover_launch_graph_operator.py":return shared
        if path.name == "renew_fleet_credentials.py":return {"protected":lambda *a,**kw:None}
        return core
    monkeypatch.setattr(helper,"definitions",definitions)
    def run(args,**kwargs):
        assert args[:3] == ["/usr/bin/setpriv","--no-new-privs","--"] and args[-1] == "--child"
        assert kwargs["user"] == 993 and kwargs["group"] == 993 and kwargs["extra_groups"] == ()
        assert kwargs["cwd"] == "/" and kwargs["stderr"] is helper.subprocess.DEVNULL
        assert root_key.decode() not in json.dumps(args)+json.dumps(kwargs["env"])+kwargs["input"].decode()
        assert set(json.loads(kwargs["input"])) == {"run_id","old","bundle","expires_at"}
        return SimpleNamespace(returncode=0,stdout=json.dumps(good()).encode())
    monkeypatch.setattr(helper.subprocess,"run",run)
    assert helper.main() == 0
    output = capsys.readouterr().out
    assert root_key.decode() not in output
    result = json.loads(output)
    assert result["running_synthetic_gateway_reload_qualified"]
    assert result["running_gateway_reload_qualified"] is False and result["fleet_launch_approved"] is False
