import hashlib
import json
from pathlib import Path
import re
import subprocess
# Parse only reviewer-generated local pytest JUnit receipts, not external XML.
import xml.etree.ElementTree as ET

repo=Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
scratch=Path(__file__).parent
manifest=json.loads((scratch/'source-manifest.json').read_text())
mismatches=[r['path'] for r in manifest if hashlib.sha256((repo/r['path']).read_bytes()).hexdigest()!=r['sha256']]
def git(*args):
    return subprocess.check_output(['git',*args],text=True,cwd=repo)
tracked=git('diff','--name-only').splitlines()
new=git('ls-files','--others','--exclude-standard').splitlines()
actual={p for p in tracked+new if Path(p).suffix in {'.py','.json'} and not p.startswith('docs/')}
expected={r['path'] for r in manifest}
inventory=json.loads((repo/'integrations/hermes/deployment/roles.json').read_text())
diff=git('diff','--unified=0','--',*[p for p in tracked if p.endswith('.py')])
patterns={
    'shell_execution':r'os\.system\(|shell\s*=\s*True',
    'dynamic_code':r'\b(?:eval|exec)\(',
    'pickle_deserialization':r'pickle\.loads?\(',
    'sql_interpolation':r'''\.execute\(f["']''',
}
hits=[]
current=None
line=0
for source in diff.splitlines():
    if source.startswith('+++ b/'):
        current=source[6:]
    elif source.startswith('@@'):
        line=int(re.search(r'\+(\d+)',source).group(1))-1
    elif source.startswith('+') and not source.startswith('+++'):
        line+=1
        for kind,pattern in patterns.items():
            if re.search(pattern,source):
                hits.append({'path':current,'line':line,'category':kind})
    elif not source.startswith('-') and not source.startswith(chr(92)):
        line+=1
for path in sorted(actual-set(tracked)):
    for line,source in enumerate((repo/path).read_text().splitlines(),1):
        for kind,pattern in patterns.items():
            if re.search(pattern,source):
                hits.append({'path':path,'line':line,'category':kind})
out={
    'baseline':git('rev-parse','HEAD').strip(),
    'manifest_count':len(manifest),
    'source_count':sum(not r['path'].startswith('tests/') for r in manifest),
    'test_file_count':sum(r['path'].startswith('tests/') for r in manifest),
    'manifest_mismatches':mismatches,
    'unmanifested_source_changes':sorted(actual-expected),
    'manifest_not_in_changed_source':sorted(expected-actual),
    'inventory_count':len(inventory['profiles']),
    'inventory_unique':len(set(inventory['profiles'])),
    'static_scan_added_line_hits':hits,
}
a=ET.parse(scratch/'challenges.xml').getroot().findall('.//testcase')
b=ET.parse(scratch/'challenges-v2.xml').getroot().findall('.//testcase')
corrected={x.attrib['name'] for x in b}
chosen=[x for x in a if x.attrib['name'] not in corrected]+b
chosen+=ET.parse(scratch/'grants.xml').getroot().findall('.//testcase')
out['fresh_challenges']={
    'distinct':len(chosen),
    'passed':sum(x.find('failure') is None and x.find('error') is None for x in chosen),
    'failed':sum(x.find('failure') is not None or x.find('error') is not None for x in chosen),
    'failed_case_names':[x.attrib['name'] for x in chosen if x.find('failure') is not None or x.find('error') is not None],
}
out['fixture_mapping']=[{
    'original_file':'test_independent_challenges.py',
    'corrected_file':'test_independent_challenges_v2.py',
    'case_name':name,
} for name in sorted(corrected)]
reg=ET.parse(scratch/'regressions.xml').getroot().findall('.//testcase')
out['candidate_regressions']={
    'cases':len(reg),
    'failed':sum(x.find('failure') is not None or x.find('error') is not None for x in reg),
}
(scratch/'reconciliation.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
