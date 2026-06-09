"""
Webhook Manager - Phase 12 (17.2)
====================================
Delivers HMAC-signed HTTP POST notifications to registered endpoints when
Enhanced Cognee events occur (memory added, backup complete, consolidation
finished, GDPR request processed, etc.).

Features:
    - HMAC-SHA256 signatures (header: X-Enhanced-Cognee-Signature)
    - Configurable retry with exponential backoff (up to 3 attempts)
    - Per-webhook event type filtering
    - Enable/disable individual webhooks without deleting them
    - In-memory storage (no DB dependency); falls back gracefully

Webhook payload structure:
    {
        "event": "memory.added",
        "timestamp": "2026-05-13T12:00:00Z",
        "data": { ... event-specific data ... },
        "webhook_id": "wh-abc123"
    }

Signature verification (for receiver):
    import hmac, hashlib
    expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    assert request.headers["X-Enhanced-Cognee-Signature"] == f"sha256={expected}"
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Retry configuration
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds (doubles each attempt)

# Supported event types
WEBHOOK_EVENTS = {
    "memory.added",
    "memory.updated",
    "memory.deleted",
    "memory.reverted",
    "backup.completed",
    "backup.failed",
    "consolidation.completed",
    "gdpr.delete_requested",
    "gdpr.export_requested",
    "maintenance.completed",
    "health.degraded",
    "health.recovered",
}


class WebhookConfig:
    """Represents a single registered webhook endpoint."""

    def __init__(
        self,
        url: str,
        secret: str,
        events: Optional[List[str]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.id = f"wh-{uuid.uuid4().hex[:8]}"
        self.url = url
        self.secret = secret
        self.events = set(events) if events else set(WEBHOOK_EVENTS)  # subscribe all
        self.name = name or self.id
        self.enabled = True
        self.created_at = datetime.now(UTC).isoformat()
        self.last_triggered: Optional[str] = None
        self.delivery_count = 0
        self.failure_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": sorted(self.events),
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
            "delivery_count": self.delivery_count,
            "failure_count": self.failure_count,
        }


class WebhookManager:
    """
    Manage webhook registrations and deliver signed event notifications.

    Storage: in-memory dict (webhooks survive the process but not restarts).
    For persistent storage, extend _store_webhook / _load_webhooks to
    write to PostgreSQL.
    """

    def __init__(self) -> None:
        self._webhooks: Dict[str, WebhookConfig] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        url: str,
        secret: str,
        events: Optional[List[str]] = None,
        name: Optional[str] = None,
    ) -> WebhookConfig:
        """Register a new webhook endpoint and return its config."""
        # Validate events
        if events:
            unknown = set(events) - WEBHOOK_EVENTS
            if unknown:
                logger.warning(
                    "register_webhook: unknown event type(s): %s", unknown
                )
        wh = WebhookConfig(url=url, secret=secret, events=events, name=name)
        self._webhooks[wh.id] = wh
        logger.info("Registered webhook %s -> %s", wh.id, url)
        return wh

    def deregister(self, webhook_id: str) -> bool:
        """Permanently remove a webhook. Returns True if found and removed."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info("Deregistered webhook %s", webhook_id)
            return True
        return False

    def disable(self, webhook_id: str) -> bool:
        """Temporarily disable a webhook without deleting it."""
        wh = self._webhooks.get(webhook_id)
        if not wh:
            return False
        wh.enabled = False
        return True

    def enable(self, webhook_id: str) -> bool:
        """Re-enable a previously disabled webhook."""
        wh = self._webhooks.get(webhook_id)
        if not wh:
            return False
        wh.enabled = True
        return True

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """Return all registered webhooks as dicts."""
        return [wh.to_dict() for wh in self._webhooks.values()]

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        return self._webhooks.get(webhook_id)

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    @staticmethod
    def _sign_payload(secret: str, body: bytes) -> str:
        """Return HMAC-SHA256 hex signature of *body* using *secret*."""
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    async def _deliver_once(
        self,
        wh: WebhookConfig,
        payload: Dict[str, Any],
    ) -> bool:
        """Attempt a single delivery. Returns True on HTTP 2xx."""
        import asyncio

        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        signature = self._sign_payload(wh.secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-Enhanced-Cognee-Signature": signature,
            "X-Enhanced-Cognee-Event": payload.get("event", "unknown"),
            "X-Enhanced-Cognee-Webhook-ID": wh.id,
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(wh.url, content=body, headers=headers)
                return 200 <= resp.status_code < 300
        except ImportError:
            # httpx not installed — try stdlib urllib
            import urllib.request
            req = urllib.request.Request(
                wh.url,
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=10)
                )
                return 200 <= int(response.status) <= 299
            except Exception as exc:
                logger.debug("_deliver_once urllib failed: %s", exc)
                return False
        except Exception as exc:
            logger.debug("_deliver_once failed for %s: %s", wh.url, exc)
            return False

    async def fire(
        self,
        event: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """
        Deliver *event* to all enabled webhooks subscribed to it.

        Returns {"delivered": N, "failed": N, "skipped": N}.
        """
        import asyncio

        payload_base: Dict[str, Any] = {
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data or {},
        }

        delivered = 0
        failed = 0
        skipped = 0

        for wh in list(self._webhooks.values()):
            if not wh.enabled:
                skipped += 1
                continue
            if event not in wh.events:
                skipped += 1
                continue

            payload = dict(payload_base)
            payload["webhook_id"] = wh.id

            success = False
            for attempt in range(_MAX_RETRIES):
                success = await self._deliver_once(wh, payload)
                if success:
                    break
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE ** attempt
                    await asyncio.sleep(wait)

            wh.last_triggered = datetime.now(UTC).isoformat()
            if success:
                wh.delivery_count += 1
                delivered += 1
            else:
                wh.failure_count += 1
                failed += 1
                logger.warning(
                    "Webhook %s delivery failed for event %s after %d attempts",
                    wh.id, event, _MAX_RETRIES,
                )

        return {"delivered": delivered, "failed": failed, "skipped": skipped}

    async def test_webhook(self, webhook_id: str) -> bool:
        """Send a test ping to a specific webhook. Returns True on success."""
        wh = self._webhooks.get(webhook_id)
        if not wh:
            return False
        result = await self.fire("webhook.test", {"test": True, "webhook_id": webhook_id})
        return result.get("delivered", 0) > 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_webhook_manager: Optional[WebhookManager] = None


def init_webhook_manager() -> WebhookManager:
    global _webhook_manager
    _webhook_manager = WebhookManager()
    logger.info("OK WebhookManager initialized")
    return _webhook_manager


def get_webhook_manager() -> Optional[WebhookManager]:
    return _webhook_manager
