"""Preserve the existing Telegram home record as inactive configuration only."""
from __future__ import annotations
import ast
import copy
import hashlib
import json
from pathlib import Path

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PARENT=BASE/'operator-main-rea-reviewed-candidate-v1/assess_rea_candidate_settings_owner.py'
PARENT_SHA='23ae2a66c8bf3ee1c16fc116988894fb12f3b0c36212c341d3f5c8abc0853699'
CONFIG=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/repo/gateway/config.py')
CONFIG_SHA='81eafc6a1f56d0185685bc4683fd859b23aa4d4a759e4fabbf018feab9bd1f2f'
PHASE='source_configuration'
_base=None


def require(value):
    if not value:raise ValueError('inactive_telegram_configuration_refused')


def base():
    global _base
    if _base is None:
        raw=PARENT.read_bytes();require(0<len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==PARENT_SHA)
        value={'__name__':'verified_telegram_preservation_parent','__file__':str(PARENT)}
        exec(compile(raw,'<verified-telegram-preservation-parent>','exec'),value)
        value['_original_policy']=value['preservation_policy'];value['_original_schema']=value['public_schema']
        value['preservation_policy']=preservation_policy;value['public_schema']=public_schema
        _base=value
    return _base


def home_fields():
    raw=CONFIG.read_bytes();require(len(raw)<=524288 and hashlib.sha256(raw).hexdigest()==CONFIG_SHA)
    nodes=[node for node in ast.parse(raw).body if isinstance(node,ast.ClassDef) and node.name=='HomeChannel']
    require(len(nodes)==1)
    fields={node.target.id for node in nodes[0].body if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name)}
    require(fields=={'platform','chat_id','name','thread_id','user_id','scope_id'})
    return fields


def public_schema():
    schema=base()['_original_schema']()
    schema['platforms']['telegram']={'enabled':{},'home_channel':{key:{} for key in home_fields()}}
    return schema


def safe_value(path,value,exists):return base()['safe_value'](path,value,exists)
def setting_kind(value,exists):return base()['setting_kind'](value,exists)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def telegram_home_shape(value):
    if not isinstance(value,dict) or set(value)!={'enabled','home_channel'} or type(value['enabled']) is not bool:return False
    home=value['home_channel']
    if not isinstance(home,dict) or not {'platform','chat_id','name'}<=set(home)<=home_fields() or home.get('platform')!='telegram':return False
    if not isinstance(home['name'],str) or len(home['name'])>512 or '\x00' in home['name']:return False
    for key in set(home)-{'name','platform'}:
        item=home[key]
        if key!='chat_id' and item is None:continue
        if not isinstance(item,str) or not 0<len(item)<=256 or any(char in item for char in ('\x00','\r','\n')):return False
    return True


def preservation_policy(previous,current,platforms):
    normalized=copy.deepcopy(current);preserved=False
    old=previous.get('platforms');new=current.get('platforms')
    if isinstance(new,dict) and 'telegram' in new and (old is None or isinstance(old,dict) and 'telegram' not in old):
        if telegram_home_shape(new['telegram']):
            remaining={key:value for key,value in new.items() if key!='telegram'}
            if isinstance(old,dict):normalized['platforms']=remaining;preserved=True
            elif not remaining:
                if 'platforms' in previous:normalized['platforms']=None
                else:normalized.pop('platforms')
                preserved=True
    result=base()['_original_policy'](previous,normalized,platforms)
    if preserved:result['allowed_preserved_changes'].append('platforms.telegram.inactive_copy')
    # This grants only copying into an inactive profile. No adapter, connector,
    # notification, routing identity or production setting is accepted here.
    require(result['fleet_settings_accepted'] is False)
    return result


def child():
    global PHASE
    parent=base()
    try:parent['child']()
    finally:PHASE=parent.get('PHASE','source_configuration')
