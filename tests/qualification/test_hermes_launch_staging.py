"""Public artifact admission and preservation before operator staging."""
import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/stage_launch_runtime.py"
spec = importlib.util.spec_from_file_location("launch_staging", SOURCE)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def test_differing_public_bytes_refused(tmp_path):
    path = tmp_path / "artifact"
    path.write_bytes(b"different")
    with pytest.raises(ValueError, match="public_artifact_hash"):
        stage.checked_bytes(path, hashlib.sha256(b"approved").hexdigest(), 100)


def test_symlink_never_admitted_even_with_matching_bytes(tmp_path):
    path = tmp_path / "artifact"
    path.write_bytes(b"approved")
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        stage.checked_bytes(link, hashlib.sha256(b"approved").hexdigest(), 100)


def test_fifo_rejected_without_blocking(tmp_path):
    path = tmp_path / "artifact"
    os.mkfifo(path)
    with pytest.raises(ValueError, match="public_artifact_type_or_size"):
        stage.checked_bytes(path, "unused", 100)


def test_size_budget_enforced_before_hash(tmp_path):
    path = tmp_path / "artifact"
    path.write_bytes(b"oversized")
    with pytest.raises(ValueError, match="public_artifact_type_or_size"):
        stage.checked_bytes(path, hashlib.sha256(b"oversized").hexdigest(), 1)


def test_existing_artifact_preserved(tmp_path):
    path = tmp_path / "artifact"
    path.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        stage.write_new(path, b"replacement")
    assert path.read_bytes() == b"original"


def test_ordinary_user_cannot_stage(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    with pytest.raises(ValueError, match="operator_authentication_required"):
        stage.stage()
