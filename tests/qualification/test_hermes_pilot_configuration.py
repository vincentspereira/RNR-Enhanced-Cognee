"""Settings preservation and actual-provider read contract preparation checks."""
import importlib.util
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def configuration():
    path = Path("integrations/hermes/deployment/configure_pilot_provider.py").resolve()
    spec = importlib.util.spec_from_file_location("pilot_configuration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed_settings_have_no_model_or_credential_configuration(configuration):
    assert configuration.FILES["config.yaml"] == b"memory:\n  provider: enhanced_cognee\n"
    assert json.loads(configuration.FILES["enhanced_cognee.json"]) == {
        "base_url": "http://127.0.0.1:28080", "timeout": 10,
        "include_shared": True, "capture_policy": "selected"}
    assert configuration.TOKEN_NAME.encode() not in b"".join(configuration.FILES.values())


def test_settings_created_privately_and_matching_retry_is_unchanged(configuration, tmp_path):
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert configuration.create_settings(directory, os.getuid()) == list(configuration.FILES)
        before = {}
        for name, raw in configuration.FILES.items():
            target = tmp_path / name
            assert target.read_bytes() == raw and target.stat().st_mode & 0o777 == 0o600
            assert target.stat().st_nlink == 1
            before[name] = target.stat().st_mtime_ns
        assert configuration.create_settings(directory, os.getuid()) == []
        assert before == {name: (tmp_path / name).stat().st_mtime_ns for name in before}
        assert {p.name for p in tmp_path.iterdir()} == set(configuration.FILES)
    finally:
        os.close(directory)


@pytest.mark.parametrize("which", ["config.yaml", "enhanced_cognee.json"])
@pytest.mark.parametrize("mutation", ["different", "public", "symlink", "hardlink"])
def test_existing_edits_or_unsafe_files_are_preserved_before_any_write(configuration, tmp_path, which, mutation):
    target = tmp_path / which
    raw = b"ORIGINAL_PRIVATE_TEST_SETTING" if mutation == "different" else configuration.FILES[which]
    target.write_bytes(raw)
    target.chmod(0o600)
    if mutation == "public": target.chmod(0o644)
    elif mutation == "symlink":
        target.rename(tmp_path / "original")
        target.symlink_to("original")
    elif mutation == "hardlink": os.link(target, tmp_path / "original")
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises((configuration.ConfigurationError, OSError)) as error:
            configuration.create_settings(directory, os.getuid())
        assert "ORIGINAL_PRIVATE_TEST_SETTING" not in str(error.value)
        assert target.read_bytes() == raw
        other = "enhanced_cognee.json" if which == "config.yaml" else "config.yaml"
        assert not (tmp_path / other).exists()
    finally:
        os.close(directory)


def test_interrupted_matching_settings_resume_without_overwrite(configuration, tmp_path):
    target = tmp_path / "enhanced_cognee.json"
    target.write_bytes(configuration.FILES[target.name])
    target.chmod(0o600)
    before = target.stat().st_mtime_ns
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert configuration.create_settings(directory, os.getuid()) == ["config.yaml"]
        assert target.stat().st_mtime_ns == before
    finally:
        os.close(directory)


def test_destination_created_by_other_writer_is_never_replaced(configuration, monkeypatch, tmp_path):
    original_publish = configuration.publish
    def publish(directory, source, target):
        (tmp_path / target).write_bytes(b"CONCURRENT_TEST_SETTING")
        original_publish(directory, source, target)
    monkeypatch.setattr(configuration, "publish", publish)
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(configuration.ConfigurationError, match="retained"):
            configuration.create_settings(directory, os.getuid())
        assert (tmp_path / "enhanced_cognee.json").read_bytes() == b"CONCURRENT_TEST_SETTING"
        assert len(list(tmp_path.glob(".cognee-pilot-config-*"))) == 1
    finally:
        os.close(directory)


def status():
    return {"ready": True, "tenant_id": "qualification", "project_id": "hermes_pilot",
            "subject": "hermes_pilot_runtime", "capture": "selected", "notebook_mirroring": False,
            "schema_version": 3, "encryption": "AES-256-GCM", "active_records": 0}


def test_qualification_calls_only_status_and_recall_tools(configuration):
    calls = []
    class Provider:
        def handle_tool_call(self, name, args):
            calls.append((name, args))
            if name == "enhanced_status": return json.dumps(status())
            assert name == "enhanced_recall"
            assert args == {"query": "Invented pilot connector qualification fixture", "limit": 1}
            return '{"results":[]}'
    configuration.qualify_provider(Provider())
    assert [name for name, _ in calls] == ["enhanced_status", "enhanced_recall"]


@pytest.mark.parametrize("mutation", ["expired", "tenant", "project", "subject", "capture", "mirroring", "schema", "cipher", "records", "boolean-count", "recall-error", "recall-records"])
def test_mismatched_scope_status_or_unexpected_recall_never_becomes_success(configuration, mutation):
    data = status()
    changes = {"tenant": ("tenant_id", "other"), "project": ("project_id", "other"),
               "subject": ("subject", "other"), "capture": ("capture", "explicit"),
               "mirroring": ("notebook_mirroring", True), "schema": ("schema_version", 2),
               "cipher": ("encryption", "none"), "records": ("active_records", 1),
               "boolean-count": ("active_records", False)}
    if mutation in changes:
        field, value = changes[mutation]
        data[field] = value
    if mutation == "expired": data = {"error": "PRIVATE_TEST_SENTINEL", "status_code": 401}
    class Provider:
        def handle_tool_call(self, name, args):
            if name == "enhanced_status": return json.dumps(data)
            if mutation == "recall-error": return '{"error":"PRIVATE_TEST_SENTINEL","results":[]}'
            return '{"results":[{"content":"PRIVATE_TEST_SENTINEL"}]}'
    with pytest.raises(configuration.ConfigurationError) as error:
        configuration.qualify_provider(Provider())
    assert "PRIVATE_TEST_SENTINEL" not in str(error.value)


def test_identity_failure_reports_only_phase_before_profile_or_import_work(configuration, monkeypatch, capsys):
    from types import SimpleNamespace
    monkeypatch.setattr(configuration.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="wrong-user", pw_uid=0))
    monkeypatch.setattr(configuration, "open_profile", lambda uid: pytest.fail("No profile access permitted"))
    with pytest.raises(SystemExit) as error:
        configuration.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out) == {
        "complete": False, "failure_stage": "identity", "existing_and_prepared_files_retained": True}
