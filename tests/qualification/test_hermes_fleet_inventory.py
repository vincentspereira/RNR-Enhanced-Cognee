"""Inventory must never follow profile redirects or read credential bytes."""
import importlib.util
import os
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/inventory_fleet.py"
spec = importlib.util.spec_from_file_location("fleet_inventory", SOURCE)
fleet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fleet)


def home(tmp_path):
    path = tmp_path / "home"
    path.mkdir(mode=0o700)
    (path / "profiles").mkdir(mode=0o700)
    return path


def test_metadata_without_reading_private_or_special_files(tmp_path):
    path = home(tmp_path)
    profile = path / "profiles" / "invented"
    profile.mkdir(mode=0o700)
    # A FIFO would block a content-reading inventory; metadata is sufficient.
    os.mkfifo(profile / ".env", mode=0o600)
    (profile / "auth.json").symlink_to("/unavailable/private/credentials")
    result = fleet.inventory(path)
    assert result["profile_directory_count"] == 2
    row = result["profiles"][1]
    assert row["markers"][".env"]["regular"] is False
    assert row["markers"]["auth.json"]["symlink"] is True
    assert row["admission"] == "pending"
    assert row["scope_mapping"] is None
    assert result["fleet_inventory_complete"] is False


def test_redirected_profile_is_retained_as_unresolved(tmp_path):
    path = home(tmp_path)
    (path / "profiles" / "peer").symlink_to("/unavailable/private", target_is_directory=True)
    result = fleet.inventory(path)
    assert result["profile_directory_count"] == 1
    assert result["unresolved_entries"] == [{"entry": "peer", "category": "symlink_not_followed"}]


def test_redirected_home_refused(tmp_path):
    path = home(tmp_path)
    link = tmp_path / "redirect"
    link.symlink_to(path, target_is_directory=True)
    with pytest.raises(OSError):
        fleet.inventory(link)


def test_root_never_walks_agent_trees(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    with pytest.raises(ValueError, match="run_as_profile_owner_not_root"):
        fleet.inventory(tmp_path / "does-not-exist")


def test_writable_profile_parent_remains_unqualified(tmp_path):
    path = home(tmp_path)
    (path / "profiles").chmod(0o777)
    result = fleet.inventory(path)
    assert {"entry": "profiles", "category": "writable_profiles_directory"} in result["unresolved_entries"]
    assert result["fleet_launch_approved"] is False


def test_bounded_inventory(tmp_path, monkeypatch):
    path = home(tmp_path)
    (path / "profiles" / "one").mkdir()
    monkeypatch.setattr(fleet, "LIMIT", 0)
    with pytest.raises(ValueError, match="profile_inventory_budget_exceeded"):
        fleet.inventory(path)
