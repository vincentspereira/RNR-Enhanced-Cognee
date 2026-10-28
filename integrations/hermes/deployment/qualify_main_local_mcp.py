"""Qualify two public local MCP components; keep all fleet admission closed."""
from __future__ import annotations
import hashlib
import json
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
ARTIFACT=BASE/'operator-main-local-mcp-v1'
UNIT='ec-main-local-mcp-operator-v1-20261028.service'
PROGRAM_ROOT=Path('/opt/hermes-runtime/programs')
SUPPORT=BASE/'operator-main-rea-reviewed-candidate-v2/prepare_main_with_telegram.py'
SUPPORT_SHA='fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51'
PASSED=BASE/'operator-evidence/main-rea-reviewed-lsamkulo/finish.summary.json'
OWNER_SHA='e6aa3a3db3d6b7a9917314035c8646e446e5600a87fa253399b205bfefc37c82'
PROBE_SHA='415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
SNAPSHOT_SHA='b180a6e83e9a00a7e287645adb3ea82db4455319029c44e2dc2d20e10087a42c'
NODE_SHA='41a74efb34cbde5c7632cdac0cf8bd1a14d0b8d73dc1e82755014d9a9ce70f5c'
FIELDS=['LoadState','ActiveState','SubState','Result','ExecMainStatus','ExecMainPID','InvocationID',
    'User','PrivateNetwork','ProtectHome','NoNewPrivileges','CapabilityBoundingSet','AmbientCapabilities',
    'IPAddressDeny','RestrictAddressFamilies']


def require(value):
    if not value:raise ValueError('main_local_mcp_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_main_local_mcp_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-main-local-mcp-support>','exec'),value);return value


def helpers():
    support=definitions(SUPPORT,SUPPORT_SHA)
    old,c,read,write=support['helpers']();return support,old,c,read,write


def metadata(unit):
    process=subprocess.run(['/usr/bin/systemctl','show',unit,'--property='+','.join(FIELDS)],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=15)
    require(len(process.stdout)<=32768)
    return dict(row.split('=',1) for row in process.stdout.decode().splitlines() if '=' in row)


def retained(read):
    value=json.loads(read(PASSED,0))
    require(value.get('source_revision')==BASE.name and value.get('operator_helper_sha256')==SUPPORT_SHA
        and value.get('evidence')==str(PASSED.parent) and value.get('checkpoint')=='complete'
        and value.get('new_inactive_candidate')=='/var/lib/enhanced-cognee-profiles/5592956882ea9a13/ec-main-operational-restore-dzqxxbdg'
        and all(type(value.get(k)) is int for k in ('mcp_definitions_preserved','sqlite_databases_recovered',
            'remaining_reference_count','credentials_issued','encrypted_generations_created'))
        and value.get('mcp_definitions_preserved')==6 and value.get('sqlite_databases_recovered')==9
        and value.get('remaining_reference_count')==0 and value.get('credentials_issued')==value.get('encrypted_generations_created')==2
        and all(value.get(k) is True for k in ('complete','configured_candidate_restore_qualified','operator_job_stopped',
            'inactive_current_settings_preservation_qualified','prior_dependency_pass_preserved','rea_dependency_execution_qualified',
            'telegram_configuration_preserved_inactive_only','all_admission_policies_preserved_disabled',
            'current_auth_snapshot_preserved','source_current_at_completion'))
        and all(value.get(k) is False for k in ('candidate_promoted','source_profiles_changed','previous_candidates_changed',
            'programs_replayed','fleet_launch_approved','fleet_settings_accepted','telegram_activation_qualified')))
    return value


def validate_probe(value,invocation):
    keys={'complete','invocation_id','cases','real_profiles_read','credentials_read','model_called','memory_api_called',
        'external_sends','full_main_tool_coverage_qualified'}
    require(isinstance(value,dict) and set(value)==keys and value['invocation_id']==invocation
        and type(value['complete']) is bool and type(value['external_sends']) is int and value['external_sends']==0
        and all(value[k] is False for k in ('real_profiles_read','credentials_read','model_called','memory_api_called','full_main_tool_coverage_qualified'))
        and isinstance(value['cases'],dict) and set(value['cases'])=={'filesystem','rea'})
    for name,case in value['cases'].items():
        require(isinstance(case,dict) and type(case.get('complete')) is bool)
        if not case['complete']:
            require(set(case)=={'complete','error_kind'} and case['error_kind'] in
                {'ValueError','TimeoutError','OSError','PermissionError','JSONDecodeError','BrokenPipeError','other'})
            continue
        extra={'invented_write_read_passed','outside_root_denied'} if name=='filesystem' else {'binary_analysis_requested'}
        require(set(case)=={'complete','initialize_passed','tools_list_passed','tools_count','tools_called'}|extra
            and case['initialize_passed'] is case['tools_list_passed'] is True
            and type(case['tools_count']) is int and 1<=case['tools_count']<=512
            and type(case['tools_called']) is int and case['tools_called']==(4 if name=='filesystem' else 0))
        if name=='filesystem':require(case['invented_write_read_passed'] is case['outside_root_denied'] is True)
        else:require(case['binary_analysis_requested'] is False)
    require(value['complete']==all(case['complete'] for case in value['cases'].values()))
    return value


def journal_receipt(rows,state):
    invocation=state.get('InvocationID','');pid=state.get('ExecMainPID','')
    require(re.fullmatch('[a-f0-9]{32}',invocation) and pid.isdecimal() and int(pid)>0)
    candidates=[row for row in rows if isinstance(row,dict) and row.get('_SYSTEMD_INVOCATION_ID')==invocation
        and row.get('_PID')==pid and row.get('_UID')==str(pwd.getpwnam('ecbot_5592956882ea9a13').pw_uid)
        and row.get('_TRANSPORT')=='stdout' and isinstance(row.get('MESSAGE'),str)]
    require(len(candidates)==1 and len(candidates[0]['MESSAGE'])<=8192)
    value=validate_probe(json.loads(candidates[0]['MESSAGE']),invocation)
    require((state.get('Result')=='success' and state.get('ExecMainStatus')=='0')==value['complete'])
    return value


def proof(context,account,programs,write):
    ident=context['id'];unit='ec-main-local-mcp-'+ident+'.service';home=Path('/run')/unit.removesuffix('.service')
    public=PROGRAM_ROOT/('mcp-driver-'+ident);require(not os.path.lexists(public))
    raw=(ARTIFACT/'probe_main_local_mcp.py').read_bytes();require(hashlib.sha256(raw).hexdigest()==PROBE_SHA)
    public.mkdir(mode=0o755);public.chmod(0o755);write(public/'probe.py',raw);(public/'probe.py').chmod(0o644)
    require(metadata(unit).get('LoadState')=='not-found')
    settings=dict(Type='oneshot',RemainAfterExit='yes',User=account.pw_name,Group=str(account.pw_gid),
        NoNewPrivileges='yes',CapabilityBoundingSet='',AmbientCapabilities='',UMask='0077',
        PrivateNetwork='yes',IPAddressDeny='any',RestrictAddressFamilies='AF_UNIX',ProtectHome='yes',
        ProtectSystem='strict',PrivateTmp='yes',RuntimeDirectory=home.name,RuntimeDirectoryMode='0700',
        RuntimeDirectoryPreserve='yes',ReadWritePaths=str(home),TimeoutStartSec='240',MemoryMax='2G',
        InaccessiblePaths='/var/lib/enhanced-cognee-profiles /etc/enhanced-cognee /var/backups/enhanced-cognee /opt/enhanced-cognee-memory',
        StandardOutput='journal',StandardError='null',KillMode='control-group',Restart='no',LimitCORE='0',
        SystemCallFilter='~ptrace process_vm_writev',RestrictSUIDSGID='yes')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+unit]+['--property='+k+'='+v for k,v in settings.items()]
    args+=['/usr/bin/python3','-I','-B',str(public/'probe.py'),programs['filesystem'],programs['rea'],str(home)]
    try:
        subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
        deadline=time.monotonic()+260
        while time.monotonic()<deadline:
            state=metadata(unit)
            if state.get('SubState')=='exited' or state.get('ActiveState') in {'inactive','failed'}:break
            time.sleep(2)
        else:raise TimeoutError('offline_local_mcp_unit_deadline')
        require(state.get('User')==account.pw_name and state.get('PrivateNetwork')==state.get('ProtectHome')==state.get('NoNewPrivileges')=='yes'
            and state.get('CapabilityBoundingSet')==state.get('AmbientCapabilities')==''
            and state.get('RestrictAddressFamilies')=='AF_UNIX' and state.get('IPAddressDeny') in {'any','0.0.0.0/0 ::/0','::/0 0.0.0.0/0'})
        # Journald may finish delivering stdout just after the oneshot exits.
        # Wait for delivery, never rerun the probe to manufacture evidence.
        delivery_deadline=time.monotonic()+10
        while True:
            process=subprocess.run(['/usr/bin/journalctl','--no-pager','--output=json','--lines=16','--unit='+unit],
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=15)
            require(len(process.stdout)<=65536)
            rows=[json.loads(row) for row in process.stdout.splitlines()]
            present=any(row.get('_PID')==state.get('ExecMainPID') and row.get('_SYSTEMD_INVOCATION_ID')==state.get('InvocationID')
                and row.get('_TRANSPORT')=='stdout' for row in rows)
            if present or time.monotonic()>=delivery_deadline:break
            time.sleep(0.25)
        receipt=journal_receipt(rows,state)
    finally:
        subprocess.run(['/usr/bin/systemctl','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
        state=metadata(unit);require(state.get('ActiveState') in {'inactive','failed'} and state.get('SubState') in {'dead','failed'})
    return receipt


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    support,old,c,read,write=helpers();context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-local-mcp-'))
    retained(read);pass_bytes=read(PASSED,0);driver=c['legacy']();before=driver['policies'](read)
    entry,_=driver['fixed_entry'](read);require(entry['user']=='ecbot_5592956882ea9a13' and entry['enabled'] is False)
    account=pwd.getpwnam(entry['user']);source_account=pwd.getpwnam('vincentspereira')
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,operator_helper_sha256=context['source_sha256'],
        credentials_issued=0,keys_read=False,source_profiles_changed=False,previous_candidates_changed=False,
        model_called=False,memory_api_called=False,external_platform_sends=0,platform_adapters_started=0,
        binary_analysis_requested=False,completed_tests_replayed=False,main_tool_program_coverage_qualified=False,
        actual_profile_admission_qualified=False,production_dispatch_qualified=False,production_renewal_timer_enabled=False,
        fleet_launch_approved=False,automatic_retry=False,invocation_id=os.environ.get('INVOCATION_ID',''),
        qualification_surface='two_public_local_mcp_components_empty_home_actual_main_uid')
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']))
        bundle=definitions(ARTIFACT/'mcp_public_programs.py',OWNER_SHA);snapshot=bundle['library']();programs={};receipts={}
        for name,pin in bundle['PACKAGES'].items():
            result['checkpoint']='public_bundle_'+name
            value,body=c['owner'](source_account,bundle['_verified_source_bytes'],c['packet'](source_account,'public_mcp_archive',program=name),
                limit=pin['archive_bytes']+65537)
            require(value==dict(complete=True,program=name,archive_bytes=pin['archive_bytes'],archive_sha256=pin['sha256'],source_preserved=True)
                and len(body)==pin['archive_bytes'] and hashlib.sha256(body).hexdigest()==pin['sha256'])
            destination=PROGRAM_ROOT/('mcp-'+name+'-'+pin['sha256'][:16]);manifest=snapshot['validate'](body,name)
            reused=os.path.lexists(destination)
            if reused:snapshot['verify'](destination,manifest)
            else:snapshot['restore'](body,name,destination)
            programs[name]=str(destination);receipts[name]=dict(archive_sha256=pin['sha256'],archive_bytes=len(body),
                public_copy_readback_verified=True,existing_copy_reused=reused,version=pin['version'])
            del body
        write(evidence/'public-programs.json',canonical(receipts));result['public_programs']=receipts
        result['checkpoint']='network_isolated_mcp_requests';receipt=proof(context,account,programs,write)
        write(evidence/'component-receipt.json',canonical(receipt));result['components']=receipt['cases']
        result.update(complete=receipt['complete'],checkpoint='complete' if receipt['complete'] else 'component_failure',
            local_mcp_components_qualified=receipt['complete'],qualification_unit_stopped=True,network_isolated=True,
            original_main_candidate_pass_preserved=True)
        if not result['complete']:result['category']='local_mcp_component_incomplete_preserve_evidence'
    except Exception as error:
        result.update(category='main_local_mcp_incomplete_preserve_evidence',error_kind=type(error).__name__
            if type(error).__name__ in {'ValueError','OSError','PermissionError','TimeoutError','TimeoutExpired'} else 'other')
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
    require(read(PASSED,0)==pass_bytes and all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));return 0 if result['complete'] else 1


def watch(read,write):
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-local-mcp-'))
    if os.path.lexists(evidence/'finish.summary.json'):
        result=json.loads(read(evidence/'finish.summary.json',0));require(result.get('operator_helper_sha256')==context['source_sha256'] and result.get('operator_job_stopped') is True)
        print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
    try:
        last=0;deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            state=metadata(UNIT)
            if os.path.lexists(evidence/'summary.json') and (state.get('SubState')=='exited' or state.get('ActiveState') in {'inactive','failed'}):
                result=json.loads(read(evidence/'summary.json',0));require(result.get('operator_helper_sha256')==context['source_sha256'])
                if result['complete']:require(state.get('Result')=='success' and state.get('ExecMainStatus')=='0' and state.get('InvocationID')==result['invocation_id'])
                subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
                require(metadata(UNIT).get('ActiveState') in {'inactive','failed'})
                result['operator_job_stopped']=True;write(evidence/'finish.summary.json',canonical(result));print(json.dumps(result),flush=True)
                return 0 if result['complete'] else 1
            require(state.get('ActiveState') not in {'inactive','failed'})
            if time.monotonic()-last>=10:
                print('{"event":"main_local_mcp_running","note":"Ctrl+C detaches; repeat the same command to reattach without replay."}',flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print('{"detached":true,"job_continues":true}',flush=True);return 0
    raise TimeoutError('local_mcp_operator_watch_deadline')


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    source=Path(__file__).read_bytes();digest=hashlib.sha256(source).hexdigest();support,old,c,read,write=helpers()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context['source_sha256']==digest)
        for name,pin in json.loads(read(ARTIFACT/'sources.json',0)).items():
            require(re.fullmatch(r'[a-z0-9_]+\.py',name) and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==pin)
        return watch(read,write)
    retained(read);driver=c['legacy']();before=driver['policies'](read)
    node=Path('/usr/bin/node');info=node.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022
        and hashlib.sha256(node.read_bytes()).hexdigest()==NODE_SHA)
    require(not os.path.lexists(ARTIFACT) and metadata(UNIT).get('LoadState')=='not-found')
    directory=Path(__file__).parent
    sources={'qualify_main_local_mcp.py':source}
    for name,pin in [('mcp_public_programs.py',OWNER_SHA),('probe_main_local_mcp.py',PROBE_SHA),('public_program_snapshot.py',SNAPSHOT_SHA)]:
        sources[name]=definitions(directory/name,pin)['_verified_source_bytes']
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    for name,raw in sources.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='main-local-mcp-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,evidence=str(evidence),id=uuid.uuid4().hex)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='CAP_SETUID CAP_SETGID',
        ProtectSystem='strict',ProtectHome='no',PrivateTmp='yes',ReadWritePaths=' '.join([str(ARTIFACT),str(BASE/'operator-evidence'),str(PROGRAM_ROOT)]),
        Restart='no',TimeoutStartSec='800',MemoryMax='3G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/'qualify_main_local_mcp.py'),'--worker']
    require(all(read(path,0)==raw for path,raw in before.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return watch(read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:] in ([],['--worker']))
        raise SystemExit(worker() if sys.argv[1:]==['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"main_local_mcp_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
