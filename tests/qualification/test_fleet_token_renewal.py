"""Tests for the fleet token renewal job cores."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renew = load('renew_fleet_memory_tokens')


def token_with_exp(exp: int) -> str:
    def seg(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    return seg({"alg": "HS256", "typ": "JWT"}) + "." + \
        seg({"sub": "x", "tenant": "hermes_gateway", "project_id": "default",
             "exp": exp}) + ".sig"


def test_decode_exp_reads_claim_with_shape_checks():
    assert renew.decode_exp(token_with_exp(1_800_000_000)) == 1_800_000_000
    for bad in ("", "not-a-jwt", "a.b", token_with_exp(0)):
        with pytest.raises(ValueError):
            renew.decode_exp(bad)


def test_needs_renewal_window_boundaries():
    now = 1_800_000_000
    assert renew.needs_renewal(now + 7 * 86400, now) is True      # exactly at window
    assert renew.needs_renewal(now + 7 * 86400 + 1, now) is False  # just outside
    assert renew.needs_renewal(now - 10, now) is True              # already expired


def test_load_profile_token_finds_and_ignores():
    env = Path("/tmp") / "test-env-renewal"
    env.write_text("MODEL=x\n# ENHANCED_COGNEE_ACCESS_TOKEN=commented\n"
                   "ENHANCED_COGNEE_ACCESS_TOKEN=abc.def.ghi\nOTHER=1\n")
    assert renew.load_profile_token(env) == "abc.def.ghi"
    empty = Path("/tmp") / "test-env-renewal-none"
    empty.write_text("MODEL=x\n")
    assert renew.load_profile_token(empty) is None
    assert renew.load_profile_token(Path("/tmp/definitely-missing-env")) is None
    env.unlink()
    empty.unlink()


def test_profiles_starts_with_default_then_sorted_roles():
    names = renew.profiles()
    assert names[0] == "default"
    assert "enhanced-cognee-test" not in names and "enhanced-cognee-test-two" not in names
    assert names[1:] == sorted(names[1:]) and len(names) >= 40
