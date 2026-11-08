"""Offline repair regressions using the immutable independent challenge inputs.

Only source-hash/output bindings are rebound in memory. Original challenge bodies
and their exact mapped readers are retained. Fixed refusal paths are asserted
explicitly rather than expecting the historical false-PASS assertion to run.
"""
import hashlib
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs/reports/audits/2026-11-01-security-first-cutover/review-round1/test_independent_challenges.py"
HELPER = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
REVIEW_SHA256 = "549b332ca4b469ed17101f9e4e1fc4341bd49551ce82ab38fd569d53a78af12f"
REJECTED_SHA256 = "cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813"


@pytest.fixture
def challenge(tmp_path):
    raw = REVIEW.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REVIEW_SHA256
    old = "PIN = '" + REJECTED_SHA256 + "'"
    new = "PIN = '" + hashlib.sha256(HELPER.read_bytes()).hexdigest() + "'"
    text = raw.decode("ascii")
    assert text.count(old) == 1
    module = ModuleType("repair_independent_inputs")
    module.__file__ = str(REVIEW)
    exec(compile(text.replace(old, new), str(REVIEW), "exec"), module.__dict__)
    module.OUT = tmp_path
    return module


def test_S01_alias_dotdot_rejects_hidden_symlink_before_fingerprinting(challenge, tmp_path, monkeypatch):
    with pytest.raises(challenge.h.Refusal, match="^unsafe_path_link$"):
        challenge.test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor(tmp_path, monkeypatch)


def test_L01_exact_installed_module_mapping_is_readable(challenge, monkeypatch):
    challenge.test_L01_installed_site_packages_layout_is_readable(monkeypatch)


def test_L02_root_decoys_cannot_authorize_changed_installed_modules(challenge, monkeypatch):
    with pytest.raises(challenge.h.Refusal, match="^inventory_or_loaded_or_candidate_drift$"):
        challenge.test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules(monkeypatch)
