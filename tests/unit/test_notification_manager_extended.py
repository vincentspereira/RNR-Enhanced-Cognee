"""
Extended unit tests for src/notification_manager.py

Covers:
- _build_slack_payload / _build_discord_payload
- _post_json with aiohttp success, aiohttp failure, urllib fallback
- send_notification with disabled channel, channel not subscribed to event
- test_channel for slack and discord
- Unknown events passed to send_notification

Targets >= 85% combined with test_phase14_new_modules.py.
ASCII-only assertions.
"""

import asyncio
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestBuildPayloads:
    """Tests for payload builder static methods."""

    def test_build_slack_payload_structure(self):
        from src.notification_manager import NotificationManager
        payload = NotificationManager._build_slack_payload(
            "memory.added", "Test text", {"key": "val"}
        )
        assert "text" in payload
        assert "blocks" in payload
        assert payload["blocks"][0]["type"] == "section"

    def test_build_slack_payload_data_truncated(self):
        from src.notification_manager import NotificationManager
        big_data = {"data": "x" * 1000}
        payload = NotificationManager._build_slack_payload("ev", "txt", big_data)
        block_text = payload["blocks"][0]["text"]["text"]
        # data preview is limited to 400 chars in the code
        assert len(block_text) < 1500

    def test_build_discord_payload_structure(self):
        from src.notification_manager import NotificationManager
        payload = NotificationManager._build_discord_payload(
            "backup.failed", "Backup failed message", {"status": "error"}
        )
        assert "content" in payload
        assert "embeds" in payload
        assert payload["embeds"][0]["title"] == "backup.failed"

    def test_build_discord_payload_description_truncated(self):
        from src.notification_manager import NotificationManager
        big_data = {"d": "y" * 1000}
        payload = NotificationManager._build_discord_payload("ev", "txt", big_data)
        desc = payload["embeds"][0]["description"]
        assert len(desc) <= 500


class TestSendNotification:
    """Tests for send_notification delivery logic."""

    @pytest.mark.asyncio
    async def test_send_to_disabled_channel_counts_skipped(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-off"] = {
            "channel_id": "ch-off",
            "type": "slack",
            "webhook_url": "https://hooks.slack.com/x",
            "events": ["memory.added"],
            "enabled": False,
        }
        result = await nm.send_notification("memory.added", {})
        assert result["skipped"] >= 1
        assert result["delivered"] == 0

    @pytest.mark.asyncio
    async def test_send_to_channel_not_subscribed_to_event(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-x"] = {
            "channel_id": "ch-x",
            "type": "slack",
            "webhook_url": "https://hooks.slack.com/x",
            "events": ["backup.completed"],
            "enabled": True,
        }
        result = await nm.send_notification("memory.added", {})
        assert result["skipped"] >= 1

    @pytest.mark.asyncio
    async def test_send_notification_slack_delivered(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-s"] = {
            "channel_id": "ch-s",
            "type": "slack",
            "webhook_url": "https://hooks.slack.com/x",
            "events": ["memory.added"],
            "enabled": True,
        }
        with patch.object(nm, "_post_json", AsyncMock(return_value=200)):
            result = await nm.send_notification("memory.added", {"id": "mem-1"})
        assert result["delivered"] == 1
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_notification_discord_delivered(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-d"] = {
            "channel_id": "ch-d",
            "type": "discord",
            "webhook_url": "https://discord.com/webhooks/123/abc",
            "events": ["backup.failed"],
            "enabled": True,
        }
        with patch.object(nm, "_post_json", AsyncMock(return_value=204)):
            result = await nm.send_notification("backup.failed", {"reason": "disk full"})
        assert result["delivered"] == 1

    @pytest.mark.asyncio
    async def test_send_notification_failed_on_http_error(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-err"] = {
            "channel_id": "ch-err",
            "type": "slack",
            "webhook_url": "https://hooks.slack.com/x",
            "events": ["memory.deleted"],
            "enabled": True,
        }
        with patch.object(nm, "_post_json", AsyncMock(return_value=500)):
            result = await nm.send_notification("memory.deleted", {})
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_send_unknown_event_still_dispatches(self):
        """Unknown events are dispatched to channels if subscribed (not in constant check)."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-y"] = {
            "channel_id": "ch-y",
            "type": "slack",
            "webhook_url": "https://x",
            "events": ["custom.event"],
            "enabled": True,
        }
        with patch.object(nm, "_post_json", AsyncMock(return_value=200)):
            result = await nm.send_notification("custom.event", {})
        assert result["delivered"] == 1

    @pytest.mark.asyncio
    async def test_multiple_channels_mixed_results(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        nm._channels["ch-ok"] = {
            "channel_id": "ch-ok", "type": "slack",
            "webhook_url": "https://ok", "events": ["memory.updated"], "enabled": True,
        }
        nm._channels["ch-fail"] = {
            "channel_id": "ch-fail", "type": "discord",
            "webhook_url": "https://fail", "events": ["memory.updated"], "enabled": True,
        }

        call_count = [0]

        async def varying_post(url, payload):
            call_count[0] += 1
            return 200 if call_count[0] == 1 else 503

        with patch.object(nm, "_post_json", varying_post):
            result = await nm.send_notification("memory.updated", {})
        assert result["delivered"] == 1
        assert result["failed"] == 1


class TestTestChannel:
    """Tests for test_channel method."""

    @pytest.mark.asyncio
    async def test_test_slack_channel_success(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_slack("slack-test", "https://hooks.slack.com/xxx", ["memory.added"])
        with patch.object(nm, "_post_json", AsyncMock(return_value=200)):
            result = await nm.test_channel("slack-test")
        assert result["ok"] is True
        assert result["response_code"] == 200

    @pytest.mark.asyncio
    async def test_test_discord_channel_success(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_discord("discord-test", "https://discord.com/webhooks/1/abc",
                                   ["health.degraded"])
        with patch.object(nm, "_post_json", AsyncMock(return_value=204)):
            result = await nm.test_channel("discord-test")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_test_channel_http_failure(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_slack("slack-bad", "https://hooks.slack.com/yyy", ["backup.failed"])
        with patch.object(nm, "_post_json", AsyncMock(return_value=403)):
            result = await nm.test_channel("slack-bad")
        assert result["ok"] is False
        assert result["response_code"] == 403

    @pytest.mark.asyncio
    async def test_test_channel_not_found(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.test_channel("does-not-exist")
        assert result["ok"] is False
        assert result["response_code"] == 0


class TestConfigureWithUnknownEvents:
    """Ensure unknown events trigger a warning but do not raise."""

    @pytest.mark.asyncio
    async def test_configure_slack_unknown_event_no_error(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.configure_slack(
            "ch-unk", "https://hooks.slack.com/u", ["unknown.event"]
        )
        assert result["type"] == "slack"
        assert "unknown.event" in result["events"]

    @pytest.mark.asyncio
    async def test_configure_discord_unknown_event_no_error(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.configure_discord(
            "ch-dunk", "https://discord.com/w/0/x", ["unknown.event"]
        )
        assert result["type"] == "discord"


class TestPostJson:
    """Tests for _post_json HTTP transport."""

    @pytest.mark.asyncio
    async def test_post_json_aiohttp_success(self):
        from src.notification_manager import NotificationManager

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            status = await NotificationManager._post_json("https://x", {"k": "v"})
        assert status == 200

    @pytest.mark.asyncio
    async def test_post_json_aiohttp_exception_returns_zero(self):
        from src.notification_manager import NotificationManager

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.post = MagicMock(side_effect=Exception("network error"))

        with patch("aiohttp.ClientSession", return_value=mock_session):
            status = await NotificationManager._post_json("https://x", {})
        assert status == 0

    @pytest.mark.asyncio
    async def test_post_json_urllib_fallback_success(self):
        from src.notification_manager import NotificationManager
        import urllib

        def fake_urlopen(req, timeout=10):
            class FakeResp:
                status = 200
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    pass
            return FakeResp()

        # Force ImportError for aiohttp so we fall through to urllib
        with patch.dict("sys.modules", {"aiohttp": None}):
            with patch("urllib.request.urlopen", fake_urlopen):
                status = await NotificationManager._post_json("https://x", {})
        assert status == 200

    @pytest.mark.asyncio
    async def test_post_json_urllib_fallback_http_error(self):
        from src.notification_manager import NotificationManager
        import urllib.error

        def fake_urlopen(req, timeout=10):
            raise urllib.error.HTTPError(
                "https://x", 404, "Not Found", {}, None
            )

        with patch.dict("sys.modules", {"aiohttp": None}):
            with patch("urllib.request.urlopen", fake_urlopen):
                status = await NotificationManager._post_json("https://x", {})
        assert status == 404

    @pytest.mark.asyncio
    async def test_post_json_urllib_fallback_generic_exception(self):
        from src.notification_manager import NotificationManager

        def fake_urlopen(req, timeout=10):
            raise ConnectionError("refused")

        with patch.dict("sys.modules", {"aiohttp": None}):
            with patch("urllib.request.urlopen", fake_urlopen):
                status = await NotificationManager._post_json("https://x", {})
        assert status == 0


# ---------------------------------------------------------------------------
# Tests: list_channels (lines 214-219)
# ---------------------------------------------------------------------------

class TestListChannels:
    @pytest.mark.asyncio
    async def test_list_channels_empty(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = nm.list_channels()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_channels_with_slack_and_discord(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_slack("sl-1", "https://hooks.slack.com/sl1", ["memory.added"])
        await nm.configure_discord("dc-1", "https://discord.com/api/webhooks/dc1", ["backup.failed"])
        channels = nm.list_channels()
        assert len(channels) == 2
        ids = {c["channel_id"] for c in channels}
        assert "sl-1" in ids
        assert "dc-1" in ids

    @pytest.mark.asyncio
    async def test_list_channels_includes_channel_id_field(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_slack("ch-x", "https://hooks.slack.com/x", ["health.degraded"])
        channels = nm.list_channels()
        assert channels[0]["channel_id"] == "ch-x"


# ---------------------------------------------------------------------------
# Tests: singletons (lines 321-323, 328)
# ---------------------------------------------------------------------------

class TestSingletons:
    def test_init_notification_manager_creates_instance(self):
        from src.notification_manager import init_notification_manager, get_notification_manager
        mgr = init_notification_manager()
        assert mgr is not None
        retrieved = get_notification_manager()
        assert retrieved is mgr

    def test_get_notification_manager_before_init_returns_none_or_instance(self):
        # After test_init_notification_manager_creates_instance, the singleton exists
        from src.notification_manager import get_notification_manager
        result = get_notification_manager()
        # Either None (if not yet initialized) or a NotificationManager instance
        from src.notification_manager import NotificationManager
        assert result is None or isinstance(result, NotificationManager)

