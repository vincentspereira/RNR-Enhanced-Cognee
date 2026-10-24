"""Actual canonical HTTP, dashboard and scoped SDK compatibility boundaries."""
import asyncio
import os
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import httpx
import jwt
import pytest

from sdk_pkg.enhanced_cognee_client.project_memory import ProjectMemoryClient, MemoryRequestError
from src.encryption_manager import EncryptionManager
from src.memory_api import create_app
from src.memory_service import MemoryService


@pytest.mark.asyncio
async def test_clients_dashboard_and_tools_share_records_and_authorization(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable PostgreSQL database")
    secret = "synthetic-adapter-signing-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", secret)
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    monkeypatch.setenv("ENHANCED_RATE_LIMIT_PER_MINUTE", "500")
    monkeypatch.setenv("ENHANCED_MAX_CONCURRENT_REQUESTS", "1")
    for name in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
        monkeypatch.delenv(name, raising=False)
    tenant = "adapter_" + uuid.uuid4().hex[:20]

    def token(project="one", role="api_client"):
        return jwt.encode(dict(sub="fixture_owner", roles=[role], tenant=tenant, project_id=project,
                               agent_id="fixture_agent", exp=int(time.time())+300), secret, algorithm="HS256")

    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    await service.initialize()
    app = create_app(service)
    transport = httpx.ASGITransport(app=app)
    try:
        async with ProjectMemoryClient("http://localhost", token(), transport=transport) as sdk:
            first = await sdk.remember("Cedar retains synthetic archives for eleven days.", "fixture-one")
            ident = first["id"]
            assert (await sdk.list_records())["results"][0]["id"] == ident
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost",
                                        headers={"Authorization": "Bearer " + token()}) as http:
                listing = await http.get("/api/memories")
                assert listing.status_code == 200 and listing.json()[0]["memory_id"] == ident
                assert listing.json()[0]["version"] == 1
                args = dict(content="Birch retains synthetic archives.", idempotency_key="fixture-two")
                second = await http.post("/tools/add_memory", json={"arguments": args})
                assert second.status_code == 200
                replay = await http.post("/tools/add_memory", json={"arguments": args})
                assert replay.json()["result"]["id"] == second.json()["result"]["id"]
                assert (await http.post("/tools/ingest_url", json={"arguments": {"url": "http://localhost"}})).status_code == 403
                assert (await http.post("/tools/add_memory", json={"arguments": args | {"project_id": "other"}})).status_code == 403
                malformed = await http.post("/tools/add_memory", json={"arguments": args | {
                    "evidence": {"confidence": "synthetic-sensitive-field"}}})
                assert malformed.status_code == 422 and "synthetic-sensitive-field" not in malformed.text
                assert (await http.patch("/api/memories/"+ident, json={"content": "Changed", "expected_version": 1})).status_code == 200
                with pytest.raises(MemoryRequestError) as stale:
                    await sdk.correct(ident, "Stale synthetic change", 1)
                assert stale.value.status_code == 409
                assert (await sdk.get(ident))["version"] == 2
                deleted = await http.post("/api/memories/"+ident+"/retract", params={"expected_version": 2})
                assert deleted.status_code == 200 and deleted.json()["history_preserved"]
                assert len((await sdk.history(ident))["versions"]) == 3
                assert (await http.get("/api/sessions")).status_code == 501
                assert (await http.get("/api/memories", headers={"Authorization": "Bearer " + token("other")})).json() == []
                assert (await http.get("/api/memories", headers={"Authorization": ""})).status_code == 401
                assert (await http.post("/tools/add_memory", json={"arguments": args},
                    headers={"Authorization": "Bearer " + token(role="readonly")})).status_code == 403
                # Hold one admitted request. Excess work fails promptly and
                # liveness remains available, then capacity is released.
                entered, release = asyncio.Event(), asyncio.Event()
                original = service.status

                async def held(scope):
                    entered.set()
                    await release.wait()
                    return await original(scope)

                monkeypatch.setattr(service, "status", held)
                pending = asyncio.create_task(http.get("/v1/memories/status"))
                await asyncio.wait_for(entered.wait(), 2)
                assert (await http.get("/v1/memories/status")).status_code == 503
                assert (await http.get("/health/live")).status_code == 200
                release.set()
                assert (await pending).status_code == 200
                monkeypatch.setattr(service, "status", original)
                assert (await sdk.status())["active_records"] == 1
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_sdk_never_forwards_tokens_or_echoes_server_secrets():
    calls = []

    async def response(request):
        calls.append(request)
        return httpx.Response(409, json={"detail": "synthetic-private-server-content", "clarification_required": True})

    async with ProjectMemoryClient("http://localhost", "synthetic-scoped-token",
                                   transport=httpx.MockTransport(response)) as sdk:
        for path in ("https://example.com/v1/memories", "//example.com/v1/memories", "/v1/memories/../secret", "/v1/memoriesevil"):
            with pytest.raises(ValueError):
                await sdk.request("GET", path)
        assert calls == []
        with pytest.raises(MemoryRequestError) as refused:
            await sdk.remember("Synthetic fact", "retry-identity")
        assert refused.value.clarification_required and "private" not in str(refused.value)
        assert len(calls) == 1
