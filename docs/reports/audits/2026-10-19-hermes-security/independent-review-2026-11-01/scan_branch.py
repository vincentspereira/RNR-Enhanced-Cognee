"""Local branch-history scan. Never emit candidate values or token hashes."""
import collections
import json
from pathlib import Path
import re
import subprocess
import time

OUT=Path(__file__).parent
started=time.monotonic()
patterns={
 'provider_key':re.compile(rb'(?<![A-Za-z0-9])(?:sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{32,}|gh[pousr]_[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16})(?![A-Za-z0-9])'),
 'jwt_literal':re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}'),
 'private_key_block':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
}
# Match the current role tokens only in memory; no secret bytes go to files/stdout.
tokens=set()
home=Path.home()/'.hermes'
for path in [home/'.env']+list((home/'profiles').glob('*/.env')):
    for line in path.read_bytes().splitlines():
        if line.startswith(b'ENHANCED_COGNEE_ACCESS_TOKEN='):
            value=line.split(b'=',1)[1].strip()
            if value: tokens.add(value)
objects=subprocess.check_output(['git','rev-list','--objects','HEAD']).splitlines()
paths={}
for line in objects:
    oid,_,name=line.partition(b' ')
    paths[oid.decode()]=name.decode('utf-8','replace')
check=subprocess.run(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                     input=b'\n'.join(x.split(b' ',1)[0] for x in objects)+b'\n',capture_output=True,check=True)
blobs=[]
for line in check.stdout.splitlines():
    oid,kind,size=line.split()
    if kind==b'blob':blobs.append((oid.decode(),int(size)))
p=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
assert p.stdin is not None and p.stdout is not None
candidates=[]
bytes_read=0
for oid,size in blobs:
    p.stdin.write((oid+'\n').encode());p.stdin.flush()
    header=p.stdout.readline()
    actual=int(header.split()[2]);assert actual==size
    data=p.stdout.read(size);assert len(data)==size
    assert p.stdout.read(1)==b'\n'
    bytes_read+=size
    for rule,pattern in patterns.items():
        matches=list(pattern.finditer(data))
        if matches:
            candidates.append({'object':oid,'path':paths.get(oid,''),'rule':rule,'matches':len(matches),
                               'line_numbers':[data.count(b'\n',0,m.start())+1 for m in matches[:20]]})
    if any(t in data for t in tokens):
        candidates.append({'object':oid,'path':paths.get(oid,''),'rule':'current_fleet_token_exact_match'})
p.stdin.close();p.wait(timeout=20)
summary={'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'scope':'all unique blobs reachable from current branch HEAD, including history',
         'objects':len(objects),'blobs':len(blobs),'bytes_scanned':bytes_read,
         'rules':list(patterns)+['current_fleet_token_exact_match'],
         'candidate_objects_by_rule':dict(collections.Counter(c['rule'] for c in candidates)),
         'seconds':round(time.monotonic()-started,3),'candidate_values_emitted':False,
         'limits':'Pattern scan is not proof of absence of arbitrary passwords or unknown formats; no provider validation and no unreadable LLM key comparison.',
         'candidates':candidates}
(OUT/'secret-scan.json').write_text(json.dumps(summary,indent=2,ensure_ascii=True))
print(json.dumps({k:v for k,v in summary.items() if k!='candidates'},indent=2))
for c in candidates[:60]:print(json.dumps(c,ensure_ascii=True))
