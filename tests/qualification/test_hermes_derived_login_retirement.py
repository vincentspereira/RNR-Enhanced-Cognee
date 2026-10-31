"""Retirement transformations and rollback; no installed store claims."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/retire_launch_derived_logins.py"
spec = importlib.util.spec_from_file_location("derived_login_retirement",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def graph_fixture():
    old = {kind:dict(INDEX_ARCADEDB_USER="old_"+kind,INDEX_ARCADEDB_PASSWORD="invented_"+kind) for kind in ("api","worker")}
    current = {kind:dict(INDEX_ARCADEDB_USER="new_"+kind) for kind in old}
    rows = [dict(name="root",password="preserve-root",databases={"*":"admin"})]
    rows += [dict(name=row["INDEX_ARCADEDB_USER"],password="hash-"+row["INDEX_ARCADEDB_PASSWORD"],databases={"invented":"reader"}) for row in old.values()]
    rows += [dict(name=row["INDEX_ARCADEDB_USER"],password="preserve-new",databases={"invented":"reader"}) for row in current.values()]
    raw = b"".join(json.dumps(row).encode()+b"\n" for row in rows)
    return old,current,rows,raw


def test_graph_only_replaces_old_hashes_preserving_every_account_and_grant():
    old,current,rows,raw = graph_fixture()
    updated = helper.graph_replacement(raw,old,current,lambda value:"hash-new-random",lambda value,encoded:encoded == "hash-"+value)
    after = [json.loads(line) for line in updated.splitlines()]
    assert len(after) == len(rows)
    for before,row in zip(rows,after):
        if before["name"].startswith("old_"):
            assert row == dict(before,password="hash-new-random")
        else:assert row == before


def test_graph_refuses_stale_password_collision_or_root_selection():
    old,current,rows,raw = graph_fixture()
    for wrong in (dict(old,api=dict(INDEX_ARCADEDB_USER="root",INDEX_ARCADEDB_PASSWORD="invented")),
                  dict(old,api=dict(old["api"],INDEX_ARCADEDB_USER="new_api"))):
        with pytest.raises(ValueError):helper.graph_replacement(raw,wrong,current,lambda value:"new",lambda *args:True)
    with pytest.raises(ValueError,match="old_graph_hash_binding_required"):
        helper.graph_replacement(raw,old,current,lambda value:"new",lambda *args:False)


def cache_fixture():
    return ("# preserve\nuser old_worker on #"+hashlib.sha256(b"invented-old").hexdigest()+" ~ec:live:* -@all +ping +get\n"
            "user new_worker on #invented ~ec:live:* -@all +ping\nuser operator on #invented ~ec:lr_*:* -@all +ping\n").encode()


def test_cache_disables_only_old_login_preserving_other_lines_and_namespace_rules():
    raw = cache_fixture()
    updated = helper.cache_replacement(raw,"old_worker","invented-old","new_worker","operator")
    assert updated.splitlines()[1] == raw.splitlines()[1]+b" off resetpass"
    assert updated.splitlines()[2:] == raw.splitlines()[2:]


@pytest.mark.parametrize("old,password",[("new_worker","invented-old"),("operator","invented-old"),("old_worker","stale-password")])
def test_cache_refuses_active_identities_and_stale_authority(old,password):
    with pytest.raises(ValueError):helper.cache_replacement(cache_fixture(),old,password,"new_worker","operator")


def test_support_pins_and_root_guard(monkeypatch):
    for name,digest in helper.PINS.items():assert hashlib.sha256(SOURCE.with_name(name).read_bytes()).hexdigest() == digest
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()


@pytest.mark.parametrize("failure",[None,"denial_failed","concurrent_graph"])
def test_controlled_restart_restores_only_own_selections_and_preserves_concurrent_files(failure):
    paths = {name:Path("/invented/"+name) for name in ("graph","cache")}
    owners = {name:0 for name in paths}
    original = {name:b"original-"+name.encode() for name in paths}
    changed = {name:b"changed-"+name.encode() for name in paths}
    files = {paths[name]:raw for name,raw in original.items()}
    events = []
    def check(retired):
        if retired and failure:
            if failure == "concurrent_graph":files[paths["graph"]] = b"concurrent-preserve"
            raise ValueError("old_cache_login_still_accepted")
    shared = dict(await_check=lambda check:check(),http_status=lambda *args:200)
    result = dict(complete=False)
    helper.run_selection(shared,lambda path,owner:files[path],lambda path,raw,owner:files.__setitem__(path,raw),
        paths,owners,original,changed,lambda action,name:events.append((action,name)),check,lambda:None,result)
    if failure is None:
        assert result["complete"] and all(files[paths[name]] == changed[name] for name in paths)
    else:
        assert not result["complete"]
        assert files[paths["cache"]] == original["cache"]
        assert all(("start",name) in events for name in ("graph","cache","api","worker"))
        if failure == "concurrent_graph":
            assert files[paths["graph"]] == b"concurrent-preserve"
            assert not result["rollback_current_logins_and_api_verified"]
        else:assert result["rollback_current_logins_and_api_verified"]
