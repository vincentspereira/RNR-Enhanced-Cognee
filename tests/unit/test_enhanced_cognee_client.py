"""
test_enhanced_cognee_client.py - Unit tests for EnhancedCogneeClient.

All tests use unittest.mock.AsyncMock; no live HTTP calls are made.
All output is ASCII-only (no Unicode symbols).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from enhanced_cognee_client import EnhancedCogneeClient, EnhancedCogneeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Response with the given JSON payload."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    mock_resp.text = json.dumps(payload)
    mock_resp.raise_for_status = MagicMock()  # does nothing by default
    return mock_resp


# ---------------------------------------------------------------------------
# 1. Default constructor values
# ---------------------------------------------------------------------------


class TestClientInitDefaults:
    """test_client_init_defaults: verify default host, port, and timeout."""

    def test_defaults(self) -> None:
        client = EnhancedCogneeClient()
        assert client.host == "localhost"
        assert client.port == 8080
        assert client.timeout == 30.0
        assert client.api_key is None

    def test_base_url_uses_defaults(self) -> None:
        client = EnhancedCogneeClient()
        assert client._base_url == "http://localhost:8080"


# ---------------------------------------------------------------------------
# 2. Custom constructor values
# ---------------------------------------------------------------------------


class TestClientInitCustom:
    """test_client_init_custom: verify custom host and port are stored."""

    def test_custom_host_port(self) -> None:
        client = EnhancedCogneeClient(host="10.0.0.5", port=9999, timeout=5.0)
        assert client.host == "10.0.0.5"
        assert client.port == 9999
        assert client.timeout == 5.0

    def test_custom_api_key(self) -> None:
        client = EnhancedCogneeClient(api_key="secret-token")
        assert client.api_key == "secret-token"

    def test_base_url_reflects_custom_host_port(self) -> None:
        client = EnhancedCogneeClient(host="myhost", port=1234)
        assert client._base_url == "http://myhost:1234"


# ---------------------------------------------------------------------------
# 3. Successful _call round-trip
# ---------------------------------------------------------------------------


class TestCallSuccess:
    """test_call_success: mock httpx to verify _call parses JSON correctly."""

    @pytest.mark.asyncio
    async def test_call_returns_parsed_json(self) -> None:
        client = EnhancedCogneeClient()
        expected = {"memory_id": "abc-123", "status": "OK"}
        mock_resp = _make_mock_response(expected)

        client._client.post = AsyncMock(return_value=mock_resp)

        result = await client._call("add_memory", content="hello")

        assert result == expected

    @pytest.mark.asyncio
    async def test_call_sends_correct_url(self) -> None:
        client = EnhancedCogneeClient()
        mock_resp = _make_mock_response({"status": "OK"})
        client._client.post = AsyncMock(return_value=mock_resp)

        await client._call("health")

        client._client.post.assert_called_once()
        call_args = client._client.post.call_args
        assert call_args[0][0] == "/tools/health"

    @pytest.mark.asyncio
    async def test_call_sends_arguments_in_body(self) -> None:
        client = EnhancedCogneeClient()
        mock_resp = _make_mock_response({"status": "OK"})
        client._client.post = AsyncMock(return_value=mock_resp)

        await client._call("add_memory", content="test", agent_id="bot")

        call_kwargs = client._client.post.call_args[1]
        body = json.loads(call_kwargs["content"])
        assert body == {"arguments": {"content": "test", "agent_id": "bot"}}


# ---------------------------------------------------------------------------
# 4. Network error returns error dict
# ---------------------------------------------------------------------------


class TestCallNetworkError:
    """test_call_network_error: mock httpx to raise; verify error dict returned."""

    @pytest.mark.asyncio
    async def test_connect_error_returns_error_dict(self) -> None:
        import httpx

        client = EnhancedCogneeClient()
        client._client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await client._call("health")

        assert "error" in result
        assert "ERR" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout_returns_error_dict(self) -> None:
        import httpx

        client = EnhancedCogneeClient()
        client._client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        result = await client._call("get_stats")

        assert "error" in result
        assert "ERR" in result["error"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_dict(self) -> None:
        client = EnhancedCogneeClient()
        client._client.post = AsyncMock(side_effect=RuntimeError("boom"))

        result = await client._call("health")

        assert "error" in result


# ---------------------------------------------------------------------------
# 5. add_memory calls the correct tool
# ---------------------------------------------------------------------------


class TestAddMemoryCallsCorrectTool:
    """test_add_memory_calls_correct_tool: verify _call is invoked with 'add_memory'."""

    @pytest.mark.asyncio
    async def test_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"memory_id": "x"})

        await client.add_memory("some content", agent_id="my-agent")

        client._call.assert_called_once()
        call_args = client._call.call_args
        assert call_args[0][0] == "add_memory"

    @pytest.mark.asyncio
    async def test_passes_content_and_agent_id(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"memory_id": "x"})

        await client.add_memory("hello world", agent_id="agent-42")

        kwargs = client._call.call_args[1]
        assert kwargs["content"] == "hello world"
        assert kwargs["agent_id"] == "agent-42"

    @pytest.mark.asyncio
    async def test_metadata_forwarded(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"memory_id": "x"})
        meta = '{"category": "trading"}'

        await client.add_memory("fact", metadata=meta)

        kwargs = client._call.call_args[1]
        assert kwargs["metadata"] == meta


# ---------------------------------------------------------------------------
# 6. search_memories calls the correct tool
# ---------------------------------------------------------------------------


class TestSearchMemoriesCallsCorrectTool:
    """test_search_memories_calls_correct_tool: verify 'search_memories' tool name."""

    @pytest.mark.asyncio
    async def test_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value=[{"content": "match"}])

        await client.search_memories("query text")

        client._call.assert_called_once()
        assert client._call.call_args[0][0] == "search_memories"

    @pytest.mark.asyncio
    async def test_query_and_limit_forwarded(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value=[])

        await client.search_memories("find this", limit=5)

        kwargs = client._call.call_args[1]
        assert kwargs["query"] == "find this"
        assert kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_wraps_non_list_result_in_list(self) -> None:
        """If the server returns a dict (e.g. an error), wrap it in a list."""
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"error": "ERR something went wrong"})

        result = await client.search_memories("anything")

        assert isinstance(result, list)
        assert result[0]["error"] == "ERR something went wrong"


# ---------------------------------------------------------------------------
# 7. health calls the correct tool
# ---------------------------------------------------------------------------


class TestHealthCallsCorrectTool:
    """test_health_calls_correct_tool: verify 'health' tool name is used."""

    @pytest.mark.asyncio
    async def test_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"status": "OK"})

        await client.health()

        client._call.assert_called_once_with("health")

    @pytest.mark.asyncio
    async def test_returns_server_response(self) -> None:
        client = EnhancedCogneeClient()
        expected = {"postgresql": "OK", "qdrant": "OK", "neo4j": "OK", "redis": "OK"}
        client._call = AsyncMock(return_value=expected)

        result = await client.health()

        assert result == expected


# ---------------------------------------------------------------------------
# 8. Context manager support
# ---------------------------------------------------------------------------


class TestContextManager:
    """test_context_manager: verify __aenter__ / __aexit__ behaviour."""

    @pytest.mark.asyncio
    async def test_aenter_returns_client(self) -> None:
        client = EnhancedCogneeClient()
        client._client.aclose = AsyncMock()

        returned = await client.__aenter__()
        await client.__aexit__(None, None, None)

        assert returned is client

    @pytest.mark.asyncio
    async def test_aexit_calls_close(self) -> None:
        client = EnhancedCogneeClient()
        client._client.aclose = AsyncMock()

        async with client:
            pass

        client._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_usable_end_to_end(self) -> None:
        """Verify that the client is usable inside an async with block."""
        async with EnhancedCogneeClient() as client:
            client._call = AsyncMock(return_value={"status": "OK"})
            result = await client.health()
            assert result == {"status": "OK"}

    @pytest.mark.asyncio
    async def test_aexit_closes_even_on_exception(self) -> None:
        client = EnhancedCogneeClient()
        client._client.aclose = AsyncMock()

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("deliberate test error")

        client._client.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# 9. GDPR methods forward arguments correctly
# ---------------------------------------------------------------------------


class TestGdprMethods:
    """Verify GDPR tool names and argument forwarding."""

    @pytest.mark.asyncio
    async def test_gdpr_delete_dry_run_default(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"would_delete": 5})

        await client.gdpr_delete_user_data("user-99")

        kwargs = client._call.call_args[1]
        assert kwargs["user_id"] == "user-99"
        assert kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_gdpr_delete_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={})

        await client.gdpr_delete_user_data("user-99", dry_run=False)

        assert client._call.call_args[0][0] == "gdpr_delete_user_data"

    @pytest.mark.asyncio
    async def test_gdpr_export_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"data": []})

        await client.gdpr_export_user_data("user-77")

        assert client._call.call_args[0][0] == "gdpr_export_user_data"
        assert client._call.call_args[1]["user_id"] == "user-77"


# ---------------------------------------------------------------------------
# 10. Lifecycle / history methods
# ---------------------------------------------------------------------------


class TestLifecycleMethods:
    """Spot-checks on lifecycle method tool names."""

    @pytest.mark.asyncio
    async def test_get_memory_history_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value=[])

        await client.get_memory_history("mem-id-1", limit=5)

        assert client._call.call_args[0][0] == "get_memory_history"
        assert client._call.call_args[1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_revert_memory_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"status": "OK"})

        await client.revert_memory("mem-id-2", version_number=3)

        assert client._call.call_args[0][0] == "revert_memory"
        assert client._call.call_args[1]["version_number"] == 3

    @pytest.mark.asyncio
    async def test_promote_memory_tier_tool_name(self) -> None:
        client = EnhancedCogneeClient()
        client._call = AsyncMock(return_value={"status": "OK"})

        await client.promote_memory_tier("mem-id-3")

        assert client._call.call_args[0][0] == "promote_memory_tier"
        assert client._call.call_args[1]["memory_id"] == "mem-id-3"
