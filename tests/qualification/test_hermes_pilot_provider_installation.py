"""Preservation, payload and privilege boundaries for pilot-only installation."""
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest


@pytest.fixture
def installer():
    path = Path("integrations/hermes/deployment/install_pilot_provider.py").resolve()
    spec = importlib.util.spec_from_file_location("pilot_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def payload():
    base = Path("integrations/hermes/enhanced_cognee")
    return {name: (base / name).read_bytes() for name in ("__init__.py", "client.py", "plugin.yaml")}


def test_reviewed_payload_matches_maintained_source(installer, payload):
    installer.verify_payload(payload)
    assert sum(map(len, payload.values())) < 65536


@pytest.mark.parametrize("mutation", ["changed", "missing", "extra", "not-bytes"])
def test_changed_or_extra_payload_is_not_admitted(installer, payload, mutation):
    if mutation == "changed":
        payload["client.py"] += b"\n# changed"
    elif mutation == "missing":
        payload.pop("client.py")
    elif mutation == "extra":
        payload[".env"] = b"SYNTHETIC_SECRET_MUST_NOT_COPY"
    else:
        payload["client.py"] = "not bytes"
    with pytest.raises(installer.InstallError) as error:
        installer.verify_payload(payload)
    assert "SYNTHETIC_SECRET" not in str(error.value)


def test_source_directory_ancestors_cannot_redirect(installer, tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    (tmp_path / "link").symlink_to(original, target_is_directory=True)
    with pytest.raises(OSError):
        installer.open_directory(tmp_path / "link")
    assert not list(original.iterdir())


@pytest.mark.parametrize("owner,mode", [(1000, 0o755), (0, 0o775), (0, 0o777)])
def test_addon_parent_requires_root_and_protected_modes(installer, monkeypatch, owner, mode):
    monkeypatch.setattr(installer.os, "fstat", lambda fd: SimpleNamespace(st_uid=owner, st_mode=stat.S_IFDIR | mode))
    with pytest.raises(installer.InstallError, match="root-owned"):
        installer.protected_directory(7)


@pytest.fixture
def staged_root(installer, monkeypatch, tmp_path):
    root = tmp_path / "synthetic-filesystem"
    parent = root / "opt/hermes-runtime"
    parent.mkdir(parents=True)
    real_open_directory = installer.open_directory
    monkeypatch.setattr(installer, "open_directory", lambda path: real_open_directory(root if path == Path("/") else path))
    real_fstat = installer.os.fstat
    def root_metadata(fd):
        info = real_fstat(fd)
        return SimpleNamespace(st_uid=0, st_mode=info.st_mode, st_nlink=info.st_nlink, st_size=info.st_size)
    monkeypatch.setattr(installer.os, "fstat", root_metadata)
    return parent / "providers" / installer.ARTIFACT_NAME


def test_stage_is_small_detached_and_idempotent_without_overwrite(installer, payload, staged_root):
    assert installer.stage_artifact(payload) is True
    before = {}
    for name, raw in payload.items():
        path = staged_root / name
        assert path.read_bytes() == raw
        assert path.stat().st_mode & 0o777 == 0o644
        assert path.stat().st_nlink == 1
        before[name] = path.stat().st_mtime_ns
    assert installer.stage_artifact(payload) is False
    assert before == {name: (staged_root / name).stat().st_mtime_ns for name in payload}
    assert set(path.name for path in staged_root.iterdir()) == set(payload)


@pytest.mark.parametrize("mutation", ["bytes", "extra", "linked-file", "hardlink", "writable"])
def test_existing_damaged_artifact_is_preserved_and_refused(installer, payload, staged_root, mutation):
    installer.stage_artifact(payload)
    client = staged_root / "client.py"
    if mutation == "bytes":
        client.write_bytes(b"ORIGINAL_CHANGED_DATA_MUST_STAY")
    elif mutation == "extra":
        (staged_root / ".env").write_bytes(b"SYNTHETIC_PRIVATE_FILE")
    elif mutation == "linked-file":
        client.rename(staged_root / "original-client.py")
        client.symlink_to("original-client.py")
    elif mutation == "hardlink":
        os.link(client, staged_root.parent / "client-alias")
    else:
        client.chmod(0o666)
    before = client.read_bytes()
    with pytest.raises((installer.InstallError, OSError)):
        installer.stage_artifact(payload)
    assert client.read_bytes() == before


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_atomic_publication_never_replaces_existing_destination(installer, tmp_path, kind):
    source, target = tmp_path / "candidate", tmp_path / "destination"
    source.mkdir()
    if kind == "directory":
        target.mkdir()
        (target / "original").write_bytes(b"PRESERVE")
    else:
        target.symlink_to(tmp_path / "never-created")
    fd = installer.open_directory(tmp_path)
    try:
        with pytest.raises(installer.InstallError, match="preserved"):
            installer.publish(fd, source.name, target.name)
    finally:
        os.close(fd)
    assert source.is_dir() and target.is_symlink() == (kind == "symlink")
    if kind == "directory":
        assert (target / "original").read_bytes() == b"PRESERVE"


def child_receipt(installer):
    return {"profile_plugin_link_created": True, "native_loader_passed": True,
            "registered_tools": sorted(installer.TOOLS), "effective_user": "hermes-runtime"}


def test_application_exec_happens_only_after_uid_group_drop_and_nnp(installer, monkeypatch):
    source = Path(installer.__file__).read_bytes()
    def run(command, **options):
        assert command[:4] == ["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env"]
        assert "-i" in command and "-I" in command and "-B" in command
        assert command[command.index("-c") - 3] == str(installer.RELEASE / "venv/bin/python")
        assert "HERMES_HOME=" + str(installer.PROFILE) in command
        assert options["user"] == 993 and options["group"] == 985 and options["extra_groups"] == ()
        assert options["cwd"] == installer.HOME
        compile(command[-1], "child", "exec")
        assert len(command[-1].encode()) < 131072
        return SimpleNamespace(returncode=0, stdout=json.dumps(child_receipt(installer)).encode(), stderr=b"")
    monkeypatch.setattr(installer.subprocess, "run", run)
    assert installer.run_native_child(SimpleNamespace(pw_uid=993, pw_gid=985), source)["native_loader_passed"]


@pytest.mark.parametrize("mutation", ["failure", "extra", "tools", "identity", "link-flag"])
def test_bad_native_receipt_is_refused_without_echoing_private_stderr(installer, monkeypatch, mutation):
    receipt = child_receipt(installer)
    code = 0
    if mutation == "failure": code = 1
    elif mutation == "extra": receipt["unexpected"] = "SYNTHETIC_SECRET"
    elif mutation == "tools": receipt["registered_tools"].pop()
    elif mutation == "identity": receipt["effective_user"] = "root"
    else: receipt["profile_plugin_link_created"] = "yes"
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=code, stdout=json.dumps(receipt).encode(), stderr=b"SYNTHETIC_PRIVATE_ERROR"))
    with pytest.raises(installer.InstallError) as error:
        installer.run_native_child(SimpleNamespace(pw_uid=993, pw_gid=985), b"# source")
    assert "SYNTHETIC" not in str(error.value)


def test_wrong_operator_is_refused_before_any_profile_or_artifact_work(installer, payload, monkeypatch):
    monkeypatch.setattr(installer.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(installer, "stage_artifact", lambda files: pytest.fail("Wrong user must not stage files"))
    with pytest.raises(SystemExit, match="No credential or provider selection was requested"):
        installer.main(payload, b"# source")


@pytest.mark.parametrize("phase", ["provider_registration", "SYNTHETIC_PRIVATE_ERROR"])
def test_child_failure_reports_only_reviewed_phase_labels(installer, monkeypatch, phase):
    raw = json.dumps({"native_loader_passed": False, "failure_stage": phase}).encode()
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stdout=raw, stderr=b"SYNTHETIC_PRIVATE_ERROR"))
    with pytest.raises(installer.InstallError) as error:
        installer.run_native_child(SimpleNamespace(pw_uid=993, pw_gid=985), b"# source")
    assert "SYNTHETIC_PRIVATE" not in str(error.value)
    assert ("provider_registration" in str(error.value)) == (phase == "provider_registration")
