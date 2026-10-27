"""Admit bounded new test partitions after the retained V2 scope refusal.

Repeating launch attaches to the retained job; it never repeats model turns.
Only ordinary model/API credentials cross owner pipes. No root keys, private
profile contents, prompts or model replies enter output or evidence. Existing
profiles, launchers, records, admission policies and completed tests are retained.
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile
import time
import uuid

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-current-model-native-v3'
RELEASE=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROVIDER=Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
FIXTURES=Path('/var/lib/hermes-renewal-qualification')
UNIT='ec-launch-current-model-native-v3-20261027.service'
GUARD_SHA='61d33085610488c6ed41db6d502d7ba715cd2579353b253e8b9d8678cd285ffb'
OBSERVER_SHA='2488f9255af9cefd9230a22eae062c49c845e7a57c366da628937f2a50e7af27'
CHILD_NAME='qualify_launch_model_child.py'
CHILD_SHA='68e4cee48692fd5759a705153045f489b1d13f87cb41b0699cac1daf99bf7bf4'
PINS={
    CHILD_NAME:CHILD_SHA,
    'zai_native_qualification_guard_v2.py':GUARD_SHA,
    'observe_launch_native_runtime.py':OBSERVER_SHA,
    'bind_launch_model_route.py':'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52',
    'qualify_launch_isolated_accounts.py':'d0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94',
    'recover_launch_graph_operator.py':'d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef',
    'qualify_launch_gateway_renewal_v2.py':'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2',
}
PHASE='identity'
PHASES={'identity','fixture','imports','scope','agent','native_turn','verification','cleanup'}
SAFE_KINDS={'ValueError','GuardError','PermissionError','FileNotFoundError','AuthError','TimeoutExpired','RuntimeError'}
PHYSICAL={'capture':6,'recall':6}
OBSERVATION={}
OWNER_OBSERVER=None


def require(value):
    if not value:raise ValueError('current_model_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes()
    require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    namespace={'__name__':'verified_current_model_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-public-current-model-support>','exec'),namespace)
    return namespace


def install_child(directory):
    child=definitions(directory/CHILD_NAME,CHILD_SHA)
    for name in ('identity','packet_shape','validate_result','safe_report','SAFE_KINDS'):
        globals()[name]=child[name]


def owner(helper,source,account,packet):
    packet_shape(packet)
    code,line=helper['owner_program'](source)
    frame=canonical(packet);require(len(frame)<=65536)
    process=subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',code],
        input=line+frame+b'\n',stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=180,cwd='/',
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    require(0<len(process.stdout)<=8192)
    try:value=json.loads(process.stdout)
    except Exception:
        if OWNER_OBSERVER is not None:OWNER_OBSERVER(packet['stage'],None)
        raise
    if OWNER_OBSERVER is not None:OWNER_OBSERVER(packet['stage'],value)
    validate_result(value,packet['stage'])
    return value


def properties(unit=None):
    result=subprocess.run(['/usr/bin/systemctl','show',unit or UNIT,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    require(len(result.stdout)<=8192)
    return dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line)


def quiescent(value):
    return value.get('ActiveState') in {'inactive','failed'} and value.get('MainPID')==value.get('ControlPID')=='0'


def retained_scope_refusal(read):
    previous=BASE/'operator-evidence/current-model-native-spnm6ro6'
    value=json.loads(read(previous/'summary.json',0))
    require(value.get('complete') is False and value.get('failure_phase')=='capture'
        and value.get('credentials_issued')==2 and value.get('error_kind')=='ValueError'
        and value.get('operator_helper_sha256')=='e21579372b94a1a881908e543342fbfcd7582d593ac579d7f2b23a1d805dbda1'
        and value.get('new_invented_scope')=='e04a048d26af4631b2126bcd27a9174a'
        and value.get('all_admission_policies_preserved_disabled') is True)
    old=BASE/'operator-current-model-native-v2'
    context=json.loads(read(old/'context.json',0))
    require(context.get('evidence')==str(previous) and context.get('run_id')==value['new_invented_scope']
        and hashlib.sha256(read(old/'qualify_launch_current_model_v2.py',0)).hexdigest()==value['operator_helper_sha256']
        and quiescent(properties('ec-launch-current-model-native-v2-20261027.service')))
    capture=json.loads(read(previous/'capture.summary.json',0))
    require(capture.get('complete') is False and capture.get('phase')=='scope'
        and capture.get('error_kind')=='other' and capture.get('observation')=={})
    return str(previous)


def worker(read,write):
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    install_child(ARTIFACT)
    context=json.loads(read(ARTIFACT/'context.json',0));ident=context['run_id'];identity(ident)
    evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('current-model-native-[A-Za-z0-9_-]{6,64}',evidence.name))
    helper=definitions(ARTIFACT/'qualify_launch_isolated_accounts.py',PINS['qualify_launch_isolated_accounts.py'])
    route=definitions(ARTIFACT/'bind_launch_model_route.py',PINS['bind_launch_model_route.py'])
    native=definitions(ARTIFACT/'qualify_launch_gateway_renewal_v2.py',PINS['qualify_launch_gateway_renewal_v2.py'])
    for name,digest in native['NATIVE'].items():require(hashlib.sha256((RELEASE/'repo'/name).read_bytes()).hexdigest()==digest)
    for name,digest in native['PROVIDER_FILES'].items():require(hashlib.sha256((PROVIDER/name).read_bytes()).hexdigest()==digest)
    policies=[Path('/etc/enhanced-cognee/fleet-credentials.json'),BASE/'operator-isolated-issuer-candidate-v3/candidate-policy.json']
    before={path:read(path,0) for path in policies}
    require(all(row['enabled'] is False for raw in before.values() for row in json.loads(raw)['profiles']))
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,new_invented_scope=ident,
        source_profiles_changed=False,existing_launchers_changed=False,private_keys_sent_to_owner=False,
        credentials_issued=0,production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,
        maximum_context_verified=False,fleet_launch_approved=False,automatic_model_retry=False,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(evidence/'started.json',canonical(result));phase='preflight'
    try:
        result['continued_from']=retained_scope_refusal(read)
        _,_,authority=route['prepare']((ARTIFACT/'bind_launch_model_route.py').read_bytes(),definitions)
        require(authority['endpoint_path']=='/api/coding/paas/v4')
        issuer=definitions(BASE/'operator-issuer-candidate-v2/provision_pilot_access.py',
            'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6')
        key=issuer['load_signing_key']();now=int(time.time())
        ordinary=[issuer['sign_claims'](dict(identity(ident,peer),iat=now,exp=now+1200),key) for peer in (False,True)]
        del key;result['credentials_issued']=2
        guard=(ARTIFACT/'zai_native_qualification_guard_v2.py').read_bytes()
        require(hashlib.sha256(guard).hexdigest()==GUARD_SHA)
        observer=(ARTIFACT/'observe_launch_native_runtime.py').read_bytes()
        require(hashlib.sha256(observer).hexdigest()==OBSERVER_SHA)
        packet=dict(stage='capture',run_id=ident,key=authority['key'],token=ordinary[0],peer=ordinary[1],
            guard=guard.decode(),observer=observer.decode(),record_id=None)
        account=pwd.getpwnam('hermes-runtime');source=(ARTIFACT/CHILD_NAME).read_bytes()
        def observe(stage,value):
            report=safe_report(value)
            write(evidence/(stage+'.observation.json'),canonical(report))
            result['child_observation']=report
        globals()['OWNER_OBSERVER']=observe
        for stage in ('capture','recall'):
            phase=stage;packet['stage']=stage
            write(evidence/(stage+'.started.json'),canonical(dict(stage=stage,automatic_retry=False)))
            value=owner(helper,source,account,packet)
            write(evidence/(stage+'.summary.json'),canonical(value))
            require(value.get('complete') is True)
            if stage=='capture':packet['record_id']=value['record_id']
        result.update(complete=True,current_configured_model_native_capture_qualified=True,
            current_configured_model_fresh_process_recall_qualified=True,invented_sensitive_input_excluded=True,
            invented_record_retracted_history_preserved=True,model_route='zai/glm-5.3-flash',
            physical_model_request_limit=12,separate_native_processes=2)
    except Exception as error:
        result.update(category='current_model_native_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase,
            error_kind=type(error).__name__ if type(error).__name__ in SAFE_KINDS else 'other')
    require(all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));sync(evidence)
    return 0 if result['complete'] else 1


def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def watch(read):
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence']);last=0
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('current-model-native-[A-Za-z0-9_-]{6,64}',evidence.name))
    try:
        while True:
            value=properties()
            try:result=json.loads(read(evidence/'summary.json',0))
            except FileNotFoundError:result=None
            if result is not None or value.get('ActiveState')=='failed' or value.get('SubState')=='exited':
                result=result or dict(complete=False,evidence=str(evidence),category='current_model_worker_exited_preserve_evidence')
                if not quiescent(value):
                    subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=True)
                result['operator_job_stopped']=quiescent(properties())
                result['complete']=result.get('complete') is True and result['operator_job_stopped']
                print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            if quiescent(value):
                print(json.dumps(dict(complete=False,evidence=str(evidence),category='current_model_job_not_running_preserve_evidence')),flush=True);return 1
            if time.monotonic()-last>=15:
                print('{"event":"current_model_native_running","note":"Ctrl+C detaches; repeat qualify-model-scope to reattach without repeating model turns."}',flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def launch():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    shared=definitions(directory/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
    read,write=shared['read_file'],shared['private_write']
    if os.path.lexists(ARTIFACT):return watch(read)
    install_child(directory)
    retained_scope_refusal(read)
    require(properties().get('LoadState')=='not-found' and quiescent(properties()))
    # Retain both completed batches as preconditions; never call their workers.
    main=json.loads(read(BASE/'operator-evidence/main-operational-recovery-0xjyrv2b/summary.json',0))
    named=json.loads(read(BASE/'operator-evidence/named-runtime-routes-ivk3f5hw/summary.json',0))
    require(main.get('complete') is True and main.get('main_operational_snapshot_restore_qualified') is True
        and named.get('complete') is True and named.get('qualified_profiles')==40 and named.get('failed_profiles')==0)
    driver=definitions(BASE/'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    driver['protected'](FIXTURES)
    native=definitions(directory/'qualify_launch_gateway_renewal_v2.py',PINS['qualify_launch_gateway_renewal_v2.py'])
    for name in native['NATIVE']:driver['protected'](RELEASE/'repo'/name)
    for name in native['PROVIDER_FILES']:driver['protected'](PROVIDER/name)
    account=pwd.getpwnam('hermes-runtime');require(account.pw_uid>0)
    ident=uuid.uuid4().hex;profile=FIXTURES/('zai_model_'+ident)
    profile.mkdir(mode=0o700);os.chown(profile,account.pw_uid,account.pw_gid)
    sources={Path(__file__).name:globals()['_verified_source_bytes']}
    for name,digest in PINS.items():sources[name]=definitions(directory/name,digest)['_verified_source_bytes']
    evidence=Path(tempfile.mkdtemp(prefix='current-model-native-',dir=BASE/'operator-evidence'))
    ARTIFACT.mkdir(mode=0o700)
    for name,raw in sources.items():write(ARTIFACT/name,raw)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    write(ARTIFACT/'context.json',canonical(dict(evidence=str(evidence),run_id=ident)));sync(ARTIFACT)
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='',ProtectHome='no',ProtectSystem='strict',
        PrivateTmp='no',ReadWritePaths=str(BASE/'operator-evidence')+' '+str(profile),
        Restart='no',TimeoutStartSec='480',MemoryMax='2G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+k+'='+v for k,v in settings.items()]
    args += [str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/Path(__file__).name),'--worker']
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=True)
    return watch(read)


if __name__=='__main__':
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        require(sys.argv[1:]==['--worker'])
        shared=definitions(ARTIFACT/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
        raise SystemExit(worker(shared['read_file'],shared['private_write']))
    except Exception:
        print('{"complete":false,"category":"current_model_native_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
