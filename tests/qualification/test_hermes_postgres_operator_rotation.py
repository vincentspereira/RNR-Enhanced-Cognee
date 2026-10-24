"""Protected admin/backup binding preservation; no live password operations."""
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit,unquote

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/rotate_launch_postgres_operator.py"
spec = importlib.util.spec_from_file_location("postgres_operator_rotation",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_shared_operator_backup_role_rotates_one_password_and_preserves_data_keys():
    url = "postgresql://invented_operator:old@127.0.0.1:28434/memory?sslmode=disable"
    operator = {helper.FIELD:url,"ENCRYPTION_MASTER_KEY":"invented-preserve","ENHANCED_JWT_SECRET":"invented-issuer"}
    backup = {helper.FIELD:url,"ENHANCED_BACKUP_SIGNING_KEY":"invented-preserve-backup"}
    old,new,configs = helper.prepare(operator,backup,"invented-"+"x"*43)
    assert len(old) == len(new) == 1
    assert configs["operator"]["ENCRYPTION_MASTER_KEY"] == operator["ENCRYPTION_MASTER_KEY"]
    assert configs["backup"]["ENHANCED_BACKUP_SIGNING_KEY"] == backup["ENHANCED_BACKUP_SIGNING_KEY"]
    assert configs["operator"]["ENHANCED_JWT_SECRET"] == operator["ENHANCED_JWT_SECRET"]
    assert configs["operator"][helper.FIELD] == configs["backup"][helper.FIELD]
    assert urlsplit(configs["operator"][helper.FIELD]).username == "invented_operator"


def test_separate_backup_role_gets_separate_generated_secret_without_renaming():
    operator = {helper.FIELD:"postgresql://invented_operator:old@127.0.0.1:28434/memory"}
    backup = {helper.FIELD:"postgresql://invented_backup:old_backup@127.0.0.1:28434/memory"}
    _,new,configs = helper.prepare(operator,backup,"invented-"+"x"*43)
    assert len(new) == 2 and len(set(new.values())) == 2
    assert unquote(urlsplit(configs["backup"][helper.FIELD]).password) == new["invented_backup"]
    assert urlsplit(configs["backup"][helper.FIELD]).username == "invented_backup"


def test_same_role_with_conflicting_passwords_is_not_silently_reconciled():
    operator = {helper.FIELD:"postgresql://invented:one@127.0.0.1:28434/memory"}
    backup = {helper.FIELD:"postgresql://invented:two@127.0.0.1:28434/memory"}
    with pytest.raises(ValueError,match="operator_backup_password_binding_differs"):
        helper.prepare(operator,backup,"invented-"+"x"*43)


@pytest.mark.parametrize("url",["postgresql://invented:old@remote.invalid:28434/memory",
    "postgresql://invented:old@127.0.0.1:5432/memory","postgresql://127.0.0.1:28434/memory"])
def test_external_unbound_or_wrong_port_admin_credentials_refused(url):
    with pytest.raises(ValueError,match="fixed_protected_postgres_binding_required"):
        helper.binding(url)


def test_ordinary_user_refused_before_database_client_import(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="protected_operator_python_required"):
        helper.main()
