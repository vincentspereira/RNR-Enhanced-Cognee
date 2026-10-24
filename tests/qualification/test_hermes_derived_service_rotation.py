"""Service credential selection/grant preservation; no live store calls."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/rotate_launch_derived_services.py"
spec = importlib.util.spec_from_file_location("derived_service_rotation",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def candidate(kind):
    return {"username":"ec_"+kind+"_0123456789ab","password":"invented-"+"x"*43}


def test_graph_clones_only_existing_service_grants_and_preserves_original_bytes():
    rows = [{"name":"root","password":"preserve-root","databases":{"*":["admin"]}},
            {"name":"old-api","password":"old-api-hash","databases":{"live":["reader"]}},
            {"name":"old-worker","password":"old-worker-hash","databases":{"live":["writer"]}}]
    raw = b"\n".join(json.dumps(row).encode() for row in rows)+b"\n"
    configs = {kind:{"INDEX_ARCADEDB_USER":"old-"+kind} for kind in ("api","worker")}
    result = helper.append_graph_users(raw,configs,{kind:candidate(kind) for kind in configs},lambda password:"invented-new-hash")
    assert result.startswith(raw)
    added = [json.loads(line) for line in result[len(raw):].splitlines()]
    assert [row["databases"] for row in added] == [{"live":["reader"]},{"live":["writer"]}]
    assert all("*" not in row["databases"] for row in added)


def test_graph_service_cannot_clone_root_or_global_admin_grants():
    raw = b'{"name":"root","password":"hash","databases":{"*":["admin"]}}\n'
    configs = {"api":{"INDEX_ARCADEDB_USER":"root"},"worker":{"INDEX_ARCADEDB_USER":"root"}}
    with pytest.raises(ValueError,match="restricted_existing_graph_service_grants_required"):
        helper.append_graph_users(raw,configs,{kind:candidate(kind) for kind in configs},lambda password:"hash")


def test_cache_worker_clone_preserves_prefix_commands_and_original_lines():
    password = "invented-old-secret"
    digest = hashlib.sha256(password.encode()).hexdigest()
    raw = ("user old-worker on #"+digest+" ~ec:live:* -@all +ping +get +set +del\n").encode()
    result = helper.append_cache_worker(raw,"old-worker",password,candidate("worker"))
    assert result.startswith(raw)
    new = result[len(raw):].decode()
    assert "~ec:live:* -@all +ping +get +set +del" in new
    assert candidate("worker")["password"] not in new
    assert "+@all" not in new


def test_wrong_existing_cache_password_stops_before_clone():
    raw = ("user old-worker on #"+"a"*64+" ~ec:live:* +set\n").encode()
    with pytest.raises(ValueError,match="existing_worker_password_hash_not_verified"):
        helper.append_cache_worker(raw,"old-worker","invented-different",candidate("worker"))


def test_vector_selection_changes_only_two_keys_without_mutating_original():
    original = {"service":{"host":"127.0.0.1","http_port":28535,"api_key":"old","read_only_api_key":"old-read"},
                "storage":{"storage_path":"/invented/data"}}
    keys = {kind:{"api_key":"invented-"+"x"*43} for kind in ("readonly","admin_write")}
    changed = helper.qdrant_configuration(original,keys)
    assert original["service"]["api_key"] == "old"
    assert changed["service"]["host"] == "127.0.0.1"
    assert changed["storage"] == original["storage"]
    assert changed["service"]["api_key"] == keys["admin_write"]["api_key"]
    assert changed["service"]["read_only_api_key"] == keys["readonly"]["api_key"]


def test_source_hashes_match_reviewed_file_primitives_and_cache_auth():
    for name,digest in helper.SOURCES.items():
        assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest


def test_ordinary_user_cannot_import_store_configuration_or_control_services(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="protected_operator_python_required"):
        helper.main()


def test_readonly_probe_uses_valid_uuid_and_proven_absent_disposable_point(monkeypatch):
    calls = []
    def status(port,path,headers,method="GET",body=None):
        calls.append((path,method,body))
        if len(calls) == 1:return 200
        if len(calls) == 2:return 404
        assert method == "POST" and path.endswith("/points/delete?wait=true")
        assert len(body["points"]) == 1
        assert body["points"][0] == calls[1][0].rsplit("/",1)[1]
        return 403
    monkeypatch.setattr(helper,"http_status",status)
    passed,result = helper.readonly_write_probe("invented-admin","invented-readonly")
    assert passed and result["readonly_delete_http"] == 403
    assert all("/ec_lr_cc098bbed2b9424a" in row[0] for row in calls)


@pytest.mark.parametrize("existence,absence",[(404,404),(200,200)])
def test_denial_probe_never_deletes_if_collection_or_absence_unverified(monkeypatch,existence,absence):
    calls = []
    def status(port,path,headers,method="GET",body=None):
        assert method == "GET"
        calls.append(path)
        return existence if len(calls) == 1 else absence
    monkeypatch.setattr(helper,"http_status",status)
    assert helper.readonly_write_probe("invented-admin","invented-readonly")[0] is False


@pytest.mark.parametrize("code",[200,400,404,500])
def test_non_authorization_failure_is_not_misreported_as_readonly_denial(monkeypatch,code):
    responses = iter([200,404,code])
    monkeypatch.setattr(helper,"http_status",lambda *args,**kwargs:next(responses))
    assert helper.readonly_write_probe("invented-admin","invented-readonly")[0] is False
