"""Export selection and private pipe boundaries; no real host credential reads."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/export_launch_credential_custody.py"
spec = importlib.util.spec_from_file_location("credential_custody_export",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def configs():
    values = {name:{field:"invented-current" for field in fields} for name,fields in helper.FIELDS.items()}
    for value in values.values():
        value.update(ENCRYPTION_MASTER_KEY="excluded-cipher-key",ENHANCED_INDEX_KEY="excluded-index-key",
            ENHANCED_BACKUP_SIGNING_KEY="excluded-backup-key",UNRELATED="excluded-unrelated")
    values["api"]["ENHANCED_JWT_SECRET"] = values["operator"]["ENHANCED_JWT_SECRET"]
    return values


def test_only_current_authentication_fields_exported_without_recovery_or_data_keys():
    raw = helper.payload(configs())
    result = json.loads(raw)
    assert result["source_revision"] == helper.BASE.name
    for name,fields in helper.FIELDS.items():assert set(result["active_authentication"][name]) == set(fields)
    assert b"excluded-" not in raw


@pytest.mark.parametrize("wrong",[None,"",123,"invented\nunsafe"])
def test_missing_or_malformed_authentication_refused(wrong):
    values = configs()
    values["worker"]["INDEX_VALKEY_URL"] = wrong
    with pytest.raises(ValueError,match="current_authentication_fields_required"):helper.payload(values)


def test_different_active_signing_keys_refused():
    values = configs()
    values["api"]["ENHANCED_JWT_SECRET"] = "invented-different"
    with pytest.raises(ValueError,match="active_signing_binding_required"):helper.payload(values)


def test_encrypt_and_decrypt_use_only_pipes_with_existing_identity(monkeypatch):
    calls = []
    raw = b"invented-private-payload"
    encrypted = b"age-encryption.org/v1\ninvented-ciphertext"
    def run(arguments,**kwargs):
        assert raw.decode() not in json.dumps(arguments)
        assert raw.decode() not in json.dumps(kwargs["env"])
        assert kwargs["stderr"] is helper.subprocess.DEVNULL
        assert "--output" not in arguments and "-o" not in arguments
        calls.append((arguments,kwargs["input"]))
        return SimpleNamespace(returncode=0,stdout=encrypted if "--encrypt" in arguments else raw)
    monkeypatch.setattr(helper.subprocess,"run",run)
    assert helper.encrypt_verified(raw,"age1"+"q"*58) == encrypted
    assert calls[0][1] == raw and calls[1][1] == encrypted
    assert calls[1][0][-1] == str(helper.IDENTITY)


@pytest.mark.parametrize("failure",["recipient","format","roundtrip","process"])
def test_bad_recipient_ciphertext_roundtrip_or_process_failure_refused(monkeypatch,failure):
    def run(arguments,**kwargs):
        if failure == "process":return SimpleNamespace(returncode=1,stdout=b"invented-private-error")
        if "--encrypt" in arguments:
            return SimpleNamespace(returncode=0,stdout=b"wrong-format" if failure == "format" else b"age-encryption.org/v1\ninvented")
        return SimpleNamespace(returncode=0,stdout=b"different" if failure == "roundtrip" else b"invented")
    monkeypatch.setattr(helper.subprocess,"run",run)
    with pytest.raises(ValueError):helper.encrypt_verified(b"invented","not-an-age-recipient" if failure == "recipient" else "age1"+"q"*58)


def test_root_and_exact_support_guards(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_root_operator_required"):helper.main()
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SUPPORT_SHA256
