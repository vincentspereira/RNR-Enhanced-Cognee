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


def table_fixture(module, environment, monkeypatch, raw, committed):
    site = environment / "lib/python3.14/site-packages"
    site.mkdir(parents=True)
    (site / "__editable__fixture_finder.py").write_text(raw)
    tree = b"".join(b"100644 blob " + b"a" * 40 + b"\t" + name.encode() + b"\0"
                    for name in committed)
    def git(*args):
        assert args == ("ls-tree", "-r", "-z", module.EXPECTED_REVISION)
        return tree
    monkeypatch.setattr(module, "git", git)


def test_table_diagnosis_discloses_only_committed_names_and_never_executes_code(inspector, monkeypatch, tmp_path):
    module, environment = inspector
    sentinel = tmp_path / "never-execute"
    raw = (
        "MAPPING = {'hermes_cli': '/old/root/hermes_cli', "
        "'helper-backup': '/old/root/helper-backup', "
        "'helper.old': '/old/root/helper.old', "
        "'PRIVATE_UNKNOWN_KEY': '/private/root/PRIVATE_UNKNOWN_TARGET'}\n"
        "NAMESPACES = {}\n"
        f"__import__('pathlib').Path({str(sentinel)!r}).touch()\n"
    )
    table_fixture(module, environment, monkeypatch, raw,
                  ["hermes_cli/__init__.py", "helper-backup.py", "helper.old.py"])
    result = module.editable_table_audit(environment)["editable_tables"][0]
    assert result["entries_checked"] == 4
    rows = result["problem_entries"]
    assert len(rows) == 3
    assert rows[0]["public_module"] == "helper-backup"
    assert rows[0]["problems"] == ["nonstandard_module_name"]
    assert rows[0]["target_matches_flat_root_module"] is True
    assert rows[1]["public_module"] == "helper.old"
    assert "declared_module_suffix_mismatch" in rows[1]["problems"]
    assert rows[2]["module"] == "redacted_not_in_commit"
    output = json.dumps(result)
    assert "PRIVATE_UNKNOWN" not in output and "/old/root" not in output
    assert not sentinel.exists()
    assert not (tmp_path / "old/root").exists()


def test_duplicate_keys_nonliteral_paths_and_unbound_home_references_are_reported(inspector, monkeypatch):
    module, environment = inspector
    raw = (
        "MAPPING = {'agent': '/old/root/agent', 'agent': '/old/root/agent', "
        "'hermes_cli': call_that_must_not_run()}\n"
        f"UNRELATED = {str(module.HOME / 'PRIVATE_STRAY_PATH')!r}\n"
    )
    table_fixture(module, environment, monkeypatch, raw, ["agent/__init__.py", "hermes_cli/__init__.py"])
    result = module.editable_table_audit(environment)["editable_tables"][0]
    assert result["unbound_home_path_count"] == 1
    assert result["problem_entries"][0]["problems"] == ["duplicate_module_name"]
    assert result["problem_entries"][1]["problems"] == ["nonliteral_import_path"]
    assert "PRIVATE_STRAY_PATH" not in json.dumps(result)


@pytest.mark.parametrize("name", ["", ".", "..", "../escape", "a/b", "a\\b"])
def test_invalid_names_are_reported_without_crashing_or_exposing_unknown_keys(inspector, monkeypatch, name):
    module, environment = inspector
    raw = f"MAPPING = {{{name!r}: '/old/root/module.py'}}\n"
    table_fixture(module, environment, monkeypatch, raw, ["hermes_cli/__init__.py"])
    result = module.editable_table_audit(environment)["editable_tables"][0]
    assert result["problem_entry_count"] == 1
    assert result["problem_entries"][0]["module"] == "redacted_not_in_commit"
    assert "public_module" not in result["problem_entries"][0]


def test_table_audit_reports_all_problem_counts_and_truncation(inspector, monkeypatch):
    module, environment = inspector
    raw = "MAPPING = {" + ",".join(f"'private-{i}': '/old/root/private-{i}'" for i in range(45)) + "}\n"
    table_fixture(module, environment, monkeypatch, raw, ["hermes_cli/__init__.py"])
    result = module.editable_table_audit(environment)["editable_tables"][0]
    assert result["problem_entry_count"] == 45
    assert len(result["problem_entries"]) == 40 and result["problems_truncated"] is True


def test_table_diagnosis_rejects_a_linked_finder_and_missing_finder(inspector, monkeypatch, tmp_path):
    module, environment = inspector
    table_fixture(module, environment, monkeypatch, "MAPPING = {}\n", ["hermes_cli/__init__.py"])
    site = environment / "lib/python3.14/site-packages"
    finder = site / "__editable__fixture_finder.py"
    retained = tmp_path / "original.retained"
    finder.rename(retained)
    with pytest.raises(module.InspectionError, match="missing"):
        module.editable_table_audit(environment)
    finder.symlink_to(retained)
    with pytest.raises(module.InspectionError, match="link"):
        module.editable_table_audit(environment)
