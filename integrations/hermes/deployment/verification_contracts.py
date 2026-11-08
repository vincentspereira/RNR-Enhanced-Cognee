"""Non-privileged verification contracts. No live work at module import."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError

HOME = Path('/home/vincentspereira/.hermes')
INSTALL = HOME / 'mcp-servers/enhanced-cognee/server.py'
def approved_python():
    # Read the exact installed-runtime identifier as data. Never reconstruct a
    # redacted/display-masked path or import an executable enablement module.
    tree=ast.parse(Path(__file__).with_name('enable_fleet_memory_mcp.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='GATEWAY_PYTHON' for n in node.targets):
            assert isinstance(node.value,ast.BinOp) and isinstance(node.value.op,ast.Div)
            relative=ast.literal_eval(node.value.right)
            assert isinstance(relative,str) and relative.startswith('tools/python-') and relative.endswith('/bin/python3')
            return HOME/relative
    raise ValueError('approved_runtime_not_recorded')


PY = approved_python()
READ = {'recall','get_memories','get_memory','get_memory_history','get_related','list_agents','get_shared_memories','library_membership','get_stats','health'}
GROUPS = {'memory_read': READ, 'ingest': {'ingest_url','ingest_text'},
          'analysis': {'summarize_memories','find_consolidation_candidates','get_summarization_status','translate_text','detect_language'}}
FAMILIES = ['postgresql','valkey','qdrant','application','arcadedb']


def expected_tools(groups):
    names=set()
    for group in groups.split(','):
        names |= GROUPS[group]
    return names


def role_groups():
    # Inventory is data-only. No import/exec of an enablement script.
    path=Path(__file__).with_name('roles.json')
    roles=json.loads(path.read_text())['profiles']
    ops={'devops-engineer','deployment-engineer','cloud-engineer','observability-specialist','performance-optimiser'}
    analysis={'backend-developer','frontend-developer','mobile-developer','code-implementer','code-reviewer','debug-specialist','test-engineer','integration-specialist','software-architect','security-specialist','governance-privacy','ai-safety-guardrails','legal-specialist','chief-of-staff','project-orchestrator','cross-project-collaborator','deliberation-moderator'}
    assert len(roles)==45 and len(set(roles))==45 and 'default' in roles
    return {role: 'memory_read' if role in ops else 'memory_read,analysis' if role in analysis else 'memory_read,ingest,analysis'
            for role in roles if role!='default'}


def profile_contract(config, *, groups, main=False):
    try:
        if config.get('memory',{}).get('provider')!='enhanced_cognee':return False,'provider_not_selected'
        enabled=config.get('plugins',{}).get('enabled')
        if not main and (enabled is None or 'enhanced_cognee' not in enabled):
            return False,'plugin_admission_not_verified'
        if 'memory' in config.get('agent',{}).get('disabled_toolsets',[]):return False,'memory_disabled'
        if 'memory' not in config.get('platform_toolsets',{}).get('cli',[]):return False,'cli_memory_not_allowed'
        entry=config['mcp_servers']['enhanced_cognee']
        if entry.get('command')!=str(PY) or entry.get('args')!=['-I',str(INSTALL),'--tool-groups',groups]:
            return False,'configured_launch_mismatch'
        if entry.get('env')!={'ENHANCED_COGNEE_ACCESS_TOKEN':'${ENHANCED_COGNEE_ACCESS_TOKEN}'}:
            return False,'credential_binding_mismatch'
        if not PY.is_file() or not INSTALL.is_file():return False,'configured_runtime_missing'
        return True,'provider_config_and_launch_contract'
    except (KeyError,TypeError,AttributeError):
        return False,'invalid_profile_contract'


def token_from(path):
    values=[line.split('=',1)[1].strip() for line in path.read_text().splitlines()
            if line.startswith('ENHANCED_COGNEE_ACCESS_TOKEN=')]
    if len(values)!=1 or not values[0] or any(c.isspace() for c in values[0]):
        raise ValueError('token_binding_invalid')
    return values[0]


def api_status(token):
    request=Request('http://127.0.0.1:28080/v1/memories/status',headers={'Authorization':'Bearer '+token})
    with urlopen(request,timeout=15) as response:
        return json.loads(response.read(262145))


def probe_profile(home,groups,*,main=False):
    import yaml
    config=yaml.safe_load((home/'config.yaml').read_text())
    ok,detail=profile_contract(config,groups=groups,main=main)
    if not ok:return False,detail
    entry=config['mcp_servers']['enhanced_cognee']
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'independent-catalogue-verifier','version':'2'}}},
              {'jsonrpc':'2.0','method':'notifications/initialized'},
              {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_stats','arguments':{}}}]
    with tempfile.TemporaryDirectory(prefix='ec-catalogue-') as temporary:
        env={'HOME':temporary,'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','DO_NOT_TRACK':'1',
             'ENHANCED_COGNEE_ACCESS_TOKEN':token_from(home/'.env')}
        result=subprocess.run([entry['command']]+entry['args'],input=''.join(json.dumps(m)+'\n' for m in messages),
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=45,env=env,cwd=temporary)
    if result.returncode!=0 or len(result.stdout)>262144:return False,'catalogue_process_failed'
    replies={}
    for line in result.stdout.splitlines():
        value=json.loads(line)
        if value.get('id') in replies:return False,'duplicate_rpc_reply'
        replies[value.get('id')]=value
    tools=replies.get(2,{}).get('result',{}).get('tools',[])
    names=[tool['name'] for tool in tools]
    if len(names)!=len(set(names)) or set(names)!=expected_tools(groups):return False,'catalogue_mismatch'
    call=replies.get(3,{}).get('result',{})
    if call.get('isError') is True:return False,'authenticated_status_refused'
    status=json.loads(call['content'][0]['text'])
    project='default' if main else home.name.replace('-','_')
    if status.get('project_id')!=project or status.get('ready') is not True or 'error' in status:
        return False,'authenticated_scope_or_readiness_mismatch'
    return True,str(len(names))+' catalogue tools; scoped status verified; capture not exercised'


def rotation_checks(root):
    rows=[]
    try:
        latest={}
        for candidate in root.iterdir():
            if candidate.is_dir():
                for path in candidate.glob('execution-*.json'):
                    body=json.loads(path.read_text())
                    family=body.get('family')
                    if family=='arcadedb-apply':family='arcadedb'
                    if family in FAMILIES and (family not in latest or path.name>latest[family][0]):
                        latest[family]=(path.name,body.get('complete') is True)
        for family in FAMILIES:
            rows.append({'name':'rotation: '+family,'status':'OK' if latest.get(family,('',False))[1] else 'ERR',
                         'detail':'retained receipt only; credentials not retested'})
    except PermissionError:
        rows=[{'name':'rotation: '+family,'status':'SKIP','detail':'owner-only receipt access'} for family in FAMILIES]
    except (OSError,ValueError,TypeError):
        rows=[{'name':'rotation: '+family,'status':'ERR','detail':'receipt unavailable or malformed'} for family in FAMILIES]
    return rows


def summarise(rows):
    failed=[r['name'] for r in rows if r['status']=='ERR']
    skipped=[r['name'] for r in rows if r['status']=='SKIP']
    return {'complete':not failed and not skipped,'checks':len(rows),'failed':failed,'skipped':skipped,
            'scope':'configuration, catalogue, scoped status and job metadata; NOT native capture qualification'}
