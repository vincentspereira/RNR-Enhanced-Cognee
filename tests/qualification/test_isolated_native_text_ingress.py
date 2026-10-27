"""Closed native text conversion and fail-closed process-local dispatch guards.

Native types are small test doubles here. Installed native handler execution is
separate offline host evidence, not claimed by these tests.
"""
import asyncio
import copy
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


@pytest.fixture
def bridge(monkeypatch):
    monkeypatch.syspath_prepend(str(DIRECTORY))
    class Source(SimpleNamespace):
        def __init__(self, **values):
            super().__init__(role_authorized=False, profile=None, delivered_via_upstream_relay=False,
                **values)
    class Event(SimpleNamespace):
        def __init__(self, **values):
            defaults = dict(message_type='text', allow_gateway_control=True, reply_expected=None,
                internal=False, metadata={}, media_urls=[])
            defaults.update(values)
            super().__init__(**defaults)
    definitions = {
        'gateway.config':dict(Platform=SimpleNamespace(WHATSAPP='whatsapp')),
        'gateway.session':dict(SessionSource=Source),
        'gateway.platforms.event':dict(MessageEvent=Event, MessageType=SimpleNamespace(TEXT='text')),
    }
    for name, values in definitions.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)
    namespace = runpy.run_path(str(DIRECTORY / 'isolated_native_text_ingress.py'))
    namespace.update(Event=Event, Source=Source)
    return namespace


def packet(bridge, request='a'):
    source = dict(platform='whatsapp', chat_id='invented', user_id='invented', thread_id=None)
    return dict(version=1, kind='message', profile_id='b'*16, request_id=request*32,
        session_id=bridge['session_binding'](source), source=source, text='/help')


def event(bridge):
    return bridge['Event'](text='/help', user_id='invented',
        source=bridge['Source'](platform='whatsapp',chat_type='dm',chat_id='invented',
            user_id='invented',thread_id=None))


def runner(handler):
    return SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True, profile_routes=[]),
        _profile_adapters={}, _primary_message_handler=lambda:handler)


def test_native_events_do_not_receive_caller_trust_or_profile_flags(bridge):
    value = bridge['native_event'](packet(bridge), 'b'*16)
    assert value.internal is False
    assert value.source.role_authorized is False
    assert value.source.delivered_via_upstream_relay is False
    assert value.source.profile is None
    assert value.source.chat_type == 'dm'
    assert value.message_id == 'a'*32
    assert bridge['outbound_packet'](event(bridge),profile_id='b'*16,request_id='a'*32) == packet(bridge)


@pytest.mark.parametrize('owner,name,value',[
    ('source','platform','cli'), ('source','chat_type','group'), ('source','thread_id','invented'),
    ('source','role_authorized',True), ('source','profile','other'), ('source','is_bot',True),
    ('source','delivered_via_upstream_relay',True), ('source','profile_route_rejected',True),
    ('source','scope_id','invented'), ('source','user_id_alt','invented'),
    ('source','auto_thread_created',True), ('event','internal',True), ('event','media_urls',['invented']),
    ('event','metadata',{'internal':True}), ('event','prompt_response',{'approved':True}),
    ('event','allow_gateway_control',False), ('event','reply_expected',False),
    ('event','inherit_channel_pin',True), ('event','reply_to_text','invented'),
    ('event','edit_revision','invented'), ('event','ledger_message_id','invented'),
    ('event','reply_anchor_override','invented'), ('event','message_type','photo'),
    ('event','channel_prompt','invented'), ('event','user_id','different'),
])
def test_unsupported_native_semantics_are_refused_before_serialization(bridge,owner,name,value):
    candidate = event(bridge)
    setattr(candidate.source if owner == 'source' else candidate, name, value)
    with pytest.raises(bridge['NativeIngressError']):
        bridge['outbound_packet'](candidate, profile_id='b'*16, request_id='a'*32)


@pytest.mark.parametrize('damage',['cli','thread','session','profile','trust_field','cancel'])
def test_wire_data_cannot_select_trusted_local_auth_or_another_session(bridge,damage):
    value = packet(bridge)
    if damage == 'cli':value['source']['platform'] = 'cli'
    if damage == 'thread':value['source']['thread_id'] = 'invented'
    if damage == 'session':value['session_id'] = 'd'*32
    if damage == 'profile':value['profile_id'] = 'd'*16
    if damage == 'trust_field':value['source']['role_authorized'] = True
    if damage == 'cancel':value = {key:value[key] for key in ('version','kind','profile_id','request_id')};value['kind']='cancel'
    from isolated_gateway_transport import TransportError
    with pytest.raises((bridge['NativeIngressError'], TransportError)):
        bridge['native_event'](value, 'b'*16)


@pytest.mark.parametrize('outcome',['reply','denied','empty','exception','cancelled','unsupported'])
def test_native_reservations_survive_all_outcomes_and_never_replay(bridge,outcome):
    calls = []
    async def handler(value):
        calls.append(value)
        if outcome == 'exception':raise ValueError('invented-private-native-error')
        if outcome == 'cancelled':raise asyncio.CancelledError()
        return {'reply':'Invented reply.','denied':None,'empty':'','unsupported':{}}[outcome]
    async def check():
        ingress = bridge['NativeTextIngress'](runner(handler), profile_id='b'*16)
        try:
            response = await ingress.handle(packet(bridge))
            assert response['completed'] is (outcome == 'reply')
        except (ValueError, asyncio.CancelledError, bridge['NativeIngressError']):
            assert outcome in {'exception','cancelled','unsupported'}
        with pytest.raises(bridge['NativeIngressError'], match='duplicate_native_request_denied'):
            await ingress.handle(packet(bridge))
        assert len(calls) == 1
    asyncio.run(check())


def test_concurrent_native_dispatch_is_serial_and_request_budget_never_evicts(bridge):
    active = 0
    async def handler(value):
        nonlocal active
        active += 1
        assert active == 1
        await asyncio.sleep(0)
        active -= 1
        return 'Invented reply.'
    async def check():
        ingress = bridge['NativeTextIngress'](runner(handler), profile_id='b'*16, maximum_requests=2)
        await asyncio.gather(ingress.handle(packet(bridge,'a')), ingress.handle(packet(bridge,'c')))
        with pytest.raises(bridge['NativeIngressError'], match='native_request_budget_exhausted'):
            await ingress.handle(packet(bridge,'d'))
        with pytest.raises(bridge['NativeIngressError'], match='duplicate_native_request_denied'):
            await ingress.handle(packet(bridge,'a'))
    asyncio.run(check())


@pytest.mark.parametrize('damage',['routes','secondary','standalone'])
def test_drifting_native_runtime_cannot_admit_a_request(bridge,damage):
    async def check():
        async def handler(value):pytest.fail('native handler must not run')
        candidate = runner(handler)
        ingress = bridge['NativeTextIngress'](candidate, profile_id='b'*16)
        if damage == 'routes':candidate.config.profile_routes = ['invented']
        if damage == 'secondary':candidate._profile_adapters['other'] = object()
        if damage == 'standalone':candidate.config.multiplex_profiles = False
        with pytest.raises(bridge['NativeIngressError'], match='fixed_native_runtime_required'):
            await ingress.handle(packet(bridge))
        assert not ingress._reserved
    asyncio.run(check())
