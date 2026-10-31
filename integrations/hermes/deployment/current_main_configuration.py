"""Preserve current main settings in a NEW inactive restricted profile.

Only enhanced memory selection and the one already reviewed filesystem root
change. No MCP is executed. Unknown path references remain unresolved, never
silently replaced or treated as authorized filesystem access.
"""
from __future__ import annotations
import copy
import math
from pathlib import Path
import re

SOURCE_WORKSPACE='/home/vincentspereira/agent-workspace'


def require(value,category='current_main_configuration_refused'):
    if not value:raise ValueError(category)


def validate_tree(value):
    active=set();count=0
    def walk(item,depth):
        nonlocal count
        count+=1;require(count<=10000 and depth<=32)
        if isinstance(item,(dict,list)):
            require(id(item) not in active)
            active.add(id(item))
            try:
                if isinstance(item,dict):
                    require(all(isinstance(key,str) for key in item))
                    for key,child in item.items():walk(key,depth+1);walk(child,depth+1)
                else:
                    for child in item:walk(child,depth+1)
            finally:active.remove(id(item))
        else:require(item is None or type(item) in {bool,int,str} or type(item) is float and math.isfinite(item))
    walk(value,0)


def load(raw):
    import yaml
    require(isinstance(raw,bytes) and 0<len(raw)<=262144 and b'\x00' not in raw)
    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self,node,deep=False):
            self.flatten_mapping(node)
            result={}
            for key_node,value_node in node.value:
                key=self.construct_object(key_node,deep=deep)
                require(isinstance(key,str) and key not in result,'duplicate_or_nonstring_configuration_key')
                result[key]=self.construct_object(value_node,deep=deep)
            return result
    try:value=yaml.load(raw,Loader=UniqueLoader)
    except (yaml.YAMLError,UnicodeError):raise ValueError('current_main_yaml_refused') from None
    require(isinstance(value,dict));validate_tree(value)
    return value


def candidate(path):
    require(isinstance(path,Path) and path.is_absolute() and '..' not in path.parts
        and re.fullmatch('[a-f0-9]{16}',path.parent.name) is not None
        and path.parent.parent==Path('/var/lib/enhanced-cognee-profiles')
        and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}',path.name) is not None,
        'fixed_inactive_main_candidate_required')


def _rewrite(config,source,destination,*,select):
    validate_tree(config);candidate(destination)
    require(isinstance(config,dict) and isinstance(config.get('gateway'),dict)
        and config['gateway'].get('multiplex_profiles') is True
        and not config['gateway'].get('profile_routes')
        and isinstance(config.get('mcp_servers'),dict) and 1<=len(config['mcp_servers'])<=128
        and all(isinstance(server,dict) for server in config['mcp_servers'].values())
        and isinstance(config.get('memory',{}),dict))
    require(config.get('memory',{}).get('provider') in ({None,'enhanced_cognee'} if select else {'enhanced_cognee'}),
        'current_memory_provider_requires_review')
    result=copy.deepcopy(config);matches=[]
    for name,server in result['mcp_servers'].items():
        args=server.get('args')
        if isinstance(args,list) and source in args:
            require(server.get('command')=='npx' and args.count(source)==1
                and any(isinstance(arg,str) and (arg=='@modelcontextprotocol/server-filesystem'
                    or arg.startswith('@modelcontextprotocol/server-filesystem@')) for arg in args),
                'reviewed_main_filesystem_reference_required')
            matches.append(name)
    require(len(matches)==1,'unique_main_filesystem_reference_required')
    arguments=result['mcp_servers'][matches[0]]['args']
    arguments[arguments.index(source)]=str(destination/'workspace')
    if select:result['memory']=dict(copy.deepcopy(config.get('memory',{})),provider='enhanced_cognee')
    # Verify every unrelated field, including all opaque remote/inline auth
    # settings, against the source structure rather than a hardcoded MCP count.
    comparison=copy.deepcopy(result)
    args=comparison['mcp_servers'][matches[0]]['args']
    args[args.index(str(destination/'workspace'))]=source
    if 'memory' in config:comparison['memory']=copy.deepcopy(config['memory'])
    else:comparison.pop('memory',None)
    require(comparison==config and len(result['mcp_servers'])==len(config['mcp_servers']))
    return result


def transform(config,destination):
    return _rewrite(config,SOURCE_WORKSPACE,destination,select=True)


def rebase(config,original,destination):
    candidate(original)
    return _rewrite(config,str(original/'workspace'),destination,select=False)
