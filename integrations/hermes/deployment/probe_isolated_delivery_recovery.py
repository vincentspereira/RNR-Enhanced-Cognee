"""Invented native adapter delivery plus real process-crash reconciliation.

The only platform send is an in-memory SendResult. No real social adapter is
connected. Existing native handlers, session tracking and final-delivery code
remain intact; journal admission does not hold a turn lock across a native await.
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
import sys

from isolated_delivery_journal import DeliveryJournal, DurableNativeTextIngress, JournalError
from isolated_native_text_ingress import native_event, session_binding
from probe_isolated_native_text_ingress import guards, ALLOWED, REPO

PHASE = 'identity'
COUNTS = {}


def require(value):
    if not value:raise ValueError('delivery_recovery_probe_refused')


def request(packet, label, text='/help'):
    source=dict(platform='whatsapp',chat_id=ALLOWED,user_id=ALLOWED,thread_id=None)
    return dict(version=1,kind='message',profile_id=packet['profile_id'],
        request_id=hashlib.sha256((packet['run_id']+label).encode()).hexdigest()[:32],
        session_id=session_binding(source),source=source,text=text)


def synthetic_response(value):
    return dict(version=1,kind='response',profile_id=value['profile_id'],request_id=value['request_id'],
        text='Invented unacknowledged reply.',completed=True)


def refused(journal, value):
    try:journal.reserve(value)
    except JournalError as error:require(str(error)=='journal_request_not_replayed')
    else:require(False)


async def native_adapter(packet, profile, journal):
    global PHASE
    sys.path.insert(0,REPO)
    PHASE='native_imports'
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig,Platform,PlatformConfig
    from gateway.platforms.base import BasePlatformAdapter,SendResult
    runner=GatewayRunner(GatewayConfig(multiplex_profiles=True,sessions_dir=profile/'sessions',
        unauthorized_dm_behavior='ignore'))
    ingress=DurableNativeTextIngress(runner,journal)
    value=request(packet,'native-help')
    responses=[];sends=[]
    class Sink(BasePlatformAdapter):
        async def connect(self,is_reconnect=False):raise AssertionError('no_adapter_connection_permitted')
        async def disconnect(self):pass
        async def get_chat_info(self,chat_id):
            require(chat_id==ALLOWED)
            return dict(name='Invented offline DM',type='dm')
        async def send(self,chat_id,content,reply_to=None,metadata=None):
            require(len(responses)==1 and not sends and content==responses[0]['text'] and chat_id==ALLOWED)
            journal.transition(value,responses[0],'sending')
            sends.append(True)  # Invented local acceptance; never an external send.
            result=SendResult(success=True,message_id='invented-native-delivery')
            journal.transition(value,responses[0],'sent',external_id=result.message_id)
            return result
    adapter=Sink(PlatformConfig(typing_indicator=False),Platform.WHATSAPP)
    async def handler(_runner,event):
        wire=await ingress.handle_native(event)
        require(wire['completed'] is True and bool(wire['text']))
        responses.append(wire)
        return wire['text']
    runner._wire_adapter_handlers(adapter,message_handler=handler.__get__(runner))
    adapter.gateway_runner=runner
    runner.adapters[Platform.WHATSAPP]=adapter
    PHASE='native_adapter_pipeline'
    event=native_event(value,packet['profile_id'])
    await adapter.handle_message(event)
    tasks=list(adapter._session_tasks.values())
    require(len(tasks)==1)
    await asyncio.wait_for(asyncio.gather(*tasks),timeout=25)
    require(sends==[True] and len(responses)==1 and not adapter._session_tasks and not runner._agent_cache)
    require(journal._record(value['request_id'],'sent')['stage']=='sent')


def operation(packet):
    global PHASE,COUNTS
    require(isinstance(packet,dict) and set(packet)=={'uid','gid','worker_uid','profile_id','run_id','phase'})
    require(packet['phase'] in {'initial','restart','finish','peer'}
        and isinstance(packet['run_id'],str) and len(packet['run_id'])==32
        and all(c in '0123456789abcdef' for c in packet['run_id']))
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    uid,gid=packet['uid'],packet['gid']
    require(type(uid) is int and uid>0 and type(gid) is int and gid>0
        and os.getresuid()==(uid,)*3 and os.getresgid()==(gid,)*3 and not os.getgroups()
        and fields['NoNewPrivs'].strip()=='1'
        and all(fields[name].strip()=='0000000000000000' for name in ('CapEff','CapAmb','CapInh')))
    base=Path('/tmp')/('ec-delivery-recovery-'+packet['run_id'])
    COUNTS=guards()
    PHASE=packet['phase']
    if packet['phase']=='peer':
        require(uid!=packet['worker_uid'])
        try:fd=os.open(base,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        except PermissionError as error:require(error.errno==13)
        else:os.close(fd);require(False)
        return dict(complete=True,phase='peer',peer_os_access_denied=True),0
    require(uid==packet['worker_uid'])
    profile=base/'profile';directory=profile/'isolated-delivery'
    if packet['phase']=='initial':
        base.mkdir(mode=0o700);profile.mkdir(mode=0o700);directory.mkdir(mode=0o700)
        for name,content in {'.env':'GATEWAY_ALLOWED_USERS='+ALLOWED+'\n',
            'config.yaml':'gateway:\n  multiplex_profiles: true\n  unauthorized_dm_behavior: ignore\n'}.items():
            fd=os.open(profile/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as output:output.write(content)
    for path in (base,profile,directory):
        info=path.lstat()
        require(__import__('stat').S_ISDIR(info.st_mode) and info.st_uid==uid and info.st_mode&0o777==0o700)
    os.environ.clear();os.environ.update(HOME=str(profile),HERMES_HOME=str(profile),PATH='/usr/bin:/bin',LANG='C.UTF-8')
    os.chdir(profile)
    journal=DeliveryJournal(directory,profile_id=packet['profile_id'])
    native=request(packet,'native-help');before=request(packet,'before-handler');ambiguous=request(packet,'ambiguous-send')
    if packet['phase']=='initial':
        asyncio.run(native_adapter(packet,profile,journal))
        journal.reserve(before)
        require(COUNTS==dict(network=0,real_profile=0,subprocess=0))
        return dict(complete=True,phase='initial',native_base_adapter_text_component_qualified=True,
            reservation_fsynced_before_forced_exit=True),73
    refused(journal,native);refused(journal,before)
    if packet['phase']=='restart':
        journal.reserve(ambiguous)
        journal.transition(ambiguous,synthetic_response(ambiguous),'handled')
        journal.transition(ambiguous,synthetic_response(ambiguous),'sending')
        return dict(complete=True,phase='restart',completed_handler_not_replayed=True,
            interrupted_reservation_not_replayed=True,send_started_fsynced_before_forced_exit=True),74
    refused(journal,ambiguous)
    try:journal.transition(ambiguous,synthetic_response(ambiguous),'sending')
    except JournalError as error:require(str(error)=='journal_transition_not_replayed')
    else:require(False)
    require(len(journal._inventory())==3 and COUNTS==dict(network=0,real_profile=0,subprocess=0))
    require(journal._record(ambiguous['request_id'],'sending')['stage']=='sending')
    raw=b'\n'.join(path.read_bytes() for path in directory.iterdir())
    require(b'Invented unacknowledged reply.' not in raw and b'"text"' not in raw and b'"user_id"' not in raw)
    journal.close()
    return dict(complete=True,phase='finish',ambiguous_send_not_replayed=True,
        journal_metadata_only=True,interrupted_evidence_preserved=True),0


def main():
    signal.signal(signal.SIGALRM,lambda *args:os._exit(2));signal.alarm(65)
    logging.disable(logging.CRITICAL)
    try:
        packet=json.loads(sys.stdin.buffer.readline(4097))
        with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
            result,status=operation(packet)
    except Exception as error:
        result=dict(complete=False,phase=PHASE,error_kind=type(error).__name__ if type(error).__name__ in
            {'ValueError','PermissionError','JournalError','AttributeError','TypeError','TimeoutError'} else 'other',
            denied_attempt_counts=COUNTS)
        status=1
    print(json.dumps(result),flush=True)
    if status in {73,74}:os._exit(status)
    return status
