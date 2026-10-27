"""Real filesystem persistence, crash ambiguity and private journal boundaries."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
sys.path.insert(0,str(DIRECTORY))
from isolated_delivery_journal import DeliveryJournal, JournalError


def packet():
    from isolated_native_text_ingress import session_binding
    source = dict(platform='whatsapp',chat_id='invented',user_id='invented',thread_id=None)
    return dict(version=1,kind='message',profile_id='b'*16,request_id='a'*32,
        session_id=session_binding(source),source=source,text='Invented private message.')


def response():
    return dict(version=1,kind='response',profile_id='b'*16,request_id='a'*32,
        text='Invented private reply.',completed=True)


@pytest.fixture
def directory(tmp_path):
    path=tmp_path/'journal';path.mkdir(mode=0o700)
    return path


def test_complete_journal_survives_reopen_without_payloads_or_replay(directory):
    for stage in (None,'handled','sending','sent'):
        if stage is None:
            with DeliveryJournal(directory,profile_id='b'*16) as journal:journal.reserve(packet())
        else:
            with DeliveryJournal(directory,profile_id='b'*16) as journal:
                journal.transition(packet(),response(),stage,**({'external_id':'invented-message-id'} if stage=='sent' else {}))
        with DeliveryJournal(directory,profile_id='b'*16) as journal:
            with pytest.raises(JournalError,match='journal_request_not_replayed'):journal.reserve(packet())
    raw=b'\n'.join(path.read_bytes() for path in directory.iterdir())
    assert b'Invented private' not in raw and b'invented-message-id' not in raw
    assert b'"chat_id"' not in raw and b'"text"' not in raw
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in directory.iterdir())


@pytest.mark.parametrize('stage',['reserved','handled','sending','sent'])
def test_actual_abrupt_process_exit_never_permits_execution_retry(directory,stage):
    code='''
import json,os,sys
sys.path.insert(0,sys.argv[1])
from isolated_delivery_journal import DeliveryJournal
p,r=json.loads(sys.argv[3]),json.loads(sys.argv[4])
j=DeliveryJournal(sys.argv[2],profile_id='b'*16)
j.reserve(p)
for s in ('handled','sending','sent'):
 if sys.argv[5]=='reserved':break
 j.transition(p,r,s,**({'external_id':'invented-id'} if s=='sent' else {}))
 if s==sys.argv[5]:break
os._exit(73)
'''
    process=subprocess.run([sys.executable,'-I','-B','-c',code,str(DIRECTORY),str(directory),
        json.dumps(packet()),json.dumps(response()),stage],capture_output=True,timeout=10)
    assert process.returncode==73 and process.stdout==b'' and process.stderr==b''
    with DeliveryJournal(directory,profile_id='b'*16) as journal:
        with pytest.raises(JournalError,match='journal_request_not_replayed'):journal.reserve(packet())


@pytest.mark.parametrize('damage',['mode','symlink','hardlink','partial','changed_binding','unexpected','gap'])
def test_unsafe_or_partial_records_fail_closed_and_are_preserved(directory,tmp_path,damage):
    with DeliveryJournal(directory,profile_id='b'*16) as journal:journal.reserve(packet())
    start=directory/('a'*32+'.reserved.json')
    if damage=='mode':start.chmod(0o644)
    if damage=='symlink':(directory/('c'*32+'.reserved.json')).symlink_to(start)
    if damage=='hardlink':os.link(start,directory/('c'*32+'.reserved.json'))
    if damage=='partial':start.write_bytes(b'{')
    if damage=='changed_binding':
        binding=json.loads((directory/'binding.json').read_bytes());binding['profile_id']='d'*16
        (directory/'binding.json').write_text(json.dumps(binding,sort_keys=True,separators=(',',':')))
    if damage=='unexpected':(directory/'unknown').write_bytes(b'invented')
    if damage=='gap':(directory/('c'*32+'.sent.json')).write_bytes(b'{}')
    before={path.name:path.lstat().st_ino for path in directory.iterdir()}
    with pytest.raises((JournalError,OSError)):
        with DeliveryJournal(directory,profile_id='b'*16) as journal:
            altered=packet()
            if damage in {'symlink','hardlink'}:altered['request_id']='c'*32
            journal.reserve(altered)
    assert {path.name:path.lstat().st_ino for path in directory.iterdir()}==before


def test_fsync_failure_prevents_dispatch_and_preserves_reservation(monkeypatch,directory):
    with DeliveryJournal(directory,profile_id='b'*16) as journal:
        monkeypatch.setattr(os,'fsync',lambda fd:(_ for _ in ()).throw(OSError('invented sync failure')))
        with pytest.raises(JournalError,match='journal_io_failed'):journal.reserve(packet())
        with pytest.raises(JournalError,match='journal_request_not_replayed'):journal.reserve(packet())


def test_changed_payload_response_and_missing_predecessor_are_refused(directory):
    with DeliveryJournal(directory,profile_id='b'*16) as journal:
        journal.reserve(packet())
        changed=packet();changed['text']='Changed invented private message.'
        with pytest.raises(JournalError,match='journal_request_conflict'):journal.reserve(changed)
        with pytest.raises(JournalError):journal.transition(packet(),response(),'sending')
        journal.transition(packet(),response(),'handled')
        changed_response=response();changed_response['text']='Changed invented private reply.'
        with pytest.raises(JournalError,match='journal_transition_conflict'):
            journal.transition(packet(),changed_response,'sending')
        journal.transition(packet(),response(),'sending')
        with pytest.raises(JournalError):journal.transition(packet(),response(),'sending')


def test_directory_and_profile_binding_cannot_be_swapped(directory,tmp_path):
    link=tmp_path/'link';link.symlink_to(directory,target_is_directory=True)
    with pytest.raises(JournalError,match='journal_io_failed'):DeliveryJournal(link,profile_id='b'*16)
    with DeliveryJournal(directory,profile_id='b'*16):pass
    with pytest.raises(JournalError,match='journal_binding_changed'):DeliveryJournal(directory,profile_id='c'*16)
    directory.chmod(0o755)
    with pytest.raises(JournalError):DeliveryJournal(directory,profile_id='b'*16)


def test_exclusive_lock_and_capacity_do_not_allow_eviction(directory):
    with DeliveryJournal(directory,profile_id='b'*16,maximum_requests=1) as first:
        with DeliveryJournal(directory,profile_id='b'*16,maximum_requests=1) as second:
            with first._locked():
                with pytest.raises(JournalError,match='journal_busy'):second.reserve(packet())
            first.reserve(packet())
            changed=packet();changed['request_id']='c'*32
            with pytest.raises(JournalError,match='journal_capacity_exceeded'):second.reserve(changed)
            with pytest.raises(JournalError,match='journal_request_not_replayed'):second.reserve(packet())


@pytest.mark.parametrize('outcome',['pending_reply','exception','cancelled'])
def test_durable_native_admission_releases_the_lock_for_later_inputs(monkeypatch,directory,outcome):
    import isolated_delivery_journal as module
    from types import SimpleNamespace
    def make_event(value,profile):
        return SimpleNamespace(packet=value,message_id=value['request_id'])
    monkeypatch.setattr(module,'native_event',make_event)
    monkeypatch.setattr(module,'outbound_packet',lambda event,**kwargs:event.packet)
    async def check():
        waiting=asyncio.Event();answer=asyncio.Event();calls=[]
        async def native(event):
            calls.append(event.message_id)
            if event.message_id=='a'*32:
                waiting.set()
                if outcome=='exception':raise ValueError('invented-private-native-error')
                if outcome=='cancelled':raise asyncio.CancelledError()
                await answer.wait()
            else:answer.set()
            return 'Invented native result.'
        runner=SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True,profile_routes=[]),
            _profile_adapters={},_primary_message_handler=lambda:native)
        with DeliveryJournal(directory,profile_id='b'*16) as journal:
            ingress=module.DurableNativeTextIngress(runner,journal)
            first=asyncio.create_task(ingress.handle(packet()))
            await waiting.wait()
            next_packet=packet();next_packet['request_id']='c'*32
            await asyncio.wait_for(ingress.handle(next_packet),timeout=1)
            if outcome=='pending_reply':await first
            else:
                with pytest.raises(ValueError if outcome=='exception' else asyncio.CancelledError):await first
            with pytest.raises(JournalError,match='journal_request_not_replayed'):
                await ingress.handle(packet())
            assert calls==['a'*32,'c'*32]
    asyncio.run(check())


def test_io_failure_does_not_expose_a_private_path(monkeypatch,directory):
    def denied(*args,**kwargs):raise PermissionError('invented-private-path')
    monkeypatch.setattr(os,'open',denied)
    with pytest.raises(JournalError) as error:DeliveryJournal(directory,profile_id='b'*16)
    assert str(error.value)=='journal_io_failed'
