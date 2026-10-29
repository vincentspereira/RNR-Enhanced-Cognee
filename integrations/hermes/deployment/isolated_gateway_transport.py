"""Linux-authenticated local channel for one fixed isolated Hermes profile.

No credential values, caller-selected scope, process launch or durable logging.
Every received byte is bound to kernel SCM_CREDENTIALS, including connections
created by root socket activation and passed to unprivileged workers. SO_PEERCRED
alone identifies the listener creator, not necessarily its current worker.
Native adapter/session integration and production admission are separate.
"""
from __future__ import annotations
import array
import json
import math
import os
import re
import socket
import struct
import time

MAX_FRAME = 1024 * 1024
MAX_TEXT = 256 * 1024
UCRED = struct.Struct('3i')
LENGTH = struct.Struct('!I')


class TransportError(RuntimeError):
    """Fixed categories only; never include a private payload or remote error."""


def require(value, category='transport_contract_refused'):
    if not value: raise TransportError(category)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_transport_field')
        result[key] = value
    return result


def identifier(value, size):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{' + str(size) + '}', value) is not None


def text(value, *, nonempty):
    require(isinstance(value, str) and '\x00' not in value)
    try: size = len(value.encode('utf-8'))
    except UnicodeError: raise TransportError('transport_text_refused') from None
    require((size > 0 or not nonempty) and size <= MAX_TEXT, 'transport_text_budget')


def source(value):
    require(isinstance(value, dict) and set(value) == {'platform', 'chat_id', 'user_id', 'thread_id'})
    require(isinstance(value['platform'], str) and value['platform'] in {'cli', 'whatsapp'})
    for key in ('chat_id', 'user_id'):
        require(isinstance(value[key], str) and value[key].isascii() and 0 < len(value[key]) <= 256
                and not any(ord(char) < 32 for char in value[key]))
    require(value['thread_id'] is None or (isinstance(value['thread_id'], str) and value['thread_id'].isascii()
            and 0 < len(value['thread_id']) <= 256 and not any(ord(char) < 32 for char in value['thread_id'])))


def envelope(value, profile_id):
    require(identifier(profile_id, 16))
    require(isinstance(value, dict) and value.get('version') == 1 and type(value.get('version')) is int
            and value.get('profile_id') == profile_id, 'fixed_profile_binding_refused')
    require(identifier(value.get('request_id'), 32))
    kind = value.get('kind')
    common = {'version', 'kind', 'profile_id', 'request_id'}
    if kind == 'message':
        require(set(value) == common | {'session_id', 'source', 'text'})
        require(identifier(value['session_id'], 32))
        text(value['text'], nonempty=True)
        source(value['source'])
    elif kind == 'response':
        require(set(value) == common | {'text', 'completed'})
        require(type(value['completed']) is bool)
        text(value['text'], nonempty=False)
    elif kind == 'cancel':
        require(set(value) == common)
    else:
        require(False, 'unsupported_transport_operation')
    return value


def encode(value, profile_id):
    envelope(value, profile_id)
    try: raw = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    except (TypeError, ValueError): raise TransportError('transport_encoding_refused') from None
    require(0 < len(raw) <= MAX_FRAME, 'transport_frame_budget')
    return LENGTH.pack(len(raw)) + raw


def decode(raw, profile_id):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_FRAME, 'transport_frame_budget')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
            parse_constant=lambda value: require(False, 'transport_number_refused'))
    except (UnicodeError, ValueError, RecursionError):
        raise TransportError('transport_decoding_refused') from None
    return envelope(value, profile_id)


class CredentialChannel:
    """One connected Linux AF_UNIX stream, fixed peer and per-message sender UIDs.

    A root-activated listener requires listener_uid=0 explicitly on the client.
    Payload sender_uid is always a positive restricted UID. The root listener
    credential therefore cannot authenticate an ordinary worker's message.
    Received descriptors are closed and refused, never exposed to a handler.
    """
    def __init__(self, connection, *, profile_id, sender_uid, listener_uid=None, timeout=10):
        require(identifier(profile_id, 16) and type(sender_uid) is int and 0 < sender_uid < 2**31)
        listener_uid = sender_uid if listener_uid is None else listener_uid
        require(type(listener_uid) is int and 0 <= listener_uid < 2**31
                and type(timeout) in {int, float} and math.isfinite(timeout) and 0 < timeout <= 120)
        require(connection.family == socket.AF_UNIX and connection.type == socket.SOCK_STREAM)
        require(hasattr(socket, 'SCM_CREDENTIALS') and hasattr(socket, 'SO_PASSCRED'))
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            pid, uid, gid = UCRED.unpack(connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, UCRED.size))
        except OSError: raise TransportError('transport_socket_refused') from None
        require(pid > 0 and uid == listener_uid and gid >= 0, 'connection_identity_denied')
        self.socket = connection
        self.profile_id, self.sender_uid, self.timeout = profile_id, sender_uid, timeout

    def receive(self):
        deadline = time.monotonic() + self.timeout
        def read(count):
            chunks = []; remaining = count
            while remaining:
                wait = deadline - time.monotonic()
                require(wait > 0, 'transport_deadline')
                self.socket.settimeout(wait)
                try:
                    raw, ancillary, flags, _ = self.socket.recvmsg(remaining,
                        socket.CMSG_SPACE(UCRED.size) + socket.CMSG_SPACE(64), socket.MSG_CMSG_CLOEXEC)
                except TimeoutError: raise TransportError('transport_deadline') from None
                except OSError: raise TransportError('transport_receive_failed') from None
                credentials = []; other = False
                for level, kind, body in ancillary:
                    if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                        descriptors = array.array('i')
                        descriptors.frombytes(body[:len(body) - len(body) % descriptors.itemsize])
                        for fd in descriptors:
                            try: os.close(fd)
                            except OSError: pass
                        other = True
                    elif level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and len(body) == UCRED.size:
                        credentials.append(UCRED.unpack(body))
                    else: other = True
                require(not other and not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), 'transport_ancillary_refused')
                require(bool(raw), 'transport_connection_closed')
                require(len(credentials) == 1 and credentials[0][0] > 0
                        and credentials[0][1] == self.sender_uid and credentials[0][2] >= 0,
                        'message_sender_identity_denied')
                chunks.append(raw); remaining -= len(raw)
            return b''.join(chunks)
        size = LENGTH.unpack(read(LENGTH.size))[0]
        require(0 < size <= MAX_FRAME, 'transport_frame_budget')
        return decode(read(size), self.profile_id)

    def send(self, value):
        data = encode(value, self.profile_id)
        self.socket.settimeout(self.timeout)
        try: self.socket.sendall(data)
        except TimeoutError: raise TransportError('transport_deadline') from None
        except OSError: raise TransportError('transport_send_failed') from None
