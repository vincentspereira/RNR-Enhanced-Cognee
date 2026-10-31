"""Only verified ciphertext may reach the ordinary owner; no host secrets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/release_launch_encrypted_custody_copy.py"
spec = importlib.util.spec_from_file_location("encrypted_custody_pickup",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_exact_file_support_hash():
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


@pytest.fixture
def owner(monkeypatch,tmp_path):
    account = SimpleNamespace(pw_uid=os.geteuid(),pw_dir="/home/"+helper.OWNER)
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:account)
    monkeypatch.setattr(helper.os,"getgroups",lambda:[])
    monkeypatch.setattr(helper.os,"umask",lambda *args:None)
    original_read = Path.read_text
    def read(path,*args,**kwargs):
        if str(path) == "/proc/self/status":return "NoNewPrivs:\t1\nCapEff:\t0000000000000000\nCapAmb:\t0000000000000000\n"
        return original_read(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",read)
    original_mkdtemp = helper.tempfile.mkdtemp
    monkeypatch.setattr(helper.tempfile,"mkdtemp",lambda **kwargs:original_mkdtemp(prefix=kwargs["prefix"],dir=tmp_path))
    return account


def test_owner_copy_is_private_ciphertext_and_original_input_is_preserved(owner,monkeypatch):
    raw = b"age-encryption.org/v1\ninvented-encrypted-fixture"
    monkeypatch.setattr(helper,"EXPECTED_SHA256",hashlib.sha256(raw).hexdigest())
    report = helper.owner_copy(raw)
    file = Path(report["owner_file"])
    assert file.read_bytes() == raw
    assert file.stat().st_mode & 0o777 == 0o600 and file.parent.stat().st_mode & 0o777 == 0o700
    assert report["plaintext_file_written"] is False
    assert file.stat().st_uid == owner.pw_uid


@pytest.mark.parametrize("raw",[b'{"plaintext_secret":"invented"}',b"age-encryption.org/v1\nwrong-ciphertext"])
def test_plaintext_and_wrong_ciphertext_refused(owner,raw):
    with pytest.raises(ValueError,match="verified_ciphertext_required"):helper.owner_copy(raw)


def test_receipt_cannot_select_private_root_path_or_claim_plaintext_output():
    report = dict(complete=True,owner_file="/tmp/ec-owner-custody-abcdefgh/current-logins.json.age",
        encrypted_export_sha256=helper.EXPECTED_SHA256,byte_count=32,plaintext_file_written=False)
    assert helper.validate_receipt(report,32) == report
    for wrong in (dict(report,owner_file="/etc/private.age"),dict(report,plaintext_file_written=True),
                  dict(report,byte_count=True),dict(report,private_key="invented")):
        with pytest.raises(ValueError):helper.validate_receipt(wrong,32)


def test_ordinary_parent_and_root_child_refused_before_any_file_write(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()
    monkeypatch.setattr(helper.pwd,"getpwnam",lambda name:SimpleNamespace(pw_uid=1000,pw_dir="/home/"+helper.OWNER))
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    with pytest.raises(ValueError,match="restricted_owner_required"):helper.owner_copy(b"invented")
