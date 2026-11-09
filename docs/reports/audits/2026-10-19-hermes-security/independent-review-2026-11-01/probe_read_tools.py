"""Exercise all ten advertised read tools; one invented fixture, then retract."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
import uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import yaml

OUT=Path(__file__).parent
HOME=Path.home()/'.hermes'
role=HOME/'profiles/web-researcher'
token=next(x.split('=',1)[1].strip() for x in (role/'.env').read_text().splitlines() if x.startswith('ENHANCED_COGNEE_ACCESS_TOKEN='))
def api(method,path,body=None):
    req=Request('http://127.0.0.1:28080'+path,data=json.dumps(body).encode() if body is not None else None,method=method,
                headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=30) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.loads(e.read())
code,fixture=api('POST','/v1/memories',{'content':'Invented read-tool audit fixture: calibration module amber.',
                                    'category':'independent_read_tools','idempotency_key':'audit-read-'+uuid.uuid4().hex})
assert code==200 and fixture.get('id')
ident=fixture['id']
rows=[]
config=yaml.safe_load((role/'config.yaml').read_text())['mcp_servers']['enhanced_cognee']
env={'HOME':str(HOME),'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','ENHANCED_COGNEE_ACCESS_TOKEN':token,'PYTHONDONTWRITEBYTECODE':'1'}
p=subprocess.Popen([config['command']]+config['args'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
assert p.stdin is not None and p.stdout is not None
sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
sequence=0
def rpc(method,params):
    global sequence
    assert p.stdin is not None and p.stdout is not None
    sequence+=1
    p.stdin.write((json.dumps({'jsonrpc':'2.0','id':sequence,'method':method,'params':params})+'\n').encode());p.stdin.flush()
    assert sel.select(30),'rpc deadline'
    answer=json.loads(p.stdout.readline(524289));assert answer.get('id')==sequence
    return answer.get('result',{})
try:
    rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'independent-read-audit','version':'1'}})
    calls=[('recall',{'query':'Invented read-tool audit fixture calibration','limit':5}),('get_memories',{'limit':10}),
           ('get_memory',{'record_id':ident}),('get_memory_history',{'record_id':ident}),
           ('get_related',{'query':'calibration'}),('list_agents',{}),('get_shared_memories',{}),
           ('library_membership',{}),('get_stats',{}),('health',{})]
    for name,args in calls:
        result=rpc('tools/call',{'name':name,'arguments':args})
        body=json.loads(result['content'][0]['text'])
        row={'tool':name,'mcp_isError':result.get('isError',False),'payload_error_present':isinstance(body,dict) and 'error' in body,
             'http_error_status':body.get('status_code') if isinstance(body,dict) else None,
             'fixed_detail':body.get('detail') if isinstance(body,dict) else None,
             'payload_type':type(body).__name__}
        rows.append(row);print(json.dumps(row),flush=True)
        (OUT/'read-tool-live.json').write_text(json.dumps(rows,indent=2))
        time.sleep(0.7)
finally:
    sel.close();p.stdin.close()
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=3)
    time.sleep(3)
    code,got=api('GET','/v1/memories/'+ident)
    assert code==200
    status,_=api('POST','/v1/memories/'+ident+'/retract',{'expected_version':got['version']})
    get_status,_=api('GET','/v1/memories/'+ident)
    list_status,data=api('GET','/v1/memories?limit=200&include_shared=false')
    active=data if isinstance(data,list) else data.get('results',[])
    cleanup={'retract_status':status,'get_status_after':get_status,'active_count_after':len(active),'list_status':list_status}
    (OUT/'read-tool-cleanup.json').write_text(json.dumps(cleanup,indent=2));print('CLEANUP',json.dumps(cleanup))
    assert status==200 and get_status==404 and list_status==200 and len(active)==0
