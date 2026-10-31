"""Compare actual SDK requests against registered server signatures."""
import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from enhanced_cognee_client import EnhancedCogneeClient


def test_every_literal_sdk_tool_call_matches_the_real_registry():
    server = ast.parse(Path("bin/enhanced_cognee_mcp_server.py").read_text())
    contracts = {node.name: {arg.arg for arg in node.args.args + node.args.kwonlyargs}
                 for node in server.body if isinstance(node, ast.AsyncFunctionDef)
                 and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                         and d.func.attr == "tool" for d in node.decorator_list)}
    sdk = ast.parse(Path("sdk_pkg/enhanced_cognee_client/client.py").read_text())
    calls = [node for node in ast.walk(sdk) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "_call"
             and node.args and isinstance(node.args[0], ast.Constant)]
    assert len(calls) >= 17
    for call in calls:
        name = call.args[0].value
        assert name in contracts
        assert {arg.arg for arg in call.keywords} <= contracts[name], name


@pytest.mark.asyncio
async def test_graph_sdk_uses_real_fields_and_refuses_to_ignore_agent_scope():
    async with EnhancedCogneeClient() as sdk:
        sdk._call = AsyncMock(return_value={"result": "synthetic"})
        await sdk.remember("Synthetic fixture", session_id="session")
        sdk._call.assert_awaited_once_with("remember", data="Synthetic fixture", session_id="session")
        sdk._call.reset_mock()
        await sdk.recall("Synthetic fixture", limit=3)
        sdk._call.assert_awaited_once_with("recall", query="Synthetic fixture", top_k=3)
        sdk._call.reset_mock()
        assert "error" in await sdk.remember("fixture", agent_id="must_not_ignore")
        assert "error" in (await sdk.recall("fixture", agent_id="must_not_ignore"))[0]
        sdk._call.assert_not_awaited()
