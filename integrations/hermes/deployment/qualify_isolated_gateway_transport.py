"""One no-model, no-profile-data transport qualification under two real UIDs.

Reuse existing restricted candidate identities and the completed backup pass.
Root-created socket pairs reproduce inherited listener credentials. Per-message
kernel credentials must identify each restricted sender independently. No
service is installed, no native conversation runs and no admission policy changes.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import socket
import subprocess
import sys
import tempfile
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-launch-completion-batch-v2'
ARTIFACT = BASE / 'operator-isolated-gateway-transport-v1'
BACKUP_PASS = BASE / 'operator-fleet-daily-backups-v2/installed.summary.json'
BACKUP_SHA = '19956e7f031a0e70d9758bb8e9aede7c13f631f44ebfb8b7e50727eec8dcb16b'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
POLICY_SHA = '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102'
HELPER_SHA = 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94'
TRANSPORT_SHA = '543a712ebe8ab95bdd9ab48bb202e71be116e5a51ea138236f0a4baa6acf9711'
EXECUTABLE = '/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python'
ERROR_CATEGORIES = frozenset({'transport_contract_refused','duplicate_transport_field','transport_text_refused',
    'transport_text_budget','fixed_profile_binding_refused','unsupported_transport_operation','transport_encoding_refused',
    'transport_frame_budget','transport_number_refused','transport_decoding_refused','transport_socket_refused',
    'connection_identity_denied','transport_deadline','transport_receive_failed','transport_ancillary_refused',
    'transport_connection_closed','message_sender_identity_denied','transport_send_failed'})

CHILD = b'''
import contextlib,signal,sys
CHILD_PHASE='identity'
def child_operation():
 global CHILD_PHASE
 signal.signal(signal.SIGALRM,lambda *args:os._exit(2));signal.alarm(15)
 packet=json.loads(sys.stdin.buffer.readline(4097))
 require(set(packet)=={'uid','gid','role','case','fd','frontend_uid','worker_uid','profile_id','request_id'})
 status=dict(line.split(':',1) for line in __import__('pathlib').Path('/proc/self/status').read_text().splitlines())
 require(os.getuid()==os.geteuid()==packet['uid']>0 and os.getgid()==os.getegid()==packet['gid']>0
   and os.getresuid()==(packet['uid'],)*3 and os.getresgid()==(packet['gid'],)*3
   and not os.getgroups() and status['NoNewPrivs'].strip()=='1'
   and all(status[key].strip()=='0000000000000000' for key in ('CapEff','CapAmb','CapInh')))
 require(packet['case'] in {'roundtrip','wrong_sender','wrong_profile'} and packet['role'] in {'sender','receiver'})
 expected=packet['frontend_uid'] if packet['role']=='receiver' else packet['worker_uid']
 CHILD_PHASE='socket_identity'
 with socket.socket(fileno=packet['fd']) as connection:
  channel=CredentialChannel(connection,profile_id=packet['profile_id'],sender_uid=expected,listener_uid=0,timeout=5)
  value={'version':1,'kind':'message','profile_id':packet['profile_id'],'request_id':packet['request_id'],
    'session_id':'a'*32,'source':{'platform':'cli','chat_id':'invented','user_id':'invented','thread_id':None},
    'text':'Invented isolated transport qualification only.'}
  denied=False;accepted=False
  if packet['role']=='sender':
   CHILD_PHASE='sender_send'
   if packet['case']=='wrong_profile':
    other='f'*16 if packet['profile_id']!='f'*16 else 'e'*16
    value['profile_id']=other;connection.sendall(encode(value,other))
   else:channel.send(value)
   if packet['case']=='roundtrip':
    CHILD_PHASE='sender_receive'
    response=channel.receive()
    require(response=={'version':1,'kind':'response','profile_id':packet['profile_id'],
      'request_id':packet['request_id'],'text':'Invented transport reply.','completed':True})
    accepted=True
  else:
   CHILD_PHASE='receiver_receive'
   try:received=channel.receive()
   except TransportError as error:
    category='message_sender_identity_denied' if packet['case']=='wrong_sender' else 'fixed_profile_binding_refused'
    require(packet['case']!='roundtrip' and str(error)==category);denied=True
   else:
    require(packet['case']=='roundtrip' and received==value);accepted=True
    CHILD_PHASE='receiver_reply'
    channel.send({'version':1,'kind':'response','profile_id':packet['profile_id'],
      'request_id':packet['request_id'],'text':'Invented transport reply.','completed':True})
 signal.alarm(0)
 print(json.dumps({'complete':True,'role':packet['role'],'case':packet['case'],'identity_restricted':True,
  'accepted':accepted,'denied':denied,'profile_contents_read':False,'model_called':False}))
def child():
 try:child_operation()
 except Exception as error:
  kind=type(error).__name__;number=getattr(error,'errno',None)
  label=str(error) if isinstance(error,TransportError) else ''
  print(json.dumps({'complete':False,'phase':CHILD_PHASE,'error_kind':kind if kind in {
   'TransportError','PermissionError','ValueError','OSError','TimeoutError','TypeError'} else 'other',
   'errno':number if type(number) is int and number in {1,2,13,20,30,40} else None,
   'category':label if label in ERROR_CATEGORIES else 'other'}))
  raise SystemExit(1)
'''


def require(value):
    if not value: raise ValueError('isolated_transport_qualification_refused')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def owner_program_source(transport):
    require(hashlib.sha256(transport).hexdigest()==TRANSPORT_SHA)
    return transport+b'\nERROR_CATEGORIES='+repr(sorted(ERROR_CATEGORIES)).encode()+b'\n'+CHILD


def definitions(path,digest):
    raw=path.read_bytes()
    require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    scope={'__name__':'verified_transport_qualification_support','__file__':str(path)}
    exec(compile(raw,'<verified-transport-qualification-support>','exec'),scope)
    return scope


def admission(read,policy):
    result=json.loads(read(BACKUP_PASS,0))
    require(result.get('complete') is True and result.get('operator_helper_sha256')==BACKUP_SHA
        and result.get('source_revision')==BASE.name and result.get('completed_profiles')==result.get('selected_profiles')==41
        and result.get('signed_encrypted_generations_created')==41
        and result.get('scheduled_fleet_profile_backup_qualified') is True
        and result.get('installed_daily_timer_enabled') is True
        and result.get('journal_scheduling_proof',{}).get('verified') is True
        and result.get('all_admission_policies_preserved_disabled') is True
        and all(result.get(key) is False for key in ('model_called','memory_api_called','keys_changed',
            'private_keys_sent_to_owner','source_profiles_changed','fleet_launch_approved')))
    rows=policy['load'](BASE/'operator-named-fleet-issuer-review-v1/candidate-policy.json')['profiles']
    require(len(rows)==len({row['uid'] for row in rows})==40 and all(row['enabled'] is False for row in rows))
    members=json.loads(read(BACKUP_PASS.parent/'members.private.json',0))
    require(isinstance(members,list) and len(members)==len({row['entry']['uid'] for row in members})==41
        and members[:-1]==[dict(kind='named',entry=row) for row in rows] and members[-1].get('kind')=='main')
    selected=rows[:2]
    for row in selected:
        account=pwd.getpwnam(row['user'])
        require(account.pw_uid==row['uid']>0 and account.pw_dir==row['home']
            and re.fullmatch('ecbot_[a-f0-9]{16}',row['user'])
            and account.pw_dir=='/var/lib/enhanced-cognee-profiles/'+row['user'][6:]
            and row['profile']==str(Path(account.pw_dir)/'.hermes') and account.pw_gid>0
            and account.pw_shell=='/usr/sbin/nologin'
            and os.getgrouplist(account.pw_name,account.pw_gid)==[account.pw_gid])
    require(selected[0]['uid']!=selected[1]['uid'])
    return selected


def spawn(account,packet,helper,source):
    code,line=helper['owner_program'](source)
    process=subprocess.Popen(['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--',
        EXECUTABLE,'-I','-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        cwd='/',user=account.pw_uid,group=account.pw_gid,extra_groups=(),pass_fds=(packet['fd'],),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    process.stdin.write(line+canonical(packet)+b'\n');process.stdin.flush();process.stdin.close()
    return process


def receipt(value,role,case):
    require(isinstance(value,dict) and set(value)=={'complete','role','case','identity_restricted','accepted','denied',
        'profile_contents_read','model_called'} and value.get('complete') is True
        and value.get('role')==role and value.get('case')==case and value.get('identity_restricted') is True
        and value.get('profile_contents_read') is False and value.get('model_called') is False
        and value.get('accepted') is (case=='roundtrip') and value.get('denied') is (role=='receiver' and case!='roundtrip'))
    return value


def failure_projection(value,role,status):
    result=dict(role=role,phase='startup',error_kind='other',exit_code=status)
    if isinstance(value,dict):
        if isinstance(value.get('phase'),str) and value['phase'] in {'identity','socket_identity','sender_send','sender_receive','receiver_receive','receiver_reply'}:
            result['phase']=value['phase']
        if isinstance(value.get('error_kind'),str) and value['error_kind'] in {'TransportError','PermissionError','ValueError','OSError','TimeoutError','TypeError'}:
            result['error_kind']=value['error_kind']
        if type(value.get('errno')) is int and value['errno'] in {1,2,13,20,30,40}:result['errno']=value['errno']
        if isinstance(value.get('category'),str) and value['category'] in ERROR_CATEGORIES:result['category']=value['category']
    return result


def run_case(case,rows,helper,source):
    require(case in {'roundtrip','wrong_sender','wrong_profile'})
    frontend,worker=[pwd.getpwnam(row['user']) for row in rows]
    sender=worker if case=='wrong_sender' else frontend
    sockets=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    for connection in sockets:connection.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
    processes=[];request=uuid.uuid4().hex;profile=rows[1]['user'][6:]
    try:
        for role,account,connection in [('receiver',worker,sockets[1]),('sender',sender,sockets[0])]:
            packet=dict(uid=account.pw_uid,gid=account.pw_gid,role=role,case=case,fd=connection.fileno(),
                frontend_uid=frontend.pw_uid,worker_uid=worker.pw_uid,profile_id=profile,request_id=request)
            processes.append((role,spawn(account,packet,helper,source)))
        for connection in sockets:connection.close()
        results=[];failures=[]
        for role,process in processes:
            status=process.wait(timeout=20)
            output=process.stdout.read(4097);require(len(output)<=4096)
            try:value=json.loads(output)
            except (ValueError,UnicodeError):value=None
            if status!=0 or not isinstance(value,dict) or value.get('complete') is not True:
                failures.append(failure_projection(value,role,status));continue
            results.append(receipt(value,role,case))
        if failures:
            error=ValueError('transport_owner_incomplete');error.child_diagnostics=failures;raise error
        return dict(complete=True,case=case,two_restricted_processes=True,
            root_created_descriptor_handoff=True,kernel_sender_identity_checked=True,
            positive_roundtrip=case=='roundtrip',unauthorized_sender_denied=case=='wrong_sender',
            different_profile_denied=case=='wrong_profile',profile_contents_read=False,
            native_turn_started=False)
    finally:
        for connection in sockets:connection.close()
        for _,process in processes:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            for stream in (process.stdin,process.stdout):
                if stream:stream.close()


def main():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    support=definitions(PACKAGE/'recover_launch_graph_operator.py',SUPPORT_SHA)
    read,write=support['read_file'],support['private_write']
    source=globals()['_verified_source_bytes'];digest=hashlib.sha256(source).hexdigest()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0))
        require(context.get('source_sha256')==digest and context.get('transport_sha256')==TRANSPORT_SHA)
        require(isinstance(context.get('bindings_sha256'),str) and re.fullmatch('[a-f0-9]{64}',context['bindings_sha256'])
            and hashlib.sha256(read(ARTIFACT/'selected-bindings.private.json',0)).hexdigest()==context['bindings_sha256'])
        require(hashlib.sha256((ARTIFACT/'isolated_gateway_transport.py').read_bytes()).hexdigest()==TRANSPORT_SHA
            and hashlib.sha256((ARTIFACT/'qualify_isolated_gateway_transport.py').read_bytes()).hexdigest()==digest)
        evidence=Path(context['evidence'])
        require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('isolated-transport-'))
        require(os.path.lexists(evidence/'summary.json'))
        result=json.loads(read(evidence/'summary.json',0))
        require(result.get('operator_helper_sha256')==digest and result.get('transport_component_sha256')==TRANSPORT_SHA
            and result.get('source_revision')==BASE.name and result.get('binding_manifest_sha256')==context['bindings_sha256'])
        print(json.dumps(result),flush=True)
        return 0 if result.get('complete') is True else 1
    policy=definitions(PACKAGE/'fleet_credential_policy.py',POLICY_SHA)
    rows=admission(read,policy)
    helper=definitions(PACKAGE/'qualify_launch_isolated_accounts.py',HELPER_SHA)
    protected=definitions(PACKAGE/'renew_fleet_credentials.py',
        '146f340ad9258179bf3555f8949ce08ba66aff5554264537603244018d4e7495')['protected']
    protected(Path(EXECUTABLE),final_link=True);protected(Path(EXECUTABLE).resolve(strict=True))
    protected(Path('/usr/bin/setpriv'))
    transport=(directory/'isolated_gateway_transport.py').read_bytes()
    require(hashlib.sha256(transport).hexdigest()==TRANSPORT_SHA)
    owner_source=owner_program_source(transport)
    helper['owner_program'](owner_source)
    require(not os.path.lexists(ARTIFACT))
    ARTIFACT.mkdir(mode=0o755)
    write(ARTIFACT/'qualify_isolated_gateway_transport.py',source)
    write(ARTIFACT/'isolated_gateway_transport.py',transport)
    bindings=canonical(rows);binding_digest=hashlib.sha256(bindings).hexdigest()
    write(ARTIFACT/'selected-bindings.private.json',bindings)
    for path in ARTIFACT.glob('*.py'):path.chmod(0o644)
    evidence=Path(tempfile.mkdtemp(prefix='isolated-transport-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,transport_sha256=TRANSPORT_SHA,
        bindings_sha256=binding_digest,evidence=str(evidence))))
    fd=os.open(ARTIFACT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    before=read(BASE/'operator-named-fleet-issuer-review-v1/candidate-policy.json',0)
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,operator_helper_sha256=digest,
        transport_component_sha256=TRANSPORT_SHA,distinct_restricted_uids=2,completed_cases=0,
        binding_manifest_sha256=binding_digest,
        qualification_surface='synthetic_local_transport_with_actual_distinct_uids',
        credentials_issued=0,keys_read=False,source_profiles_changed=False,profile_contents_read=False,
        services_installed=False,platform_adapters_started=0,model_called=False,memory_api_called=False,
        canonical_memory_edits=False,native_gateway_integration_qualified=False,
        production_dispatch_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False)
    try:
        for index,case in enumerate(('roundtrip','wrong_sender','wrong_profile'),1):
            print(json.dumps(dict(event='isolated_transport_progress',current=index,total=3)),flush=True)
            write(evidence/(case+'.started.json'),canonical(dict(case=case)))
            report=run_case(case,rows,helper,owner_source)
            write(evidence/(case+'.receipt.json'),canonical(report));result['completed_cases']+=1
        require(read(BASE/'operator-named-fleet-issuer-review-v1/candidate-policy.json',0)==before)
        result.update(complete=True,kernel_authenticated_transport_qualified=True,all_admission_policies_preserved_disabled=True)
    except (Exception,KeyboardInterrupt) as error:
        result.update(category='isolated_transport_incomplete_preserve_evidence_no_automatic_retry',
            error_kind=type(error).__name__ if type(error).__name__ in {'ValueError','PermissionError','TimeoutExpired','KeyboardInterrupt'} else 'other')
        if isinstance(getattr(error,'child_diagnostics',None),list):result['child_diagnostics']=error.child_diagnostics
    write(evidence/'summary.json',canonical(result));print(json.dumps(result),flush=True)
    return 0 if result['complete'] else 1
