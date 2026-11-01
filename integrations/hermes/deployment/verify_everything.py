#!/usr/bin/env python3
"""Read-only installed-host checks with explicit FAIL/SKIP and bounded scope."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen
from verification_contracts import HOME, INSTALL, api_status, probe_profile, role_groups, rotation_checks, summarise, token_from


def system(*args):
    result=subprocess.run(['/usr/bin/systemctl',*args],capture_output=True,text=True,timeout=20)
    return result.returncode,result.stdout.strip()


def main():
    if os.geteuid()==0:
        print(json.dumps({'complete':False,'failed':['unsafe_root_invocation'],'skipped':[]}))
        return 1
    rows=[]
    def check(name,operation):
        try:
            ok,detail=operation()
            row={'name':name,'status':'OK' if ok else 'ERR','detail':detail}
        except PermissionError:
            row={'name':name,'status':'SKIP','detail':'owner-only evidence'}
        except Exception as error:
            row={'name':name,'status':'ERR','detail':'check_error:'+type(error).__name__}
        rows.append(row)
    for unit in ['api','postgres','qdrant','graph','cache','index']:
        check('service '+unit,lambda unit=unit:(system('is-active','enhanced-cognee-'+unit+'.service')[1]=='active','service activity only'))
    def health():
        with urlopen('http://127.0.0.1:28080/health/ready',timeout=10) as response:
            data=json.loads(response.read(262145))
            return data.get('ready') is True,'schema readiness; not a retrieval/capture test'
    check('memory API health',health)
    def main_status():
        data=api_status(token_from(HOME/'.env'))
        return data.get('project_id')=='default' and data.get('ready') is True,'authenticated main scope'
    check('main assistant memory status',main_status)
    source=Path(__file__).parent.parent/'enhanced_cognee_mcp/server.py'
    check('installed MCP equals candidate',lambda:(INSTALL.read_bytes()==source.read_bytes(),'byte equality; source fixes are not installed until this passes'))
    groups=role_groups()
    for role,spec in sorted(groups.items()):
        check('role '+role,lambda role=role,spec=spec:probe_profile(HOME/'profiles'/role,spec))
    check('main assistant tools',lambda:probe_profile(HOME,'memory_read,ingest,analysis',main=True))
    check('renewal timer active',lambda:(system('is-active','ec-hermes-memory-token-renew.timer')[1]=='active','schedule only'))
    check('renewal last service result',lambda:(system('show','ec-hermes-memory-token-renew.service','-p','Result','--value')[1]=='success','last execution result, not future success'))
    check('renewal root-safe entry point',lambda:('/usr/bin/python3 -I -B /opt/' in system('show','ec-hermes-memory-token-renew.service','-p','ExecStart','--value')[1],'must not execute a user-writable virtual environment'))
    def renewal_state():
        body=json.loads(Path('/opt/enhanced-cognee-memory/fleet-renewal/state.json').read_text())
        expected=set(groups)|{'default'}
        stamp=datetime.datetime.strptime(body['last_run_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        age=(datetime.datetime.now(datetime.timezone.utc)-stamp).total_seconds()
        ok=body.get('failed')==[] and set(body.get('expires_utc',{}))==expected and 0<=age<=8*86400
        return ok,'requires all 45 identities and state no older than eight days; never runs renewal'
    check('renewal inventory and freshness',renewal_state)
    for unit in ['enhanced-cognee-backup','enhanced-cognee-profile-backup','enhanced-cognee-qualified-fleet-backup-v2']:
        check(unit+' timer',lambda unit=unit:(system('is-active',unit+'.timer')[1]=='active','activity only, not restore proof'))
        check(unit+' last result',lambda unit=unit:(system('show',unit+'.service','-p','Result','--value')[1]=='success','retained service execution result'))
    rows.extend(rotation_checks(Path('/var/lib/enhanced-cognee-rotation')))
    for row in rows:
        print('%-4s %-48s %s'%(row['status'],row['name'],row['detail']),flush=True)
    summary=summarise(rows)
    print(json.dumps(summary,sort_keys=True))
    return 1 if summary['failed'] else 2 if summary['skipped'] else 0


if __name__=='__main__':
    raise SystemExit(main())
