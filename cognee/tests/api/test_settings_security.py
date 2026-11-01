"""Global-settings and owner-configuration regressions using invented data.

The route tests override only the authenticated session dependency, not the
administrator check. The ownership test executes actual SQLite queries in RAM.
No provider or real account configuration is read or modified.
"""
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def upstream():
    with patch("dotenv.load_dotenv"):
        admin = importlib.import_module("cognee.modules.users.methods.require_global_admin")
        routes = importlib.import_module("cognee.api.v1.settings.routers.get_settings_router")
        settings = importlib.import_module("cognee.modules.settings")
        get_settings = importlib.import_module("cognee.modules.settings.get_settings")
        yield SimpleNamespace(admin=admin, routes=routes, settings=settings, getter=get_settings)


@pytest.mark.parametrize("role,status", [("anonymous", 401), ("regular", 403), ("admin", 200)])
@pytest.mark.parametrize("method", ["get", "post"])
def test_global_settings_require_a_real_admin(upstream, monkeypatch, role, status, method):
    app = FastAPI()
    app.include_router(upstream.routes.get_settings_router(), prefix="/settings")

    async def session():
        if role == "anonymous":
            raise HTTPException(401)
        return SimpleNamespace(is_superuser=role == "admin")

    app.dependency_overrides[upstream.admin._authenticated] = session
    llm = SimpleNamespace(llm_provider="ollama", llm_model="fixture", llm_endpoint="http://127.0.0.1",
                          llm_api_version=None, llm_api_key="synthetic-provider-secret")
    vector = SimpleNamespace(vector_db_provider="lancedb", vector_db_url="fixture",
                             vector_db_key="synthetic-vector-secret")
    monkeypatch.setattr(upstream.getter, "get_llm_config", lambda: llm)
    monkeypatch.setattr(upstream.getter, "get_vectordb_config", lambda: vector)
    save_llm, save_vector = AsyncMock(), AsyncMock()
    monkeypatch.setattr(upstream.settings, "save_llm_config", save_llm)
    monkeypatch.setattr(upstream.settings, "save_vector_db_config", save_vector)
    client = TestClient(app)
    if method == "get":
        response = client.get("/settings")
    else:
        response = client.post("/settings", json={"llm": {"provider": "ollama", "model": "fixture", "api_key": "synthetic"}})
    assert response.status_code == status, response.text
    assert "synthetic-provider-secret" not in response.text
    assert "synthetic-vector-secret" not in response.text
    if role != "admin" or method == "get":
        save_llm.assert_not_awaited()
    else:
        save_llm.assert_awaited_once()
    save_vector.assert_not_awaited()
    if role == "admin" and method == "get":
        assert response.json()["llm"]["apiKey"] == "********"
        assert response.json()["vectorDb"]["apiKey"] == "********"


def test_public_registration_is_disabled_by_default(monkeypatch, upstream):
    module = importlib.import_module("cognee.api.v1.users.routers.get_register_router")
    monkeypatch.delenv("COGNEE_PUBLIC_REGISTRATION_ENABLED", raising=False)
    app = FastAPI()
    app.include_router(module.get_register_router())
    assert TestClient(app).post("/register", json={"email": "fixture@example.invalid", "password": "synthetic"}).status_code == 403


def test_real_auth_dependency_refuses_anonymous_default_user(monkeypatch, upstream):
    managers = importlib.import_module("cognee.modules.users.get_user_manager")
    default = importlib.import_module("cognee.modules.users.methods.get_default_user")
    monkeypatch.setenv("REQUIRE_AUTHENTICATION", "false")
    monkeypatch.setenv("ENABLE_BACKEND_ACCESS_CONTROL", "false")
    fallback = AsyncMock(side_effect=AssertionError("Global settings must never create a default administrator"))
    monkeypatch.setattr(default, "get_default_user", fallback)
    app = FastAPI()
    app.include_router(upstream.routes.get_settings_router(), prefix="/settings")

    async def manager():
        yield AsyncMock()

    # Replace database access, while retaining the actual authentication and
    # administrator dependencies on the public route.
    app.dependency_overrides[managers.get_user_manager] = manager
    assert TestClient(app).get("/settings").status_code == 401
    fallback.assert_not_awaited()


def test_import_cleanup_hook_preserves_every_existing_log(upstream, tmp_path):
    from cognee.shared.logging_utils import cleanup_old_logs
    paths = [tmp_path / ("fixture_" + str(i) + ".log") for i in range(12)]
    for path in paths:
        path.write_text("Synthetic retained log fixture")
    cleanup_old_logs(tmp_path, max_files=2)
    assert all(path.read_text() == "Synthetic retained log fixture" for path in paths)


@pytest.mark.asyncio
async def test_configuration_id_never_overrides_its_authenticated_owner(upstream, monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from cognee.modules.users.models.Principal import Principal
    from cognee.modules.users.models.PrincipalConfiguration import PrincipalConfiguration
    lookup = importlib.import_module("cognee.modules.users.methods.get_principal_configuration")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner, other, config_id = uuid4(), uuid4(), uuid4()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync: Principal.metadata.create_all(sync, tables=[Principal.__table__, PrincipalConfiguration.__table__]))
        async with sessions() as session:
            session.add_all([Principal(id=owner), Principal(id=other),
                             PrincipalConfiguration(id=config_id, owner_id=owner, name="fixture",
                                                    configuration={"private": "synthetic owner fixture"})])
            await session.commit()
        monkeypatch.setattr(lookup, "get_relational_engine", lambda: SimpleNamespace(get_async_session=sessions))
        assert await lookup.get_principal_configuration(config_id, principal_id=owner) == {"private": "synthetic owner fixture"}
        assert await lookup.get_principal_configuration(config_id, principal_id=other) == {}
        with pytest.raises(ValueError):
            await lookup.get_principal_configuration(config_id, principal_id=None)
    finally:
        await engine.dispose()
