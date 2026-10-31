"""Opt-in language SDKs against the same real canonical HTTP/database contract."""
import asyncio
import os
from pathlib import Path
import socket
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import jwt
import pytest
import uvicorn

from src.encryption_manager import EncryptionManager
from src.memory_api import create_app
from src.memory_service import MemoryService


@pytest.mark.asyncio
@pytest.mark.parametrize("language,command", [
    ("node", ["node", "test/project-live.mjs"]),
    ("go", ["go", "test", "-race", "-run", "^TestCanonicalLiveProjectMemory$", "-count=1"]),
    ("rust", ["cargo", "test", "--locked", "--test", "project_live", "--", "--ignored"]),
])
async def test_real_project_sdk(language, command, monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url or os.getenv("RNR_QUALIFICATION_CROSS_LANGUAGE") != "1":
        pytest.skip("Prepare compiled SDKs and explicitly select synthetic cross-language qualification")
    key = "synthetic-language-client-signing-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_JWT_SECRET", key)
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    tenant = "client_" + uuid.uuid4().hex[:20]

    def credential(project):
        return jwt.encode(dict(sub="synthetic_owner", tenant=tenant, project_id=project, agent_id=language,
            roles=["api_client"], exp=int(time.time())+300), key, algorithm="HS256")

    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    await service.initialize()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(service), lifespan="off", log_level="error", access_log=False, ws="none"))
    running = asyncio.create_task(server.serve(sockets=[listener]))
    process = None
    try:
        async with asyncio.timeout(5):
            while not server.started:
                await asyncio.sleep(.01)
        env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in
               ("KEY", "SECRET", "PASSWORD", "TOKEN", "DATABASE_URL", "TENANT"))}
        env.update(RNR_CLIENT_QUALIFICATION_URL=f"http://127.0.0.1:{port}",
                   RNR_CLIENT_QUALIFICATION_TOKEN=credential("one"), RNR_CLIENT_OTHER_TOKEN=credential("other"))
        process = await asyncio.create_subprocess_exec(*command,
            cwd=Path(__file__).resolve().parents[2] / "clients" / language, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        output, _ = await asyncio.wait_for(process.communicate(), 120)
        assert process.returncode == 0, output.decode(errors="replace")
    finally:
        if process and process.returncode is None:
            process.kill()
            await process.wait()
        server.should_exit = True
        await asyncio.wait_for(running, 5)
        listener.close()
        await pool.close()
