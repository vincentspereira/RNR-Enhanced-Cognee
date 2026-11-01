"""Offline lifecycle proof that optional model accounting cannot break memory."""
import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from src import memory_api as api
from src import llm_summarize as llm
from src.security.auth import Role
from src.security.enterprise_auth import Principal


@pytest.mark.parametrize("ledger", ["missing", "unsafe", "valid"])
def test_lifespan_preserves_memory_and_fails_closed_without_ledger(monkeypatch, tmp_path, ledger):
    import asyncpg
    import src.mcp_security as security
    import src.security.enterprise_auth as auth
    closed = []

    async def close():
        closed.append(True)

    async def create_pool(*args, **kwargs):
        return SimpleNamespace(close=close)

    class Store:
        def __init__(self, *args, **kwargs):
            pass

        async def check_schema(self):
            pass

        async def get(self, scope, record_id):
            return {"id": record_id, "content": "synthetic memory"}

    monkeypatch.setattr(asyncpg, "create_pool", create_pool)
    monkeypatch.setattr(security, "enforce_production_auth", lambda: None)
    monkeypatch.setattr(auth, "jwt_secret_configured", lambda: True)
    monkeypatch.setattr(api, "canonical_cipher_from_environment", lambda: object())
    monkeypatch.setattr(api, "MemoryService", Store)
    monkeypatch.setenv("ENHANCED_MEMORY_DATABASE_URL", "synthetic-unused")
    for name in ("ENHANCED_LLM_BUDGET_DB", "ENHANCED_INDEX_CONFIG", "ENHANCED_EMBEDDING_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm, "load_route_env", lambda: {
        "base_url": "https://model.invalid", "model": "synthetic", "api_key": "synthetic", "daily_token_cap": 50000})
    if ledger != "missing":
        directory = tmp_path / "ledger"
        directory.mkdir(mode=0o700)
        if ledger == "unsafe":
            directory.chmod(0o777)
        monkeypatch.setenv("ENHANCED_LLM_BUDGET_DB", str(directory / "budget.sqlite3"))
    app = api.create_app()
    request = Request({"type": "http", "state": {"principal": Principal(
        subject="owner", role=Role.USER, tenant_id="tenant", claims={"project_id": "project"})}})

    async def exercise():
        async with api.lifespan(app):
            endpoint = next(r.endpoint for r in app.routes if r.path == "/v1/memories/{record_id}" and "GET" in r.methods)
            assert (await endpoint("a", request))["content"] == "synthetic memory"
            assert (app.state.llm_budget is not None) is (ledger == "valid")
            if ledger != "valid":
                endpoint = next(r.endpoint for r in app.routes if r.path == "/v1/memories/translate")
                with pytest.raises(llm.LlmUnavailable):
                    await endpoint(api.TranslateRequest(text="hello", target_language="French"), request)

    asyncio.run(exercise())
    assert closed == [True]
