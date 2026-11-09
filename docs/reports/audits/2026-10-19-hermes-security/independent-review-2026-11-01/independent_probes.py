"""Bounded invented-data investigation; no bot/qualification launches."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import yaml

OUT = Path(__file__).parent
HOME = Path.home() / '.hermes'
results = []

def emit(name, **data):
    row = dict(check=name, **data)
    results.append(row)
    (OUT / 'independent-probes.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(row), flush=True)

def token(role):
    return next(x.split('=',1)[1].strip() for x in (HOME/'profiles'/role/'.env').read_text().splitlines()
                if x.startswith('ENHANCED_COGNEE_ACCESS_TOKEN='))

def api(t, method, path, body=None, timeout=90):
    raw = json.dumps(body).encode() if body is not None else None
    req = Request('http://127.0.0.1:28080'+path, data=raw, method=method,
                  headers={'Authorization':'Bearer '+t,'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except HTTPError as e:
        return e.code, json.loads(e.read())

def rows(data):
    return data if isinstance(data,list) else data.get('results',[])

# A separately implemented MCP client; no use of the delivered verifier helper.
cfg = yaml.safe_load((HOME/'profiles/legal-specialist/config.yaml').read_text())['mcp_servers']['enhanced_cognee']
env = {'HOME':str(HOME), 'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8',
       'ENHANCED_COGNEE_ACCESS_TOKEN':token('legal-specialist'), 'PYTHONDONTWRITEBYTECODE':'1'}
p = subprocess.Popen([cfg['command']]+cfg['args'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL, env=env)
assert p.stdin is not None and p.stdout is not None
sel = selectors.DefaultSelector()
sel.register(p.stdout,selectors.EVENT_READ)
sequence = 0

def rpc(method, params):
    global sequence
    sequence += 1
    ident = sequence
    p.stdin.write((json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params})+'\n').encode())
    p.stdin.flush()
    if not sel.select(25):
        raise TimeoutError('independent_mcp_deadline')
    raw = p.stdout.readline(262145)
    answer = json.loads(raw)
    assert answer.get('id') == ident
    return answer.get('result', {})

try:
    init = rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'independent-audit','version':'1'}})
    p.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    p.stdin.flush()
    adv = rpc('tools/list',{})
    names = sorted(t['name'] for t in adv['tools'])
    expected = sorted(['recall','get_memories','get_memory','get_memory_history','get_related',
                       'list_agents','get_shared_memories','library_membership','get_stats','health',
                       'summarize_memories','find_consolidation_candidates','get_summarization_status',
                       'translate_text','detect_language'])
    emit('manual_legal_specialist_mcp_names', passed=names==expected, count=len(names), names=names)
    live = rpc('tools/call',{'name':'get_stats','arguments':{}})
    stats = json.loads(live['content'][0]['text'])
    emit('manual_legal_specialist_auth_call', passed=stats.get('project_id')=='legal_specialist' and stats.get('ready') is True,
         isError=live.get('isError',False))
    denied = rpc('tools/call',{'name':'ingest_text','arguments':{'text':'Invented unoffered-tool probe'}})
    emit('manual_unoffered_tool_refused', passed=denied.get('isError') is True)
    # Low-impact malformed params: see whether the server survives, no API write.
    p.stdin.write(b'{"jsonrpc":"2.0","id":99,"method":"tools/call","params":[]}\n')
    p.stdin.flush()
    if sel.select(10):
        line=p.stdout.readline(262145)
        emit('malformed_params_empty_list', server_alive=p.poll() is None, reply_received=bool(line))
    p.stdin.write(b'{"jsonrpc":"2.0","id":100,"method":"tools/call","params":[1]}\n')
    p.stdin.flush()
    time.sleep(0.5)
    emit('malformed_params_nonempty_list', server_alive=p.poll() is None, exit_code=p.poll())
finally:
    sel.close()
    if p.stdin: p.stdin.close()
    try: p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.terminate()
        p.wait(timeout=3)

wr=token('web-researcher')
code,current=api(wr,'GET','/v1/memories?limit=200&include_shared=true')
assert code==200 and not rows(current), 'Refusing unfiltered analysis over pre-existing records'
for endpoint in ['summarize','consolidation/candidates']:
    code,body=api(wr,'POST','/v1/memories/'+endpoint,{'limit':10})
    emit('empty_scope_'+endpoint.replace('/','_'), status=code, fixed_detail=body.get('detail'))

category='independent_audit_'+uuid.uuid4().hex[:10]
owned=[]
try:
    for i in range(2):
        time.sleep(3)
        code,body=api(wr,'POST','/v1/memories',{
            'content':'Invented audit fixture: calibration module seven uses technique three. Example '+str(i)+'.',
            'idempotency_key':'independent-audit-'+uuid.uuid4().hex,'category':category})
        ident=body.get('id')
        if ident: owned.append(ident)
        emit('paced_fixture_write_'+str(i+1), status=code, id_present=bool(ident))
        assert code==200 and ident
        read_code,row=api(wr,'GET','/v1/memories/'+ident)
        emit('paced_fixture_readback_'+str(i+1), passed=read_code==200 and row.get('id')==ident)
    time.sleep(3)
    code,budget=api(wr,'GET','/v1/memories/summarization/status')
    emit('llm_route_status', status=code, configured=budget.get('configured'), model=budget.get('model'),
         daily_token_cap=budget.get('daily_token_cap'), used_today=budget.get('used_today'))
    started=time.monotonic()
    code,summary=api(wr,'POST','/v1/memories/summarize',{'limit':10,'category':category,'title':'Invented independent audit fixtures only'})
    if summary.get('record_id'): owned.append(summary['record_id'])
    emit('seeded_summary_investigation',status=code,sources=summary.get('sources'),tokens_used=summary.get('tokens_used'),
         summary_present=bool(summary.get('summary')), record_id_present=bool(summary.get('record_id')),
         seconds=round(time.monotonic()-started,3), fixed_detail=summary.get('detail'))
    if summary.get('record_id'):
        c,saved=api(wr,'GET','/v1/memories/'+summary['record_id'])
        emit('seeded_summary_readback',passed=c==200 and saved.get('content')==summary.get('summary'))
    time.sleep(3)
    code,cons=api(wr,'POST','/v1/memories/consolidation/candidates',{'limit':10})
    emit('seeded_consolidation_investigation',status=code,compared=cons.get('compared'),report_only=cons.get('report_only'),
         tokens_used=cons.get('tokens_used'),fixed_detail=cons.get('detail'))
finally:
    for ident in reversed(owned):
        time.sleep(3)
        code,row=api(wr,'GET','/v1/memories/'+ident)
        if code==200:
            status,body=api(wr,'POST','/v1/memories/'+ident+'/retract',{'expected_version':row['version']})
            read_status,read_row=api(wr,'GET','/v1/memories/'+ident)
            emit('audit_fixture_retraction',status=status,readback_status=read_status,readback_state=read_row.get('state'))
    code,current=api(wr,'GET','/v1/memories?limit=200&include_shared=false')
    emit('audit_scope_clean_readback',passed=code==200 and not rows(current),active_rows=len(rows(current)))
