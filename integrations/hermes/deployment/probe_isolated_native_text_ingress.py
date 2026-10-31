"""Offline invented text fixture for two restricted transport processes.

Never reads a real profile or credential. The worker uses the installed native
gateway's actual scoped handler, authorization, command and clarify primitives.
No native method or authorization guard is replaced by the fixture.
"""
from __future__ import annotations
import asyncio
import contextlib
import hashlib
import json
import logging
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile

from isolated_gateway_transport import CredentialChannel
from isolated_native_text_ingress import NativeIngressError, NativeTextIngress, native_event, outbound_packet, session_binding

REPO = '/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/repo'
ALLOWED = '15550000001@s.whatsapp.net'
DENIED = '15550000002@s.whatsapp.net'
PHASE = 'identity'
OBSERVATION = {}
FLAGS = {'complete', 'identity_restricted', 'invented_text_roundtrip',
         'profile_override_absent', 'network_unused', 'real_profiles_unread'}
WORKER_FLAGS = {'native_sender_denial', 'duplicate_request_denial',
                'native_clarification_preserved_and_resolved'}


def require(value):
    if not value:
        raise ValueError('native_ingress_probe_refused')


def messages(profile):
    result = []
    for request, user, content in [('1', ALLOWED, '/help'), ('2', DENIED, '/help'),
            ('1', ALLOWED, '/help'), ('3', ALLOWED, '/help'),
            ('4', DENIED, 'Invented answer.'), ('5', ALLOWED, 'Invented answer.')]:
        source = dict(platform='whatsapp', chat_id=user, user_id=user, thread_id=None)
        result.append(dict(version=1, kind='message', profile_id=profile, request_id=request * 32,
            session_id=session_binding(source), source=source, text=content))
    return result


def guards():
    counts = dict(network=0, real_profile=0, subprocess=0)
    def audit(name, args):
        if name in {'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname'}:
            counts['network'] += 1
            raise PermissionError('fixture_network_denied')
        if name in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'}:
            counts['subprocess'] += 1
            raise PermissionError('fixture_process_denied')
        if name in {'open', 'os.listdir', 'os.scandir'} and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.path.abspath(os.fsdecode(args[0]))
            if any(path == root or path.startswith(root + '/') for root in
                    ('/home', '/root', '/var/lib/enhanced-cognee-profiles')):
                counts['real_profile'] += 1
                raise PermissionError('fixture_real_profile_denied')
    sys.addaudithook(audit)
    return counts


async def worker(channel, packets):
    global PHASE, OBSERVATION
    profile = Path(tempfile.mkdtemp(prefix='ec-native-text-fixture-'))
    os.environ.clear()
    os.environ.update(HOME=str(profile), HERMES_HOME=str(profile), PATH='/usr/bin:/bin', LANG='C.UTF-8')
    os.chdir(profile)
    preserved = {'.env': 'GATEWAY_ALLOWED_USERS=' + ALLOWED + '\n',
        'config.yaml': 'gateway:\n  multiplex_profiles: true\n  unauthorized_dm_behavior: ignore\n'}
    for name, content in preserved.items():
        fd = os.open(profile / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(content)
    counts = guards()
    OBSERVATION = counts
    PHASE = 'native_imports'
    sys.path.insert(0, REPO)
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig
    from tools import clarify_gateway
    runner = GatewayRunner(GatewayConfig(multiplex_profiles=True, sessions_dir=profile / 'sessions',
        unauthorized_dm_behavior='ignore'))
    ingress = NativeTextIngress(runner, profile_id=packets[0]['profile_id'])
    clarification = None
    for index, expected in enumerate(packets):
        PHASE = 'native_receive'
        packet = channel.receive()
        require(packet == expected)
        require(outbound_packet(native_event(packet, ingress.profile_id), profile_id=ingress.profile_id,
            request_id=packet['request_id']) == packet)
        if index == 3:
            event = native_event(packet, ingress.profile_id)
            runner._admit_primary_source(event.source, profile)
            key = runner._session_key_for_source(event.source)
            clarification = clarify_gateway.register('invented-ingress-clarification', key,
                'Invented transport question only.', None)
        PHASE = 'native_dispatch'
        try:
            response = await ingress.handle(packet)
            require(index != 2)
        except NativeIngressError as error:
            require(index == 2 and str(error) == 'duplicate_native_request_denied')
            response = dict(version=1, kind='response', profile_id=ingress.profile_id,
                request_id=packet['request_id'], text='', completed=False)
        if index in {3, 4}:
            require(clarification is not None and not clarification.event.is_set())
        if index == 5:
            require(clarification.event.is_set() and clarification.response == 'Invented answer.')
            require(clarify_gateway.wait_for_response(clarification.clarify_id, 0.1) == 'Invented answer.')
        require(response['completed'] is (index in {0, 3}))
        channel.send(response)
    PHASE = 'preservation'
    require(not runner.adapters and not runner._profile_adapters and not runner._agent_cache)
    require(all((profile / name).read_text() == content for name, content in preserved.items()))
    require(counts == dict(network=0, real_profile=0, subprocess=0))


def operation(packet):
    global PHASE
    require(isinstance(packet, dict) and set(packet) == {'uid','gid','role','fd','frontend_uid','worker_uid','profile_id'})
    require(packet['role'] in {'frontend','worker'} and packet['frontend_uid'] != packet['worker_uid'])
    uid, gid = packet['uid'], packet['gid']
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(type(uid) is int and uid > 0 and type(gid) is int and gid > 0
        and os.getresuid() == (uid,) * 3 and os.getresgid() == (gid,) * 3 and not os.getgroups()
        and uid == packet['frontend_uid' if packet['role'] == 'frontend' else 'worker_uid']
        and fields['NoNewPrivs'].strip() == '1'
        and all(fields[name].strip() == '0000000000000000' for name in ('CapEff','CapAmb','CapInh')))
    PHASE = 'socket_identity'
    with socket.socket(fileno=packet['fd']) as connection:
        channel = CredentialChannel(connection, profile_id=packet['profile_id'], listener_uid=0, timeout=120,
            sender_uid=packet['frontend_uid' if packet['role'] == 'worker' else 'worker_uid'])
        packets = messages(packet['profile_id'])
        if packet['role'] == 'worker':
            asyncio.run(worker(channel, packets))
        else:
            for index, value in enumerate(packets):
                PHASE = 'frontend_exchange'
                channel.send(value)
                response = channel.receive()
                require(response['kind'] == 'response' and response['request_id'] == value['request_id']
                    and response['completed'] is (index in {0,3})
                    and bool(response['text']) is (index in {0,3}))
    flags = FLAGS | (WORKER_FLAGS if packet['role'] == 'worker' else set())
    return dict(dict.fromkeys(flags, True), role=packet['role'])


def main():
    signal.signal(signal.SIGALRM, lambda *args: os._exit(2))
    signal.alarm(130)
    logging.disable(logging.CRITICAL)
    try:
        packet = json.loads(sys.stdin.buffer.readline(4097))
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            result = operation(packet)
    except Exception as error:
        result = dict(complete=False, phase=PHASE,
            error_kind=type(error).__name__ if type(error).__name__ in
                {'ValueError','PermissionError','NativeIngressError','TransportError','AttributeError','TypeError'} else 'other')
        if OBSERVATION:
            result['denied_attempt_counts'] = dict(OBSERVATION)
    print(json.dumps(result), flush=True)
    return 0 if result['complete'] else 1
