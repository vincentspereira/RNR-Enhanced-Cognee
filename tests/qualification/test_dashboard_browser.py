"""Optional built-dashboard browser test; never uses an existing profile or keys."""
import asyncio
import os
from pathlib import Path
import socket
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import httpx
import jwt
import pytest
import uvicorn

from src.encryption_manager import EncryptionManager
from src.memory_api import create_app
from src.memory_service import MemoryService


@pytest.mark.asyncio
async def test_built_dashboard_real_browser(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url or os.getenv("RNR_QUALIFICATION_BROWSER") != "1":
        pytest.skip("Prepare a built dashboard and Chromium and explicitly select browser qualification")
    key = "synthetic-dashboard-signing-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_JWT_SECRET", key)
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_DASHBOARD_ORIGINS", "http://localhost:9050")
    tenant = "browser_" + uuid.uuid4().hex[:20]
    token = jwt.encode(dict(sub="synthetic_owner", tenant=tenant, project_id="browser",
        agent_id="synthetic_dashboard", roles=["api_client"], exp=int(time.time())+300), key, algorithm="HS256")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    await service.initialize()
    listener = socket.socket()
    # Matches this build's explicitly selected NEXT_PUBLIC_API_URL. Refuse an
    # occupied port; no existing service is stopped or silently reused.
    listener.bind(("127.0.0.1", 8000))
    server = uvicorn.Server(uvicorn.Config(create_app(service), lifespan="off", log_level="error", access_log=False, ws="none"))
    running = asyncio.create_task(server.serve(sockets=[listener]))
    processes = []
    root = Path(__file__).resolve().parents[2] / "dashboard/nextjs-dashboard"
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in
        ("KEY", "SECRET", "PASSWORD", "TOKEN", "DATABASE_URL", "TENANT"))}
    try:
        processes.append(await asyncio.create_subprocess_exec("node", "node_modules/next/dist/bin/next", "start",
            "-H", "127.0.0.1", "-p", "9050", cwd=root, env=env,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL))
        async with httpx.AsyncClient(trust_env=False) as http:
            async with asyncio.timeout(15):
                while True:
                    try:
                        if (await http.get("http://localhost:9050/login")).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(.1)
        env.update(RNR_DASHBOARD_QUALIFICATION_URL="http://localhost:9050", RNR_DASHBOARD_API_URL="http://localhost:8000",
                   RNR_DASHBOARD_QUALIFICATION_TOKEN=token)
        child = await asyncio.create_subprocess_exec("node", "tests/canonical-live.mjs", cwd=root, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        processes.append(child)
        output, _ = await asyncio.wait_for(child.communicate(), 90)
        assert child.returncode == 0, output.decode(errors="replace")
    finally:
        for child in processes:
            if child.returncode is None:
                child.terminate()
                try:
                    await asyncio.wait_for(child.wait(), 5)
                except asyncio.TimeoutError:
                    child.kill()
                    await child.wait()
        server.should_exit = True
        await asyncio.wait_for(running, 5)
        listener.close()
        await pool.close()
