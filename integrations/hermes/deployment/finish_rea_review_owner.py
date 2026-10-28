"""Compare authenticated settings under their restricted owner; publish no secrets."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
FROZEN=BASE/'operator-rea-main-programs-v3/rea_candidate_owner_v3.py'
FROZEN_SHA='acc61a7c0bd4b7b8b6faa1f2865c81b71c773d12531e0e05ec2bbd99fc9b4494'
DEFAULTS=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/repo/hermes_cli/config_defaults.py')
DEFAULTS_SHA='93c989bcd0a4c3aff116ad2534375ece02bce4b79b9e9166dfacf834f09bc63b'
TOOLS=DEFAULTS.with_name('tools_config.py')
TOOLS_SHA='35012cc12fc709a5a95c3f547ebb76a1938f231f0012e7e6fa843bf4be52a2fd'
PROOF_ID='03053e75993f4b73aa063fc2890e5970'
PHASE='identity'
NUMERIC={('_config_version',),('agent','max_turns'),('agent','run_budget_seconds'),('agent','gateway_timeout')}
BOOLEAN={('display','compact'),('display','tui_native'),('display','resume_last_session')}
ENUMS={('display','interface'):{'cli','tui'},('display','cli_layout'):{'modern','classic'}}


def require(value):
    if not value:raise ValueError('rea_settings_review_refused')


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def public_schema():
    raw=DEFAULTS.read_bytes();require(len(raw)<=262144 and hashlib.sha256(raw).hexdigest()==DEFAULTS_SHA)
    tree=ast.parse(raw);nodes=[node.value for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='DEFAULT_CONFIG' for target in node.targets)]
    require(len(nodes)==1 and isinstance(nodes[0],ast.Dict))
    def fields(node,depth=0):
        require(depth<=32)
        if not isinstance(node,ast.Dict):return {}
        return {key.value:fields(value,depth+1) for key,value in zip(node.keys,node.values)
            if isinstance(key,ast.Constant) and isinstance(key.value,str)}
    result=fields(nodes[0])
    raw=TOOLS.read_bytes();require(len(raw)<=262144 and hashlib.sha256(raw).hexdigest()==TOOLS_SHA)
    keys={node.args[0].value for node in ast.walk(ast.parse(raw)) if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Attribute) and node.func.attr=='get' and node.args
        and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)}
    platforms={name:{} for name in ('cli','tui','whatsapp','telegram','discord','slack','signal','matrix','api','webhook','email')}
    for name in ('known_builtin_toolsets','known_plugin_toolsets'):
        require(name in keys);result[name]=dict(platforms)
    return result


def setting_kind(value,exists):
    if not exists:return 'absent'
    return {type(None):'null',bool:'boolean',int:'integer',float:'number',str:'string',list:'list',dict:'mapping'}[type(value)]


def safe_value(path,value,exists):
    if not exists:return {}
    if path==('approvals','timeout') and type(value) is int and 0<=value<=86400:return {'value':value}
    if path in NUMERIC and (value is None or type(value) is int and abs(value)<=10**9):return {'value':value}
    if path in BOOLEAN and type(value) is bool:return {'value':value}
    if path in ENUMS and isinstance(value,str) and value in ENUMS[path]:return {'value':value}
    return {}


def delta(previous,current,schema):
    """Only names from pinned public defaults; all arbitrary fields are counted."""
    rows=[];redacted=0;overflow=0
    def walk(left,right,public,path=(),left_exists=True,right_exists=True):
        nonlocal redacted,overflow
        if left_exists==right_exists and encoded(left)==encoded(right):return
        if type(left) is dict and type(right) is dict and (public or not path):
            for key in sorted(set(left)|set(right)):
                old=left.get(key);new=right.get(key)
                if (key in left)==(key in right) and encoded(old)==encoded(new):continue
                if key not in public:redacted+=1;continue
                walk(old,new,public[key],path+(key,),key in left,key in right)
            return
        if len(rows)>=128:overflow+=1;return
        rows.append(dict(path=list(path),previous=dict(kind=setting_kind(left,left_exists),**safe_value(path,left,left_exists)),
            current=dict(kind=setting_kind(right,right_exists),**safe_value(path,right,right_exists))))
    walk(previous,current,schema)
    return dict(changed_public_fields=rows,redacted_changed_fields=redacted,additional_public_changes=overflow,
        values_policy='only_fixed_nonsecret_numeric_boolean_and_display_enum_fields')


def compare(c,original,packet,body,account,schema):
    size=packet['capsule_bytes'];require(type(size) is int and 0<size<=1100*1024)
    current=c['capsule'](body[:size]);require(c['fingerprints'](current)==packet['fingerprints'])
    config,_=c['inspect_source'](current);transform=c['public']('current_main_configuration.py')
    prior=Path(packet['original']);transform['candidate'](prior);require(prior.parent==Path(account.pw_dir))
    previous=transform['load'](original['archived_config'](c,body[size:]))
    expected=transform['transform'](config,prior)
    critical={'model','memory','gateway','mcp_servers'}
    same=all(encoded({key:expected[key]} if key in expected else {})==encoded({key:previous[key]} if key in previous else {}) for key in critical)
    result=delta({k:v for k,v in previous.items() if k not in critical},{k:v for k,v in expected.items() if k not in critical},schema)
    result.update(complete=True,critical_sections_equal=same,source_capsule_verified=True,
        configuration_semantically_equivalent=encoded(previous)==encoded(expected),settings_accepted=False)
    return result


def receipt_at(directory,uid,completed_ns):
    require(os.geteuid()==uid and uid>0 and type(completed_ns) is int and completed_ns>0)
    fd=os.open('receipt.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOATIME,dir_fd=directory)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid==uid and before.st_nlink==1
            and stat.S_IMODE(before.st_mode)==0o600 and 0<before.st_size<=4096
            and 0<before.st_mtime_ns<=completed_ns and 0<before.st_ctime_ns<=completed_ns)
        raw=stream.read(4097);after=os.fstat(stream.fileno());named=os.stat('receipt.json',dir_fd=directory,follow_symlinks=False)
        attrs=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns','st_atime_ns')
        require(len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in attrs))
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result);result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    require(value==dict(complete=True,java_version_verified=True,ghidra_headless_import_passed=True,
        real_profiles_read=False,rea_server_started=False,model_called=False,external_sends=0)
        and all(type(value[k]) is bool for k in value if k!='external_sends') and type(value['external_sends']) is int)
    return value


def retained_receipt(uid,proof_id,completed_ns):
    require(proof_id==PROOF_ID)
    fd=os.open('/',os.O_PATH|os.O_DIRECTORY)
    try:
        for part in ('run','ec-rea-program-proof-'+proof_id):
            child=os.open(part,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
            info=os.fstat(fd);require(info.st_uid in {0,uid} and not info.st_mode&0o022)
        info=os.fstat(fd);require(info.st_uid==uid and stat.S_IMODE(info.st_mode)==0o700)
        return receipt_at(fd,uid,completed_ns)
    finally:os.close(fd)


def child():
    global PHASE
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));os.umask(0o077)
    packet=json.loads(sys.stdin.buffer.readline(65537));mode=packet.get('mode')
    schemas={'review_configuration':{'original','capsule_bytes','archive_bytes','fingerprints'},'read_retained_receipt':{'proof_id','completed_ns'}}
    require(mode in schemas and set(packet)=={'mode','uid','gid','entry'}|schemas[mode])
    raw=FROZEN.read_bytes();require(0<len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==FROZEN_SHA)
    original={'__name__':'verified_rea_finish_parent','__file__':str(FROZEN)}
    exec(compile(raw,'<verified-rea-finish-parent>','exec'),original)
    c=original['core']();account=c['guard'](packet)
    PHASE='source_configuration'
    counts=c['public']('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    if mode=='read_retained_receipt':
        receipt=retained_receipt(account.pw_uid,packet['proof_id'],packet['completed_ns'])
        result=dict(complete=True,receipt=receipt,owner_read_verified=True,receipt_unchanged_since_completion=True)
    else:
        require(type(packet['archive_bytes']) is int and 0<packet['archive_bytes']<=c['MAX_ARCHIVE']
            and type(packet['capsule_bytes']) is int and 0<packet['capsule_bytes']<=1100*1024)
        size=packet['archive_bytes']+packet['capsule_bytes'];body=sys.stdin.buffer.read(size+1);require(len(body)==size)
        result=compare(c,original,packet,body,account,public_schema())
    require(counts['forbidden']==0)
    print(json.dumps(result,sort_keys=True),flush=True)
