"""Read-only owner preflight with explicit identity/file/comparison observations."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import sys

FROZEN=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/operator-rea-main-programs-v1/rea_candidate_owner.py')
FROZEN_SHA='25ed007609af9d86b6f0386e340ef7265ef325e3f8d295185bfd809f7468128f'
NAMES={'config.yaml','.env','auth.json'}


def require(value):
    if not value:raise ValueError('rea_preflight_inspection_refused')


def observe(packet,core_loader):
    result=dict(complete=True,preflight_passed=False,core_loaded=False,identity_verified=False,
        source_files_read=False,source_fingerprints_match=False,profiles_changed=False,
        credentials_issued=0,model_called=False,memory_api_called=False,phase='core_loading')
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    account=pwd.getpwuid(os.geteuid())
    result['identity_predicates']=dict(uid_matches=os.getresuid()==(packet['uid'],)*3,
        gid_matches=os.getresgid()==(packet['gid'],)*3,no_supplementary_groups=not os.getgroups(),
        no_new_privileges=fields['NoNewPrivs'].strip()=='1',
        effective_capabilities_zero=fields['CapEff'].strip()=='0000000000000000',
        ambient_capabilities_zero=fields['CapAmb'].strip()=='0000000000000000',
        inheritable_capabilities_zero=fields['CapInh'].strip()=='0000000000000000',
        passwd_identity_matches=account.pw_uid==packet['uid'] and account.pw_gid==packet['gid']
            and account.pw_name=='vincentspereira' and account.pw_dir=='/home/vincentspereira')
    try:
        c=core_loader();result['core_loaded']=True;result['phase']='identity_verification'
        account=c['guard'](dict(mode='verify_source',uid=packet['uid'],gid=packet['gid']))
        result['identity_verified']=True;result['phase']='source_file_read'
        values=c['files'](Path(account.pw_dir)/'.hermes');result['source_files_read']=True
        result['phase']='source_fingerprint_comparison'
        actual=c['fingerprints'](values)
        require(set(actual)==NAMES and set(packet['fingerprints'])==NAMES)
        result['source_files_equal']={name:actual[name]==packet['fingerprints'][name] for name in sorted(NAMES)}
        result['source_fingerprints_match']=all(result['source_files_equal'].values())
        result['preflight_passed']=result['source_fingerprints_match']
        result['phase']='complete'
    except Exception as error:
        result['error_kind']=type(error).__name__ if type(error).__name__ in {'ValueError','PermissionError','FileNotFoundError','OSError'} else 'other'
        frames=[];tb=error.__traceback__
        while tb:
            name=tb.tb_frame.f_code.co_name
            if name in {'observe','core','definitions','guard','require','public','files','open_profile','read_at'}:
                frames.append(dict(function=name,line=tb.tb_lineno))
            tb=tb.tb_next
        result['public_helper_frames']=frames[-8:]
    return result


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.umask(0o077)
    packet=json.loads(sys.stdin.buffer.readline(65537))
    require(isinstance(packet,dict) and set(packet)=={'mode','uid','gid','fingerprints'} and packet['mode']=='inspect'
        and type(packet['uid']) is int and packet['uid']>0 and type(packet['gid']) is int and packet['gid']>0
        and isinstance(packet['fingerprints'],dict) and set(packet['fingerprints'])==NAMES)
    raw=FROZEN.read_bytes();require(hashlib.sha256(raw).hexdigest()==FROZEN_SHA)
    original={'__name__':'verified_rea_preflight_original','__file__':str(FROZEN)}
    exec(compile(raw,'<verified-rea-preflight-original>','exec'),original)
    result=observe(packet,original['core'])
    print(json.dumps(result,sort_keys=True),flush=True)
