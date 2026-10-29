"""Check the built full runtime without databases, private data or networking.

Run inside the image with production tenant enforcement enabled, for example:
docker run -i --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m
    --entrypoint python IMAGE - < tests/qualification/full_runtime_smoke.py
The qualification workflow supplies invented database credentials solely to
allow configuration construction. No database connection is initialized.
"""
import asyncio
import importlib.util
import os
import stat
from datetime import timedelta
from pathlib import Path


async def main():
    assert os.environ.get("ENHANCED_ENV") == "production"
    assert os.environ.get("ENHANCED_REQUIRE_TENANT") == "1"
    assert importlib.util.find_spec("pip") is None
    assert os.geteuid() != 0
    for path in ("/app/src", "/app/bin", "/app/runtime"):
        assert Path(path).stat().st_uid == 0, "Service code must remain root-owned"
    privileged_files = []
    for base in ("/usr", "/opt", "/app"):
        for folder, _, names in os.walk(base):
            for name in names:
                item = Path(folder) / name
                mode = item.stat(follow_symlinks=False).st_mode
                if stat.S_ISREG(mode) and mode & (stat.S_ISUID | stat.S_ISGID):
                    privileged_files.append(str(item))
    assert not privileged_files, "Runtime files must not carry setuid/setgid mode bits"
    forbidden = {".cognee_system", ".data_storage", ".cognee_cache", ".data", "secrets"}
    for base in (Path("/app/cognee"), Path("/app/runtime/cognee")):
        assert not any(set(item.parts) & forbidden for item in base.rglob("*")), \
            "Local data or secret paths must not enter a release image"

    from src.multi_tenant import get_tenant, tenant_scoped_table, MissingTenantError
    assert get_tenant() is None
    import src.memory_api  # noqa: F401
    from src.enhanced_cognee_mcp import _load_bin_mcp
    registry, _ = _load_bin_mcp()
    assert registry is not None, "Tool registry failed to import before a request tenant exists"
    assert len(await registry.list_tools()) == 122
    assert get_tenant() is None
    try:
        tenant_scoped_table("shared_memory.documents")
    except MissingTenantError:
        pass
    else:
        raise AssertionError("Registry discovery must not relax storage enforcement")

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import sys
    env = dict(os.environ, ENHANCED_MCP_ROLE="readonly",
               ENHANCED_MCP_TENANT="qualification")
    params = StdioServerParameters(command=sys.executable,
                                  args=["/app/bin/enhanced_cognee_mcp_server.py"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
            await client.initialize()
            assert len((await client.list_tools()).tools) == 122
            denied = await client.call_tool("remember", {"data": "Synthetic denied write"})
            assert denied.isError
            assert any("Permission denied" in getattr(item, "text", "") for item in denied.content)
    print("Full built runtime: no local stores/pip/setuid/setgid files; APIs and 122 tools import with production tenant enforcement; real MCP readonly denial passed")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=90))
