"""Reconcile actual receipts and exact bindings; write only new review evidence."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT=Path(__file__).resolve().parents[6]
OUT=Path(__file__).resolve().parent
REPAIR=OUT.parent/'repair-v2'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    with (OUT/name).open('x',encoding='ascii') as f:json.dump(obj,f,indent=2,ensure_ascii=True);f.write('\n')

manifest=json.loads((REPAIR/'review-input-manifest.json').read_text())
assert len(manifest)==20
checks={p:{'expected':pin,'actual':sha(ROOT/p)} for p,pin in manifest.items()}
assert all(v['expected']==v['actual'] for v in checks.values())
save('final-bindings.json',{'manifest_sha256':sha(REPAIR/'review-input-manifest.json'),'files':checks,'all_match':True})
run_dirs=sorted([p.parent for p in OUT.glob('*/receipt.json')], key=lambda p: json.loads((p/'receipt.json').read_text())['junit_suites'][0]['timestamp'])
assert len(run_dirs)==5
runs=[];canonical=[];fresh={};history=[];case_mapping=[]
for run in run_dirs:
    r=json.loads((run/'receipt.json').read_text())
    records=json.loads((run/'execution-records.json').read_text())
    collected=json.loads((run/'collection-bindings.json').read_text())
    assert len(collected)==len(r['cases'])
    calls=[x for x in records['records'] if x['when']=='call']
    assert len(calls)==len(collected)
    assert not [x for x in records['records'] if x['when']!='call' and x['outcome']!='passed']
    assert records['exitstatus']==r['exit_code']
    for name,pin in r['artifacts'].items():assert sha(run/name)==pin
    for row in collected:
        assert row['declared_helper']['sha256']==manifest['integrations/hermes/deployment/prepare_security_first_cutover_v2.py']
        if 'actual_import' in row:assert row['actual_import']==row['declared_helper']
        assert row['test_source']['sha256']==sha(Path(row['test_source']['path']))
    by_id={x['nodeid']:x for x in calls}
    for row in collected:
        n=row['nodeid'];outcome=by_id[n]['outcome']
        record={'nodeid':n,'outcome':outcome,'receipt':str((run/'receipt.json').relative_to(OUT)),
                'test_sha256':row['test_source']['sha256'],'helper_sha256':row['declared_helper']['sha256']}
        if run.name.startswith('canonical-'):
            assert outcome=='passed';canonical.append(record)
        else:
            key=n.split('::',1)[1];history.append(record)
            if outcome=='passed':
                if key in fresh:case_mapping.append({'previous_nodeid':fresh[key]['nodeid'],'new_nodeid':n,'reason':'Replayed unchanged reader assertions with child-output receipt instrumentation.'})
                fresh[key]=record
            elif key=='test_owner_shell_ast_and_commands':
                case_mapping.append({'previous_nodeid':n,'new_nodeid':'test_fresh_review_corrected2.py::'+key,'reason':'Reviewer-only instrumentation: shlex does not remove shell backslash-newline; substring restart also matched services_restarted. Original shell syntax was valid; corrected lexing and command-word matching, with exact expected argv and safety assertions retained.'})
            else:raise AssertionError('Unresolved source/probe failure: '+n)
    runs.append({'receipt':str((run/'receipt.json').relative_to(OUT)),'exit_code':r['exit_code'],'tests':len(r['cases']),
                 'failures':sum(x['outcome']=='failed' for x in calls),'errors':sum(int(x['errors']) for x in r['junit_suites']),
                 'skipped':sum(int(x['skipped']) for x in r['junit_suites'])})
assert len(canonical)==202 and len(fresh)==40 and all(x['outcome']=='passed' for x in fresh.values())
assert len(history)==45
mapping=json.loads((REPAIR/'test-inventory-and-mapping.json').read_text())
assert {x['id'] for x in mapping['canonical_v2']}=={x['nodeid'] for x in canonical}
old={x['canonical_v2_node_id'] for x in mapping['replay_mapping']};new={x['id'] for x in mapping['new_v2_cases']}
assert len(old)==126 and len(new)==76 and not old&new and old|new=={x['nodeid'] for x in canonical}
for row in canonical:row['classification']='historical-context-replay' if row['nodeid'] in old else 'v2-context-case'
save('named-case-inventory.json',{'canonical':canonical,'fresh_final':list(fresh.values()),'all_fresh_executions':history,'review_instrumentation_mapping':case_mapping,
 'counting_rule':'Each collected parameterized case counted once; internal assertions, SITE8 module checks and positive/negative pipeline subruns are not additional cases. Replayed historical cases and V2 contexts are not claimed as new logical contracts.'})
assert sum(x['tests'] for x in runs)==247
assert sum(x['failures'] for x in runs)==2 and sum(x['errors']+x['skipped'] for x in runs)==0
checks_git={}
for name,args in [('head',['git','rev-parse','HEAD']),('branch',['git','branch','--show-current']),('tracked_diff',['git','diff','--exit-code','HEAD']),('index_diff',['git','diff','--cached','--exit-code'])]:
    result=subprocess.run(args,cwd=ROOT,capture_output=True)
    checks_git[name]={'argv':args,'exit_code':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()}
    assert result.returncode==0
assert checks_git['head']['stdout'].strip()=='72d2d90c3383cc9a83b7dfed7e3060c6ab27a8cf'
assert checks_git['branch']['stdout'].strip()=='codex/enhanced-cognee-security-first-cutover-20261101'
save('final-git-checks.json',checks_git)
verdict={'passed':True,'security_concerns':[],'logic_errors':[],'suggestions':[],
 'summary':'Exact-hash V2 helper and runnable owner bootstrap/read-only-plan instructions pass the bounded offline source review; protected installation, actual owner root plan and all later operational gates remain pending.',
 'acceptance_scope':{'helper_source':True,'owner_bootstrap_and_read_only_plan_source':True,'installed_v2':False,'protected_owner_plan':False,'live_activation':False},
 'counts':{'manifest_bindings_verified':len(checks),'canonical_v2_passed':len(canonical),'canonical_historical_context_replays':len(old),'canonical_v2_added_context_cases':len(new),'fresh_independent_distinct_cases_passed':len(fresh),'fresh_helper_cases':sum(not k.startswith('test_owner_') for k in fresh),'fresh_owner_boundary_cases':sum(k.startswith('test_owner_') for k in fresh),'final_distinct_passed_cases':len(canonical)+len(fresh),'raw_test_executions':sum(x['tests'] for x in runs),'raw_passed_executions':sum(x['tests']-x['failures'] for x in runs),'retained_reviewer_instrumentation_failures':2,'unresolved_source_failures':0,'pytest_errors':0,'pytest_skips':0},
 'source_hashes':manifest,'manifest_sha256':sha(REPAIR/'review-input-manifest.json'),
 'receipts':{'runs':runs,'named_case_inventory':'named-case-inventory.json','initial_bindings':'initial-bindings.json','final_bindings':'final-bindings.json','static_review':'static-review.json','function_comparison':'ast-function-comparison.json','independent_actual_diff':'actual-v1-to-v2.diff','systemd_local_reference':'systemd-default-reference.json','final_git_checks':'final-git-checks.json','evidence_index':'evidence-index.json'},
 'instrumentation_notes':['Both failing subprocess exits/JUnit/full stdout are retained. They identify reviewer shell-analysis instrumentation errors, not candidate defects. Only copied reviewer probes were corrected; no candidate, canonical test, old owner instruction or earlier evidence was edited.','Corrected owner shell case replayed alone after two retained instrumentation failures. Three ordinary reader cases additionally replayed with explicit nested subprocess output receipts; counted once in final coverage.'],
 'limitations':['Offline invented units are structural positive controls only, never a claim about private 20-launch-runtime.conf bytes or its hash. Known source pins remain unchanged in candidate source.','Root script behavior was evaluated in controlled no-launch OS/Path doubles only. Original shell blocks were syntax checked, not executed. Ordinary reader and synthetic pipeline controls ran unprivileged on invented files. No sudo, root installer, systemctl, service, API, model, profile, fleet or credential action was performed.','Actual protected V2 installation/hash/ownership, owner --plan result, real host source-manager identity and later staging/activation/resource/ledger/credential gates remain unverified and pending. V1 installed helper and old bundle were not modified.','This is a standalone helper/owner-command review, not requalification of the eight previously accepted application modules or proof of full installed runtime/dependency integrity. Their exact hash bindings were verified, without application imports.','Forty newly authored reviewer case implementations challenge this scope; they are not claimed to be forty novel logical security contracts. The canonical 76 additions are V2 context cases, separate from 126 historical-context replays.','Two reviewer instrumentation failures and all their receipts remain preserved; language-server diagnostics from its separate environment are not pytest/runtime failures.']}
assert type(verdict['passed']) is bool and not verdict['security_concerns'] and not verdict['logic_errors']
save('independent-verdict.json',verdict)
# Index regular evidence files without following sandbox symlinks or reading FIFOs.
index={}
for p in OUT.rglob('*'):
    if 'sandbox' in p.relative_to(OUT).parts:continue
    if stat.S_ISREG(p.lstat().st_mode):index[str(p.relative_to(OUT))]=sha(p)
save('evidence-index.json',index)
print(json.dumps({'passed':verdict['passed'],'counts':verdict['counts'],'verdict':str(OUT/'independent-verdict.json'),'verdict_sha256':sha(OUT/'independent-verdict.json'),'evidence_index_sha256':sha(OUT/'evidence-index.json')},indent=2))
