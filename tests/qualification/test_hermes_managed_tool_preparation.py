"""Fail-closed admission of existing tools to a separate protected generation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def builder():
    path = Path("integrations/hermes/deployment/prepare_restricted_runtime.py").resolve()
    spec = importlib.util.spec_from_file_location("tool_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tools(builder, tmp_path, monkeypatch):
    root = tmp_path / "original-tools"
    root.mkdir()
    monkeypatch.setattr(builder, "TOOL_STORE", root)
    lock = {"schema": 1, "packages": {}}
    facts = {"schema": 1, "packages": {}}
    for name, (version, binary) in builder.MANAGED_TOOLS.items():
        entry = name + "-" + version + "-linux-x64"
        directory = root / entry
        executable = directory / binary
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"#!/bin/sh\nprintf synthetic-version\n")
        executable.chmod(0o755)
        sha = hashlib.sha256(name.encode()).hexdigest()
        lock["packages"][name] = {"version": version, "artifacts": {
            "any" if name == "npm" else "linux-x64": {
                "sha256": sha, "url": "https://example.invalid/public-program"}}}
        facts["packages"][name] = {"entry": entry, "version": version,
                                   "target": "linux-x64", "artifacts": [sha],
                                   "digest": builder.tool_digest(directory),
                                   "env": {"UNAPPROVED_PRIVATE_SETTING": "must-not-transfer"}}
    return root, lock, facts


def select(builder, lock, facts):
    return builder.selected_tools(json.dumps(lock).encode(), json.dumps(facts).encode())


def test_admission_uses_lock_identity_and_reconstructs_only_program_path(builder, tools):
    root, lock, facts = tools
    selected = select(builder, lock, facts)
    assert set(selected) == set(builder.MANAGED_TOOLS)
    for name, record in selected.items():
        assert set(record["env"]) == {"PATH"}
        assert record["env"]["PATH"][0].startswith("{{store}}/" + record["entry"])
        assert "must-not-transfer" not in json.dumps(record)
        assert record["digest"] == builder.tool_digest(root / record["entry"])


@pytest.mark.parametrize("field,value", [
    ("entry", "../outside"), ("entry", "/etc"), ("entry", "node-other-linux-x64"),
    ("version", "0.0.1"), ("target", "win32-x64"), ("artifacts", []),
    ("artifacts", ["a" * 64]), ("digest", None), ("digest", "A" * 64),
    ("digest", "not-a-hash"),
])
def test_unverified_or_changed_source_identity_is_rejected(builder, tools, field, value):
    _, lock, facts = tools
    facts["packages"]["node"][field] = value
    with pytest.raises(builder.PreparationError, match="identity|fingerprint"):
        select(builder, lock, facts)


@pytest.mark.parametrize("which", ["facts", "lock"])
def test_schema_is_required(builder, tools, which):
    _, lock, facts = tools
    (facts if which == "facts" else lock).pop("schema")
    with pytest.raises(builder.PreparationError, match="schema"):
        select(builder, lock, facts)


def test_changed_pin_is_not_admitted_even_with_matching_source_record(builder, tools):
    _, lock, facts = tools
    lock["packages"]["node"]["version"] = "unreviewed"
    facts["packages"]["node"]["version"] = "unreviewed"
    with pytest.raises(builder.PreparationError, match="identity"):
        select(builder, lock, facts)


def test_payload_hash_matches_pm_order_links_and_cache_policy(builder, tmp_path):
    root = tmp_path / "tree"
    (root / "a").mkdir(parents=True)
    (root / "a/z").write_bytes(b"nested")
    (root / "a.txt").write_bytes(b"first")
    (root / "link").symlink_to("a", target_is_directory=True)
    (root / "__pycache__").mkdir()
    (root / "__pycache__/ignored.pyc").write_bytes(b"runtime-only")
    reference = hashlib.sha256()
    for name, raw in [("a.txt", b"first"), ("a/z", b"nested"), ("link", b"a")]:
        reference.update(name.encode() + b"\0" + raw)
    assert builder.tool_digest(root) == reference.hexdigest()
    (root / "__pycache__/ignored.pyc").write_bytes(b"changed-runtime-only")
    assert builder.tool_digest(root) == reference.hexdigest()


def test_copy_never_executes_binaries_and_keeps_originals(builder, tools, tmp_path, monkeypatch):
    root, lock, facts = tools
    selected = select(builder, lock, facts)
    original = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    stage = tmp_path / "new-generation"
    (stage / "python").mkdir(parents=True)
    monkeypatch.setattr(builder.subprocess, "run", lambda *a, **kw: pytest.fail("No program execution allowed"))
    reports = builder.copy_managed_tools(stage, selected)
    assert len(reports) == 4
    assert all(row["source_payload_verified"] and row["copy_payload_verified"] for row in reports)
    assert not any(row["tool_version_verified_by_execution"] for row in reports)
    for relative, raw in original.items():
        assert (root / relative).read_bytes() == raw
        copied = stage / "python" / relative
        assert copied.read_bytes() == raw
        assert copied.stat().st_ino != (root / relative).stat().st_ino


def test_absolute_and_cross_tool_links_rebase_and_hash_actual_copy(builder, tools, tmp_path):
    root, lock, facts = tools
    node = root / facts["packages"]["node"]["entry"]
    npm = root / facts["packages"]["npm"]["entry"]
    (node / "node-alias").symlink_to(node / "bin/node")
    (npm / "node-alias").symlink_to(node / "bin/node")
    for name in ("node", "npm"):
        facts["packages"][name]["digest"] = builder.tool_digest(root / facts["packages"][name]["entry"])
    selected = select(builder, lock, facts)
    stage = tmp_path / "new-generation"
    (stage / "python").mkdir(parents=True)
    builder.copy_managed_tools(stage, selected)
    target = stage / "python" / node.name / "bin/node"
    for name in ("node", "npm"):
        copied = stage / "python" / selected[name]["entry"]
        assert (copied / "node-alias").resolve() == target
        assert not os.path.isabs(os.readlink(copied / "node-alias"))
        assert selected[name]["digest"] == builder.tool_digest(copied)
        assert selected[name]["digest"] != facts["packages"][name]["digest"]


@pytest.mark.parametrize("mutation", ["content", "outside-link", "fifo", "setuid", "linked-directory"])
def test_unsafe_or_modified_payload_is_refused(builder, tools, tmp_path, mutation):
    root, lock, facts = tools
    source = root / facts["packages"]["ffmpeg"]["entry"]
    if mutation == "content":
        (source / "bin/ffmpeg").write_bytes(b"changed")
    elif mutation == "outside-link":
        (source / "outside").symlink_to(tmp_path / "never-copy")
        facts["packages"]["ffmpeg"]["digest"] = builder.tool_digest(source)
    elif mutation == "fifo":
        os.mkfifo(source / "pipe")
    elif mutation == "setuid":
        (source / "bin/ffmpeg").chmod(0o4755)
    else:
        retained = source.with_name("original-preserved")
        source.rename(retained)
        source.symlink_to(retained, target_is_directory=True)
    selected = select(builder, lock, facts)
    stage = tmp_path / "new-generation"
    (stage / "python").mkdir(parents=True)
    with pytest.raises((builder.PreparationError, OSError)):
        builder.copy_managed_tools(stage, selected)
    assert not (tmp_path / "never-copy").exists()


def test_existing_payload_slot_is_not_replaced(builder, tools, tmp_path):
    _, lock, facts = tools
    selected = select(builder, lock, facts)
    stage = tmp_path / "new-generation"
    target = stage / "python" / selected["ffmpeg"]["entry"]
    target.mkdir(parents=True)
    (target / "preserved").write_text("original")
    with pytest.raises(FileExistsError):
        builder.copy_managed_tools(stage, selected)
    assert (target / "preserved").read_text() == "original"


@pytest.mark.parametrize("change_source", [True, False])
def test_drift_during_copy_cannot_be_recorded_as_verified(builder, tools, tmp_path, monkeypatch, change_source):
    root, lock, facts = tools
    selected = select(builder, lock, facts)
    stage = tmp_path / "new-generation"
    (stage / "python").mkdir(parents=True)
    original_copy = builder.copy_tree
    def copy(source, destination, mappings, **kwargs):
        original_copy(source, destination, mappings, **kwargs)
        if source.name.startswith("ffmpeg-"):
            target = source if change_source else destination
            (target / "bin/ffmpeg").write_bytes(b"changed during copy")
    monkeypatch.setattr(builder, "copy_tree", copy)
    with pytest.raises(builder.PreparationError, match="changed during"):
        builder.copy_managed_tools(stage, selected)
    assert selected["ffmpeg"]["digest"] == facts["packages"]["ffmpeg"]["digest"]


def test_excluded_private_file_is_never_copied_or_silently_admitted(builder, tools, tmp_path):
    root, lock, facts = tools
    source = root / facts["packages"]["ffmpeg"]["entry"]
    (source / ".env").write_bytes(b"SYNTHETIC_PRIVATE_VALUE")
    facts["packages"]["ffmpeg"]["digest"] = builder.tool_digest(source)
    selected = select(builder, lock, facts)
    stage = tmp_path / "new-generation"
    (stage / "python").mkdir(parents=True)
    with pytest.raises(builder.PreparationError, match="changed during"):
        builder.copy_managed_tools(stage, selected)
    assert not list(stage.rglob(".env"))


def test_metadata_rejects_linked_parent_or_file(builder, tmp_path):
    directory = tmp_path / "metadata"
    directory.mkdir()
    (directory / "facts.json").write_text('{"schema": 1}')
    assert builder.tool_metadata(directory / "facts.json") == b'{"schema": 1}'
    linked = tmp_path / "linked"
    linked.symlink_to(directory, target_is_directory=True)
    with pytest.raises(OSError):
        builder.tool_metadata(linked / "facts.json")
    (directory / "redirect.json").symlink_to(directory / "facts.json")
    with pytest.raises(OSError):
        builder.tool_metadata(directory / "redirect.json")


def test_cli_refuses_tool_mode_without_apply():
    result = subprocess.run(["/usr/bin/python3", "-I", "-S", "-B",
                             "integrations/hermes/deployment/prepare_restricted_runtime.py",
                             "--preflight", "--with-managed-tools"], capture_output=True)
    assert result.returncode == 2
    assert b"requires --apply" in result.stderr
