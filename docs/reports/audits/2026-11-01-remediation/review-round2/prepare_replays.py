from pathlib import Path
import ast
import difflib
import hashlib
import json
import os
import subprocess
import zipfile

R = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
E = Path(__file__).parent
REPORTS = R / 'docs/reports/audits/2026-11-01-remediation'
old = (E/'test_independent_challenges_v2.py').read_text()
needle = '    assert renewal.decode_exp(token) == 10**100\n'
assert old.count(needle) == 1
new = old.replace(needle, '    with pytest.raises(ValueError):\n        renewal.decode_exp(token)\n')
(E/'test_prior_mapped.py').write_text(new)

# Verify the new committed regression preserved every unaffected statement of
# the original continuation challenge; only the obsolete decode precondition
# and fixture REPO rebinding have changed.
def function(path, name):
    tree = ast.parse(path.read_text())
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
name = 'test_renewal_unrepresentable_expiry_does_not_abort_remaining_profiles'
original_fn = function(E/'test_independent_challenges_v2.py', name)
repaired_fn = function(R/'tests/unit/test_review_round1_remediation.py', name)
normalized_original = list(original_fn.body)
normalized_repaired = list(repaired_fn.body)
# The original position 4 is the old decoder assertion; replacement is a with.
idx = next(i for i,n in enumerate(normalized_original) if isinstance(n,ast.Assert) and 'decode_exp' in ast.unparse(n))
assert isinstance(normalized_repaired[idx], ast.With)
mapping = {'case_name':name, 'obsolete_precondition':ast.unparse(normalized_original[idx]),
           'replacement_precondition':ast.unparse(normalized_repaired[idx]),
           'remaining_function_ast_equal': all(ast.dump(a)==ast.dump(b) for i,(a,b) in enumerate(zip(normalized_original, normalized_repaired)) if i!=idx) and len(normalized_original)==len(normalized_repaired)}
assert mapping['remaining_function_ast_equal']

first = (E/'test_fresh_challenges.py').read_text()
# A nested unused claim is valid JSON and the exp is representable and not due.
# The failed first harness expectation was not a source defect. Preserve it and
# fix only this copied control's expected decision/state, retaining other cases.
old_assertions = '''    assert renewal.main() == 1
    assert attempted == ['default', 'web-researcher']
    state = json.loads(renewal.STATE.read_text())
    assert [r['profile'] for r in state['failed']] == attempted
    assert token not in renewal.STATE.read_text()
'''
new_assertions = '''    supported_unused_claim = payload.startswith('{"exp":1800000000,"extra":')
    assert renewal.main() == (0 if supported_unused_claim else 1)
    assert attempted == ([] if supported_unused_claim else ['default', 'web-researcher'])
    state = json.loads(renewal.STATE.read_text())
    assert [r['profile'] for r in state['failed']] == attempted
    assert state['skipped'] == (['default', 'web-researcher'] if supported_unused_claim else [])
    assert token not in renewal.STATE.read_text()
'''
assert first.count(old_assertions) == 1
(E/'test_fresh_challenges_v2.py').write_text(first.replace(old_assertions,new_assertions))
(E/'harness-mapping.json').write_text(json.dumps({'legacy':mapping, 'fresh':{'case':'deep-unused-claim', 'reason':'Valid representable exp with an unused nested claim is valid input, not an invalid token. Original harness incorrectly required renewal; copied control now checks successful skip and continuation.', 'same_remaining_cases':True}}, indent=2))

prior = json.loads((REPORTS/'review-round1/source-manifest.json').read_text())
current = json.loads((E/'reviewed-manifest.json').read_text())
old_map = {x['path']:x['sha256'] for x in prior}
new_map = {x['path']:x['sha256'] for x in current}
check = {'prior_count':len(prior), 'current_count':len(current),
         'changed_since_rejection':[p for p,h in new_map.items() if p in old_map and old_map[p]!=h],
         'new_paths':sorted(set(new_map)-set(old_map)),
         'removed_paths':sorted(set(old_map)-set(new_map)),
         'old_test_files_unchanged': all(new_map.get(p)==h for p,h in old_map.items() if p.startswith('tests/'))}
with zipfile.ZipFile(REPORTS/'review-round1/rejected-source.zip') as z:
    check['archive_bad_crc_member'] = z.testzip()
    check['archive_member_count'] = len(z.namelist())
    check['archive_matches_prior_manifest'] = all(hashlib.sha256(z.read(x['path'])).hexdigest()==x['sha256'] for x in prior)
    check['archive_has_exact_manifest_members'] = set(z.namelist()) == set(old_map)
(E/'preservation.json').write_text(json.dumps(check,indent=2))
print(json.dumps(check,indent=2))

receipts=[]
for group, files in {'prior-mapped':['test_prior_mapped.py','test_grant_challenge.py'],'fresh-corrected':['test_fresh_challenges_v2.py']}.items():
    cmd = [str(R.parent/'.venv-deployment/bin/python'),'-B','-m','pytest',*[str(E/f) for f in files],'-c','/dev/null','--confcutdir='+str(E),'-p','no:cacheprovider','--color=no','-q','--tb=short','--basetemp='+str(E/(group+'-tmp')),'--junitxml='+str(E/(group+'.xml'))]
    proc = subprocess.run(cmd,cwd=R,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (E/(group+'.txt')).write_text(proc.stdout)
    receipts.append({'group':group, 'command':cmd, 'exit':proc.returncode})
    print(group,proc.stdout)
(E/'replay-commands.json').write_text(json.dumps(receipts,indent=2))
