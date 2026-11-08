"""Reconcile only local generated receipts, verify input freeze and archive scope."""
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
AUDIT = OUT.parent
sha = lambda data: hashlib.sha256(data).hexdigest()
file_sha = lambda path: sha(path.read_bytes())
def write_json(path, value):
    path.open('x', encoding='ascii').write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n')
assert os.geteuid() != 0
manifest = json.loads((AUDIT / 'parent/round2-review-manifest.json').read_text())
actual = {p: file_sha(ROOT / p) for p in manifest['files']}
assert actual == manifest['files']
helper_rel = 'integrations/hermes/deployment/prepare_security_first_cutover.py'
helper = ROOT / helper_rel
owner = AUDIT / 'OWNER-NEXT-PLAN.md'
archive = AUDIT / 'parent/round1-source.zip'
assert file_sha(archive) == 'ff21c524ac91e1fdb426de8c7c4c2ec4533c94bc554252282bf0efedd495196b'
with zipfile.ZipFile(archive) as z:
    old = z.read(helper_rel)
assert sha(old) == 'cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813'
old_ast, new_ast = ast.parse(old), ast.parse(helper.read_bytes())
assert len(old_ast.body) == len(new_ast.body)
changed = []
for before, after in zip(old_ast.body, new_ast.body):
    if ast.dump(before) != ast.dump(after):
        assert isinstance(before, ast.FunctionDef) and isinstance(after, ast.FunctionDef) and before.name == after.name
        changed.append(after.name)
assert changed == ['trusted_path', 'collect_snapshot']
assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'eval', 'exec', 'compile'} for n in ast.walk(new_ast))
assert all(not isinstance(n, ast.keyword) or n.arg != 'shell' or not isinstance(n.value, ast.Constant) or n.value.value is False for n in ast.walk(new_ast))
maintained = [helper, owner, *[p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.py', '.md', '.sh')]]
for p in maintained:
    text = p.read_text('ascii')
    assert all(line == line.rstrip() for line in text.splitlines()), str(p)
write_json(OUT / 'static-and-freeze-verification.json', dict(input_manifest_verified_after_execution=True, hashes=actual,
    baseline_archive_sha256=file_sha(archive), rejected_helper_sha256=sha(old), changed_functions=changed,
    all_other_module_ast_nodes_unchanged=True, helper_dynamic_code_execution_calls=0, shell_true_calls=0,
    maintained_ascii_and_trailing_whitespace_checks=True, euid=os.geteuid()))

case_groups = {}
all_cases = []
for group, promised in [('historical', 176), ('fresh', 80), ('payload', 4)]:
    run = OUT / (group + '-run')
    receipt = json.loads((run / 'process-receipt.json').read_text())
    ids = json.loads((run / 'collected-case-ids.json').read_text())
    phases = json.loads((run / 'case-phase-outcomes.json').read_text())
    assert receipt['returncode'] == phases['exitstatus'] == 0
    assert receipt['case_count'] == len(ids) == promised
    assert len(ids) == len(set(ids))
    assert receipt['counts'] == dict(passed=promised, failed=0, error=0, skipped=0)
    assert receipt['log_sha256'] == file_sha(run / 'process.log')
    assert receipt['junit_sha256'] == file_sha(run / 'junit.xml')
    assert len(phases['reports']) == 3 * promised
    assert Counter((p['when'], p['outcome']) for p in phases['reports']) == Counter({('setup', 'passed'): promised, ('call', 'passed'): promised, ('teardown', 'passed'): promised})
    assert Counter(p['nodeid'] for p in phases['reports']) == Counter({n: 3 for n in ids})
    assert all(file_sha(ROOT / p) == v for p, v in receipt['source_and_test_bindings'].items())
    case_groups[group] = ids
    all_cases += ids
assert len(set(all_cases)) == len(all_cases)
parent_map = json.loads((AUDIT / 'repair-round1/case-reconciliation.json').read_text())
mapping = []
for row in parent_map['case_mapping']:
    current = row['corrected_nodeid'].replace('/repair-round1/', '/review-round2/')
    assert current in case_groups['historical']
    mapping.append(dict(original_nodeid=row['original_nodeid'], current_nodeid=current,
                        transformation=row['transformation'], state='passed'))
assert len(mapping) == len({x['current_nodeid'] for x in mapping}) == 173
regressions = [n for n in case_groups['historical'] if n not in {x['current_nodeid'] for x in mapping}]
assert len(regressions) == 3
family_counts = Counter(n.split('::', 1)[1].split('[', 1)[0] for n in case_groups['fresh'] + case_groups['payload'])
assert len(family_counts) == 13
counts = dict(executed=sum(len(v) for v in case_groups.values()), passed=sum(len(v) for v in case_groups.values()), failed=0, errors=0, skipped=0,
              original_cases=123, historical_reviewer_cases=50, historical_distinct_logical_case_identities=len(mapping),
              duplicate_regression_implementations=len(regressions), corrected_historical_executions=len(case_groups['historical']),
              fresh_authored_parameterized_cases=len(case_groups['fresh']) + len(case_groups['payload']), fresh_test_families=len(family_counts),
              bash_blocks_syntax_checked=2, embedded_python_blocks_parsed=3)
assert counts['executed'] == 260
write_json(OUT / 'case-reconciliation.json', dict(counts=counts, historical_mapping=mapping, duplicate_regression_implementations=regressions,
    fresh_case_ids=case_groups['fresh'] + case_groups['payload'], fresh_family_counts=dict(family_counts),
    counting_note='84 fresh implementations/input variants in 13 families overlap prior safety properties; no claim of 84 novel contracts or 260 distinct logical contracts.'))
source_hashes = dict(helper=file_sha(helper), owner_instructions=file_sha(owner), input_manifest=file_sha(AUDIT / 'parent/round2-review-manifest.json'), immutable_rejected_archive=file_sha(archive))
paths = [OUT / n for n in ['REPORT.md', 'input-verification.json', 'static-and-freeze-verification.json', 'fixture-adaptations.patch', 'case-reconciliation.json', 'command-extraction.json', 'historical-run/process-receipt.json', 'fresh-run/process-receipt.json', 'payload-run/process-receipt.json', 'archive-index.json']]
verdict = dict(passed=True, security_concerns=[], logic_errors=[], suggestions=[],
    summary='Exact-hash source acceptance for repaired stage-only helper and owner hash-bound bootstrap/read-only-plan commands; all 260 offline ordinary-user test executions passed. Protected installation/root plan, preparation and live activation remain unperformed and separately gated.',
    evidence_paths=[str(p) for p in paths], counts=counts, source_hashes=source_hashes,
    owner_pending=['protected helper installation and installed readback', 'actual root --plan including protected 20-launch-runtime.conf validation', 'approved exact-digest --prepare', 'separate live installation/reload/restart and installed behavior gates'],
    source_changes=0, prior_evidence_changes=0, root_commands_executed=0,
    artifacts_created='NEW review scripts, test copies/wrappers, synthetic sandboxes, source-bound receipts, report and focused archive under review-round2 only')
write_json(OUT / 'verdict.json', verdict)

# Focused archive: never traverse synthetic symlinks, FIFOs or sandbox fixtures.
# JUnit/logs here were locally generated by the explicit ordinary-user tests.
payloads = {str(p.relative_to(OUT)): p.read_bytes() for p in OUT.iterdir() if p.is_file() and p.name not in ('evidence.zip', 'archive-index.json')}
for group in case_groups:
    for p in (OUT / (group + '-run')).iterdir():
        assert p.is_file() and not p.is_symlink()
        payloads[str(p.relative_to(OUT))] = p.read_bytes()
payloads['source-snapshots/prepare_security_first_cutover.py'] = helper.read_bytes()
payloads['source-snapshots/OWNER-NEXT-PLAN.md'] = owner.read_bytes()
payloads['source-snapshots/round2-review-manifest.json'] = (AUDIT / 'parent/round2-review-manifest.json').read_bytes()
archive_out = OUT / 'evidence.zip'
with zipfile.ZipFile(archive_out, 'x', zipfile.ZIP_DEFLATED) as z:
    for name, data in sorted(payloads.items()):
        z.writestr(name, data)
with zipfile.ZipFile(archive_out) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == set(payloads) and len(z.namelist()) == len(payloads)
    assert all(z.read(name) == data for name, data in payloads.items())
index = dict(archive=str(archive_out), archive_sha256=file_sha(archive_out), members=len(payloads),
             payloads={name: dict(sha256=sha(data), bytes=len(data)) for name, data in sorted(payloads.items())},
             crc_and_all_payload_hashes_verified=True, exclusions=['synthetic sandbox trees, symlinks and FIFOs; fixtures remain preserved outside archive under review-round2'],
             source_snapshot_bindings={'source-snapshots/prepare_security_first_cutover.py': str(helper), 'source-snapshots/OWNER-NEXT-PLAN.md': str(owner), 'source-snapshots/round2-review-manifest.json': str(AUDIT / 'parent/round2-review-manifest.json')})
write_json(OUT / 'archive-index.json', index)
assert all(file_sha(ROOT / p) == v for p, v in manifest['files'].items())
print(json.dumps(dict(verdict_path=str(OUT / 'verdict.json'), passed=True, counts=counts, source_hashes=source_hashes,
                     archive=str(archive_out), archive_sha256=index['archive_sha256'], archive_members=index['members']), indent=2))
