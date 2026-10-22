"""Read-only diagnostics must distinguish links from editable package paths."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def inspector(monkeypatch, tmp_path):
    path = Path("integrations/hermes/deployment/inspect_restricted_runtime.py").resolve()
    spec = importlib.util.spec_from_file_location("link_inspector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = tmp_path / "home"
    monkeypatch.setattr(module, "HOME", home)
    monkeypatch.setattr(module, "SOURCE", home / "source")
    monkeypatch.setattr(module, "PYTHON", home / "python")
    for root in (module.SOURCE, module.PYTHON):
        root.mkdir(parents=True)
    return module, home / "venv"


def test_link_and_editable_escape_are_separate_and_no_code_executes(inspector, monkeypatch, tmp_path):
    module, environment = inspector
    site = environment / "lib/python3.14/site-packages"
    site.mkdir(parents=True)
    sentinel = tmp_path / "must-not-exist"
    finder = site / "__editable__fixture_finder.py"
    secret_path = str(module.HOME / "private-do-not-print-token")
    finder.write_text(
        f"MAPPING = {{'module': {str(module.SOURCE / 'module')!r}, 'bad': {secret_path!r}}}\n"
        f"__import__('pathlib').Path({str(sentinel)!r}).touch()\n"
    )
    (environment / "python").symlink_to(module.PYTHON / "bin/python")
    (module.PYTHON / "external").symlink_to("/usr/bin/fixture-python")
    oid = b"a" * 40
    calls = []
    def git(*args):
        calls.append(args)
        if args[0] == "ls-tree":
            return b"120000 blob " + oid + b"\tpublic-link\0"
        assert args == ("cat-file", "blob", oid.decode())
        return b"../../private-do-not-print-token"
    monkeypatch.setattr(module, "git", git)
    result = module.link_audit(environment)
    assert result["links_inspected"] == {
        "hermes_source": 1, "managed_python": 1, "selected_environment": 1}
    assert result["external_link_count"] == 2
    assert len(result["editable_paths"]) == 2
    assert result["editable_paths"][0]["reference"]["kind"] == "hermes_source"
    assert result["editable_paths"][1]["reference"]["area"] == "other_operator_home"
    assert "private-do-not-print-token" not in json.dumps(result)
    assert not sentinel.exists()
    assert finder.read_text().startswith("MAPPING")


def test_directory_links_are_not_followed_and_dangling_links_are_visible(inspector, tmp_path):
    module, environment = inspector
    environment.mkdir()
    external = tmp_path / "outside"
    external.mkdir()
    (external / "hidden-link").symlink_to("/etc/shadow")
    (environment / "linked-directory").symlink_to(external, target_is_directory=True)
    (environment / "dangling").symlink_to("missing-target")
    result = dict(module.runtime_links(environment))
    assert set(result) == {"linked-directory", "dangling"}
    assert not list(external.glob("*new*"))


@pytest.mark.parametrize("relative,expected", [
    ("../private", "outside_selected_runtime"),
    ("module/../../private", "outside_selected_runtime"),
    ("module/../valid", "hermes_source"),
])
def test_lexical_check_matches_preparer_normalization(inspector, relative, expected):
    module, environment = inspector
    result = module.lexical_location(module.SOURCE / relative, environment)
    assert result["kind"] == expected


def test_malformed_git_object_is_not_used_as_an_argument(inspector, monkeypatch):
    module, environment = inspector
    monkeypatch.setattr(module, "git", lambda *args: b"120000 blob --unsafe\tlink\0")
    with pytest.raises(module.InspectionError, match="unexpected metadata"):
        module.link_audit(environment)


def test_missing_program_tree_cannot_be_reported_as_inspected(inspector):
    module, environment = inspector
    with pytest.raises(module.InspectionError, match="could not be inspected"):
        list(module.runtime_links(environment))
