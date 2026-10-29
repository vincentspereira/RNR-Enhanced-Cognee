"""The full-run gate must reject incomplete evidence and keep raw logs private."""
import importlib.util
import json
from pathlib import Path
import stat
import types

import pytest


@pytest.fixture
def runner(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[2] / "tests/qualification/run_complete.py"
    spec = importlib.util.spec_from_file_location("complete_memory_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = tmp_path / "checkout"
    for name in ("clients/node/dist/index.js", "dashboard/nextjs-dashboard/.next/BUILD_ID"):
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic build fixture", encoding="ascii")
    monkeypatch.setattr(module, "REPOSITORY_ROOT", repo)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/synthetic/tools/" + name)
    for name in ("RNR_QUALIFICATION_DATABASE_URL", "RNR_QUALIFICATION_MODEL_CACHE", "RNR_QUALIFICATION_INDEX_SETTINGS"):
        monkeypatch.setenv(name, "synthetic-only-" + name)
    return module, repo, tmp_path / "private-results"


@pytest.mark.parametrize(("xml", "exit_code", "expected"), [
    ('<testsuites><testsuite tests="3" failures="0" errors="0" skipped="0"/></testsuites>', 0, 0),
    ('<testsuites><testsuite tests="3" failures="0" errors="0" skipped="1"/></testsuites>', 0, 1),
    ('<testsuites><testsuite tests="3" failures="1" errors="0" skipped="0"/></testsuites>', 0, 1),
    ('<testsuites><testsuite tests="3" failures="0" errors="1" skipped="0"/></testsuites>', 0, 1),
    ('<testsuites><testsuite tests="3" failures="0" errors="0" skipped="0"/></testsuites>', 2, 1),
    ('<testsuites><testsuite tests="0"/></testsuites>', 0, 1),
    ('<testsuites><testsuite tests="1" skipped="-1"/></testsuites>', 0, 1),
    ('<testsuites><testsuite tests="1" skipped="2"/></testsuites>', 0, 1),
    ('<malformed', 0, 1),
    (None, 0, 1),
])
def test_complete_gate_rejects_incomplete_or_invalid_reports(runner, monkeypatch, capsys, xml, exit_code, expected):
    module, repo, artifacts = runner

    def execute(command, **kwargs):
        assert kwargs["cwd"] == repo
        env = kwargs["env"]
        assert env["RNR_QUALIFICATION_CROSS_LANGUAGE"] == env["RNR_QUALIFICATION_BROWSER"] == "1"
        assert env["ENHANCED_LOAD_DOTENV"] == env["COGNEE_TELEMETRY_ENABLED"] == "0"
        kwargs["stdout"].write("synthetic-only-private-diagnostic\n")
        if xml is not None:
            Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--junitxml="))).write_text(xml)
        return types.SimpleNamespace(returncode=exit_code)

    monkeypatch.setattr(module.subprocess, "run", execute)
    assert module.main(["--artifacts", str(artifacts)]) == expected
    assert stat.S_IMODE(artifacts.stat().st_mode) == 0o700
    assert "synthetic-only-private-diagnostic" not in capsys.readouterr().out
    summary = artifacts / "summary.json"
    if summary.is_file():
        assert json.loads(summary.read_text())["complete"] == (expected == 0)


@pytest.mark.parametrize("through_symlink", [False, True])
def test_raw_artifacts_cannot_be_written_inside_checkout(runner, monkeypatch, tmp_path, through_symlink):
    module, repo, artifacts = runner
    if through_symlink:
        alias = tmp_path / "checkout-alias"
        alias.symlink_to(repo, target_is_directory=True)
        artifacts = alias / "private-logs"
    else:
        artifacts = repo / "private-logs"
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: pytest.fail("Must refuse before tests run"))
    with pytest.raises(SystemExit) as exc:
        module.main(["--artifacts", str(artifacts)])
    assert exc.value.code == 2 and not artifacts.exists()


def test_existing_artifacts_are_preserved(runner, monkeypatch):
    module, repo, artifacts = runner
    artifacts.mkdir()
    marker = artifacts / "pytest.log"
    marker.write_text("retained earlier evidence")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: pytest.fail("Must preserve earlier run"))
    with pytest.raises(FileExistsError):
        module.main(["--artifacts", str(artifacts)])
    assert marker.read_text() == "retained earlier evidence"


def test_backup_tools_are_required_before_starting(runner, monkeypatch):
    module, repo, artifacts = runner
    monkeypatch.setattr(module.shutil, "which", lambda name: None if name == "age" else "/synthetic/tools/" + name)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: pytest.fail("Missing tool must stop execution"))
    with pytest.raises(SystemExit) as exc:
        module.main(["--artifacts", str(artifacts)])
    assert exc.value.code == 2 and not artifacts.exists()
