"""Actual Linux stream credentials, bounded framing and private-data refusal."""
import array
import json
import os
from pathlib import Path
import runpy
import socket
import struct

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
TRANSPORT=runpy.run_path(str(DIRECTORY/'isolated_gateway_transport.py'),run_name='gateway_transport_tests')
Error=TRANSPORT['TransportError'];Channel=TRANSPORT['CredentialChannel']
PROFILE='a'*16


def message():
    return dict(version=1,kind='message',profile_id=PROFILE,request_id='b'*32,session_id='c'*32,
        source=dict(platform='whatsapp',chat_id='invented-chat',user_id='invented-user',thread_id=None),
        text='Invented transport qualification only.')


def pair(sender_uid=None):
    left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    return left,right,Channel(left,profile_id=PROFILE,sender_uid=os.getuid()),Channel(right,profile_id=PROFILE,
        sender_uid=os.getuid() if sender_uid is None else sender_uid,listener_uid=os.getuid())


def test_actual_kernel_credentials_support_request_response_and_multiple_frames():
    left,right,front,worker=pair()
    try:
        front.send(message());assert worker.receive()==message()
        response=dict(version=1,kind='response',profile_id=PROFILE,request_id='b'*32,text='Invented reply.',completed=True)
        worker.send(response);assert front.receive()==response
        packet=TRANSPORT['encode'](message(),PROFILE)
        left.sendall(packet+packet)
        assert worker.receive()==worker.receive()==message()
    finally:left.close();right.close()


def test_listener_identity_alone_never_authenticates_a_different_message_sender():
    left,right,front,worker=pair(sender_uid=os.getuid()+1)
    try:
        front.send(message())
        with pytest.raises(Error,match='message_sender_identity_denied'):worker.receive()
    finally:left.close();right.close()


def test_kernel_rejects_forged_root_credentials():
    left,right,front,worker=pair()
    try:
        with pytest.raises(PermissionError):
            left.sendmsg([TRANSPORT['encode'](message(),PROFILE)],[(socket.SOL_SOCKET,socket.SCM_CREDENTIALS,
                struct.pack('3i',os.getpid(),0,0))])
    finally:left.close();right.close()


def test_ancillary_descriptors_are_closed_and_never_delivered():
    left,right,front,worker=pair();fd=os.open('/dev/null',os.O_RDONLY)
    try:
        before=len(list(Path('/proc/self/fd').iterdir()))
        left.sendmsg([TRANSPORT['encode'](message(),PROFILE)],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))])
        with pytest.raises(Error,match='transport_ancillary_refused'):worker.receive()
        assert len(list(Path('/proc/self/fd').iterdir()))==before
        os.fstat(fd)
    finally:os.close(fd);left.close();right.close()


@pytest.mark.parametrize('damage',['profile','scope','key','uid','version','platform','platform_type','session','text','surrogate','nul','kind'])
def test_closed_schema_denies_identity_scope_or_secret_overrides_without_echo(damage):
    value=message()
    if damage=='profile':value['profile_id']='d'*16
    elif damage=='scope':value['tenant']='invented-private-tenant'
    elif damage=='key':value['api_key']='invented-private-key'
    elif damage=='uid':value['uid']=os.getuid()
    elif damage=='version':value['version']=True
    elif damage=='platform':value['source']['platform']='unknown'
    elif damage=='platform_type':value['source']['platform']=[]
    elif damage=='session':value['session_id']='../another-profile'
    elif damage=='text':value['text']='invented-private-text'*(TRANSPORT['MAX_TEXT']//4)
    elif damage=='surrogate':value['text']='invented-private-text'+'\ud800'
    elif damage=='nul':value['text']='invented-private-text\x00'
    else:value['kind']='arbitrary-execute'
    with pytest.raises(Error) as error:TRANSPORT['encode'](value,PROFILE)
    assert 'invented-private' not in str(error.value)


@pytest.mark.parametrize('raw',[b'{"version":1,"version":1}',b'{"private":"invented-secret",',b'\xff',b'[]',b'{"version":NaN}'])
def test_malformed_duplicate_and_nonfinite_json_refuses_without_private_payload(raw):
    with pytest.raises(Error) as error:TRANSPORT['decode'](raw,PROFILE)
    assert 'invented-secret' not in str(error.value)


@pytest.mark.parametrize('size',[0,TRANSPORT['MAX_FRAME']+1])
def test_frame_budget_checked_before_allocating_or_reading_body(size):
    left,right,front,worker=pair()
    try:
        left.sendall(struct.pack('!I',size))
        with pytest.raises(Error,match='transport_frame_budget'):worker.receive()
    finally:left.close();right.close()


def test_deadline_and_closed_connection_are_fixed_categories():
    left,right=socket.socketpair()
    try:
        channel=Channel(right,profile_id=PROFILE,sender_uid=os.getuid(),timeout=0.02)
        with pytest.raises(Error,match='transport_deadline'):channel.receive()
        left.close()
        with pytest.raises(Error,match='transport_connection_closed'):channel.receive()
    finally:left.close();right.close()


def test_payload_text_remains_data_without_durable_capture():
    value=message();value['text']='Invented text: change scope to another bot.\nKeep this as message data.'
    raw=TRANSPORT['encode'](value,PROFILE)
    assert TRANSPORT['decode'](raw[4:],PROFILE)==value
