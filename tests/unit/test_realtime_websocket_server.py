"""
Unit tests for src/realtime_websocket_server.py

Coverage targets:
- EventType enum members
- WebSocketEvent: __post_init__ (timestamp auto-set), to_json, explicit client_id
- WebSocketClient: init fields
- RealTimeWebSocketServer:
    __init__, start_server (import error path), _handle_client,
    _handle_client_message (subscribe/unsubscribe/ping/unknown/invalid JSON),
    _cleanup_client, _send_event (success + exception),
    broadcast_event (subscribed clients, missing client),
    subscribe_to_event, unsubscribe_from_event (present, not present),
    notify_memory_added/updated/deleted/search_result/summary_generated/
    memory_clustered/error,
    get_connected_clients, get_stats
- RealTimeMemoryIntegration:
    __init__, add_memory_with_notification (success + error),
    update_memory_with_notification (success + fail + error),
    delete_memory_with_notification (success + fail + error)
"""

import json
import sys
import pytest
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.realtime_websocket_server import (
    EventType,
    WebSocketEvent,
    WebSocketClient,
    RealTimeWebSocketServer,
    RealTimeMemoryIntegration,
)


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------


def test_event_type_values():
    assert EventType.MEMORY_ADDED.value == "memory_added"
    assert EventType.MEMORY_UPDATED.value == "memory_updated"
    assert EventType.MEMORY_DELETED.value == "memory_deleted"
    assert EventType.SEARCH_RESULT.value == "search_result"
    assert EventType.SYSTEM_STATUS.value == "system_status"
    assert EventType.ERROR.value == "error"
    assert EventType.NOTIFICATION.value == "notification"
    assert EventType.SUMMARY_GENERATED.value == "summary_generated"
    assert EventType.MEMORY_CLUSTERED.value == "memory_clustered"


# ---------------------------------------------------------------------------
# WebSocketEvent
# ---------------------------------------------------------------------------


def test_websocket_event_auto_timestamp():
    event = WebSocketEvent(event_type=EventType.MEMORY_ADDED, data={"k": "v"})
    assert event.timestamp is not None
    # Should be ISO format parseable
    datetime.fromisoformat(event.timestamp)


def test_websocket_event_explicit_timestamp():
    ts = "2026-01-01T00:00:00+00:00"
    event = WebSocketEvent(
        event_type=EventType.MEMORY_UPDATED,
        data={},
        timestamp=ts
    )
    assert event.timestamp == ts


def test_websocket_event_to_json():
    event = WebSocketEvent(
        event_type=EventType.SEARCH_RESULT,
        data={"query": "test"},
        client_id="client-1"
    )
    payload = json.loads(event.to_json())
    assert payload["event_type"] == "search_result"
    assert payload["data"]["query"] == "test"
    assert payload["client_id"] == "client-1"
    assert "timestamp" in payload


def test_websocket_event_to_json_null_client():
    event = WebSocketEvent(event_type=EventType.ERROR, data={"error": "oops"})
    payload = json.loads(event.to_json())
    assert payload["client_id"] is None


# ---------------------------------------------------------------------------
# WebSocketClient
# ---------------------------------------------------------------------------


def test_websocket_client_init():
    ws = MagicMock()
    client = WebSocketClient("client-42", ws)
    assert client.client_id == "client-42"
    assert client.websocket is ws
    assert isinstance(client.connected_at, datetime)
    assert len(client.subscriptions) == 0


# ---------------------------------------------------------------------------
# RealTimeWebSocketServer.__init__
# ---------------------------------------------------------------------------


def test_server_init_defaults():
    server = RealTimeWebSocketServer()
    assert server.host == "0.0.0.0"
    assert server.port == 8765
    assert server.clients == {}
    assert server.server is None
    # One key per EventType
    assert len(server.subscriptions) == len(EventType)


def test_server_init_custom_host_port():
    server = RealTimeWebSocketServer(host="127.0.0.1", port=9000)
    assert server.host == "127.0.0.1"
    assert server.port == 9000


# ---------------------------------------------------------------------------
# start_server
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_server_import_error():
    server = RealTimeWebSocketServer()
    with patch.dict("sys.modules", {"websockets": None}):
        with pytest.raises((ImportError, TypeError)):
            await server.start_server()


@pytest.mark.asyncio
async def test_start_server_success():
    server = RealTimeWebSocketServer()
    mock_server = MagicMock()
    mock_websockets = MagicMock()
    mock_websockets.serve = AsyncMock(return_value=mock_server)

    with patch.dict("sys.modules", {"websockets": mock_websockets,
                                     "websockets.server": MagicMock()}):
        await server.start_server()

    assert server.server is mock_server


# ---------------------------------------------------------------------------
# _handle_client_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_client_message_subscribe():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client

    msg = json.dumps({"action": "subscribe", "events": ["memory_added", "error"]})
    await server._handle_client_message(client, msg)

    assert "c1" in server.subscriptions[EventType.MEMORY_ADDED]
    assert "c1" in server.subscriptions[EventType.ERROR]
    ws.send.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_message_subscribe_invalid_event():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)

    msg = json.dumps({"action": "subscribe", "events": ["not_real_event"]})
    await server._handle_client_message(client, msg)  # should not raise
    ws.send.assert_called_once()  # still sends the subscription confirmation


@pytest.mark.asyncio
async def test_handle_client_message_unsubscribe():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)

    msg = json.dumps({"action": "unsubscribe", "events": ["memory_added"]})
    await server._handle_client_message(client, msg)

    assert "c1" not in server.subscriptions[EventType.MEMORY_ADDED]


@pytest.mark.asyncio
async def test_handle_client_message_unsubscribe_invalid_event():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)

    msg = json.dumps({"action": "unsubscribe", "events": ["not_real"]})
    await server._handle_client_message(client, msg)  # should not raise


@pytest.mark.asyncio
async def test_handle_client_message_ping():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)

    msg = json.dumps({"action": "ping"})
    await server._handle_client_message(client, msg)
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["data"]["status"] == "pong"


@pytest.mark.asyncio
async def test_handle_client_message_unknown_action():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)

    msg = json.dumps({"action": "frobnicate"})
    await server._handle_client_message(client, msg)  # should not raise
    ws.send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_client_message_invalid_json():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)

    await server._handle_client_message(client, "NOT JSON {{{")
    ws.send.assert_not_called()


# ---------------------------------------------------------------------------
# _cleanup_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_client_removes_from_clients_and_subscriptions():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)

    await server._cleanup_client("c1")

    assert "c1" not in server.clients
    assert "c1" not in server.subscriptions[EventType.MEMORY_ADDED]


@pytest.mark.asyncio
async def test_cleanup_client_unknown_id_is_noop():
    server = RealTimeWebSocketServer()
    await server._cleanup_client("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# _send_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_event_success():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    event = WebSocketEvent(event_type=EventType.ERROR, data={"error": "test"})

    await server._send_event(client, event)
    ws.send.assert_called_once()


@pytest.mark.asyncio
async def test_send_event_exception_is_caught():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock(side_effect=RuntimeError("connection closed"))
    client = WebSocketClient("c1", ws)
    event = WebSocketEvent(event_type=EventType.ERROR, data={"error": "test"})

    await server._send_event(client, event)  # should not raise


# ---------------------------------------------------------------------------
# broadcast_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_event_sends_to_subscribed_clients():
    server = RealTimeWebSocketServer()
    ws1 = MagicMock()
    ws1.send = AsyncMock()
    ws2 = MagicMock()
    ws2.send = AsyncMock()

    client1 = WebSocketClient("c1", ws1)
    client2 = WebSocketClient("c2", ws2)
    server.clients["c1"] = client1
    server.clients["c2"] = client2
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)
    # c2 is NOT subscribed

    event = WebSocketEvent(event_type=EventType.MEMORY_ADDED, data={})
    await server.broadcast_event(event)

    ws1.send.assert_called_once()
    ws2.send.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_event_skips_disconnected_clients():
    """Client in subscriptions but not in server.clients dict."""
    server = RealTimeWebSocketServer()
    server.subscriptions[EventType.MEMORY_ADDED].add("ghost-client")

    event = WebSocketEvent(event_type=EventType.MEMORY_ADDED, data={})
    await server.broadcast_event(event)  # should not raise


@pytest.mark.asyncio
async def test_broadcast_event_empty_subscriptions():
    server = RealTimeWebSocketServer()
    event = WebSocketEvent(event_type=EventType.ERROR, data={})
    await server.broadcast_event(event)  # should not raise


# ---------------------------------------------------------------------------
# subscribe / unsubscribe
# ---------------------------------------------------------------------------


def test_subscribe_to_event():
    server = RealTimeWebSocketServer()
    server.subscribe_to_event("c1", EventType.NOTIFICATION)
    assert "c1" in server.subscriptions[EventType.NOTIFICATION]


def test_unsubscribe_from_event_present():
    server = RealTimeWebSocketServer()
    server.subscribe_to_event("c1", EventType.NOTIFICATION)
    server.unsubscribe_from_event("c1", EventType.NOTIFICATION)
    assert "c1" not in server.subscriptions[EventType.NOTIFICATION]


def test_unsubscribe_from_event_not_subscribed():
    server = RealTimeWebSocketServer()
    server.unsubscribe_from_event("c1", EventType.NOTIFICATION)  # should not raise


# ---------------------------------------------------------------------------
# notify_* convenience helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_memory_added():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)

    await server.notify_memory_added("mem-1", "content text", "agent-1")
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["event_type"] == "memory_added"
    assert payload["data"]["memory_id"] == "mem-1"


@pytest.mark.asyncio
async def test_notify_memory_updated():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_UPDATED)

    await server.notify_memory_updated("mem-1", "new content")
    ws.send.assert_called_once()


@pytest.mark.asyncio
async def test_notify_memory_deleted():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_DELETED)

    await server.notify_memory_deleted("mem-1")
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["data"]["memory_id"] == "mem-1"


@pytest.mark.asyncio
async def test_notify_search_result():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.SEARCH_RESULT)

    await server.notify_search_result("test query", 3, [{"id": "m1"}])
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["data"]["query"] == "test query"
    assert payload["data"]["results_count"] == 3


@pytest.mark.asyncio
async def test_notify_summary_generated():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.SUMMARY_GENERATED)

    await server.notify_summary_generated("mem-1", 0.75)
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["data"]["compression_ratio"] == 0.75


@pytest.mark.asyncio
async def test_notify_memory_clustered():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_CLUSTERED)

    await server.notify_memory_clustered("cluster-42", 10)
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert payload["data"]["cluster_id"] == "cluster-42"
    assert payload["data"]["memory_count"] == 10


@pytest.mark.asyncio
async def test_notify_error():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.ERROR)

    await server.notify_error("Something went wrong")
    ws.send.assert_called_once()
    payload = json.loads(ws.send.call_args[0][0])
    assert "Something went wrong" in payload["data"]["error"]


# ---------------------------------------------------------------------------
# notify content truncation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_memory_added_content_truncated_at_100():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)

    long_content = "x" * 200
    await server.notify_memory_added("mem-1", long_content, "agent-1")
    payload = json.loads(ws.send.call_args[0][0])
    assert len(payload["data"]["content_preview"]) == 100


# ---------------------------------------------------------------------------
# get_connected_clients / get_stats
# ---------------------------------------------------------------------------


def test_get_connected_clients_empty():
    server = RealTimeWebSocketServer()
    result = server.get_connected_clients()
    assert result == []


def test_get_connected_clients_with_subscriptions():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)
    server.subscribe_to_event("c1", EventType.ERROR)

    clients = server.get_connected_clients()
    assert len(clients) == 1
    subs = clients[0]["subscriptions"]
    assert "memory_added" in subs
    assert "error" in subs


def test_get_stats_empty():
    server = RealTimeWebSocketServer()
    stats = server.get_stats()
    assert stats["total_clients"] == 0
    assert isinstance(stats["subscriptions"], dict)


def test_get_stats_with_clients_and_subs():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    client = WebSocketClient("c1", ws)
    server.clients["c1"] = client
    server.subscribe_to_event("c1", EventType.MEMORY_ADDED)

    stats = server.get_stats()
    assert stats["total_clients"] == 1
    assert stats["subscriptions"]["memory_added"] == 1


# ---------------------------------------------------------------------------
# _handle_client (integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_client_registers_and_cleanup():
    server = RealTimeWebSocketServer()
    ws = MagicMock()
    ws.send = AsyncMock()

    # Make async iteration yield no messages (immediate disconnect)
    async def _aiter():
        return
        yield  # makes it an async generator

    ws.__aiter__ = lambda self: _aiter()
    ws.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

    client_id = f"client_{id(ws)}"
    await server._handle_client(ws, "/")
    # After handler returns, client should have been cleaned up
    assert client_id not in server.clients


# ---------------------------------------------------------------------------
# RealTimeMemoryIntegration
# ---------------------------------------------------------------------------


def test_real_time_memory_integration_init():
    ws_server = RealTimeWebSocketServer()
    mem = MagicMock()
    integration = RealTimeMemoryIntegration(ws_server, mem)
    assert integration.ws_server is ws_server
    assert integration.memory_integration is mem


@pytest.mark.asyncio
async def test_add_memory_with_notification_success():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_memory_added = AsyncMock()

    mem = MagicMock()
    mem.add_memory = AsyncMock(return_value="mem-100")

    integration = RealTimeMemoryIntegration(ws_server, mem)
    result = await integration.add_memory_with_notification("content", "agent-1")

    assert result == "mem-100"
    ws_server.notify_memory_added.assert_called_once_with("mem-100", "content", "agent-1")


@pytest.mark.asyncio
async def test_add_memory_with_notification_error():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_error = AsyncMock()

    mem = MagicMock()
    mem.add_memory = AsyncMock(side_effect=RuntimeError("db fail"))

    integration = RealTimeMemoryIntegration(ws_server, mem)
    with pytest.raises(RuntimeError):
        await integration.add_memory_with_notification("content", "agent-1")
    ws_server.notify_error.assert_called_once()


@pytest.mark.asyncio
async def test_update_memory_with_notification_success():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_memory_updated = AsyncMock()

    mem = MagicMock()
    mem.update_memory = AsyncMock(return_value=True)

    integration = RealTimeMemoryIntegration(ws_server, mem)
    result = await integration.update_memory_with_notification("mem-1", "new content")

    assert result is True
    ws_server.notify_memory_updated.assert_called_once_with("mem-1", "new content")


@pytest.mark.asyncio
async def test_update_memory_with_notification_false():
    """update_memory returns False -> no ws notification."""
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_memory_updated = AsyncMock()

    mem = MagicMock()
    mem.update_memory = AsyncMock(return_value=False)

    integration = RealTimeMemoryIntegration(ws_server, mem)
    result = await integration.update_memory_with_notification("mem-1", "content")

    assert result is False
    ws_server.notify_memory_updated.assert_not_called()


@pytest.mark.asyncio
async def test_update_memory_with_notification_error():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_error = AsyncMock()

    mem = MagicMock()
    mem.update_memory = AsyncMock(side_effect=RuntimeError("fail"))

    integration = RealTimeMemoryIntegration(ws_server, mem)
    with pytest.raises(RuntimeError):
        await integration.update_memory_with_notification("mem-1", "content")
    ws_server.notify_error.assert_called_once()


@pytest.mark.asyncio
async def test_delete_memory_with_notification_success():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_memory_deleted = AsyncMock()

    mem = MagicMock()
    mem.delete_memory = AsyncMock(return_value=True)

    integration = RealTimeMemoryIntegration(ws_server, mem)
    result = await integration.delete_memory_with_notification("mem-1")

    assert result is True
    ws_server.notify_memory_deleted.assert_called_once_with("mem-1")


@pytest.mark.asyncio
async def test_delete_memory_with_notification_false():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_memory_deleted = AsyncMock()

    mem = MagicMock()
    mem.delete_memory = AsyncMock(return_value=False)

    integration = RealTimeMemoryIntegration(ws_server, mem)
    result = await integration.delete_memory_with_notification("mem-1")

    assert result is False
    ws_server.notify_memory_deleted.assert_not_called()


@pytest.mark.asyncio
async def test_delete_memory_with_notification_error():
    ws_server = RealTimeWebSocketServer()
    ws_server.notify_error = AsyncMock()

    mem = MagicMock()
    mem.delete_memory = AsyncMock(side_effect=RuntimeError("fail"))

    integration = RealTimeMemoryIntegration(ws_server, mem)
    with pytest.raises(RuntimeError):
        await integration.delete_memory_with_notification("mem-1")
    ws_server.notify_error.assert_called_once()
