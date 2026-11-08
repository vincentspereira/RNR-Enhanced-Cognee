#!/usr/bin/env python3
"""Non-root configuration/catalogue/scoped-status checks; not native capture proof."""
import json
import os
from verification_contracts import HOME, probe_profile, role_groups


def main():
    if os.geteuid()==0:
        print(json.dumps({'complete':False,'error':'Do not run writable-checkout verifiers as root'}))
        return 1
    rows=[]
    for role,groups in sorted(role_groups().items()):
        try:
            ok,detail=probe_profile(HOME/'profiles'/role,groups)
        except Exception as error:
            ok,detail=False,'check_error:'+type(error).__name__
        rows.append({'role':role,'groups':groups,'pass':ok,'detail':detail})
        print(('%-30s %-4s %s')%(role,'OK' if ok else 'ERR',detail),flush=True)
    failed=[row['role'] for row in rows if not row['pass']]
    print(json.dumps({'complete':not failed,'roles':len(rows),'failures':failed,
        'scope':'full selected configuration + configured launch + catalogue + authenticated project status; no capture lifecycle'},sort_keys=True))
    return 1 if failed else 0


if __name__=='__main__':
    raise SystemExit(main())
