"""Managed-tool inspection must not execute, install or expose unrelated state."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def tool_fixture(monkeypatch, tmp_path):
    path = Path("integrations/hermes/deployment/inspect_restricted_runtime.py").resolve()
    spec = importlib.util.spec_from_file_location("managed_tool_inspector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HOME", tmp_path)
    root = tmp_path / ".hermes/tools"
    root.mkdir(parents=True)
    packages = {}
    for name, binary in {"ffmpeg": "bin/ffmpeg", "node": "bin/node", "npm": "bin/npm", "ripgrep": "rg"}.items():
        entry = name + "-1.0.0"
        program = root / entry / binary
        program.parent.mkdir(parents=True)
        program.write_text("DO NOT EXECUTE THIS SYNTHETIC TOOL")
        program.chmod(0o755)
        packages[name] = {"version": "1.0.0", "entry": entry, "unrelated_private": "NEVER_EMIT"}
    original = root / "facts.json"
    original.write_text(json.dumps({"packages": packages}))
    real_bounded = module.bounded
    def bounded(path, limit=1048576):
        if str(path).startswith("/opt/hermes-runtime/"):
            return b'{"packages":{"python":{"entry":"."}}}'
        return real_bounded(path, limit)
    monkeypatch.setattr(module, "bounded", bounded)
    def git(*args):
        assert args == ("show", module.EXPECTED_REVISION + ":pm/lock.json")
        return json.dumps({"packages": {name: {"version": "1.0.0"} for name in packages}}).encode()
    monkeypatch.setattr(module, "git", git)
    monkeypatch.setattr(module, "allocated_bytes", lambda path: 4096)
    def forbidden(*args, **kwargs):
        raise AssertionError("Tool inspection must not run any tool or installer")
    monkeypatch.setattr(module.subprocess, "run", forbidden)
    return module, root, packages, original


def test_existing_selected_tools_report_metadata_only_without_executing(tool_fixture):
    module, root, packages, facts = tool_fixture
    before = facts.read_bytes()
    result = module.managed_tool_audit()
    assert len(result["managed_tools"]) == 4
    for row in result["managed_tools"]:
        assert row["recorded_version_matches_lock"] is True
        assert row["binary_present"] is True and row["binary_executable"] is True
        assert row["protected_record_present"] is False
    assert result["tool_binaries_executed"] is False
    assert result["tool_versions_verified_by_execution"] is False
    assert result["runtime_qualified"] is False
    assert "NEVER_EMIT" not in json.dumps(result)
    assert facts.read_bytes() == before


def test_missing_original_tool_is_not_claimed_installed(tool_fixture):
    module, root, packages, facts = tool_fixture
    del packages["npm"]
    facts.write_text(json.dumps({"packages": packages}))
    # The lock still must contain the expected four package pins.
    module.git = lambda *args: json.dumps({"packages": {name: {"version": "1.0.0"}
        for name in ("ffmpeg", "node", "npm", "ripgrep")}}).encode()
    row = next(row for row in module.managed_tool_audit()["managed_tools"] if row["name"] == "npm")
    assert row["original_record_present"] is False and "binary_present" not in row


def test_version_drift_and_missing_binary_are_reported(tool_fixture):
    module, root, packages, facts = tool_fixture
    packages["node"]["version"] = "0.9.0"
    packages["ripgrep"]["entry"] = "ripgrep-missing"
    facts.write_text(json.dumps({"packages": packages}))
    rows = {row["name"]: row for row in module.managed_tool_audit()["managed_tools"]}
    assert rows["node"]["recorded_version_matches_lock"] is False
    assert rows["ripgrep"]["entry_state"] == "missing"


@pytest.mark.parametrize("linked", [False, True])
def test_external_or_linked_entries_are_not_walked_and_targets_are_hidden(tool_fixture, tmp_path, linked):
    module, root, packages, facts = tool_fixture
    outside = tmp_path / "PRIVATE_TARGET_DO_NOT_EMIT"
    outside.mkdir()
    if linked:
        (root / "node-external").symlink_to(outside, target_is_directory=True)
        packages["node"]["entry"] = "node-external"
    else:
        packages["node"]["entry"] = str(outside)
    facts.write_text(json.dumps({"packages": packages}))
    result = module.managed_tool_audit()
    row = next(row for row in result["managed_tools"] if row["name"] == "node")
    assert row["entry_state"] == ("linked_entry_requires_review" if linked else "outside_tool_store_redacted")
    assert "PRIVATE_TARGET_DO_NOT_EMIT" not in json.dumps(result)


def test_invalid_version_metadata_is_refused_without_dumping_record(tool_fixture):
    module, root, packages, facts = tool_fixture
    packages["node"]["version"] = {"private": "NEVER_EMIT"}
    facts.write_text(json.dumps({"packages": packages}))
    with pytest.raises(module.InspectionError, match="format review"):
        module.managed_tool_audit()


def test_store_metadata_changes_cannot_pass_inspection(tool_fixture, monkeypatch):
    module, root, packages, facts = tool_fixture
    original = module.allocated_bytes
    def mutate(path):
        facts.write_text('{"packages":{}}')
        return original(path)
    monkeypatch.setattr(module, "allocated_bytes", mutate)
    with pytest.raises(module.InspectionError, match="changed"):
        module.managed_tool_audit()
