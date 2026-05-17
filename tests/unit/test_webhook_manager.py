"""
Unit tests for src/webhook_manager.py
Covers: WebhookConfig, WebhookManager (register, deregister, disable, enable,
        list_webhooks, get_webhook, _sign_payload, _deliver_once, fire,
        test_webhook), singleton helpers.

HTTP calls are mocked via AsyncMock so no network access occurs.
"""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.webhook_manager import (
    WebhookConfig,
    WebhookManager,
    WEBHOOK_EVENTS,
    init_webhook_manager,
    get_webhook_manager,
)


# ---------------------------------------------------------------------------
# WebhookConfig
# ---------------------------------------------------------------------------

class TestWebhookConfig:
    @pytest.mark.unit
    def test_id_has_wh_prefix(self):
        wh = WebhookConfig(url="https://example.com/hook", secret="s3cr3t")
        assert wh.id.startswith("wh-")

    @pytest.mark.unit
    def test_default_subscribes_all_events(self):
        wh = WebhookConfig(url="https://example.com/hook", secret="s3cr3t")
        assert wh.events == WEBHOOK_EVENTS

    @pytest.mark.unit
    def test_custom_events_subset(self):
        wh = WebhookConfig(
            url="https://example.com/hook",
            secret="s3cr3t",
            events=["memory.added"],
        )
        assert wh.events == {"memory.added"}

    @pytest.mark.unit
    def test_default_name_is_id(self):
        wh = WebhookConfig(url="https://x.com", secret="s")
        assert wh.name == wh.id

    @pytest.mark.unit
    def test_custom_name_stored(self):
        wh = WebhookConfig(url="https://x.com", secret="s", name="my-hook")
        assert wh.name == "my-hook"

    @pytest.mark.unit
    def test_enabled_by_default(self):
        wh = WebhookConfig(url="https://x.com", secret="s")
        assert wh.enabled is True

    @pytest.mark.unit
    def test_counters_start_at_zero(self):
        wh = WebhookConfig(url="https://x.com", secret="s")
        assert wh.delivery_count == 0
        assert wh.failure_count == 0

    @pytest.mark.unit
    def test_to_dict_contains_required_fields(self):
        wh = WebhookConfig(url="https://x.com", secret="s", name="test")
        d = wh.to_dict()
        assert "id" in d
        assert "url" in d
        assert "events" in d
        assert "enabled" in d
        assert "created_at" in d
        assert "delivery_count" in d
        assert "failure_count" in d

    @pytest.mark.unit
    def test_to_dict_events_sorted(self):
        wh = WebhookConfig(url="https://x.com", secret="s", events=["memory.deleted", "memory.added"])
        d = wh.to_dict()
        assert d["events"] == sorted(["memory.deleted", "memory.added"])


# ---------------------------------------------------------------------------
# WebhookManager - registration
# ---------------------------------------------------------------------------

class TestWebhookManagerRegistration:
    @pytest.fixture
    def mgr(self):
        return WebhookManager()

    @pytest.mark.unit
    def test_register_returns_webhook_config(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        assert isinstance(wh, WebhookConfig)

    @pytest.mark.unit
    def test_register_stores_webhook(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        assert mgr.get_webhook(wh.id) is wh

    @pytest.mark.unit
    def test_register_with_events_warns_unknown(self, mgr):
        import logging
        with patch.object(logging.getLogger("src.webhook_manager"), "warning") as mock_warn:
            mgr.register("https://x.com", "secret", events=["unknown.event"])
            mock_warn.assert_called_once()

    @pytest.mark.unit
    def test_register_known_events_no_warning(self, mgr):
        import logging
        with patch.object(logging.getLogger("src.webhook_manager"), "warning") as mock_warn:
            mgr.register("https://x.com", "secret", events=["memory.added"])
            mock_warn.assert_not_called()

    @pytest.mark.unit
    def test_deregister_returns_true_if_found(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        result = mgr.deregister(wh.id)
        assert result is True

    @pytest.mark.unit
    def test_deregister_removes_webhook(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        mgr.deregister(wh.id)
        assert mgr.get_webhook(wh.id) is None

    @pytest.mark.unit
    def test_deregister_missing_returns_false(self, mgr):
        assert mgr.deregister("wh-nonexistent") is False

    @pytest.mark.unit
    def test_disable_sets_enabled_false(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        result = mgr.disable(wh.id)
        assert result is True
        assert wh.enabled is False

    @pytest.mark.unit
    def test_disable_missing_returns_false(self, mgr):
        assert mgr.disable("wh-missing") is False

    @pytest.mark.unit
    def test_enable_sets_enabled_true(self, mgr):
        wh = mgr.register("https://x.com", "secret")
        mgr.disable(wh.id)
        result = mgr.enable(wh.id)
        assert result is True
        assert wh.enabled is True

    @pytest.mark.unit
    def test_enable_missing_returns_false(self, mgr):
        assert mgr.enable("wh-missing") is False

    @pytest.mark.unit
    def test_list_webhooks_empty(self, mgr):
        assert mgr.list_webhooks() == []

    @pytest.mark.unit
    def test_list_webhooks_returns_dicts(self, mgr):
        mgr.register("https://x.com", "secret")
        mgr.register("https://y.com", "secret2")
        result = mgr.list_webhooks()
        assert len(result) == 2
        assert all(isinstance(d, dict) for d in result)


# ---------------------------------------------------------------------------
# WebhookManager._sign_payload
# ---------------------------------------------------------------------------

class TestSignPayload:
    @pytest.mark.unit
    def test_signature_has_sha256_prefix(self):
        body = b"test payload"
        sig = WebhookManager._sign_payload("mysecret", body)
        assert sig.startswith("sha256=")

    @pytest.mark.unit
    def test_signature_is_correct_hmac(self):
        secret = "supersecret"
        body = b'{"event": "memory.added"}'
        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        result = WebhookManager._sign_payload(secret, body)
        assert result == expected

    @pytest.mark.unit
    def test_different_secrets_produce_different_sigs(self):
        body = b"same body"
        sig1 = WebhookManager._sign_payload("secret1", body)
        sig2 = WebhookManager._sign_payload("secret2", body)
        assert sig1 != sig2

    @pytest.mark.unit
    def test_different_bodies_produce_different_sigs(self):
        secret = "same-secret"
        sig1 = WebhookManager._sign_payload(secret, b"body1")
        sig2 = WebhookManager._sign_payload(secret, b"body2")
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# WebhookManager._deliver_once (httpx mocked)
# ---------------------------------------------------------------------------

class TestDeliverOnce:
    @pytest.fixture
    def mgr(self):
        return WebhookManager()

    @pytest.fixture
    def wh(self, mgr):
        return mgr.register("https://example.com/hook", "secret")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deliver_once_success_returns_true(self, mgr, wh):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        class _AsyncCtx:
            async def __aenter__(self_inner): return mock_client
            async def __aexit__(self_inner, *a): pass

        with patch("httpx.AsyncClient", return_value=_AsyncCtx()):
            result = await mgr._deliver_once(wh, {"event": "memory.added", "data": {}})
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deliver_once_non_2xx_returns_false(self, mgr, wh):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        class _AsyncCtx:
            async def __aenter__(self_inner): return mock_client
            async def __aexit__(self_inner, *a): pass

        with patch("httpx.AsyncClient", return_value=_AsyncCtx()):
            result = await mgr._deliver_once(wh, {"event": "memory.added"})
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deliver_once_exception_returns_false(self, mgr, wh):
        with patch("httpx.AsyncClient", side_effect=Exception("network error")):
            result = await mgr._deliver_once(wh, {"event": "test"})
        assert result is False


# ---------------------------------------------------------------------------
# WebhookManager.fire
# ---------------------------------------------------------------------------

class TestFire:
    @pytest.fixture
    def mgr(self):
        return WebhookManager()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_no_webhooks_returns_zeros(self, mgr):
        result = await mgr.fire("memory.added", {})
        assert result == {"delivered": 0, "failed": 0, "skipped": 0}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_disabled_webhook_skipped(self, mgr):
        wh = mgr.register("https://x.com", "secret", events=["memory.added"])
        mgr.disable(wh.id)
        result = await mgr.fire("memory.added", {})
        assert result["skipped"] == 1
        assert result["delivered"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_event_not_subscribed_skipped(self, mgr):
        mgr.register("https://x.com", "secret", events=["backup.completed"])
        result = await mgr.fire("memory.added", {})
        assert result["skipped"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_success_increments_delivery_count(self, mgr):
        wh = mgr.register("https://x.com", "secret", events=["memory.added"])

        async def _mock_deliver(webhook, payload):
            return True

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            result = await mgr.fire("memory.added", {"key": "val"})

        assert result["delivered"] == 1
        assert wh.delivery_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_failure_increments_failure_count(self, mgr):
        wh = mgr.register("https://x.com", "secret", events=["memory.added"])

        async def _mock_deliver(webhook, payload):
            return False

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            result = await mgr.fire("memory.added", {})

        assert result["failed"] == 1
        assert wh.failure_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_sets_last_triggered(self, mgr):
        wh = mgr.register("https://x.com", "secret", events=["memory.added"])

        async def _mock_deliver(webhook, payload):
            return True

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            await mgr.fire("memory.added", {})

        assert wh.last_triggered is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_multiple_webhooks(self, mgr):
        mgr.register("https://a.com", "s1", events=["memory.added"])
        mgr.register("https://b.com", "s2", events=["memory.added"])

        async def _mock_deliver(webhook, payload):
            return True

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            result = await mgr.fire("memory.added", {})

        assert result["delivered"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fire_payload_includes_webhook_id(self, mgr):
        captured_payloads = []
        wh = mgr.register("https://x.com", "secret", events=["memory.added"])

        async def _mock_deliver(webhook, payload):
            captured_payloads.append(payload)
            return True

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            await mgr.fire("memory.added", {})

        assert captured_payloads[0]["webhook_id"] == wh.id


# ---------------------------------------------------------------------------
# WebhookManager.test_webhook
# ---------------------------------------------------------------------------

class TestTestWebhook:
    @pytest.fixture
    def mgr(self):
        return WebhookManager()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_webhook_missing_returns_false(self, mgr):
        result = await mgr.test_webhook("wh-nonexistent")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_webhook_success_returns_true(self, mgr):
        wh = mgr.register("https://x.com", "s", events=list(WEBHOOK_EVENTS) + ["webhook.test"])

        async def _mock_deliver(webhook, payload):
            return True

        with patch.object(mgr, "_deliver_once", side_effect=_mock_deliver):
            result = await mgr.test_webhook(wh.id)

        assert result is True


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

class TestSingleton:
    @pytest.mark.unit
    def test_init_returns_manager(self):
        mgr = init_webhook_manager()
        assert isinstance(mgr, WebhookManager)

    @pytest.mark.unit
    def test_get_returns_initialized_manager(self):
        init_webhook_manager()
        mgr = get_webhook_manager()
        assert mgr is not None

    @pytest.mark.unit
    def test_reinit_replaces_manager(self):
        m1 = init_webhook_manager()
        m2 = init_webhook_manager()
        assert m1 is not m2
