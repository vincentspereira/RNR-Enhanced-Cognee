"""Metadata-only migration observations; never real profile access."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/inventory_profile_migration.py'
spec = importlib.util.spec_from_file_location('migration_inventory', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def observe(path, **kwargs):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        return helper.metadata_tree(fd, os.geteuid(), **kwargs)
    finally:
        os.close(fd)


def test_headers_and_sizes_only_without_sqlite_connections(tmp_path, monkeypatch):
    with sqlite3.connect(tmp_path / 'invented.db') as database:
        database.execute('CREATE TABLE invented(x)')
    (tmp_path / 'private.txt').write_text('invented-secret-not-exported')
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('inventory opened SQLite'))
    result = observe(tmp_path)
    assert result['files'] == 2 and result['sqlite_databases'] == 1
    assert result['copy_admission_qualified'] is False
    assert 'invented-secret' not in json.dumps(result)


def test_unknown_links_and_excluded_project_not_followed(tmp_path):
    directory = tmp_path / 'legal-social-frameworks'
    directory.mkdir()
    (directory / 'excluded.txt').write_text('invented-excluded')
    (tmp_path / 'redirect').symlink_to(directory, target_is_directory=True)
    result = observe(tmp_path)
    assert result['unknown_links'] == 1 and result['excluded_entries'] == 1
    assert result['files'] == 0 and result['directories'] == 0


def test_main_does_not_double_count_nested_profiles(tmp_path):
    (tmp_path / 'profiles').mkdir()
    (tmp_path / 'profiles/private').write_text('invented')
    result = observe(tmp_path, skip_profiles=True)
    assert result['separately_inventoried_profiles'] == 1 and result['files'] == 0


def test_budget_failure_is_explicit(tmp_path, monkeypatch):
    (tmp_path / 'one').touch()
    monkeypatch.setattr(helper, 'LIMIT', 0)
    with pytest.raises(ValueError):
        observe(tmp_path)


def test_root_inventory_refused_before_access(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 0)
    with pytest.raises(ValueError):
        helper.main()
