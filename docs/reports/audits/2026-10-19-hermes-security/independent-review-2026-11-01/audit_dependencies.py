"""Read-only audit of public lockfile package versions via OSV; no install."""
import datetime
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

out=Path(__file__).parent
locks=['requirements-memory.lock','requirements-index.lock','requirements-memory-mcp.lock']
packages={}
for name in locks:
    packages[name]=re.findall(r'^([A-Za-z0-9_.-]+)==([^\s;\\]+)',Path(name).read_text(),re.M)
pairs=sorted({(name,version) for rows in packages.values() for name,version in rows})
queries=[{'package':{'name':n,'ecosystem':'PyPI'},'version':v} for n,v in pairs]
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Current public lockfiles, NOT proof of installed protected-runtime inventory',
         'locks':{n:len(rows) for n,rows in packages.items()},'unique_packages_and_versions':len(pairs),'source':'https://api.osv.dev/v1/querybatch'}
try:
    request=Request(summary['source'],data=json.dumps({'queries':queries}).encode(),headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=60) as response:
        result=json.load(response)
    assert len(result['results'])==len(pairs)
    affected=[]
    for pair,row in zip(pairs,result['results']):
        if row.get('vulns'):
            affected.append({'package':pair[0],'version':pair[1],'advisories':sorted(v['id'] for v in row['vulns']),
                             'locks':[lock for lock,rows in packages.items() if pair in rows]})
    summary.update(complete=True,affected=affected)
except Exception as exc:
    summary.update(complete=False,error_kind=type(exc).__name__)
(out/'dependency-osv.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
