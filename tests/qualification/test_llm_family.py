"""Stage D families 3-4 tests (pure cores, invented fixtures)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / 'src'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


llm = load('llm_summarize')


def test_detect_language_by_script():
    assert llm.detect_language("plain english text")["language"] == "en"
    assert llm.detect_language("hello world")["script"] == "latin"
    assert llm.detect_language("\u5efa\u8bbe\u8ba1\u5212")["language"] == "zh"
    assert llm.detect_language("\u3051\u3093\u305b\u3064\u3051\u3044\u304b")["language"] == "ja"
    assert llm.detect_language("\uac74\uc124 \uacc4\ud68d")["language"] == "ko"
    assert llm.detect_language("\u043f\u043b\u0430\u043d \u0441\u0442\u0440\u043e\u0438\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430")["language"] == "ru"
    assert llm.detect_language("\u062e\u0637\u0629 \u0627\u0644\u0628\u0646\u0627\u0621")["language"] == "ar"
    with pytest.raises(llm.LlmUnavailable):
        llm.detect_language("   ")


def test_token_budget_allow_charge_and_daily_reset():
    budget = llm.TokenBudget()
    route = {"daily_token_cap": 1000}
    assert budget.allows(route, "proj", 999) is True
    budget.charge("proj", 600)
    assert budget.used("proj") == 600
    assert budget.allows(route, "proj", 500) is False
    assert budget.allows(route, "proj", 400) is True
    budget.charge("proj", -50)  # negative charges are ignored
    assert budget.used("proj") == 600


def test_route_loading_validation(tmp_path):
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    (good_dir / "llm.json").write_text(
        '{"base_url": "https://api.example.test/v4", "api_key": "k",'
        ' "model": "m", "daily_token_cap": 2000}')
    route = llm.load_route(str(good_dir))
    assert route["model"] == "m" and route["daily_token_cap"] == 2000
    assert llm.load_route(None) is None
    assert llm.load_route(str(tmp_path / "missing")) is None
    insecure_dir = tmp_path / "insecure"
    insecure_dir.mkdir()
    (insecure_dir / "llm.json").write_text(
        '{"base_url": "http://insecure.test", "api_key": "k", "model": "m"}')
    with pytest.raises(llm.LlmUnavailable):
        llm.load_route(str(insecure_dir))
    partial_dir = tmp_path / "partial"
    partial_dir.mkdir()
    (partial_dir / "llm.json").write_text('{"base_url": "https://x.test", "model": "m"}')
    with pytest.raises(llm.LlmUnavailable):
        llm.load_route(str(partial_dir))


def test_prompt_builders_bounds():
    records = [{"id": "r%d" % i, "content": "fact number %d" % i}
               for i in range(500)]
    messages = llm.summarize_messages(records, "test topic")
    assert len(messages) == 2 and "test topic" in messages[1]["content"]
    assert len(messages[1]["content"]) <= llm.MAX_PROMPT_CHARS + 500
    with pytest.raises(llm.LlmUnavailable):
        llm.summarize_messages([], None)
    consolidation = llm.consolidation_messages(records[:5])
    assert "Records:" in consolidation[1]["content"]
    with pytest.raises(llm.LlmUnavailable):
        llm.consolidation_messages([{"id": "only"}])


def test_parse_consolidation_strict_json():
    reply = 'Here: {"groups": [["a","b"],["c","d","e"]]} done'
    assert llm.parse_consolidation(reply) == {"groups": [["a", "b"], ["c", "d", "e"]]}
    assert llm.parse_consolidation("no json here") == {"groups": []}
    assert llm.parse_consolidation('{"groups": ["not","lists"]}') == {"groups": []}
    assert llm.parse_consolidation('{"groups": [[1,2]]}') == {"groups": []}


def test_daemon_loads_llm_route_into_whitelisted_env(tmp_path, monkeypatch):
    import json as _json
    daemon = None
    spec = importlib.util.spec_from_file_location(
        "memory_daemon", SRC.parent / "src" / "memory_daemon.py")
    daemon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daemon)
    api = {"ENHANCED_MEMORY_DATABASE_URL": "postgres://invented",
           "ENHANCED_JWT_SECRET": "x" * 40}
    (tmp_path / "api.json").write_text(_json.dumps(api))
    (tmp_path / "api.json").chmod(0o600)
    plain = daemon.credential_environment("api", str(tmp_path))
    assert "ENHANCED_LLM_BASE_URL" not in plain
    (tmp_path / "llm.json").write_text(_json.dumps(
        {"base_url": "https://api.example.test/v4", "api_key": "k",
         "model": "m", "daily_token_cap": 3000}))
    (tmp_path / "llm.json").chmod(0o600)
    loaded = daemon.credential_environment("api", str(tmp_path))
    assert loaded["ENHANCED_LLM_BASE_URL"] == "https://api.example.test/v4"
    assert loaded["ENHANCED_LLM_TOKEN_CAP"] == "3000"
    monkeypatch.setenv("ENHANCED_LLM_BASE_URL", loaded["ENHANCED_LLM_BASE_URL"])
    monkeypatch.setenv("ENHANCED_LLM_API_KEY", "k")
    monkeypatch.setenv("ENHANCED_LLM_MODEL", "m")
    monkeypatch.setenv("ENHANCED_LLM_TOKEN_CAP", "3000")
    route = llm.load_route_env()
    assert route["model"] == "m" and route["daily_token_cap"] == 3000
    monkeypatch.delenv("ENHANCED_LLM_BASE_URL")
    assert llm.load_route_env() is None


def test_translate_messages_guardrails():
    messages = llm.translate_messages("hello", "French")
    assert "French" in messages[1]["content"]
    with pytest.raises(llm.LlmUnavailable):
        llm.translate_messages("", "French")
    with pytest.raises(llm.LlmUnavailable):
        llm.translate_text if False else llm.translate_messages("x" * 9000, "French")
    with pytest.raises(llm.LlmUnavailable):
        llm.translate_messages("hello", "x")
