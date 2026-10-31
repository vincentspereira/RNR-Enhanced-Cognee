"""DM text seam into the existing Hermes gateway handler, without trust flags.

The caller must supply an already kernel-authenticated, fixed-profile channel.
This module starts no listener, adapter, model or account. Native authorization,
secret scoping, commands and pending reply handling remain with GatewayRunner.
Only text DMs are represented. Durable replay/recovery, media, groups, outbound
adapter callbacks and production admission require separate implementation.
"""
from __future__ import annotations

import asyncio
import hashlib
import json

from isolated_gateway_transport import envelope, identifier


class NativeIngressError(RuntimeError):
    """Fixed error labels; do not include native exceptions or private content."""


def require(condition, category='native_text_contract_refused'):
    if not condition:
        raise NativeIngressError(category)


def session_binding(source):
    # Never accept a caller-selected native session key or persistence path.
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True).encode()).hexdigest()[:32]


def native_event(packet, profile_id):
    envelope(packet, profile_id)
    require(packet['kind'] == 'message')
    source = packet['source']
    require(source['platform'] == 'whatsapp' and source['thread_id'] is None,
        'unsupported_native_text_surface')
    require(packet['session_id'] == session_binding(source), 'native_session_binding_refused')
    from gateway.config import Platform
    from gateway.session import SessionSource
    from gateway.platforms.event import MessageEvent
    return MessageEvent(text=packet['text'], user_id=source['user_id'], message_id=packet['request_id'],
        source=SessionSource(platform=Platform.WHATSAPP, chat_id=source['chat_id'],
            user_id=source['user_id'], chat_type='dm'))


def outbound_packet(event, *, profile_id, request_id):
    """Serialize an actual adapter text DM, refusing unsupported native semantics.

    Only the trusted frontend may use this function. It does not authenticate a
    social-platform user; the receiving native gateway still does that itself.
    """
    from gateway.config import Platform
    from gateway.platforms.event import MessageEvent, MessageType
    require(isinstance(event, MessageEvent) and identifier(request_id, 32))
    source = event.source
    require(source is not None and source.platform == Platform.WHATSAPP
        and source.chat_type == 'dm' and source.thread_id is None
        and event.message_type == MessageType.TEXT, 'unsupported_native_text_surface')
    # These values carry authority or context that v1 cannot faithfully convey.
    for name in ('is_bot', 'role_authorized', 'profile', 'profile_route_rejected',
                 'delivered_via_upstream_relay', 'user_id_alt', 'chat_id_alt', 'scope_id',
                 'guild_id', 'parent_chat_id', 'prospective_thread_id', 'auto_thread_created',
                 'auto_thread_initial_name'):
        require(not getattr(source, name, None), 'unsupported_native_source_semantics')
    for name in ('internal', 'media_urls', 'media_types', 'media_text_inlined',
                 'reply_to_message_id', 'reply_to_text', 'reply_to_author_id', 'reply_to_author_name',
                 'reply_to_is_own_message', 'ledger_message_id', 'reply_anchor_override', 'platform_update_id',
                 'prompt_response', 'auto_skill', 'channel_prompt', 'channel_context', 'metadata',
                 'edit_revision', 'inherit_channel_pin'):
        require(not getattr(event, name, None), 'unsupported_native_event_semantics')
    require(event.allow_gateway_control is True and event.user_id == source.user_id
        and event.reply_expected is None)
    wire_source = dict(platform='whatsapp', chat_id=source.chat_id, user_id=source.user_id, thread_id=None)
    packet = dict(version=1, kind='message', profile_id=profile_id, request_id=request_id,
        session_id=session_binding(wire_source), source=wire_source, text=event.text)
    return envelope(packet, profile_id)


class NativeTextIngress:
    """Serial, one-process native dispatch with fail-closed duplicate refusal.

    Reservations survive handler failure/cancellation for this object's lifetime.
    They are deliberately never evicted. This is not restart-safe exactly-once
    execution and must not be exposed as a production retry mechanism.
    """
    def __init__(self, runner, *, profile_id, maximum_requests=1024):
        require(identifier(profile_id, 16) and type(maximum_requests) is int
            and 0 < maximum_requests <= 1024)
        require(runner.config.multiplex_profiles is True and not runner.config.profile_routes
            and not runner._profile_adapters, 'fixed_native_runtime_required')
        self.runner, self.profile_id = runner, profile_id
        self.maximum_requests, self._reserved = maximum_requests, set()
        self._lock = asyncio.Lock()
        self._handler = runner._primary_message_handler()

    async def handle(self, packet):
        event = native_event(packet, self.profile_id)
        request = packet['request_id']
        async with self._lock:
            require(self.runner.config.multiplex_profiles is True
                and not self.runner.config.profile_routes and not self.runner._profile_adapters,
                'fixed_native_runtime_required')
            require(request not in self._reserved, 'duplicate_native_request_denied')
            require(len(self._reserved) < self.maximum_requests, 'native_request_budget_exhausted')
            self._reserved.add(request)
            response = await self._handler(event)
            require(response is None or isinstance(response, str), 'unsupported_native_response')
            # A nonempty reply is not proof that a model turn or durable write
            # completed. None/empty can mean denied, queued, or a consumed reply.
            return envelope(dict(version=1, kind='response', profile_id=self.profile_id,
                request_id=request, text=response or '', completed=bool(response)), self.profile_id)
