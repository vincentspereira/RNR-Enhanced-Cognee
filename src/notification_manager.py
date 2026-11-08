"""
Notification Manager - Phase 12 (17.4)
=========================================
Delivers Slack and Discord notifications when RNR Enhanced Cognee events occur.

Features:
    - Slack webhook integration (blocks-based messages)
    - Discord webhook integration (embed-based messages)
    - Per-channel event type filtering
    - Enable/disable individual channels without deleting them
    - In-memory config store (no DB dependency)
    - aiohttp if available, falls back to urllib.request for sync POST

Supported events:
    memory.added, memory.updated, memory.deleted,
    backup.completed, backup.failed, health.degraded
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UTC = timezone.utc

NOTIFICATION_EVENTS = {
    "memory.added",
    "memory.updated",
    "memory.deleted",
    "backup.completed",
    "backup.failed",
    "health.degraded",
}


class NotificationManager:
    """
    Manage Slack and Discord notification channels and deliver event messages.

    Storage: in-memory dict keyed by channel_id.  Channels survive the process
    but not restarts.  Extend configure_* to write to PostgreSQL for persistence.
    """

    def __init__(self) -> None:
        # channel_id -> {"type": str, "webhook_url": str, "events": List[str], "enabled": bool}
        self._channels: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def configure_slack(
        self,
        channel_id: str,
        webhook_url: str,
        events: List[str],
    ) -> Dict[str, Any]:
        """
        Register or update a Slack webhook channel.

        Returns the stored channel config dict.
        """
        unknown = set(events) - NOTIFICATION_EVENTS
        if unknown:
            logger.warning(
                "configure_slack: unknown event type(s) for channel %s: %s",
                channel_id,
                unknown,
            )

        self._channels[channel_id] = {
            "channel_id": channel_id,
            "type": "slack",
            "webhook_url": webhook_url,
            "events": list(events),
            "enabled": True,
        }
        logger.info("OK Slack channel configured: %s", channel_id)
        return self._channels[channel_id]

    async def configure_discord(
        self,
        channel_id: str,
        webhook_url: str,
        events: List[str],
    ) -> Dict[str, Any]:
        """
        Register or update a Discord webhook channel.

        Returns the stored channel config dict.
        """
        unknown = set(events) - NOTIFICATION_EVENTS
        if unknown:
            logger.warning(
                "configure_discord: unknown event type(s) for channel %s: %s",
                channel_id,
                unknown,
            )

        self._channels[channel_id] = {
            "channel_id": channel_id,
            "type": "discord",
            "webhook_url": webhook_url,
            "events": list(events),
            "enabled": True,
        }
        logger.info("OK Discord channel configured: %s", channel_id)
        return self._channels[channel_id]

    # ------------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------------

    async def test_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Send a test payload to the given channel.

        Returns {"ok": bool, "channel_id": str, "response_code": int}.
        """
        cfg = self._channels.get(channel_id)
        if not cfg:
            logger.warning("test_channel: channel not found: %s", channel_id)
            return {"ok": False, "channel_id": channel_id, "response_code": 0}

        test_data: Dict[str, Any] = {
            "test": True,
            "channel_id": channel_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        text = f"RNR Enhanced Cognee test notification for channel: {channel_id}"

        if cfg["type"] == "slack":
            payload = self._build_slack_payload("notification.test", text, test_data)
        else:
            payload = self._build_discord_payload("notification.test", text, test_data)

        status_code = await self._post_json(cfg["webhook_url"], payload)
        ok = 200 <= status_code < 300
        if ok:
            logger.info("OK test_channel succeeded for %s (HTTP %s)", channel_id, status_code)
        else:
            logger.warning(
                "WARN test_channel got HTTP %s for channel %s", status_code, channel_id
            )
        return {"ok": ok, "channel_id": channel_id, "response_code": status_code}

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deliver *event* to all enabled channels subscribed to it.

        Returns {"delivered": int, "failed": int, "skipped": int}.
        """
        if event not in NOTIFICATION_EVENTS:
            logger.debug("send_notification: event %s not in NOTIFICATION_EVENTS", event)

        delivered = 0
        failed = 0
        skipped = 0

        timestamp = datetime.now(UTC).isoformat()
        text = f"[{event}] at {timestamp}"

        for channel_id, cfg in list(self._channels.items()):
            if not cfg.get("enabled", True):
                skipped += 1
                continue
            if event not in cfg.get("events", []):
                skipped += 1
                continue

            if cfg["type"] == "slack":
                payload = self._build_slack_payload(event, text, data)
            else:
                payload = self._build_discord_payload(event, text, data)

            status_code = await self._post_json(cfg["webhook_url"], payload)
            if 200 <= status_code < 300:
                delivered += 1
                logger.debug(
                    "OK send_notification delivered event %s to channel %s",
                    event,
                    channel_id,
                )
            else:
                failed += 1
                logger.warning(
                    "WARN send_notification HTTP %s for event %s channel %s",
                    status_code,
                    event,
                    channel_id,
                )

        return {"delivered": delivered, "failed": failed, "skipped": skipped}

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_channels(self) -> List[Dict[str, Any]]:
        """Return all configured channels as a list of dicts (with channel_id included)."""
        result = []
        for channel_id, cfg in self._channels.items():
            entry = dict(cfg)
            entry["channel_id"] = channel_id
            result.append(entry)
        return result

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_slack_payload(
        event: str,
        text: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a Slack webhook payload with a single section block."""
        data_preview = str(data)[:400]
        block_text = f"*{event}*\n{text}\n```{data_preview}```"
        return {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": block_text,
                    },
                }
            ],
        }

    @staticmethod
    def _build_discord_payload(
        event: str,
        text: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a Discord webhook payload with an embed."""
        description = str(data)[:500]
        return {
            "content": text,
            "embeds": [
                {
                    "title": event,
                    "description": description,
                }
            ],
        }

    # ------------------------------------------------------------------
    # HTTP transport
    # ------------------------------------------------------------------

    @staticmethod
    async def _post_json(url: str, payload: Dict[str, Any]) -> int:
        """Send only to an operator-approved HTTPS origin, without redirects."""
        from src.security.capabilities import validate_destination
        try:
            validate_destination(url)
            import httpx
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
                response = await client.post(url, content=json.dumps(payload, ensure_ascii=True).encode(),
                                             headers={"Content-Type": "application/json"})
                return response.status_code
        except Exception:
            logger.debug("Notification delivery unavailable or denied")
            return 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_notification_manager: Optional[NotificationManager] = None


def init_notification_manager() -> NotificationManager:
    """Create and store the global NotificationManager singleton."""
    global _notification_manager
    _notification_manager = NotificationManager()
    logger.info("OK NotificationManager initialized")
    return _notification_manager


def get_notification_manager() -> Optional[NotificationManager]:
    """Return the global NotificationManager singleton, or None if not initialised."""
    return _notification_manager
