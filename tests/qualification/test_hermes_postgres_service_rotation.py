"""Credential/grant boundaries; actual DB authentication is operator work."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/rotate_launch_postgres_services.py"
spec = importlib.util.spec_from_file_location("postgres_service_rotation",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_new_url_preserves_database_and_tls_options_without_old_credentials():
    result = helper.new_url("postgresql://invented_old:invented_old_secret@127.0.0.1:28434/memory?sslmode=disable",
                            "ec_api_0123456789ab","invented-new-secret")
    assert result == "postgresql://ec_api_0123456789ab:invented-new-secret@127.0.0.1:28434/memory?sslmode=disable"


@pytest.mark.parametrize("url",["postgresql://remote.invalid:28434/db","postgresql://127.0.0.1:5432/db","file:///private"])
def test_other_database_routes_refused(url):
    with pytest.raises(ValueError,match="fixed_local_postgres_binding_required"):
        helper.new_url(url,"invented","invented")


def test_worker_gets_projection_writes_and_only_processed_at_canonical_outbox_update():
    statements = helper.grants("ec_worker_0123456789ab","worker")
    assert any("UPDATE(processed_at) ON shared_memory.record_outbox" in x for x in statements)
    assert not any("DELETE" in x for x in statements)
    assert not any("INSERT" in x or "UPDATE" in x for x in statements if "shared_memory.records " in x)
    assert not any("record_versions" in x for x in statements)


def test_api_never_gets_canonical_or_history_delete_or_history_update():
    statements = helper.grants("ec_api_0123456789ab","api")
    assert not any("DELETE" in x for x in statements if "shared_memory.records " in x or "record_versions" in x)
    assert not any("UPDATE" in x for x in statements if "record_versions" in x or "record_audit" in x)


@pytest.mark.parametrize("role",["root",'bad"; ALTER ROLE root SUPERUSER; --'])
def test_sql_identifier_cannot_widen_or_inject_grants(role):
    with pytest.raises(ValueError,match="fixed_service_role_required"):
        helper.grants(role,"api")


def test_generated_identity_only_allows_safe_staged_password_alphabet():
    with pytest.raises(ValueError,match="generated_service_identity_required"):
        helper.identity({"username":"ec_api_0123456789ab","password":"'"+"x"*43})


def test_ordinary_user_refused_before_importing_database_client(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="protected_operator_python_required"):
        helper.main()
