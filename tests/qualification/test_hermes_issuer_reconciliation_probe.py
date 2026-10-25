"""Probe staging pins, owner launch boundaries and fixed receipts; source only."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_issuer_reconciliation.py"
spec = importlib.util.spec_from_file_location("issuer_reconciliation_probe",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_reviewed_staging_and_file_support_match_pins():
    assert hashlib.sha256(SOURCE.with_name("stage_launch_issuer.py").read_bytes()).hexdigest() == helper.STAGING_SHA256
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


def test_nonroot_parent_and_root_owner_child_are_refused(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:SimpleNamespace(pw_uid=993))
    with pytest.raises(ValueError,match="restricted_owner_required"):helper.setup_child({})


@pytest.mark.parametrize("stdout,returncode",[(b'{"complete":true,"requested_interruption_observed":true}',0),
    (b'{"complete":false}',1),(b'{"complete":true,"requested_interruption_observed":true,"unexpected":"private"}',0)])
def test_owner_launch_has_no_keys_groups_or_inherited_environment_and_strict_receipts(monkeypatch,stdout,returncode):
    account = SimpleNamespace(pw_uid=993,pw_gid=993,pw_dir="/invented/home")
    data = {"entry":{"executable":"/invented/python"},"old":"invented-ordinary-token","bundle":{"token":"invented-replacement-token"}}
    def run(arguments,**kwargs):
        assert kwargs["user"] == 993 and kwargs["group"] == 993 and kwargs["extra_groups"] == ()
        assert arguments[:3] == ["/usr/bin/setpriv","--no-new-privs","--"]
        assert "invented-ordinary-token" not in json.dumps(arguments)
        assert "invented-replacement-token" not in json.dumps(kwargs["env"])
        assert kwargs["stderr"] is helper.subprocess.DEVNULL
        assert json.loads(kwargs["input"]) == data
        return SimpleNamespace(returncode=returncode,stdout=stdout)
    monkeypatch.setattr(helper.subprocess,"run",run)
    if returncode == 0 and b"unexpected" not in stdout:helper.initialize_fixture(account,data)
    else:
        with pytest.raises(ValueError):helper.initialize_fixture(account,data)
