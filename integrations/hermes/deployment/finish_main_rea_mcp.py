"""Reuse Filesystem/copy passes and qualify only the failed REA catalogue."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
import tempfile
import uuid

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PREVIOUS=BASE/'operator-main-local-mcp-v1'
PREVIOUS_SHA='d9ecbb88b03fa32a0867ac2cfe827a23edf69eac2ca4bf7eb00632ccfc795983'
EXPECTED=BASE/'operator-evidence/main-local-mcp-hi_qvtkz'
ARTIFACT=BASE/'operator-main-rea-mcp-finish-v1'
UNIT='ec-main-rea-mcp-finish-v1-20261028.service'
PROBE_SHA='50fb6723553d1fd7098d0e5c0c5054cb3ff1c1ff6a6d2248b45a3ea667e405e7'
PROTOCOL_SHA='415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
SDK_SHA='bc81a674f25546e2a631a5f3c9cb1829654bbfcdd40cb89823aab5fb719211e5'
REA=Path('/opt/hermes-runtime/programs/mcp-rea-30a10da51b212810')
REPLY_LIMIT=10*1024**2
PINS={'filesystem':('eeac2e4bd8302b1117c040fe251b3a565f740b28cb56011a727d756e7e7353de',27525120,'2026.8.31'),
      'rea':('30a10da51b212810c6510497a87f6e93b15ea14da31702d38193a18d603ab623',132792320,'6.7.0')}


def require(value):
    if not value:raise ValueError('retained_rea_catalogue_finish_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    scope={'__name__':'verified_rea_catalogue_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-rea-catalogue-support>','exec'),scope);return scope


def helpers():
    old=definitions(PREVIOUS/'qualify_main_local_mcp.py',PREVIOUS_SHA)
    _,_,c,read,write=old['helpers']();return old,c,read,write


def stopped(state):return state.get('ActiveState') in {'inactive','failed'} and state.get('SubState') in {'dead','failed'}


def retained(old,read):
    context=json.loads(read(PREVIOUS/'context.private.json',0))
    require(context.get('source_sha256')==PREVIOUS_SHA and context.get('evidence')==str(EXPECTED)
        and isinstance(context.get('id'),str) and re.fullmatch('[a-f0-9]{32}',context['id'])
        and stopped(old['metadata'](old['UNIT']))
        and stopped(old['metadata']('ec-main-local-mcp-'+context['id']+'.service')))
    old['retained'](read)
    value=json.loads(read(EXPECTED/'finish.summary.json',0))
    require(value.get('source_revision')==BASE.name and value.get('operator_helper_sha256')==PREVIOUS_SHA
        and value.get('evidence')==str(EXPECTED) and value.get('complete') is False
        and value.get('category')=='local_mcp_component_incomplete_preserve_evidence' and value.get('checkpoint')=='component_failure'
        and value.get('credentials_issued')==value.get('external_platform_sends')==value.get('platform_adapters_started')==0
        and all(value.get(k) is True for k in ('operator_job_stopped','qualification_unit_stopped','network_isolated',
            'original_main_candidate_pass_preserved','all_admission_policies_preserved_disabled'))
        and all(value.get(k) is False for k in ('keys_read','model_called','memory_api_called','source_profiles_changed',
            'previous_candidates_changed','binary_analysis_requested','completed_tests_replayed','fleet_launch_approved',
            'main_tool_program_coverage_qualified','actual_profile_admission_qualified','production_dispatch_qualified','production_renewal_timer_enabled')))
    receipt=json.loads(read(EXPECTED/'component-receipt.json',0))
    require(isinstance(receipt.get('invocation_id'),str) and re.fullmatch('[a-f0-9]{32}',receipt['invocation_id']))
    old['validate_probe'](receipt,receipt['invocation_id'])
    require(receipt['complete'] is False and receipt['cases']==value.get('components')
        and receipt['cases']['filesystem']['complete'] is True and receipt['cases']['filesystem']['tools_count']==14
        and receipt['cases']['rea']==dict(complete=False,error_kind='ValueError'))
    programs=json.loads(read(EXPECTED/'public-programs.json',0))
    require(programs==value.get('public_programs') and set(programs)==set(PINS))
    for name,(digest,size,version) in PINS.items():
        row=programs[name]
        require(set(row)=={'archive_sha256','archive_bytes','public_copy_readback_verified','existing_copy_reused','version'}
            and row['archive_sha256']==digest and row['archive_bytes']==size and row['version']==version
            and row['public_copy_readback_verified'] is True and type(row['existing_copy_reused']) is bool)
    return context,receipt


def public_pin(path,digest):
    # Only public immutable operator-owned code is inspected. No owner profile
    # tree is traversed and no archive capture/readback is repeated.
    for parent in reversed(path.parents):
        info=parent.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022)
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode) and before.st_uid==0
            and before.st_nlink==1 and not before.st_mode&0o022 and 0<before.st_size<=16*1024**2)
        sha=hashlib.sha256();used=0
        while data:=stream.read(65536):used+=len(data);require(used<=before.st_size);sha.update(data)
        after=os.fstat(stream.fileno());named=path.lstat()
        attrs=('st_dev','st_ino','st_uid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        require(used==before.st_size and sha.hexdigest()==digest
            and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in attrs))


def validate_rea_probe(value,invocation):
    require(isinstance(value,dict) and set(value)=={'complete','invocation_id','cases','real_profiles_read','credentials_read',
        'model_called','memory_api_called','external_sends','full_main_tool_coverage_qualified'}
        and value['invocation_id']==invocation and type(value['complete']) is bool
        and type(value['external_sends']) is int and value['external_sends']==0
        and all(value[k] is False for k in ('real_profiles_read','credentials_read','model_called','memory_api_called','full_main_tool_coverage_qualified'))
        and isinstance(value['cases'],dict) and set(value['cases'])=={'rea'})
    row=value['cases']['rea'];require(isinstance(row,dict) and type(row.get('complete')) is bool and row['complete']==value['complete'])
    if row['complete']:
        require(set(row)=={'complete','initialize_passed','tools_list_passed','tools_count','tools_called','binary_analysis_requested',
            'reply_limit_bytes','catalogue_result_bytes'} and row['initialize_passed'] is row['tools_list_passed'] is True
            and row['binary_analysis_requested'] is False and type(row['tools_count']) is int and 1<=row['tools_count']<=512
            and type(row['tools_called']) is int and row['tools_called']==0
            and type(row['reply_limit_bytes']) is int and row['reply_limit_bytes']==REPLY_LIMIT
            and type(row['catalogue_result_bytes']) is int and 0<row['catalogue_result_bytes']<=REPLY_LIMIT)
    else:require(set(row)=={'complete','error_kind'} and row['error_kind'] in
        {'ValueError','TimeoutError','OSError','PermissionError','JSONDecodeError','BrokenPipeError','cleanup_failed','other'})
    return value


def configure(old):
    # Reuse the already qualified unit/journal implementation in a new namespace.
    # The new child emits ONLY REA; the old Filesystem pass is merged by root.
    old['ARTIFACT']=ARTIFACT;old['UNIT']=UNIT;old['PROBE_SHA']=PROBE_SHA
    old['validate_probe']=validate_rea_probe
    return old


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    old,c,read,write=helpers();previous,receipt=retained(old,read)
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-local-mcp-rea-finish-'))
    saved={path:read(path,0) for path in [old['PASSED'],*[EXPECTED/name for name in
        ('summary.json','finish.summary.json','component-receipt.json','public-programs.json')]]}
    driver=c['legacy']();policies=driver['policies'](read);entry,_=driver['fixed_entry'](read)
    require(entry['user']=='ecbot_5592956882ea9a13' and entry['enabled'] is False)
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,operator_helper_sha256=context['source_sha256'],
        invocation_id=os.environ.get('INVOCATION_ID',''),filesystem_evidence_reused=str(EXPECTED/'component-receipt.json'),
        filesystem_replayed=False,protected_public_programs_reused=2,full_public_readback_replayed=False,new_package_copies=0,
        java_ghidra_proof_replayed=False,credentials_issued=0,keys_read=False,model_called=False,memory_api_called=False,
        source_profiles_changed=False,previous_candidates_changed=False,external_platform_sends=0,platform_adapters_started=0,
        main_tool_program_coverage_qualified=False,actual_profile_admission_qualified=False,production_dispatch_qualified=False,
        production_renewal_timer_enabled=False,fleet_launch_approved=False,automatic_retry=False,
        qualification_surface='rea_catalogue_actual_main_uid_reusing_filesystem_pass')
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']))
        result['checkpoint']='public_code_pins'
        protocol_source=old['PROGRAM_ROOT']/('mcp-driver-'+previous['id'])/'probe.py'
        public_pin(protocol_source,PROTOCOL_SHA)
        public_pin(Path('/usr/bin/node'),old['NODE_SHA'])
        public_pin(REA/'node_modules/rea-agents/scripts/rea.mjs','ed06cee49505b95a3cc5fceb1b4b279167e26df86227c644bb366ffffdbaf738')
        public_pin(REA/'node_modules/rea-agents/dist/mcp/main-Cx-Z7m_n.js','b84c42ff88c80a77f4778515effa4edf3f67acb37b60b378ff8c2eccb70b741d')
        public_pin(REA/'node_modules/@modelcontextprotocol/server/dist/src-Cqbh3MYc.mjs',SDK_SHA)
        account=old['pwd'].getpwnam(entry['user']);configure(old)
        result['checkpoint']='rea_catalogue_only'
        # The legacy unit driver's first argument now carries public protocol
        # code. No Filesystem server path or command is passed to the child.
        current=old['proof'](context,account,{'filesystem':str(protocol_source),'rea':str(REA)},write)
        write(evidence/'rea-component-receipt.json',canonical(current))
        result.update(complete=current['complete'],components=dict(filesystem=receipt['cases']['filesystem'],rea=current['cases']['rea']),
            checkpoint='complete' if current['complete'] else 'rea_component_failure',local_mcp_components_qualified=current['complete'],
            rea_catalogue_qualified=current['complete'],qualification_unit_stopped=True,network_isolated=True)
        if not current['complete']:result['category']='rea_catalogue_incomplete_preserve_evidence'
    except Exception as error:
        result.update(category='rea_catalogue_finish_incomplete_preserve_evidence',error_kind=type(error).__name__
            if type(error).__name__ in {'ValueError','TimeoutError','TimeoutExpired','OSError','PermissionError'} else 'other')
    require(all(read(path,0)==raw for path,raw in saved.items()) and all(read(path,0)==raw for path,raw in policies.items()))
    result.update(original_failure_preserved=True,original_main_candidate_pass_preserved=True,all_admission_policies_preserved_disabled=True)
    write(evidence/'summary.json',canonical(result));return 0 if result['complete'] else 1


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    old,c,read,write=helpers();source=Path(__file__).read_bytes();digest=hashlib.sha256(source).hexdigest()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context['source_sha256']==digest)
        for name,pin in json.loads(read(ARTIFACT/'sources.json',0)).items():
            require(re.fullmatch(r'[a-z0-9_]+\.py',name) and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==pin)
        return configure(old)['watch'](read,write)
    retained(old,read);policies=c['legacy']()['policies'](read)
    require(not os.path.lexists(ARTIFACT) and old['metadata'](UNIT).get('LoadState')=='not-found')
    probe=definitions(Path(__file__).with_name('probe_rea_catalogue.py'),PROBE_SHA)
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    sources={'finish_main_rea_mcp.py':source,'probe_main_local_mcp.py':probe['_verified_source_bytes']}
    for name,raw in sources.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='main-local-mcp-rea-finish-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,evidence=str(evidence),id=uuid.uuid4().hex)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='',AmbientCapabilities='',ProtectSystem='strict',ProtectHome='yes',PrivateTmp='yes',
        ReadWritePaths=' '.join([str(ARTIFACT),str(BASE/'operator-evidence'),str(old['PROGRAM_ROOT'])]),
        Restart='no',TimeoutStartSec='400',MemoryMax='2G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/'finish_main_rea_mcp.py'),'--worker']
    require(all(read(path,0)==raw for path,raw in policies.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return configure(old)['watch'](read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:] in ([],['--worker']))
        raise SystemExit(worker() if sys.argv[1:]==['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"rea_catalogue_finish_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
