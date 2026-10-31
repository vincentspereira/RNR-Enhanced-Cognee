"""Rotation executor pure-helper tests (invented fixtures)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


executor = load('execute_staged_rotation')


def test_as_pairs_accepts_dict_and_singleton_list():
    assert executor.as_pairs({"a": "x", "b": "y"}) == [("a", "x"), ("b", "y")]
    assert executor.as_pairs([{"a": "x"}]) == [("a", "x")]
    staged = {"api": {"username": "ecmem_api", "password": "p1"},
              "worker": {"username": "ecmem_worker", "password": "p2"},
              "operator": {"username": "ecmem_ops", "password": "p3"}}
    assert executor.as_pairs(staged) == [("ecmem_api", "p1"),
                                         ("ecmem_worker", "p2"),
                                         ("ecmem_ops", "p3")]
    assert executor.as_pairs({"readonly": {"api_key": "k1"},
                              "admin_write": {"api_key": "k2"}}) == \
        [("readonly", "k1"), ("admin_write", "k2")]
    assert executor.as_pairs({"issuer": {"jwt_signing_key": "s"}}) == \
        [("issuer", "s")]
    assert executor.as_pairs({"cache": {"name": "svc", "token": "t"}}) == \
        [("svc", "t")]
    for bad in ([], ["flat"], [{"a": 1}], "string", [{"a": "x", "b": "y"}],
                {"label": {"username": "u", "not_password": "x"}},
                {"both": {"api_key": "a", "secret": "b"}}):
        with pytest.raises(ValueError):
            executor.as_pairs(bad)


def test_dsn_diagnostic_never_carries_values():
    dsn = "postgres://svc:hunter2@127.0.0.1:28434/db?sslmode=disable"
    diagnostic = executor.dsn_diagnostic(dsn)
    assert "hunter2" not in diagnostic
    import json
    parsed = json.loads(diagnostic)
    assert parsed["has_password"] is True and parsed["password_len"] == 7
    assert parsed["query_keys"] == ["sslmode"]


def test_replace_value_in_file_counts_and_refuses_silent_miss(tmp_path):
    target = tmp_path / "cfg.json"
    target.write_text('{"key": "old-secret-value-0123456789"}')
    assert executor.replace_value_in_file(target, "old-secret-value-0123456789",
                                          "new-secret-value-9876543210") == 1
    assert "new-secret-value-9876543210" in target.read_text()
    assert executor.replace_value_in_file(target, "absent", "x") == 0
    assert "absent" not in target.read_text() and "x" not in target.read_text()


def test_leaf_values_walks_nested_configs():
    value = {"a": "x", "b": {"c": "y", "d": ["z", 3]}, "e": None}
    assert sorted(str(v) for v in executor._leaf_values(value)) == \
        sorted(["x", "y", "z", "3", "None"])


def test_backup_is_timestamped_and_idempotent(tmp_path):
    target = tmp_path / "api.json"
    target.write_text('{"v": 1}')
    first = executor.backup(target, "stamp1")
    target.write_text('{"v": 2}')
    again = executor.backup(target, "stamp1")
    assert first == again and first.read_text() == '{"v": 1}'
    other = executor.backup(target, "stamp2")
    assert other is not first and other.read_text() == '{"v": 2}'


def test_arcade_pbkdf2_matches_live_format():
    sample = ("PBKDF2WithHmacSHA256:120000:"
              "c2FsdHNhbHRzYWx0c2FsdA==:aGFzaGhhc2hoYXNo")
    hashed = executor._arcade_pbkdf2("secret", sample)
    parts = hashed.split(":")
    assert parts[0] == "PBKDF2WithHmacSHA256" and parts[1] == "120000"
    assert len(parts) == 4 and parts[2] != sample.split(":")[2]
    with pytest.raises(ValueError):
        executor._arcade_pbkdf2("secret", "not-a-pbkdf2-hash")


def test_families_and_guard_constants():
    assert set(executor.FAMILIES) == {"postgresql", "valkey", "qdrant",
                                      "application"}
    assert executor.PROBE_ROLE_ENV.is_file()
