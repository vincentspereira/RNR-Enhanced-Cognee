"""Allowlisted local declarations, without credential or raw configuration output."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def inventory():
    path = Path("integrations/hermes/deployment/inspect_local_model_routes.py").resolve()
    spec = importlib.util.spec_from_file_location("local_route_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value,expected", [
    ("http://127.0.0.1:8000/v1", "http://127.0.0.1:8000/v1"),
    ("http://localhost:1234/v1/", "http://localhost:1234/v1"),
    ("https://[::1]:443/", "https://[::1]:443"),
    ("http://remote.example/v1", None), ("http://192.168.1.5:8000/v1", None),
    ("http://user:PRIVATE@127.0.0.1/v1", None), ("http://127.0.0.1/v1?key=PRIVATE", None),
    ("http://127.0.0.1/v1#PRIVATE", None), ("http://127.0.0.1/v1?", None),
    ("http://127.0.0.1:99999/v1", None), ("file:///etc/PRIVATE", None),
    ("http://127.0.0.1/private/path", None), ("http://127.0.0.1:0/v1", None),
    ("http://127.0.0.1/v1\nPRIVATE", None), (None, None)])
def test_only_explicit_credential_free_loopback_origins_are_reported(inventory, value, expected):
    assert inventory.local_origin(value) == expected


@pytest.mark.parametrize("value", ["sk-proj-1234567890abcdefgh", "ghp_1234567890abcdefgh",
                                  "AKIA1234567890ABCDEF", "AGE-SECRET-KEY-1ABCDEF",
                                  "aaaaaaaaaaaaaaaa.bbbbbbbbbbbbbbbb.cccccccccccccccc",
                                  "model\nPRIVATE", "https://user:PRIVATE@host", {"private": "value"}])
def test_credential_shapes_or_unsafe_model_strings_are_not_output(inventory, value):
    assert inventory.public_model(value) is None


def test_only_declared_local_metadata_leaves_summary(inventory):
    config = {"model": {"provider": "custom:local", "default": "unsloth/local-model"},
              "custom_providers": [{"name": "local", "base_url": "http://localhost:8000/v1",
                                    "models": {"unsloth/local-model": {"context_length": 65536}},
                                    "key_env": "PRIVATE_KEY_REFERENCE", "api_key": "PRIVATE_KEY_VALUE",
                                    "extra_headers": {"Authorization": "Bearer PRIVATE_HEADER"},
                                    "api_mode": "chat_completions"},
                                   {"name": "cloud", "base_url": "https://cloud.example/v1",
                                    "api_key": "PRIVATE_CLOUD_KEY"}],
              "private_notebook": "PRIVATE_NOTE", "fallback_model": {"api_key": "PRIVATE_FALLBACK"}}
    rows = inventory.summarize(config)
    assert len(rows) == 1
    assert rows[0] == {"route": "custom_1", "base_url": "http://localhost:8000/v1",
                       "models": [{"id": "unsloth/local-model", "configured_context_length": 65536}],
                       "api_mode": "chat_completions", "credential_reference_present": True,
                       "extra_headers_present": True}
    assert "PRIVATE" not in json.dumps(rows)
    assert "cloud.example" not in json.dumps(rows)


def test_selected_local_route_and_unknown_context_are_not_fabricated(inventory):
    rows = inventory.summarize({"model": {"base_url": "http://127.0.0.1:8000/v1",
                                         "default": "unsloth/local-model", "context_length": True}})
    assert rows[0]["route"] == "selected_model"
    assert rows[0]["models"] == [{"id": "unsloth/local-model", "configured_context_length": None}]
    assert rows[0]["api_mode"] is None


def test_provider_dictionary_list_catalog_and_bad_modes_are_handled(inventory):
    rows = inventory.summarize({"providers": {"private-provider-name": {
        "baseUrl": "http://localhost:8000/v1", "api_mode": ["bad"],
        "models": ["safe-model", {"id": "safe-second", "context_length": 32768}]}}})
    assert rows[0]["route"] == "provider_1" and rows[0]["api_mode"] is None
    assert rows[0]["models"] == [{"id": "safe-model", "configured_context_length": None},
                                 {"id": "safe-second", "configured_context_length": 32768}]
    assert "private-provider-name" not in json.dumps(rows)


def test_catalog_and_settings_boundaries_are_bounded(inventory):
    models = ["safe-model-" + str(i) for i in range(100)]
    rows = inventory.summarize({"custom_providers": [{"base_url": "http://localhost/v1", "models": models}]})
    assert len(rows[0]["models"]) == 16
    assert inventory.summarize(None) == []
    assert {p.name for p in inventory.SOURCES.values()} == {"config.yaml"}
    assert len(inventory.SOURCES) == 3


def test_wrong_identity_stops_before_private_source_reads(inventory, monkeypatch, capsys):
    from types import SimpleNamespace
    monkeypatch.setattr(inventory.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="wrong", pw_uid=0))
    monkeypatch.setattr(inventory, "read_config", lambda *args: pytest.fail("No source read permitted"))
    with pytest.raises(SystemExit, match="no private details printed"):
        inventory.main()
    assert not capsys.readouterr().out


@pytest.mark.parametrize("value,expected", [
    ("https://api.z.ai/api/coding/paas/v4/", ("https://api.z.ai/api/coding/paas/v4", "coding_chat_completions")),
    ("https://api.z.ai:443/api/anthropic", ("https://api.z.ai/api/anthropic", "coding_anthropic_messages")),
    ("https://api.z.ai/api/v1", ("https://api.z.ai/api/v1", "coding_responses")),
    ("https://api.z.ai/api/paas/v4", ("https://api.z.ai/api/paas/v4", "general_api_not_coding")),
    ("http://api.z.ai/api/coding/paas/v4", None),
    ("https://api.z.ai.evil.example/api/coding/paas/v4", None),
    ("https://user:PRIVATE@api.z.ai/api/coding/paas/v4", None),
    ("https://api.z.ai/api/coding/paas/v4?token=PRIVATE", None),
    ("https://api.z.ai/api/coding/paas/v4#PRIVATE", None),
    ("https://api.z.ai:444/api/coding/paas/v4", None),
    ("https://api.z.ai/api/unknown", None), (None, None)])
def test_zai_endpoint_inspection_distinguishes_plan_and_general_without_secrets(inventory, value, expected):
    assert inventory.zai_origin(value) == expected


def test_zai_summary_reports_only_public_fields_and_preserves_current_model(inventory):
    config = {"model": {"default": "other-model", "provider": "zai"},
              "custom_providers": [{"name": "PRIVATE_PROVIDER_NAME", "base_url": "https://api.z.ai/api/coding/paas/v4",
                                    "key_env": "PRIVATE_KEY_REFERENCE", "api_key": "PRIVATE_KEY_VALUE",
                                    "extra_headers": {"Authorization": "Bearer PRIVATE_HEADER"},
                                    "models": ["glm-5.3-flash", "glm-5.3", "another-provider-model"],
                                    "api_mode": "chat_completions", "context_length": 1000000}],
              "private_note": "PRIVATE_NOTE", "fallback_model": {"api_key": "PRIVATE_FALLBACK"}}
    before = json.dumps(config)
    result = inventory.summarize_zai(config)
    assert result["current_default_model"] == "other-model"
    assert result["current_default_matches_requested_test_model"] is False
    assert result["selected_provider_is_builtin_zai"] is True
    assert result["selected_explicit_zai_endpoint_kind"] is None
    assert result["zai_routes"] == [{
        "route": "custom_1", "base_url": "https://api.z.ai/api/coding/paas/v4",
        "endpoint_kind": "coding_chat_completions", "declared_glm_models": ["glm-5.3-flash", "glm-5.3"],
        "configured_context_length": 1000000, "api_mode": "chat_completions",
        "credential_reference_present": True, "inline_credential_field_present": True,
        "extra_headers_present": True}]
    assert "PRIVATE" not in json.dumps(result)
    assert json.dumps(config) == before


@pytest.mark.parametrize("provider", ["zai", "glm", "z-ai", "z.ai", "zhipu"])
def test_builtin_zai_aliases_do_not_invent_endpoint_or_credential_access(inventory, provider):
    result = inventory.summarize_zai({"model": {"provider": provider, "default": "glm-5.3-flash"}})
    assert result["selected_provider_is_builtin_zai"] is True
    assert result["current_default_matches_requested_test_model"] is True
    assert result["selected_explicit_zai_endpoint_kind"] is None and result["zai_routes"] == []


def test_display_case_does_not_falsely_report_a_different_model(inventory):
    result = inventory.summarize_zai({"model": {"provider": "zai", "default": "GLM-5.3-Flash"}})
    assert result["current_default_model"] == "GLM-5.3-Flash"
    assert result["current_default_matches_requested_test_model"] is True


def test_zai_provider_map_camel_fields_unknown_context_and_unsafe_origins(inventory):
    result = inventory.summarize_zai({"model": {"default": "glm-5.3-flash", "base_url": "https://api.z.ai/api/v1"},
        "providers": {"PRIVATE_PROVIDER_NAME": {"baseUrl": "https://api.z.ai/api/coding/paas/v4",
                      "keyEnv": "PRIVATE_REFERENCE", "models": {"glm-5.3-flash": {}}, "context_length": True},
                      "unsafe": {"base_url": "https://api.z.ai/api/v1?key=PRIVATE"}}})
    assert result["selected_explicit_zai_endpoint_kind"] == "coding_responses"
    assert len(result["zai_routes"]) == 2
    assert result["zai_routes"][1]["credential_reference_present"] is True
    assert result["zai_routes"][1]["configured_context_length"] is None
    assert "PRIVATE" not in json.dumps(result)


def test_zai_mode_reads_main_only_without_startup_network_or_writes(inventory, monkeypatch, capsys):
    from types import SimpleNamespace
    import sys
    monkeypatch.setattr(inventory.pwd, "getpwuid", lambda uid: SimpleNamespace(
        pw_name="vincentspereira", pw_uid=1000, pw_dir=str(inventory.HOME)))
    monkeypatch.setattr(inventory, "RELEASE", Path(sys.executable).resolve().parent)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Hermes")
    monkeypatch.setattr(inventory.os, "chdir", lambda path: None)
    reads = []
    def read(path, uid):
        reads.append(path)
        return {"model": {"provider": "zai", "default": "glm-5.3-flash"}}
    monkeypatch.setattr(inventory, "read_config", read)
    inventory.main(zai_only=True)
    result = json.loads(capsys.readouterr().out)
    assert reads == [inventory.SOURCES["main"]]
    assert result["inspection_mode"] == "zai_coding_plan" and result["complete"] is True
    for field in ("model_defaults_changed", "env_or_secret_store_files_read", "network_requests", "model_called", "files_changed"):
        assert result[field] is False
