"""Synthetic, source-only F03/F04/F05 security regressions; no live model/backend."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from src import llm_summarize as llm
from src.memory_api import create_app, SummarizeRequest, ConsolidateRequest, TranslateRequest
from src.security.enterprise_auth import Principal
from src.security.auth import Role


class AnalysisStore:
    def __init__(self):
        self.rows = {ident: {"id": ident, "version": 3, "project_id": "project",
                            "state": "active", "content": "A durable synthetic decision.",
                            "provenance": {"subject": "owner"}}
                     for ident in ("a", "b")}
        self.reads = []
        self.writes = []

    async def get(self, scope, record_id):
        self.reads.append(record_id)
        return deepcopy(self.rows[record_id])

    async def list_records(self, *args, **kwargs):
        raise AssertionError("Analysis must not select unfiltered recent records")

    async def remember(self, *args, **kwargs):
        self.writes.append(kwargs)
        return {"id": "detached"}


@pytest.fixture
def analysis(monkeypatch, tmp_path):
    store = AnalysisStore()
    app = create_app(store)
    app.state.llm_route = {"base_url": "https://model.invalid/v1", "api_key": "synthetic",
                           "model": "synthetic", "daily_token_cap": 50000}
    app.state.llm_budget = llm.TokenBudget(tmp_path / "budget.sqlite3")
    calls = []

    def chat(route, messages, **kwargs):
        calls.append(messages)
        return "Synthetic digest", 120

    monkeypatch.setattr(llm, "chat", chat)
    principal = Principal(subject="owner", role=Role.USER, tenant_id="tenant",
                          claims={"project_id": "project"})
    request = Request({"type": "http", "state": {"principal": principal}})

    def invoke(path, body):
        route = next(route for route in app.routes if route.path == path)
        return asyncio.run(route.endpoint(body, request))

    return SimpleNamespace(app=app, store=store, calls=calls, invoke=invoke, request=request)


def test_summary_is_explicit_return_only_with_source_versions(analysis):
    result = analysis.invoke("/v1/memories/summarize", SummarizeRequest(record_ids=["a"]))
    assert result["summary"] == "Synthetic digest"
    assert result["stored"] is False
    assert result["record_id"] is None
    assert result["source_records"] == [{"id": "a", "version": 3}]
    assert analysis.store.reads == ["a"]
    assert not analysis.store.writes


@pytest.mark.parametrize("request_class", [SummarizeRequest, ConsolidateRequest])
def test_analysis_requires_explicit_record_ids(request_class):
    with pytest.raises(ValidationError):
        request_class()


@pytest.mark.parametrize("path,request_class,ids", [
    ("/v1/memories/summarize", SummarizeRequest, ["a"]),
    ("/v1/memories/consolidation/candidates", ConsolidateRequest, ["a", "b"]),
])
@pytest.mark.parametrize("change", [{"project_id": "other"}, {"shared": True},
                                    {"provenance": {"subject": "another-owner"}},
                                    {"provenance": {}}, {"state": "retracted"}])
def test_analysis_rejects_non_owned_or_unverifiable_sources(analysis, path, request_class, ids, change):
    analysis.store.rows["a"].update(change)
    body = request_class(record_ids=ids)
    with pytest.raises(ValueError):
        analysis.invoke(path, body)
    assert not analysis.calls
    assert not analysis.store.writes


@pytest.mark.parametrize("change", [
    {"id": "other"}, {"version": None}, {"version": True}, {"version": 0},
    {"content": None}, {"content": " "}, {"expires_at": "2000-01-01T00:00:00+00:00"},
    {"expires_at": "not-a-date"}, {"expires_at": "2099-01-01T00:00:00"},
])
def test_analysis_rejects_invalid_source_snapshots(analysis, change):
    analysis.store.rows["a"].update(change)
    with pytest.raises(ValueError):
        analysis.invoke("/v1/memories/summarize", SummarizeRequest(record_ids=["a"]))
    assert not analysis.calls


@pytest.mark.parametrize("request_class,ids", [
    (SummarizeRequest, [""]), (SummarizeRequest, ["a", "a"]),
    (ConsolidateRequest, ["a", "a"]), (SummarizeRequest, [" " * 3]),
    (SummarizeRequest, ["x" * 201]),
])
def test_analysis_ids_are_bounded_nonempty_unique(request_class, ids):
    with pytest.raises(ValidationError):
        request_class(record_ids=ids)


@pytest.mark.parametrize("path,request_class,field", [
    ("/v1/memories/summarize", SummarizeRequest, "content"),
    ("/v1/memories/summarize", SummarizeRequest, "title"),
    ("/v1/memories/consolidation/candidates", ConsolidateRequest, "content"),
    ("/v1/memories/translate", TranslateRequest, "text"),
    ("/v1/memories/translate", TranslateRequest, "target_language"),
])
@pytest.mark.parametrize("marker", ["password=synthetic-only", '{"password": "synthetic"}',
                                   '{"api_key": "synthetic"}'])
def test_all_analysis_model_payloads_reject_credentials(analysis, path, request_class, field, marker):
    # Invented credential-shaped fixture, never a real secret.
    kwargs: dict = {"record_ids": ["a", "b"]}
    if field == "content":
        # The screen must inspect the full source before prompt truncation.
        analysis.store.rows["a"]["content"] = "ordinary " * 200 + marker
    elif request_class is TranslateRequest:
        kwargs = {"text": "hello", "target_language": "French", field: marker}
    else:
        kwargs[field] = marker
    with pytest.raises(ValueError):
        analysis.invoke(path, request_class(**kwargs))
    assert not analysis.calls


def test_chat_rejects_credentials_before_opening_connection(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("credential payload reached the network")
    monkeypatch.setattr(llm, "HTTPSConnection", forbidden)
    with pytest.raises(ValueError):
        llm.chat({"base_url": "https://model.invalid", "api_key": "synthetic", "model": "synthetic"},
                 [{"role": "user", "content": "password=synthetic-only"}])


ANALYSIS_CALLS = [
    ("/v1/memories/summarize", SummarizeRequest(record_ids=["a"])),
    ("/v1/memories/consolidation/candidates", ConsolidateRequest(record_ids=["a", "b"])),
    ("/v1/memories/translate", TranslateRequest(text="hello", target_language="French")),
]


@pytest.mark.parametrize("path,body", ANALYSIS_CALLS)
def test_missing_ledger_blocks_every_model_endpoint(analysis, path, body):
    analysis.app.state.llm_budget = None
    with pytest.raises(llm.LlmUnavailable):
        analysis.invoke(path, body)
    assert not analysis.calls


@pytest.mark.parametrize("path,body", ANALYSIS_CALLS)
@pytest.mark.parametrize("outcome", ["failure", "missing", "success"])
def test_endpoints_reserve_before_dispatch_and_keep_uncertain_charge(analysis, monkeypatch, path, body, outcome):
    budget = analysis.app.state.llm_budget
    observed = []

    def chat(*args, **kwargs):
        observed.append(budget.used("tenant", "project"))
        assert observed[-1] > 0, "must durably reserve before chat starts"
        if outcome == "failure":
            raise llm.LlmUnavailable("Synthetic transport failure")
        return "Synthetic digest", 123 if outcome == "success" else None

    monkeypatch.setattr(llm, "chat", chat)
    if outcome == "failure":
        with pytest.raises(llm.LlmUnavailable):
            analysis.invoke(path, body)
    else:
        analysis.invoke(path, body)
    reopened = llm.TokenBudget(budget.path)
    assert reopened.used("tenant", "project") == (123 if outcome == "success" else observed[0])


def test_utf8_prompt_is_reserved_conservatively_not_fixed_4000(analysis):
    analysis.app.state.llm_route["daily_token_cap"] = 5000
    with pytest.raises(llm.LlmUnavailable):
        analysis.invoke("/v1/memories/translate", TranslateRequest(text="\u4e2d" * 2000, target_language="English"))
    assert not analysis.calls


def test_concurrent_endpoint_calls_cannot_overspend(analysis, monkeypatch):
    import time
    analysis.app.state.llm_route["daily_token_cap"] = 5000
    calls = []

    def chat(*args, **kwargs):
        calls.append(1)
        time.sleep(0.04)
        return "Synthetic", None

    monkeypatch.setattr(llm, "chat", chat)
    endpoint = next(r.endpoint for r in analysis.app.routes if r.path == "/v1/memories/translate")

    async def run():
        return await asyncio.gather(*(endpoint(TranslateRequest(text="hello", target_language="French"),
                                              analysis.request) for _ in range(12)), return_exceptions=True)

    outcomes = asyncio.run(run())
    assert sum(isinstance(result, dict) for result in outcomes) == 1
    assert len(calls) == 1
    assert 2000 < analysis.app.state.llm_budget.used("tenant", "project") <= 5000


@pytest.mark.parametrize("ledger_state", ["valid", "missing", "broken"])
def test_analysis_status_is_tenant_scoped_and_honest_about_unavailable_ledger(analysis, ledger_state):
    budget = analysis.app.state.llm_budget
    budget.reserve("tenant", "project", 500, 1000)
    budget.reserve("other-tenant", "project", 900, 1000)
    if ledger_state == "missing":
        analysis.app.state.llm_budget = None
    elif ledger_state == "broken":
        # Safe failure simulation without deleting any file.
        budget.path.chmod(0o666)
    endpoint = next(r.endpoint for r in analysis.app.routes if r.path == "/v1/memories/summarization/status")
    result = asyncio.run(endpoint(analysis.request))
    assert result["configured"] is (ledger_state == "valid")
    assert result["used_today"] == (500 if ledger_state == "valid" else None)
    assert result["project_id"] == "project"


def test_cancelled_provider_call_keeps_durable_reservation(analysis, monkeypatch):
    from threading import Event
    started, release = Event(), Event()
    budget = analysis.app.state.llm_budget

    def chat(*args, **kwargs):
        started.set()
        release.wait(timeout=5)
        return "Synthetic result", 1

    monkeypatch.setattr(llm, "chat", chat)
    endpoint = next(r.endpoint for r in analysis.app.routes if r.path == "/v1/memories/translate")

    async def cancel():
        task = asyncio.create_task(endpoint(TranslateRequest(text="hello", target_language="French"), analysis.request))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            release.set()

    asyncio.run(cancel())
    assert llm.TokenBudget(budget.path).used("tenant", "project") > 2000
