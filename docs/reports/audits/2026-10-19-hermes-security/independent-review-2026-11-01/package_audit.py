"""Build the audit matrix and manifest from preserved actual evidence."""
import ast
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

out=Path(__file__).parent
root=Path.cwd()
py='/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python'
commands={
 'C1':py+' integrations/hermes/deployment/verify_everything.py',
 'C2':py+' .archive/fetch-html-diagnosis/comprehensive-functional-test.py',
 'C3':py+' integrations/hermes/deployment/verify_fleet_memory_tools.py',
 'H':py+' -B '+str(out.relative_to(root)/'inspect_host.py'),
 'P':py+' -B '+str(out.relative_to(root)/'independent_probes.py'),
 'R':py+' -B '+str(out.relative_to(root)/'probe_read_tools.py'),
 'S':py+' -B '+str(out.relative_to(root)/'scan_branch.py'),
 'D':py+' -B '+str(out.relative_to(root)/'audit_dependencies.py'),
 'O':py+' -B '+str(out.relative_to(root)/'offline_secondary_probes.py'),
 'A':py+' -B '+str(out.relative_to(root)/'offline_security_probe.py'),
}
# A was originally replayed from the scratch copy; archived bytes are identical.
consolidated=[]
for line in (out/'consolidated.txt').read_text().splitlines():
    if line.startswith(('OK  ','ERR ')):
        parts=re.split(r'\s{2,}',line.strip(),maxsplit=2)
        consolidated.append({'status':parts[0],'check':parts[1],'actual':parts[2] if len(parts)>2 else ''})
functional=[]
for line in (out/'functional-original.txt').read_text().splitlines():
    if line.startswith(('OK  ','ERR ')):
        parts=re.split(r'\s{2,}',line.strip(),maxsplit=2)
        functional.append({'status':parts[0],'check':parts[1],'actual':parts[2] if len(parts)>2 else ''})
profiles=json.loads((out/'profile-settings.json').read_text())
roles=[r for r in profiles if r['role']!='default']
role_summary=json.loads((out/'fleet-tools.txt').read_text().splitlines()[-1])
functional_summary=json.loads((out/'functional-original.txt').read_text().splitlines()[-1])
functional_command=json.loads((out/'functional-command.json').read_text())
read_tools=json.loads((out/'read-tool-live.json').read_text())
report=(out/'REPORT.md').read_text()
findings=[{'id':a,'severity':b,'title':c} for a,b,c in re.findall(r'^### (F\d+) - (HIGH|MEDIUM|LOW) - (.+)$',report,re.M)]
assert len(consolidated)==55 and all(r['status']=='OK' for r in consolidated)
assert len(roles)==44==role_summary['roles'] and role_summary['complete'] is True
assert len(functional)==20 and functional_summary['checks']==20
assert len(read_tools)==10
assert len(findings)==18 and len({r['id'] for r in findings})==18
summary={'audit_date':'2026-11-01','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'hostname':subprocess.check_output(['uname','-n'],text=True).strip(),
 'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
 'verdict':'Substantially functional; unrestricted production-readiness sign-off not recommended',
 'consolidated':{'planned':60,'ok_rows_before_receipt_exception':55,'receipt_checks_not_completed':5,'exit_code':1,'error_kind':'PermissionError'},
 'fleet_catalogue':role_summary,
 'functional':{**functional_summary,'exit_code':functional_command['exit_code'],'ok_flags':sum(r['status']=='OK' for r in functional),'warning':'A further graph false positive was established by independent live read-tool calls.'},
 'read_tools_live':{'advertised_group_count':10,'non_error_payloads':sum(not r['payload_error_present'] for r in read_tools),'error_payloads':sum(r['payload_error_present'] for r in read_tools)},
 'findings':findings,'severity_counts':dict(collections.Counter(r['severity'] for r in findings)),
 'role_groups':dict(collections.Counter(r['mcp_groups'] for r in roles)),
 'protected_backend_source_equivalence':'not established',
 'changes':{'tracked_repository_diff':subprocess.check_output(['git','diff','--stat'],text=True).strip(),'service_restarts':0,'credential_rotations':0,'fleet_bot_activations':0,'commits':0,'pushes':0,'profiles_modified':0},
 'root_evidence_pending':['rotation receipts','LLM credential file mode and accidental-copy verification','current profile backup and recovery receipts']}
(out/'audit-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=True)+'\n')
lines=['# Full verification matrix','', 'All commands ran from '+str(root)+'.',
       'PASS below means the stated check only, not unrestricted production acceptance.',
       'Script-reported flags are preserved even where independent evidence contradicts them.','',
       '## Exact command aliases','']
for alias,cmd in commands.items():lines+=['### '+alias,'','```bash',cmd,'```','']
lines+=['A was actually replayed from /home/vincentspereira/.hermes/cache/scratch/cognee_readonly_security_review_89d1be78/probe.py; the archived file is the same probe.',
        'C1/C2/C3 were run without source edits. Parent runners set PYTHONDONTWRITEBYTECODE=1.',
        'No command here is an instruction to rerun a qualification or use sudo.','',
        '## Consolidated verifier: every planned check','', '| # | Check | Command | Actual | Verdict |','|---|---|---|---|---|']
for i,row in enumerate(consolidated,1):
    lines.append('| %d | %s | C1 | %s | PASS for declared scope |'%(i,row['check'],row['actual'] or 'OK'))
for i,family in enumerate(['postgresql','valkey','qdrant','application','arcadedb'],56):
    lines.append('| %d | Rotation receipt: %s | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |'%(i,family))
lines+=['','Actual final result: complete=false, error_kind=PermissionError; exit 1. No ordinary failed-list summary.','',
        '## Functional suite: every original flag','', '| # | Check | Command | Original flag/output | Independent interpretation |','|---|---|---|---|---|']
for i,row in enumerate(functional,1):
    interpretation='PASS as scripted; see REPORT.md for assertion limitations'
    if row['status']=='ERR':interpretation='FAIL as supplied; seeded investigation passed; original failure retained'
    if 'graph traversal' in row['check']:interpretation='FAIL independently: live payload is HTTP 422 despite script OK'
    lines.append('| %d | %s | C2 | %s %s | %s |'%(i,row['check'],row['status'],row['actual'],interpretation))
lines+=['','Original suite: '+json.dumps(functional_summary,sort_keys=True)+'. Process exit 0 is erroneous.','',
        '## Fleet: all 44 catalogue/config checks','', '| Role | Expected and configured groups | Live advertised count | C3 outcome | Additional H auth scope |','|---|---|---|---|---|']
for row in roles:
    n={'memory_read':10,'memory_read,analysis':15,'memory_read,ingest,analysis':17}[row['mcp_groups']]
    lines.append('| %s | %s | %d | PASS | %s |'%(row['role'],row['mcp_groups'],n,'PASS' if row['authenticated_status_code']==200 and row['status_project_matches'] else 'FAIL'))
lines+=['','Group counts: '+json.dumps(summary['role_groups'],sort_keys=True)+'.',
        'Main has memory_read,ingest,analysis: 17 MCP tools, plus a separate eight-tool native provider.',
        'Discovery is not proof that every advertised tool call succeeds.','',
        '## Live calls to all ten memory_read tools','', '| Tool | Command | HTTP error status | MCP isError | Result |','|---|---|---|---|---|']
for row in read_tools:
    lines.append('| %s | R | %s | %s | %s |'%(row['tool'],row['http_error_status'] or '-',str(row['mcp_isError']).lower(),
                'FAIL: '+str(row['fixed_detail']) if row['payload_error_present'] else 'Non-error payload returned'))
lines+=['','One invented fixture, then versioned retraction, HTTP 404 readback and active rows=0.','',
        '## Independent bounded live probes','', '| Probe | Command | Actual selected output |','|---|---|---|']
for row in json.loads((out/'independent-probes.json').read_text()):
    lines.append('| '+row['check']+' | P | `'+json.dumps({k:v for k,v in row.items() if k!='check'},sort_keys=True)+'` |')
lines+=['','## Offline/source probes','', 'O: see offline-secondary-probes.json. A: see offline-security-receipt.json.',
        'These use invented fake networking/model/store responses; they do not exploit the deployed service.',
        'S: branch-history scan; D: public lockfile OSV lookup; full outputs retained as JSON.',
        'System metadata commands and output are preserved in the .txt files and summarised in REPORT.md.','']
(out/'VERIFICATION-MATRIX.md').write_text('\n'.join(lines))
# Fail closed if any report artifact accidentally contains a current live memory token.
tokens=[]
home=Path.home()/'.hermes'
for path in [home/'.env']+list((home/'profiles').glob('*/.env')):
    for line in path.read_bytes().splitlines():
        if line.startswith(b'ENHANCED_COGNEE_ACCESS_TOKEN='):
            token=line.split(b'=',1)[1].strip()
            if token:tokens.append(token)
artifacts=[p for p in out.iterdir() if p.is_file() and p.name not in {'MANIFEST.json','independent-audit-evidence.zip'}]
for p in artifacts:
    data=p.read_bytes()
    assert data.isascii(),'Non-ASCII artifact: '+p.name
    assert not any(t in data for t in tokens),'Credential material found in artifact (no value printed)'
    if p.suffix=='.py':ast.parse(data)
manifest=[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(artifacts)]
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=out/'independent-audit-evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(artifacts+[out/'MANIFEST.json']):z.write(p,arcname='independent-review-2026-11-01/'+p.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.infolist())==len(artifacts)+1
print(json.dumps({'severity_counts':summary['severity_counts'],'findings':len(findings),'roles':len(roles),
                  'consolidated_ok':len(consolidated),'functional_flags_ok':summary['functional']['ok_flags'],
                  'read_tools':summary['read_tools_live'],'artifacts_in_zip':len(artifacts)+1,
                  'ascii_and_current_token_checks':'passed','zip_integrity':'passed',
                  'report':str(out/'REPORT.md'),'archive':str(archive),'archive_bytes':archive.stat().st_size},indent=2))
