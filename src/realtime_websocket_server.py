#!/usr/bin/env python3
"""
Real-Time WebSocket Server for Enhanced Cognee Dashboard
Provides WebSocket connections for live updates, memory changes, and notifications
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """WebSocket event types"""
    MEMORY_ADDED = "memory_added"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    SEARCH_RESULT = "search_result"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    NOTIFICATION = "notification"
    SUMMARY_GENERATED = "summary_generated"
    MEMORY_CLUSTERED = "memory_clustered"


@dataclass
class WebSocketEvent:
    """WebSocket event message"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str = None
    client_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_json(self) -> str:
        """Convert event to JSON"""
        return json.dumps({
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "client_id": self.client_id
        })


class RealTimeWebSocketServer:
    """
    Real-Time WebSocket Server for Enhanced Cognee

    Features:
    - Live memory updates
    - Real-time search results
    - System status monitoring
    - Client connection management
    - Event broadcasting
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize WebSocket server

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port

        # Connected clients
        self.clients: Dict[str, WebSocketClient] = {}

        # Event subscriptions
        self.subscriptions: Dict[EventType, Set[str]] = {
            event_type: set() for event_type in EventType
        }

        # Server instance
        self.server = None

        logger.info(f"OK Real-Time WebSocket Server initialized on {host}:{port}")

    async def start_server(self):
        """Start WebSocket server"""
        try:
            import websockets
            from websockets.server import WebSocketServerProtocol

            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10
            )

            logger.info(f"OK WebSocket server started on ws://{self.host}:{self.port}")

        except ImportError:
            logger.error("websockets library not available. Install: pip install websockets")
            raise

    async def _handle_client(self, websocket, path: str):
        """Handle new WebSocket client connection"""
        client_id = f"client_{id(websocket)}"

        try:
            # Register client
            client = WebSocketClient(client_id, websocket)
            self.clients[client_id] = client

            logger.info(f"OK Client connected: {client_id}")

            # Send welcome message
            await self._send_event(client, WebSocketEvent(
                event_type=EventType.SYSTEM_STATUS,
                data={
                    "status": "connected",
                    "message": "Connected to Enhanced Cognee Real-Time Server",
                    "available_events": [e.value for e in EventType]
                }
            ))

            # Handle messages from client
            async for message in websocket:
                await self._handle_client_message(client, message)

        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")

        finally:
            # Unregister client
            await self._cleanup_client(client_id)

    async def _handle_client_message(self, client, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                # Subscribe to events
                event_types = data.get("events", [])
                for event_type_str in event_types:
                    try:
                        event_type = EventType(event_type_str)
                        self.subscribe_to_event(client.client_id, event_type)
                    except ValueError:
                        logger.warning(f"Invalid event type: {event_type_str}")

                await self._send_event(client, WebSocketEvent(
                    event_type=EventType.SYSTEM_STATUS,
                    data={
                        "status": "subscribed",
                        "events": event_types
                    }
                ))

            elif action == "unsubscribe":
                # Unsubscribe from events
                event_types = data.get("events", [])
                for event_type_str in event_types:
                    try:
                        event_type = EventType(event_type_str)
                        self.unsubscribe_from_event(client.client_id, event_type)
                    except ValueError:
                        pass

            elif action == "ping":
                # Respond to ping
                await self._send_event(client, WebSocketEvent(
                    event_type=EventType.SYSTEM_STATUS,
                    data={"status": "pong"}
                ))

            else:
                logger.warning(f"Unknown action: {action}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client.client_id}")

    async def _cleanup_client(self, client_id: str):
        """Clean up disconnected client"""
        if client_id in self.clients:
            del self.clients[client_id]

        # Remove from all subscriptions
        for event_type in EventType:
            if client_id in self.subscriptions[event_type]:
                self.subscriptions[event_type].remove(client_id)

        logger.info(f"OK Client disconnected: {client_id}")

    async def _send_event(self, client, event: WebSocketEvent):
        """Send event to specific client"""
        try:
            await client.websocket.send(event.to_json())
        except Exception as e:
            logger.error(f"Failed to send event to {client.client_id}: {e}")

    async def broadcast_event(self, event: WebSocketEvent):
        """Broadcast event to all subscribed clients"""
        event_type = event.event_type
        subscribed_clients = self.subscriptions.get(event_type, set())

        for client_id in subscribed_clients:
            if client_id in self.clients:
                await self._send_event(self.clients[client_id], event)

        logger.debug(f"Broadcasted {event_type.value} to {len(subscribed_clients)} clients")

    def subscribe_to_event(self, client_id: str, event_type: EventType):
        """Subscribe client to event type"""
        self.subscriptions[event_type].add(client_id)
        logger.debug(f"Client {client_id} subscribed to {event_type.value}")

    def unsubscribe_from_event(self, client_id: str, event_type: EventType):
        """Unsubscribe client from event type"""
        if client_id in self.subscriptions[event_type]:
            self.subscriptions[event_type].remove(client_id)
            logger.debug(f"Client {client_id} unsubscribed from {event_type.value}")

    async def notify_memory_added(self, memory_id: str, content: str, agent_id: str):
        """Notify clients about new memory"""
        event = WebSocketEvent(
            event_type=EventType.MEMORY_ADDED,
            data={
                "memory_id": memory_id,
                "content_preview": content[:100],
                "agent_id": agent_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
        await self.broadcast_event(event)

    async def notify_memory_updated(self, memory_id: str, content: str):
        """Notify clients about memory update"""
        event = WebSocketEvent(
            event_type=EventType.MEMORY_UPDATED,
            data={
                "memory_id": memory_id,
                "content_preview": content[:100],
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
        await self.broadcast_event(event)

    async def notify_memory_deleted(self, memory_id: str):
        """Notify clients about memory deletion"""
        event = WebSocketEvent(
            event_type=EventType.MEMORY_DELETED,
            data={
                "memory_id": memory_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
        await self.broadcast_event(event)

    async def notify_search_result(self, query: str, results_count: int, top_results: List[Dict]):
        """Notify clients about search results"""
        event = WebSocketEvent(
            event_type=EventType.SEARCH_RESULT,
            data={
                "query": query,
                "results_count": results_count,
                "top_results": top_results[:5]
            }
        )
        await self.broadcast_event(event)

    async def notify_summary_generated(self, memory_id: str, compression_ratio: float):
        """Notify clients about summary generation"""
        event = WebSocketEvent(
            event_type=EventType.SUMMARY_GENERATED,
            data={
                "memory_id": memory_id,
                "compression_ratio": compression_ratio
            }
        )
        await self.broadcast_event(event)

    async def notify_memory_clustered(self, cluster_id: str, memory_count: int):
        """Notify clients about memory clustering"""
        event = WebSocketEvent(
            event_type=EventType.MEMORY_CLUSTERED,
            data={
                "cluster_id": cluster_id,
                "memory_count": memory_count
            }
        )
        await self.broadcast_event(event)

    async def notify_error(self, error_message: str):
        """Notify clients about error"""
        event = WebSocketEvent(
            event_type=EventType.ERROR,
            data={
                "error": error_message,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
        await self.broadcast_event(event)

    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected clients"""
        return [
            {
                "client_id": client.client_id,
                "subscriptions": [
                    event_type.value for event_type in EventType
                    if client.client_id in self.subscriptions[event_type]
                ]
            }
            for client in self.clients.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "total_clients": len(self.clients),
            "subscriptions": {
                event_type.value: len(clients)
                for event_type, clients in self.subscriptions.items()
            }
        }


class WebSocketClient:
    """WebSocket client representation"""

    def __init__(self, client_id: str, websocket):
        self.client_id = client_id
        self.websocket = websocket
        self.connected_at = datetime.now(UTC)
        self.subscriptions: Set[EventType] = set()


# Integration with Enhanced Cognee Memory Operations
class RealTimeMemoryIntegration:
    """
    Integrates WebSocket server with memory operations
    Automatically notifies clients of memory changes
    """

    def __init__(self, ws_server: RealTimeWebSocketServer, memory_integration):
        """
        Initialize real-time memory integration

        Args:
            ws_server: WebSocket server instance
            memory_integration: Enhanced Cognee memory integration
        """
        self.ws_server = ws_server
        self.memory_integration = memory_integration

        logger.info("OK Real-Time Memory Integration initialized")

    async def add_memory_with_notification(
        self,
        content: str,
        agent_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add memory and notify clients"""
        try:
            # Add memory
            memory_id = await self.memory_integration.add_memory(
                content=content,
                agent_id=agent_id,
                metadata=metadata or {}
            )

            # Notify clients
            await self.ws_server.notify_memory_added(memory_id, content, agent_id)

            return memory_id

        except Exception as e:
            logger.error(f"Failed to add memory with notification: {e}")
            await self.ws_server.notify_error(f"Failed to add memory: {str(e)}")
            raise

    async def update_memory_with_notification(
        self,
        memory_id: str,
        content: str
    ) -> bool:
        """Update memory and notify clients"""
        try:
            # Update memory
            success = await self.memory_integration.update_memory(memory_id, content)

            if success:
                # Notify clients
                await self.ws_server.notify_memory_updated(memory_id, content)

            return success

        except Exception as e:
            logger.error(f"Failed to update memory with notification: {e}")
            await self.ws_server.notify_error(f"Failed to update memory: {str(e)}")
            raise

    async def delete_memory_with_notification(self, memory_id: str) -> bool:
        """Delete memory and notify clients"""
        try:
            # Delete memory
            success = await self.memory_integration.delete_memory(memory_id)

            if success:
                # Notify clients
                await self.ws_server.notify_memory_deleted(memory_id)

            return success

        except Exception as e:
            logger.error(f"Failed to delete memory with notification: {e}")
            await self.ws_server.notify_error(f"Failed to delete memory: {str(e)}")
            raise


# Example usage
async def example_websocket_server():
    """Example usage of WebSocket server"""
    server = RealTimeWebSocketServer(host="localhost", port=8765)

    # Start server
    await server.start_server()

    # Simulate memory operations
    await asyncio.sleep(1)

    # Notify clients
    await server.notify_memory_added(
        memory_id="mem_001",
        content="This is a test memory",
        agent_id="test_agent"
    )

    # Keep server running
    logger.info("WebSocket server running. Press Ctrl+C to stop.")
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(example_websocket_server())
