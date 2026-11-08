"""Source contracts only; dynamic-user installed startup is an operator gate."""
import base64
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/switch_launch_service_candidate.py"
spec = importlib.util.spec_from_file_location("launch_service_switch",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_configuration_changes_only_model_cache_preserving_all_credentials():
    original = {"ENHANCED_EMBEDDING_MODEL":"BAAI/bge-small-en-v1.5","ENHANCED_MODEL_CACHE":"old",
                "ENCRYPTION_MASTER_KEY":"invented-preserve","ENHANCED_JWT_SECRET":"invented-preserve-issuer",
                "ENHANCED_MEMORY_DATABASE_URL":"invented-preserve-database"}
    updated = json.loads(helper.configuration(json.dumps(original).encode()))
    assert updated == dict(original,ENHANCED_MODEL_CACHE=str(helper.BASE / "model-cache"))


def test_different_embedding_model_is_refused():
    with pytest.raises(ValueError,match="admitted_model_required"):
        helper.configuration(b'{"ENHANCED_EMBEDDING_MODEL":"different-model"}')


@pytest.mark.parametrize("role",["api","worker"])
def test_service_dropin_selects_fixed_runtime_without_changing_identity(role):
    value = helper.dropin(role).decode()
    assert "ExecStart=\nExecStart=" in value
    assert str(helper.BASE / "runtime/bin/python") in value
    assert "User=" not in value and "LoadCredential=" not in value
    assert "WorkingDirectory="+str(helper.BASE) in value


def test_caller_cannot_select_an_operator_role():
    with pytest.raises(ValueError,match="fixed_role_required"):
        helper.dropin("operator")


def test_new_scope_status_token_signature_and_real_expired_control():
    scope = {"tenant":"qualification","project_id":"invented","sub":"invented"}
    good,expired = [helper.token("invented-only-key",scope,flag) for flag in (False,True)]
    def decode(part):
        return base64.urlsafe_b64decode(part+"="*((4-len(part)%4)%4))
    for value in (good,expired):
        head,body,signature = value.split(".")
        expected = hmac.new(b"invented-only-key",(head+"."+body).encode(),hashlib.sha256).digest()
        assert hmac.compare_digest(decode(signature),expected)
    assert json.loads(decode(good.split('.')[1]))['exp'] > json.loads(decode(expired.split('.')[1]))['exp']


def test_ordinary_user_cannot_change_services(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    monkeypatch.setattr(helper,"systemctl",lambda *a:pytest.fail("must not control services"))
    with pytest.raises(ValueError,match="local_root_operator_required"):
        helper.main()


def test_shared_file_primitives_are_hash_pinned():
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


def test_installed_inventory_includes_client_mcp_and_license_besides_src():
    names = ["src/memory_service.py", "enhanced_cognee_client/client.py", "bin/project_memory_mcp.py",
             "rnr_enhanced_cognee_memory-LICENSE", "rnr_enhanced_cognee_memory-1.2.0.dist-info/RECORD", "src/"]
    assert helper.runtime_members(names) == names[:4]


def test_refusal_reason_does_not_expose_arbitrary_exception_messages():
    assert helper.refusal_reason(ValueError("installed_package_inventory_required")) == "installed_package_inventory_required"
    assert helper.refusal_reason(ValueError("invented-private-value")) == "protected_input_or_service_error"
    assert helper.refusal_reason(PermissionError("invented-private-path")) == "protected_input_or_service_error"


def test_shared_sticky_parent_and_private_receipt_directory_have_distinct_guards():
    helper.directory_guard(SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR | 0o1777),sticky=True)
    helper.directory_guard(SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR | 0o700),private=True)
    with pytest.raises(ValueError):
        helper.directory_guard(SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR | 0o1777))
    with pytest.raises(ValueError):
        helper.directory_guard(SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR | 0o755),private=True)


@pytest.mark.parametrize("uid,mode",[(1000,stat.S_IFDIR | 0o1777),(0,stat.S_IFDIR | 0o777),
    (0,stat.S_IFLNK | 0o1777)])
def test_sticky_exception_does_not_admit_user_owned_nonsticky_or_link_directory(uid,mode):
    with pytest.raises(ValueError):
        helper.directory_guard(SimpleNamespace(st_uid=uid,st_mode=mode),sticky=True)


def test_recovery_reader_cannot_read_arbitrary_shared_parent_files():
    with pytest.raises(ValueError,match="fixed_recovery_receipt_required"):
        helper.recovery_receipt(Path("/var/tmp/caller-selected/summary.json"))
