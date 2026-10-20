"""Real stdio MCP initialization and writes through the scoped HTTP service."""
import asyncio
import json
import os
from pathlib import Path
import socket
import sys
import time
import uuid

import asyncpg
from cryptography.fernet import Fernet
import jwt
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.encryption_manager import EncryptionManager
from src.memory_api import create_app
from src.memory_service import MemoryService


@pytest.mark.asyncio
async def test_real_stdio_project_bridge_roundtrip(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable PostgreSQL database")
    secret = "synthetic-stdio-server-signing-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", secret)
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    tenant = "stdio_" + uuid.uuid4().hex[:20]
    token = jwt.encode(dict(sub="synthetic_owner", tenant=tenant, project_id="synthetic_project",
        agent_id="synthetic_agent", roles=["api_client"], exp=int(time.time())+300), secret, algorithm="HS256")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    await service.initialize()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(service), lifespan="off", log_level="error", access_log=False, ws="none"))
    running = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                await asyncio.sleep(.01)
        root = Path(__file__).resolve().parents[2]
        params = StdioServerParameters(command=sys.executable, args=[str(root / "bin/project_memory_mcp.py")],
            env={"ENHANCED_MEMORY_URL": f"http://127.0.0.1:{port}", "ENHANCED_COGNEE_ACCESS_TOKEN": token,
                 "PYTHONPATH": str(root), "COGNEE_TELEMETRY_ENABLED": "0"})
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == {"add_memory", "search_memories", "get_memories", "get_memory", "update_memory",
                             "delete_memory", "list_agents", "memory_connections", "health"}

            async def call(name, args):
                value = await session.call_tool(name, args)
                assert not value.isError, value
                return json.loads(value.content[0].text)

            stored = await call("add_memory", {"content": "Synthetic Cedar keeps eleven daily snapshots.", "idempotency_key": "stdio-one"})
            ident = stored["id"]
            assert (await call("search_memories", {"query": "Cedar"}))["results"][0]["id"] == ident
            assert (await call("get_memories", {}))["results"][0]["id"] == ident
            changed = await call("update_memory", {"memory_id": ident, "content": "Synthetic Cedar keeps nine daily snapshots.", "expected_version": 1})
            assert changed["version"] == 2
            assert (await call("get_memory", {"memory_id": ident}))["version"] == 2
            assert (await call("health", {}))["active_records"] == 1
            assert (await call("list_agents", {}))["agents"]
            await call("delete_memory", {"memory_id": ident, "expected_version": 2})
            assert (await call("search_memories", {"query": "Cedar"}))["results"] == []
            refused = await session.call_tool("add_memory", {"content": "password: " + "synthetic-secret-value", "idempotency_key": "no-secrets"})
            assert refused.isError
    finally:
        server.should_exit = True
        await asyncio.wait_for(running, 5)
        listener.close()
        await pool.close()
