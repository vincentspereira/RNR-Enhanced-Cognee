"""Preserve reviewed current limits only in a NEW inactive memory candidate."""
from __future__ import annotations
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-main-rea-reviewed-candidate-v1'
LIB_SHA='12ea43d478806175719ae45d6ffcf35ed4aa0b51c4c5d6d7c8c18717d3964ea4'
PLATFORMS=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/repo/hermes_cli/platforms.py')
PLATFORMS_SHA='c5d4e10e7b4a05f1687430d70e6ac6cdb45f93bd3c0e54c3d9a0dff5771c48d0'
PHASE='source_configuration'
_library=None


def require(value):
    if not value:raise ValueError('rea_candidate_settings_refused')


def library():
    global _library
    if _library is None:
        path=ARTIFACT/'finish_rea_review_owner.py';raw=path.read_bytes()
        require(0<len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==LIB_SHA)
        value={'__name__':'verified_rea_settings_library','__file__':str(path)}
        exec(compile(raw,'<verified-rea-settings-library>','exec'),value);_library=value
    return _library


def platform_names():
    raw=PLATFORMS.read_bytes();require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PLATFORMS_SHA)
    nodes=[n.value for n in ast.parse(raw).body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='PLATFORMS']
    require(len(nodes)==1 and isinstance(nodes[0],ast.Call) and len(nodes[0].args)==1 and isinstance(nodes[0].args[0],ast.List))
    names=[]
    for row in nodes[0].args[0].elts:
        require(isinstance(row,ast.Tuple) and len(row.elts)==2 and isinstance(row.elts[0],ast.Constant) and isinstance(row.elts[0].value,str))
        names.append(row.elts[0].value)
    require(len(names)==len(set(names)) and 1<=len(names)<=128)
    return set(names)


def public_schema():
    schema=library()['public_schema']();platforms=platform_names()
    for name in ('known_builtin_toolsets','known_plugin_toolsets','platform_toolsets','platforms'):
        schema[name]={key:{} for key in platforms}
    # Public legacy container names are metadata only; their values stay opaque
    # and NONE of these fields are admitted by the preservation policy below.
    for name in ('api_server','custom_providers','models','version'):schema.setdefault(name,{})
    return schema


def safe_value(path,value,exists):return library()['safe_value'](path,value,exists)
def setting_kind(value,exists):return library()['setting_kind'](value,exists)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def preservation_policy(previous,current,platforms):
    """All non-admitted fields must remain exactly equal, including scalar types.

    This admits no runtime or approval-mode changes. Offered-toolset registries
    may change only while platform selections and disabled-tool settings remain
    equal, because those non-registry fields are never normalized away.
    """
    normalized=copy.deepcopy(current);allowed=[]
    old=previous.get('approvals');new=current.get('approvals')
    if isinstance(old,dict) and isinstance(new,dict) and encoded(old.get('timeout'))!=encoded(new.get('timeout')):
        if type(old.get('timeout')) is int and old['timeout']==900 and type(new.get('timeout')) is int and new['timeout']==600:
            normalized['approvals']['timeout']=old['timeout'];allowed.append('approvals.timeout')
    for name in ('known_builtin_toolsets','known_plugin_toolsets'):
        old=previous.get(name);new=current.get(name)
        if encoded({name:old} if name in previous else {})==encoded({name:new} if name in current else {}):continue
        valid=(isinstance(old,dict) and isinstance(new,dict) and set(old)==set(new) and set(new)<=platforms)
        if valid:
            valid=all(isinstance(row,list) and len(row)<=256 and all(isinstance(v,str) and 0<len(v)<=128 for v in row)
                for rows in (old,new) for row in rows.values())
        if valid:
            changed={key for key in old if encoded(old[key])!=encoded(new[key])}
            selections=previous.get('platform_toolsets')
            valid=isinstance(selections,dict) and all(isinstance(selections.get(key),list) for key in changed)
        if valid:normalized[name]=copy.deepcopy(old);allowed.append(name)
    return dict(inactive_preparation_allowed=encoded(normalized)==encoded(previous),
        allowed_preserved_changes=allowed,fleet_settings_accepted=False)


def assess(c,parent,packet,body,account):
    size=packet['capsule_bytes'];require(type(size) is int and 0<size<=1100*1024)
    values=c['capsule'](body[:size]);require(c['fingerprints'](values)==packet['fingerprints'])
    config,_=c['inspect_source'](values);transform=c['public']('current_main_configuration.py')
    original=Path(packet['original']);transform['candidate'](original);require(original.parent==Path(account.pw_dir))
    previous=transform['load'](parent['archived_config'](c,body[size:]));current=transform['transform'](config,original)
    lib=library();review=lib['delta']({k:v for k,v in previous.items() if k not in {'model','memory','gateway','mcp_servers'}},
        {k:v for k,v in current.items() if k not in {'model','memory','gateway','mcp_servers'}},public_schema())
    review.update(complete=True,source_capsule_verified=True,settings_accepted=False,
        configuration_semantically_equivalent=encoded(previous)==encoded(current),
        critical_sections_equal=all(encoded({k:previous[k]} if k in previous else {})==encoded({k:current[k]} if k in current else {}) for k in ('model','memory','gateway','mcp_servers')))
    return dict(complete=True,review=review,**preservation_policy(previous,current,platform_names()))


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));os.umask(0o077)
    packet=json.loads(sys.stdin.buffer.readline(65537))
    require(isinstance(packet,dict) and set(packet)=={'mode','uid','gid','entry','original','capsule_bytes','archive_bytes','fingerprints'} and packet['mode']=='assess_configuration')
    lib=library();raw=lib['FROZEN'].read_bytes();require(hashlib.sha256(raw).hexdigest()==lib['FROZEN_SHA'])
    parent={'__name__':'verified_rea_assessment_parent','__file__':str(lib['FROZEN'])}
    exec(compile(raw,'<verified-rea-assessment-parent>','exec'),parent)
    c=parent['core']();account=c['guard'](packet)
    require(type(packet['archive_bytes']) is int and 0<packet['archive_bytes']<=c['MAX_ARCHIVE'] and type(packet['capsule_bytes']) is int and 0<packet['capsule_bytes']<=1100*1024)
    size=packet['archive_bytes']+packet['capsule_bytes'];body=sys.stdin.buffer.read(size+1);require(len(body)==size)
    counts=c['public']('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    result=assess(c,parent,packet,body,account);require(counts['forbidden']==0)
    print(json.dumps(result,sort_keys=True),flush=True)
