from pathlib import Path
import ast
import hashlib
import importlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

R=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
E=Path(__file__).parent
sys.path.insert(0,str(R))
m=json.loads((E/'reviewed-manifest.json').read_text())
current=[dict(path=x['path'],sha256=hashlib.sha256((R/x['path']).read_bytes()).hexdigest()) for x in m]
assert current==m
original_manifest=json.loads((R/'docs/reports/audits/2026-11-01-remediation/source-manifest-round2.json').read_text())
assert original_manifest==m
python_files=[x['path'] for x in m if x['path'].endswith('.py')]
for p in python_files: ast.parse((R/p).read_bytes(),filename=p)
patterns={
 'hardcoded_secret':r'(?i)(?:api_key|secret|password|token|passwd)\s*=\s*[\x22\x27][^\x22\x27]{6,}[\x22\x27]',
 'shell_true':r'shell\s*=\s*True', 'os_system':r'os\.system\(',
 'eval_exec':r'\b(?:eval|exec)\(', 'unsafe_pickle':r'pickle\.loads?\(',
 'sql_fstring':r'execute\(f[\x22\x27]'}
hits=[]
for x in m:
    p=x['path']
    if p.startswith('tests/') or not p.endswith('.py'):continue
    result=subprocess.run(['git','show','89d1be78:'+p],cwd=R,capture_output=True)
    old=result.stdout.decode() if result.returncode==0 else ''
    import difflib
    for line in difflib.unified_diff(old.splitlines(),(R/p).read_text().splitlines()):
        if line.startswith('+') and not line.startswith('+++'):
            for category,pattern in patterns.items():
                if re.search(pattern,line[1:]):hits.append({'path':p,'category':category,'added_line':line[1:]})
static={'ast_parsed':len(python_files),'added_production_scan_matches':hits,'diff_check':subprocess.run(['git','diff','--check'],cwd=R,capture_output=True,text=True).__dict__.get('returncode')}
(E/'static-independent.json').write_text(json.dumps(static,indent=2))
assert not hits and static['diff_check']==0
bindings=[]
for name in ('src.llm_budget','src.llm_summarize','src.memory_api','src.ingestion','src.memory_queries','src.memory_library','src.memory_daemon','src.security.enterprise_auth'):
    mod=importlib.import_module(name)
    file=Path(mod.__file__).resolve()
    path=str(file.relative_to(R))
    bindings.append({'module':name,'imported_path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'manifest_match':any(x['path']==path and x['sha256']==hashlib.sha256(file.read_bytes()).hexdigest() for x in m)})
assert all(x['manifest_match'] for x in bindings)
(E/'import-bindings.json').write_text(json.dumps(bindings,indent=2))

results={}
for group in ('regressions','prior-unchanged','prior-mapped','fresh','fresh-corrected'):
    # Parse only JUnit files just produced by our local, offline pytest runs;
    # these are not external XML inputs and have no DTD/entity declarations.
    root=ET.parse(E/(group+'.xml')).getroot()
    cases=root.findall('.//testcase')
    results[group]={'cases':len(cases),'passed':sum(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases),'failures':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'case_names':[c.attrib['name'] for c in cases]}
selected=('regressions','prior-mapped','fresh-corrected')
results['accepted_case_executions']=sum(results[g]['cases'] for g in selected)
results['harness_corrections']='Prior expiry precondition contradicted repaired rejection; fresh unused claim was valid, so its positive expectation was corrected. Both original failures and corrected cases are retained and not double-counted.'
results['warnings']={'regressions':0,'prior-mapped':10,'fresh-corrected':0,'reason':'The unchanged historical SQLite grant adapter passes a sequence to named $1..$5 parameters, twice; Python 3.12 deprecation warnings, not skipped assertions.'}
(E/'reconciliation.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'static':static,'imports_bound':len(bindings),'groups':{g:{k:v for k,v in results[g].items() if k!='case_names'} for g in selected},'accepted_case_executions':results['accepted_case_executions']}))

verdict={
 'passed':True,'security_concerns':[],'logic_errors':[],
 'suggestions':[{'priority':'low','detail':'Before Python 3.14, update only the copied SQLite grant-challenge adapter to bind $1..$5 by name; preserve every grant assertion. The unchanged historical harness currently emits 10 deprecation warnings.'}],
 'summary':'Exact 30-file repaired candidate accepted for source only: original R1/R2/R3 and inventory challenges pass; no remaining reproduced contract defect. Installed backend, root upgrade and all owner/runtime gates remain unaccepted.',
 'reviewed_manifest':{'path':str(E/'reviewed-manifest.json'),'candidate_manifest':str(R/'docs/reports/audits/2026-11-01-remediation/source-manifest-round2.json'),'sha256':hashlib.sha256((R/'docs/reports/audits/2026-11-01-remediation/source-manifest-round2.json').read_bytes()).hexdigest(),'files':len(m),'production_or_data':sum(not x['path'].startswith('tests/') for x in m),'tests':sum(x['path'].startswith('tests/') for x in m),'exact_changed_non_doc_coverage':True,'frozen_hashes_rechecked_at_finish':True},
 'tests_run':{'candidate_regressions':{'passed':187,'exit':0,'warnings':0},'preserved_prior_challenges':{'passed':15,'exit':0,'warnings':10,'mapping':'14 unchanged original challenges pass; obsolete huge-expiry acceptance precondition mapped to rejection, with remaining function AST identical. Includes unchanged shared-grant assertions.'},'fresh_independent_challenges':{'passed':12,'exit':0,'warnings':0,'coverage':['writable lexical bin/runtime/ancestor rejection','HTTP 200 malformed reply followed by successful next RPC','huge/nested/malformed expiry continuation and valid unused-claim skip','persistent no-content budget charging after provider failure and reopen']},'accepted_case_executions':results['accepted_case_executions'],'excluded_harness_attempts':{'prior_unchanged':'14 passed; one failure at obsolete decode acceptance precondition, before sweep execution.','fresh_initial':'11 passed; one invalid harness expectation classified a valid unused claim as malformed. Original retained and copied positive control corrected.'},'full_suite':'Not run; unrelated optional qdrant_client baseline failure was outside this targeted acceptance.'},
 'evidence_paths':[str(E/p) for p in ['source-binding.json','reviewed-manifest.json','preservation.json','import-bindings.json','static-independent.json','regressions-command.json','regressions.txt','regressions.xml','challenge-commands.json','replay-commands.json','harness-mapping.json','prior-unchanged.txt','prior-mapped.txt','prior-mapped.xml','fresh.txt','fresh-corrected.txt','fresh-corrected.xml','test_fresh_challenges.py','test_fresh_challenges_v2.py','test_prior_mapped.py','reconciliation.json']],
 'scope_boundaries':'Repository/source and preserved evidence read only. Created evidence only in this new scratch directory. No installation, commit, package install, real model/API/service/fleet action or protected-state modification.'}
(E/'verdict.json').write_text(json.dumps(verdict,indent=2))
# A standalone archive makes all independent receipts, mappings and repros durable.
archive=E/'independent-review-evidence.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    files=sorted(p for p in E.iterdir() if p.is_file() and p!=archive and p.name!='archive-receipt.json')
    for p in files:z.write(p,p.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    archive_receipt={'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':[{'path':name,'sha256':hashlib.sha256(z.read(name)).hexdigest()} for name in z.namelist()],'crc_ok':True}
(E/'archive-receipt.json').write_text(json.dumps(archive_receipt,indent=2))
print('VERDICT',E/'verdict.json')
print('ARCHIVE_SHA256',archive_receipt['sha256'])
