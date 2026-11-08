"""One canonical service, 41 bot scopes plus a controller and reviewed sharing.

Uses invented profile IDs and real PostgreSQL. This does not install profiles in
Hermes or qualify 42 concurrent chat models or production throughput.
"""
import asyncio
import os
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import httpx
import jwt
import pytest

from src.encryption_manager import EncryptionManager
from src.memory_api import create_app
from src.memory_service import MemoryService


@pytest.mark.asyncio
async def test_forty_one_bot_spaces_and_controller_share_only_reviewed_library(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Choose an explicitly disposable PostgreSQL database")
    verifier = "synthetic-fleet-verifier-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_JWT_SECRET", verifier)
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    for name in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
        monkeypatch.delenv(name, raising=False)
    tenant = "fleet_"+uuid.uuid4().hex[:20]
    projects = ["controller"]+[f"bot_{index:02}" for index in range(41)]
    pool = await asyncpg.create_pool(url, min_size=1, max_size=8)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))

    def headers(project, reviewer=False):
        return {"Authorization": "Bearer "+jwt.encode({"tenant": tenant, "project_id": project,
            "sub": "human_review" if reviewer else project, "agent_id": project,
            "roles": ["memory_reviewer" if reviewer else "api_client"], "capture_policy": "selected",
            "exp": int(time.time())+300}, verifier, algorithm="HS256")}

    try:
        await service.initialize()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(service)), base_url="http://fixture") as http:
            async def remember(project):
                body = {"content": f"Private synthetic working note for {project} uses cedar.",
                        "idempotency_key": "fleet-private", "fact_key": "working.note"}
                for _ in range(20):
                    response = await http.post("/v1/memories", headers=headers(project), json=body)
                    busy = response.status_code == 503 and response.json().get("detail", "").startswith("Service busy;")
                    if response.status_code != 429 and not busy:
                        response.raise_for_status()
                        return response.json()
                    await asyncio.sleep(.02)
                raise AssertionError("Fixture admission did not recover")

            records = await asyncio.gather(*(remember(project) for project in projects), return_exceptions=True)
            for record in records:
                if isinstance(record, BaseException):
                    raise record
            assert len({record["id"] for record in records}) == 42
            for index, project in enumerate(projects):
                own = await http.post("/v1/memories/recall", headers=headers(project), json={"query": "cedar"})
                assert [record["id"] for record in own.json()["results"]] == [records[index]["id"]]
                other = records[(index+1) % len(records)]
                assert (await http.get("/v1/memories/"+other["id"], headers=headers(project))).status_code == 404
            member = {"library": "portfolio", "member_project": projects[1], "admitted": True}
            assert (await http.post("/v1/memories/library/membership", headers=headers(projects[1]), json=member)).status_code == 403
            shared = await http.post("/v1/memories", headers=headers("controller"), json={
                "content": "Reviewed common guidance uses a short deployment checklist.", "idempotency_key": "fleet-reviewed"})
            shared.raise_for_status()
            shared_id = shared.json()["id"]
            for project in projects:
                response = await http.post("/v1/memories/library/membership", headers=headers("controller", True), json={
                    "library": "portfolio", "member_project": project, "admitted": True, "can_publish": project == "controller"})
                response.raise_for_status()
            publication = await http.post("/v1/memories/"+shared_id+"/library", headers=headers("controller", True), json={
                "library": "portfolio", "expected_version": 1})
            publication.raise_for_status()
            for project in projects[1:]:
                response = await http.get("/v1/memories/"+shared_id, headers=headers(project))
                assert response.status_code == 200 and response.json()["shared"]
            revoked = await http.post("/v1/memories/library/membership", headers=headers("controller", True),
                json=member | {"admitted": False})
            revoked.raise_for_status()
            assert (await http.get("/v1/memories/"+shared_id, headers=headers(projects[1]))).status_code == 404
            corrected = await http.patch("/v1/memories/"+shared_id, headers=headers("controller"), json={
                "content": "Updated common guidance awaits a new review.", "expected_version": 1})
            corrected.raise_for_status()
            for project in projects[1:]:
                assert (await http.get("/v1/memories/"+shared_id, headers=headers(project))).status_code == 404
                assert (await http.get("/v1/memories/"+records[projects.index(project)]["id"], headers=headers(project))).status_code == 200
    finally:
        await pool.close()
