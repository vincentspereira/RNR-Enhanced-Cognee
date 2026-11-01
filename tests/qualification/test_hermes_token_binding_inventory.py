"""Signature metadata and owner-only nofollow reads, not profile admission."""
import base64
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/inventory_launch_token_bindings.py"
spec = importlib.util.spec_from_file_location("token_binding_inventory",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def token(claims,key=b"invented-only-key",header=None):
    def encode(value):return base64.urlsafe_b64encode(json.dumps(value,separators=(",",":")).encode()).rstrip(b"=")
    raw = encode(header or {"alg":"HS256","typ":"JWT"})+b"."+encode(claims)
    return (raw+b"."+base64.urlsafe_b64encode(hmac.new(key,raw,hashlib.sha256).digest()).rstrip(b"=")).decode()


def claims():
    return {"sub":"invented_subject","agent_id":"invented_agent","tenant":"qualification",
        "project_id":"invented_scope","roles":["api_client"],"capture_policy":"selected","iat":1,"exp":2}


def test_expired_signed_claims_can_be_inventoried_without_claiming_live_authentication():
    value = claims()
    assert helper.verified_claims(token(value),b"invented-only-key") == value
    assert helper.verified_claims(token(value),b"different-invented-key") is None


@pytest.mark.parametrize("change",[{"roles":["admin"]},{"project_id":"../other"},{"exp":True},
    {"arbitrary_private_field":"invented-private-content"}])
def test_unsupported_claims_never_become_verified_runtime_bindings(change):
    value = dict(claims(),**change)
    assert helper.verified_claims(token(value),b"invented-only-key") is None


def test_unsigned_header_and_duplicate_fields_are_refused():
    assert helper.verified_claims(token(claims(),header={"alg":"none"}),b"invented-only-key") is None
    with pytest.raises(ValueError,match="duplicate_object_fields"):
        helper.unique_object([("sub","one"),("sub","two")])


def test_profile_reader_refuses_redirected_file(tmp_path):
    original = tmp_path / "original"
    original.write_bytes(b"invented-private-marker")
    (tmp_path / ".env").symlink_to(original)
    fd = os.open(tmp_path,os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError):
            helper.read_owner_file(fd,".env",os.geteuid())
    finally:
        os.close(fd)


def test_owner_child_refuses_root_before_reading_any_profile(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    with pytest.raises(ValueError,match="restricted_owner_child_required"):
        helper.owner_child()
