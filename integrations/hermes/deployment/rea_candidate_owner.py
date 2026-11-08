"""Owner-only REA public archive handoff and NEW inactive candidate binding."""
from __future__ import annotations
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-rea-main-programs-v1'
OWNER_SHA='291f6e5f81a027c89473fedfc7bdf3275d2f00678bd3f655e47e74df7725b2b2'
ARCHIVES=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/.archive/2026-10-28-rea-public-programs')
PROGRAMS={
    'ghidra':dict(sha256='490242e4126843ff11a6c7ea090927b2316e58efe3bfaf005ee582ef3cac0e7e',size=911738880,
                  source='/home/vincentspereira/tools/ghidra_12.1.4_PUBLIC'),
    'java':dict(sha256='8293b7cf98ee35897d16b4c1c637c5b3be5d258e74fcb6ae1ee8eb2ea1d0d573',size=362168320,
                source='/home/vincentspereira/tools/jdk-21.0.13+9'),
}
PHASE='identity'


def require(value):
    if not value:raise ValueError('rea_candidate_owner_refused')


def definitions(name,digest):
    path=ARTIFACT/name;raw=path.read_bytes()
    require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    scope={'__name__':'verified_rea_owner_support','__file__':str(path)}
    exec(compile(raw,'<verified-rea-owner-support>','exec'),scope)
    return scope


def core():
    value=definitions('main_live_reconciliation_owner.py',OWNER_SHA)
    value['ARTIFACT']=ARTIFACT
    return value


def archive(program):
    require(program in PROGRAMS and os.geteuid()!=0)
    path=ARCHIVES/(program+'.tar');fd=os.open('/',os.O_PATH|os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            child=os.open(part,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
            info=os.fstat(fd);require(info.st_uid in {0,os.geteuid()} and not info.st_mode&0o022)
        opened=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(opened,'rb') as stream:
            before=os.fstat(stream.fileno());expected=PROGRAMS[program]
            require(stat.S_ISREG(before.st_mode) and before.st_uid==os.geteuid() and before.st_nlink==1
                and stat.S_IMODE(before.st_mode)==0o600 and before.st_size==expected['size'])
            body=stream.read(expected['size']+1);after=os.fstat(stream.fileno());named=os.stat(path.name,dir_fd=fd,follow_symlinks=False)
            fields=('st_dev','st_ino','st_uid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
            require(len(body)==expected['size'] and hashlib.sha256(body).hexdigest()==expected['sha256']
                and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields))
        return dict(complete=True,program=program,archive_bytes=len(body),archive_sha256=expected['sha256']),body
    finally:os.close(fd)


def rewrite(config,original,destination,programs,transform):
    require(set(programs)==set(PROGRAMS))
    for name,path in programs.items():
        require(path=='/opt/hermes-runtime/programs/rea-'+name+'-'+PROGRAMS[name]['sha256'][:16])
    result=transform['rebase'](config,original,destination);before=copy.deepcopy(result);matches=[]
    for row in result['mcp_servers'].values():
        env=row.get('env',{})
        if set(env)&{'GHIDRA_INSTALL_DIR','JAVA_HOME'}:
            require(row.get('command')=='npx' and env.get('GHIDRA_INSTALL_DIR')==PROGRAMS['ghidra']['source']
                and env.get('JAVA_HOME')==PROGRAMS['java']['source'])
            matches.append(env)
    require(len(matches)==1)
    matches[0]['GHIDRA_INSTALL_DIR']=programs['ghidra'];matches[0]['JAVA_HOME']=programs['java']
    comparison=copy.deepcopy(result)
    for row in comparison['mcp_servers'].values():
        env=row.get('env',{})
        if env.get('GHIDRA_INSTALL_DIR')==programs['ghidra']:
            env['GHIDRA_INSTALL_DIR']=PROGRAMS['ghidra']['source'];env['JAVA_HOME']=PROGRAMS['java']['source']
    require(comparison==before)
    return result


def prepare(c,packet,body,account):
    global PHASE
    import yaml
    PHASE='previous_candidate_restore'
    public=c['public'];transform=public('current_main_configuration.py')
    original=Path(packet['original']);transform['candidate'](original);require(original.parent==Path(account.pw_dir))
    destination,receipt=public('main_memory_profile_recovery.py')['restore'](public('capture_main_operational_profile_v4.py'),body)
    profile=Path(destination);transform['candidate'](profile);require(profile.parent==Path(account.pw_dir))
    saved=c['files'](profile)
    PHASE='current_configuration_prepare'
    updated=rewrite(transform['load'](saved['config.yaml']),original,profile,packet['programs'],transform)
    serialized=yaml.safe_dump(updated,sort_keys=False).encode();require(transform['load'](serialized)==updated)
    issuer=c['bind'](packet['entry']);issuer['qualify_access'](packet['bundle'])
    environment=issuer['prepare_environment'](saved['.env'],packet['bundle']['token'])
    PHASE='new_candidate_configuration'
    c['publish'](profile,'config.yaml',serialized,packet['id']);c['publish'](profile,'.env',environment,packet['id'])
    require(c['files'](profile)==dict(saved,**{'config.yaml':serialized,'.env':environment}))
    issuer['qualify_access'](packet['bundle'])
    inspected=public('inspect_launch_main_references.py')['classify'](updated,profile,Path('/home/vincentspereira'))
    require(inspected['unresolved_reference_count']==0 and inspected['enhanced_memory_selected'] is True)
    return dict(complete=True,destination=destination,mcp_definitions=len(updated['mcp_servers']),
        remaining_reference_count=0,rea_definition_preserved=True,settings_and_oauth_preserved=True,
        scoped_status_authenticated=True,receipt=receipt),b''


def child():
    global PHASE
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));os.umask(0o077)
    packet=json.loads(sys.stdin.buffer.readline(65537));mode=packet.get('mode')
    schemas={'program_archive':{'program'},'verify_source':{'fingerprints'},'prepare':{'entry','original','programs','bundle','archive_bytes','id'},
        'capture_candidate':{'entry','destination','recipient'},'restore_candidate':{'entry','destination','archive_bytes','id'}}
    require(mode in schemas and set(packet)==schemas[mode]|{'mode','uid','gid'})
    c=core();account=c['guard'](dict(packet,mode='verify_source' if mode=='program_archive' else mode))
    if 'id' in packet:require(re.fullmatch('[a-f0-9]{32}',packet['id']) is not None)
    body=b''
    if 'archive_bytes' in packet:
        require(type(packet['archive_bytes']) is int and 0<packet['archive_bytes']<=c['MAX_ARCHIVE'])
        body=sys.stdin.buffer.read(packet['archive_bytes']+1);require(len(body)==packet['archive_bytes'])
    with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
        counts=c['public']('qualify_launch_gateway_renewal_v2.py')['network_guard']()
        if mode=='program_archive':PHASE='source_configuration';value,output=archive(packet['program'])
        elif mode=='prepare':value,output=prepare(c,packet,body,account)
        elif mode=='capture_candidate':PHASE='configured_candidate_capture';value,output=c['capture_candidate'](packet,account)
        elif mode=='restore_candidate':PHASE='configured_candidate_restore';value,output=c['restore_candidate'](packet,body,account)
        else:
            require(c['fingerprints'](c['files'](Path(account.pw_dir)/'.hermes'))==packet['fingerprints'])
            value=dict(complete=True,current_source_settings_preserved=True);output=b''
        require(counts['forbidden']==0)
    sys.stdout.buffer.write(json.dumps(value,sort_keys=True).encode()+b'\n'+output);sys.stdout.buffer.flush()
