"""Source-only ACL/protocol checks; installed restart/acceptance is separate."""
import hashlib
import importlib.util
from io import BytesIO
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/install_launch_cache_operator.py"
spec = importlib.util.spec_from_file_location("cache_operator_installation", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_acl_preserves_existing_users_and_limits_new_identity_to_recovery_keys():
    original = b"user invented-worker on #"+b"a"*64+b" ~ec:live:* -@all +ping +get +set\n"
    password = "invented-"+"x"*43
    updated = helper.acl_addition(original,"ec_operator_0123456789ab",password)
    assert updated.startswith(original)
    rule = updated[len(original):].decode()
    assert "~ec:lr_*:* -@all +ping +get +set +del" in rule
    assert password not in rule
    assert hashlib.sha256(password.encode()).hexdigest() in rule
    assert "+@all" not in rule and "+acl" not in rule


def test_existing_operator_refused_without_replacing_acl():
    with pytest.raises(ValueError, match="existing_cache_operator_preserved"):
        helper.acl_addition(b"user ec_operator_0123456789ab off\n","ec_operator_0123456789ab","x"*43)


@pytest.mark.parametrize("raw,expected", [(b"+PONG\r\n",("simple",b"PONG")),
    (b"-NOPERM invented-private-details\r\n",("refused",None)),
    (b"$3\r\nabc\r\n",("bulk",b"abc")), (b":1\r\n",("integer",1))])
def test_bounded_protocol_does_not_echo_refusal_details(raw, expected):
    assert helper.read_reply(BytesIO(raw)) == expected


@pytest.mark.parametrize("raw", [b"$9999999\r\n",b"$3\r\na",b"+"+b"x"*4096+b"\r\n"])
def test_oversized_or_truncated_protocol_refused(raw):
    with pytest.raises(ValueError):
        helper.read_reply(BytesIO(raw))


def test_reviewed_shared_file_hash_matches():
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


def test_ordinary_user_refused_before_reading_secrets(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="local_root_operator_required"):
        helper.main()
