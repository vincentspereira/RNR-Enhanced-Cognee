"""Compare authenticated settings under their restricted owner; publish no secrets."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
FROZEN=BASE/'operator-rea-main-programs-v3/rea_candidate_owner_v3.py'
FROZEN_SHA='acc61a7c0bd4b7b8b6faa1f2865c81b71c773d12531e0e05ec2bbd99fc9b4494'
DEFAULTS=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/repo/hermes_cli/config_defaults.py')
DEFAULTS_SHA='93c989bcd0a4c3aff116ad2534375ece02bce4b79b9e9166dfacf834f09bc63b'
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
    return fields(nodes[0])


def setting_kind(value,exists):
    if not exists:return 'absent'
    return {type(None):'null',bool:'boolean',int:'integer',float:'number',str:'string',list:'list',dict:'mapping'}[type(value)]


def safe_value(path,value,exists):
    if not exists:return {}
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
        if type(left) is dict and type(right) is dict:
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


def child():
    global PHASE
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));os.umask(0o077)
    packet=json.loads(sys.stdin.buffer.readline(65537))
    require(isinstance(packet,dict) and set(packet)=={'mode','uid','gid','entry','original','capsule_bytes','archive_bytes','fingerprints'}
        and packet['mode']=='review_configuration')
    raw=FROZEN.read_bytes();require(0<len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==FROZEN_SHA)
    original={'__name__':'verified_rea_review_parent','__file__':str(FROZEN)}
    exec(compile(raw,'<verified-rea-review-parent>','exec'),original)
    c=original['core']();account=c['guard'](packet)
    require(type(packet['archive_bytes']) is int and 0<packet['archive_bytes']<=c['MAX_ARCHIVE']
        and type(packet['capsule_bytes']) is int and 0<packet['capsule_bytes']<=1100*1024)
    size=packet['archive_bytes']+packet['capsule_bytes'];body=sys.stdin.buffer.read(size+1);require(len(body)==size)
    PHASE='source_configuration'
    counts=c['public']('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    result=compare(c,original,packet,body,account,public_schema());require(counts['forbidden']==0)
    print(json.dumps(result,sort_keys=True),flush=True)
