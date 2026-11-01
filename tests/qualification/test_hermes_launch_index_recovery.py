"""Installed recovery may contact only the selected local store ports."""
import importlib.util
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_indexes.py"
spec = importlib.util.spec_from_file_location("launch_index_recovery", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_structure_inspection_cannot_read_arbitrary_protected_files():
    with pytest.raises(ValueError, match="structure_path_refused"):
        helper.retained_structure(Path("/etc/enhanced-cognee/operator.json"))


@pytest.mark.parametrize("rules,allowed", [
    ("~ec:live:*", False), ("~ec:*", True), ("~ec:* resetkeys ~ec:live:*", False),
    ("%R~ec:*", False), ("%W~ec:*", True), ("allkeys", True)])
def test_cache_policy_distinguishes_read_only_and_other_namespace(rules, allowed):
    raw = "user invented on >invented-private-password "+rules+" +get +set"
    report = helper.cache_write_namespace_policy(raw, "invented", "lr_0123456789abcdef")
    assert report["configured_cache_new_namespace_pattern_matches"] is allowed
    assert report["configured_cache_user_found"] is True
    assert report["effective_acl_verified"] is False
    assert "invented-private-password" not in str(report)


def test_delivery_diagnostic_never_contains_error_message_or_private_values():
    error = ValueError("invented-private-record-content")
    assert helper.delivery_failure_metadata(error) == {"kind":"ValueError", "source_frames":[]}


def test_hashed_password_token_does_not_hide_later_cache_key_rules():
    digest = "a"*64
    raw = "# comment\nuser invented on #"+digest+" ~ec:* -@all +get +set"
    report = helper.cache_write_namespace_policy(raw, "invented", "lr_0123456789abcdef")
    assert report["configured_cache_write_key_pattern_count"] == 1
    assert report["configured_cache_new_namespace_pattern_matches"] is True
    assert digest not in str(report)


@pytest.mark.parametrize("url,schemes,port", [
    ("https://example.invalid:28535", {"http", "https"}, 28535),
    ("http://127.0.0.1:6333", {"http", "https"}, 28535),
    ("redis://127.0.0.1:6379", {"redis", "rediss"}, 28537),
    ("file:///private", {"http", "https"}, 28535),
    ("http://127.0.0.1:28536", {"redis", "rediss"}, 28536),
])
def test_external_or_different_service_binding_refused(url, schemes, port):
    with pytest.raises(ValueError, match="local_store_binding_required"):
        helper.local(url, schemes, port)


@pytest.mark.parametrize("url,schemes,port", [
    ("http://127.0.0.1:28535", {"http", "https"}, 28535),
    ("http://localhost:28536", {"http", "https"}, 28536),
    ("redis://invented:synthetic@127.0.0.1:28537/0", {"redis", "rediss"}, 28537),
])
def test_exact_selected_local_binding_admitted(url, schemes, port):
    assert helper.local(url, schemes, port) == url


@pytest.mark.parametrize("path", ["/home/agent/index.json", "/tmp/index.json", "relative.json"])
def test_agent_controlled_settings_location_refused(path):
    with pytest.raises(ValueError, match="protected_index_settings_required"):
        helper.protected_settings(Path(path))


@pytest.mark.parametrize("uid,mode,reason", [
    (1000, stat.S_IFDIR | 0o700, "non_root_owner"),
    (0, stat.S_IFDIR | 0o775, "group_or_other_writable"),
    (0, stat.S_IFLNK | 0o777, "symlink"),
])
def test_diagnostic_stops_before_entering_untrusted_ancestor(monkeypatch, uid, mode, reason):
    selected = Path("/opt/enhanced-cognee-memory/invented/config.json")
    boundary = selected.parent
    visited = []
    def metadata(path):
        visited.append(path)
        if path == boundary:
            return SimpleNamespace(st_uid=uid, st_mode=mode, st_size=0)
        if path == selected:
            pytest.fail("Entered untrusted settings ancestor")
        return SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755, st_size=0)
    monkeypatch.setattr(Path, "lstat", metadata)
    report = helper.settings_protection(selected)
    assert report["accepted"] is False
    assert report["reason"] == reason
    assert selected not in visited


def test_effective_systemd_mapping_selects_exact_operator_source():
    configured = Path("/run/credentials/enhanced-cognee-index.service/index.json")
    binding = {"type": "a(ss)", "data": [["worker.json", "/etc/enhanced-cognee/worker.json"],
               ["index.json", "/etc/enhanced-cognee/index.json"]]}
    assert helper.credential_source(configured, binding) == Path("/etc/enhanced-cognee/index.json")


@pytest.mark.parametrize("data", [
    [["index.json", "/home/agent/index.json"]],
    [["other.json", "/etc/enhanced-cognee/index.json"]],
    [["index.json", "/etc/enhanced-cognee/index.json"], ["index.json", "/etc/enhanced-cognee/index.json"]],
    [],
])
def test_wrong_or_ambiguous_credential_source_refused(data):
    with pytest.raises(ValueError, match="service_index_credential_binding_unverified"):
        helper.credential_source(Path("/run/credentials/enhanced-cognee-index.service/index.json"),
                                 {"type": "a(ss)", "data": data})


def test_other_service_mount_not_substituted():
    with pytest.raises(ValueError, match="service_index_credential_binding_unverified"):
        helper.credential_source(Path("/run/credentials/other.service/index.json"),
            {"type": "a(ss)", "data": [["index.json", "/etc/enhanced-cognee/index.json"]]})


def authority():
    return {"qdrant_url": "http://127.0.0.1:28535", "arcade_url": "http://127.0.0.1:28536",
            "arcade_user": "invented_operator", "arcade_password": "invented-only-not-live",
            "cache_url": "redis://invented:synthetic@127.0.0.1:28537/0"}


def test_retained_authority_uses_only_reviewed_credential_fields():
    selected = authority()
    result = helper.authority_fields(selected, selected)
    assert set(result) == {"INDEX_ARCADEDB_USER", "INDEX_ARCADEDB_PASSWORD", "INDEX_VALKEY_URL"}
    assert "ENHANCED_JWT_SECRET" not in result
    assert "ENHANCED_MEMORY_DATABASE_URL" not in result


def test_retained_credentials_cannot_redirect_selected_store():
    selected, active = authority(), authority()
    selected["arcade_url"] = "http://127.0.0.1:2480"
    with pytest.raises(ValueError, match="retained_authority_store_binding_differs"):
        helper.authority_fields(selected, active)


def test_retained_remote_cache_is_not_contacted():
    selected = authority()
    selected["cache_url"] = "redis://example.invalid:28537/0"
    with pytest.raises(ValueError, match="local_store_binding_required"):
        helper.authority_fields(selected, selected)


def test_incomplete_retained_authority_is_not_guessed():
    with pytest.raises(ValueError, match="retained_authority_contract_unavailable"):
        helper.authority_fields({"password": "invented-only"}, authority())


@pytest.mark.parametrize("path", ["/home/agent/settings.json", "/tmp/settings.json",
    "/root/cognee-protected-continuation-20261020T190055Z/../other.json"])
def test_retained_reference_must_stay_in_explicit_operator_archive(path):
    with pytest.raises(ValueError, match="retained_authority_path_refused"):
        helper.retained_json(Path(path))


def test_identical_retained_copies_do_not_require_credential_trials():
    document = authority()
    report = {}
    selected = helper.unique_authority([(Path("one.json"), document), (Path("two.json"), document)], document, report)
    assert selected["INDEX_ARCADEDB_USER"] == "invented_operator"
    assert report["retained_authority_candidate_paths"] == ["one.json", "two.json"]
    assert "invented-only-not-live" not in str(report)


def test_conflicting_retained_credentials_require_operator_review():
    first, second = authority(), authority()
    second["arcade_password"] = "other-invented-not-live"
    report = {}
    with pytest.raises(ValueError, match="retained_authority_missing_or_ambiguous"):
        helper.unique_authority([(Path("one.json"), first), (Path("two.json"), second)], first, report)
    assert "other-invented-not-live" not in str(report)


def test_no_supported_retained_store_config_is_not_an_authority_pass():
    with pytest.raises(ValueError, match="retained_authority_missing_or_ambiguous"):
        helper.unique_authority([(Path("database-only.json"), {"RNR_QUALIFICATION_DATABASE_URL": "invented"})], authority(), {})


def test_schema_metadata_never_contains_values_or_token_shaped_keys():
    data = {"arcade_password": "invented-private-value", "roles": ["invented"],
            "private conversation text": "not emitted", "ghp_" + "invented_token_key": "not emitted"}
    result = helper.safe_field_names(data)
    assert result == ["arcade_password", "roles"]
    assert "invented-private-value" not in str(result)


def test_non_object_is_not_dumped_as_metadata():
    assert helper.safe_field_names(["invented-private-value"]) == []
