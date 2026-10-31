"""Owner-side preservation and root/claim boundaries; no host mutation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/rotate_launch_application_key.py"
spec = importlib.util.spec_from_file_location("application_key_rotation",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_replacement_preserves_comments_quotes_unrelated_values_and_human_data():
    raw = b"# preserve\nOTHER='old.token.value'\nexport ENHANCED_COGNEE_ACCESS_TOKEN='old.token.value' # keep\nMODEL=unchanged\n"
    updated = helper.replacement_environment(raw,"old.token.value","new.token.value")
    assert updated == raw.replace(b"ENHANCED_COGNEE_ACCESS_TOKEN='old.token.value'",b"ENHANCED_COGNEE_ACCESS_TOKEN='new.token.value'")


@pytest.mark.parametrize("raw",[b"OTHER=preserve\n",b"ENHANCED_COGNEE_ACCESS_TOKEN=old.token.value\nENHANCED_COGNEE_ACCESS_TOKEN=second.token.value\n",
    b"ENHANCED_COGNEE_ACCESS_TOKEN=old.token.value # old.token.value\n"])
def test_missing_duplicate_or_ambiguous_assignment_refused(raw):
    with pytest.raises(ValueError):
        helper.replacement_environment(raw,"old.token.value","new.token.value")


def test_stale_expected_token_and_newline_injection_refused():
    raw = b"ENHANCED_COGNEE_ACCESS_TOKEN=old.token.value\n"
    with pytest.raises(ValueError):helper.replacement_environment(raw,"different.token.value","new.token.value")
    with pytest.raises(ValueError):helper.replacement_environment(raw,"old.token.value","new.token.value\nOTHER=changed")


def test_profile_binding_cannot_leave_account_home_or_select_another_account():
    account = SimpleNamespace(pw_dir="/home/invented",pw_name="invented",pw_uid=1234)
    entry = {"home":account.pw_dir,"user":account.pw_name,"uid":1234,"profile_home":"/home/invented/.hermes/profiles/test"}
    assert helper.entry_guard(entry,account) == Path(entry["profile_home"])
    for wrong in ("/etc/private","/home/invented/.hermes/profiles/../other","/home/other/.hermes"):
        with pytest.raises(ValueError):helper.entry_guard(dict(entry,profile_home=wrong),account)


def test_private_candidate_creation_preserves_existing_file_and_refuses_symlinks(tmp_path):
    (tmp_path / "original").write_bytes(b"invented-preserve")
    (tmp_path / "redirect").symlink_to("original")
    fd = os.open(tmp_path,os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(FileExistsError):helper.owner_write(fd,"redirect",b"changed")
        helper.owner_write(fd,"candidate",b"invented-token-fixture")
        assert (tmp_path / "candidate").stat().st_mode & 0o777 == 0o600
        with pytest.raises(FileExistsError):helper.owner_write(fd,"candidate",b"overwrite")
    finally:os.close(fd)
    assert (tmp_path / "original").read_bytes() == b"invented-preserve"


def test_root_never_enters_owner_child_profile_code(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper,"open_profile",lambda *a,**kw:pytest.fail("must not enter profile"))
    with pytest.raises(ValueError,match="restricted_owner_child_required"):helper.child({})


def test_reviewed_support_sources_match_exact_pins():
    for name,digest in helper.PINS.items():
        assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest


@pytest.fixture
def owner_fixture(monkeypatch,tmp_path):
    uid = os.geteuid()
    original_read = Path.read_text
    def read_text(path,*args,**kwargs):
        if str(path) == "/proc/self/status":
            return "NoNewPrivs:\t1\nCapEff:\t0000000000000000\nCapAmb:\t0000000000000000\n"
        return original_read(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",read_text)
    monkeypatch.setattr(helper.os,"getgroups",lambda:[])
    monkeypatch.setattr(helper,"open_profile",lambda *args,**kwargs:os.open(tmp_path,os.O_RDONLY | os.O_DIRECTORY))
    raw = b"UNRELATED=preserved\nENHANCED_COGNEE_ACCESS_TOKEN=old.token.value\n"
    (tmp_path / ".env").write_bytes(raw)
    (tmp_path / "enhanced_cognee.json").write_text('{"base_url":"http://127.0.0.1:28080","capture_policy":"selected"}')
    (tmp_path / "auth.json").write_bytes(b'{"invented_oauth_marker":"preserve"}')
    entry = {"verified_binding":{"tenant":"qualification","project_id":"invented","sub":"invented"}}
    data = {"entry":entry,"nonce":"0123456789abcdef","old":"old.token.value","new":"new.token.value"}
    monkeypatch.setattr(helper,"api_status",lambda token:(200,{"ready":True,"tenant_id":"qualification","project_id":"invented","subject":"invented"}))
    return tmp_path,raw,data


def test_owner_transaction_stages_publishes_verifies_and_rolls_back_without_settings_edits(owner_fixture):
    home,raw,data = owner_fixture
    auth = (home / "auth.json").read_bytes()
    assert helper.child(dict(data,phase="prepare"))["environment_prepared"]
    assert (home / ".env").read_bytes() == raw
    assert helper.child(dict(data,phase="publish"))["credential_published"]
    assert helper.child(dict(data,phase="verify"))["settings_and_oauth_preserved"]
    assert helper.child(dict(data,phase="rollback"))["profile_restored"]
    assert (home / ".env").read_bytes() == raw
    assert (home / "auth.json").read_bytes() == auth
    assert (home / ".env-before-issuer-0123456789abcdef").exists()
    assert (home / ".env-failed-issuer-0123456789abcdef").exists()


def test_concurrent_environment_change_is_never_overwritten(owner_fixture):
    home,raw,data = owner_fixture
    helper.child(dict(data,phase="prepare"))
    changed = raw.replace(b"UNRELATED=preserved",b"UNRELATED=concurrent")
    (home / ".env").write_bytes(changed)
    with pytest.raises(ValueError,match="concurrent_environment_change_requires_review"):
        helper.child(dict(data,phase="publish"))
    assert (home / ".env").read_bytes() == changed


def test_changed_provider_origin_refuses_before_staging_any_token(owner_fixture):
    home,raw,data = owner_fixture
    (home / "enhanced_cognee.json").write_text('{"base_url":"https://example.invalid"}')
    with pytest.raises(ValueError,match="current_local_provider_binding_required"):
        helper.child(dict(data,phase="prepare"))
    assert (home / ".env").read_bytes() == raw
    assert not (home / ".env-issuer-0123456789abcdef").exists()


def test_partial_publication_restores_backend_and_profiles_without_transporting_signing_keys(monkeypatch,tmp_path,capsys):
    issuer = helper.definitions("provision_pilot_access.py")
    inventory = helper.definitions("inventory_launch_token_bindings.py")
    old_key = b"invented-old-signing-key-for-source-test-only"
    candidate = "invented_new_signing_key_for_source_test_only_12345"
    rows = []
    tokens = {}
    for index in range(3):
        binding = dict(tenant="qualification",project_id=f"invented_{index}",sub=f"invented_{index}",
                       agent_id=f"invented_{index}",roles=["api_client"],capture_policy="selected")
        rows.append(dict(profile_home=f"/invented/profile_{index}",token_signature_valid=True,
                         local_memory_configured=True,verified_binding=binding))
        tokens[rows[-1]["profile_home"]] = issuer["sign_claims"](dict(binding,iat=1000,exp=4600),old_key)
    configs = {name:json.dumps(dict(ENHANCED_JWT_SECRET=old_key.decode(),OTHER="preserve")).encode()
               for name in ("api","operator")}
    def read(path,owner):
        if path.name == "summary.json":
            return json.dumps(dict(complete=True,existing_qualification_bindings=3,credentials_issued=0)).encode()
        if path.name == "bindings.private.json":return json.dumps(dict(rows=rows)).encode()
        if path.name == "replacement-logins.private.json":
            return json.dumps(dict(application=dict(issuer=dict(jwt_signing_key=candidate)))).encode()
        return configs[path.stem]
    controls,phases = [],[]
    def replace(path,raw,owner):configs[path.stem] = raw
    def write(path,raw):path.write_bytes(raw)
    shared = dict(read_file=read,private_write=write,replace_file=replace,control=controls.append)
    issuer["load_signing_key"] = lambda:json.loads(configs["api"])["ENHANCED_JWT_SECRET"].encode()
    namespaces = iter((shared,issuer,inventory))
    monkeypatch.setattr(helper,"definitions",lambda name:next(namespaces))
    monkeypatch.setattr(helper,"STAGE",tmp_path)
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper.sys,"argv",[str(SOURCE)])
    monkeypatch.setattr(helper.signal,"signal",lambda *args:None)
    def status(token):
        key = json.loads(configs["api"])["ENHANCED_JWT_SECRET"].encode()
        return (200 if inventory["verified_claims"](token,key) else 401),{}
    monkeypatch.setattr(helper,"api_status",status)
    def child(entry,phase,nonce,old=None,new=None):
        payload = json.dumps(dict(entry=entry,phase=phase,nonce=nonce,old=old,new=new))
        assert candidate not in payload and old_key.decode() not in payload
        phases.append((entry["profile_home"],phase))
        if phase == "inspect":return dict(ordinary_token_for_parent=tokens[entry["profile_home"]])
        if phase == "publish" and entry["profile_home"] == rows[1]["profile_home"]:
            current = json.loads(configs["api"])
            current["OTHER"] = "concurrent-preserve"
            configs["api"] = json.dumps(current).encode()
            raise helper.OwnerPhaseRefused("concurrent_environment_change_requires_review")
        return dict(complete=True)
    monkeypatch.setattr(helper,"run_child",child)
    assert helper.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["backend_rollback_verified"] and result["profile_rollback_verified"]
    assert result["application_signing_key_changed"] is False
    assert controls == ["stop","stop","start"]
    assert sum(phase == "rollback" for _,phase in phases) == 3
    assert all(json.loads(raw)["ENHANCED_JWT_SECRET"] == old_key.decode() for raw in configs.values())
    assert json.loads(configs["api"])["OTHER"] == "concurrent-preserve"
