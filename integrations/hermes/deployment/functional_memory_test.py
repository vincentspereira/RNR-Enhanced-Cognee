#!/usr/bin/env python3
"""Maintained invented-data functional checks; explicit opt-in, strict cleanup.

Replaces the ignored archived diagnostic. Never summarises pre-existing rows.
No credential issuance, bot launch, service restart, library publication grant,
qualification rerun or permanent deletion is performed.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from verification_contracts import HOME, token_from


def verdict(rows):
    failed=[r['name'] for r in rows if r['status']=='ERR']
    skipped=[r['name'] for r in rows if r['status']=='SKIP']
    return {'complete':not failed and not skipped,'checks':len(rows),'failed':failed,'skipped':skipped}


def exit_status(summary):
    return 1 if summary['failed'] else 2 if summary['skipped'] else 0


def api(role,method,path,body=None):
    token=token_from(HOME/'profiles'/role/'.env')
    request=Request('http://127.0.0.1:28080'+path,data=json.dumps(body).encode() if body is not None else None,
                    method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        with urlopen(request,timeout=70) as response:
            raw=response.read(262145)
            if len(raw)>262144:raise ValueError('response_size')
            return response.status,json.loads(raw)
    except HTTPError as error:
        raw=error.read(4096)
        try:return error.code,json.loads(raw)
        except ValueError:return error.code,{}


def retract_owned(call,role,ident):
    code,row=call(role,'GET','/v1/memories/'+ident)
    if code!=200 or type(row.get('version')) is not int:return False
    code,_=call(role,'POST','/v1/memories/'+ident+'/retract',{'expected_version':row['version']})
    if code!=200:return False
    code,_=call(role,'GET','/v1/memories/'+ident)
    return code==404


def run(*,allow_model=False,call=api,pause=time.sleep):
    rows=[];owned=[];role='web-researcher';category='audit_'+uuid.uuid4().hex[:12]
    def record(name,ok,detail=''):
        rows.append({'name':name,'status':'OK' if ok else 'ERR','detail':detail})
    base_code,baseline=call(role,'GET','/v1/memories/status')
    baseline_count=baseline.get('active_records')
    if base_code!=200 or type(baseline_count) is not int:
        record('measured baseline',False,'refused before any fixture writes')
        return rows
    record('measured baseline',True)
    try:
        ids=[]
        for index in range(2):
            pause(3)
            code,row=call(role,'POST','/v1/memories',{'content':'Invented functional fixture: amber module uses calibration seven. Variant '+str(index),
                'category':category,'idempotency_key':'audit-'+uuid.uuid4().hex})
            ident=row.get('id')
            if isinstance(ident,str) and ident:owned.append((role,ident));ids.append(ident)
            record('remember fixture '+str(index+1),code==200 and bool(ident))
            if code!=200 or not ident:raise ValueError('fixture_not_acknowledged')
            code,read=call(role,'GET','/v1/memories/'+ident)
            record('get fixture '+str(index+1),code==200 and read.get('id')==ident)
        ident=ids[0]
        code,row=call(role,'GET','/v1/memories/'+ident)
        pause(3)
        correction_code,corrected=call(role,'PATCH','/v1/memories/'+ident,{'expected_version':row['version'],'content':'Invented corrected fixture: amber module uses calibration eight.'})
        history_code,history=call(role,'GET','/v1/memories/'+ident+'/history')
        versions=history.get('versions',[])
        record('versioned correction and history',correction_code==200 and corrected.get('version')==row['version']+1
               and history_code==200 and any(v.get('version')==corrected.get('version') for v in versions))
        code,recall=call(role,'POST','/v1/memories/recall',{'query':'Invented corrected fixture amber calibration eight','limit':20,'include_shared':False})
        record('recall exact owned fixture',code==200 and any(r.get('id')==ident for r in recall.get('results',[])))
        pause(3)
        code,ing=call(role,'POST','/v1/memories/ingest',{'text':'Invented ingested fixture for calibration.','category':category,'base_key':'audit-'+uuid.uuid4().hex})
        # Partial ingestion reports acknowledged IDs too; always register them.
        for item in ing.get('record_ids',[]):
            if isinstance(item,str):owned.append((role,item))
        record('ingestion complete receipt',code==200 and ing.get('complete',True) is True and ing.get('ingested',0)>0
               and len(ing.get('record_ids',[]))==ing.get('ingested'))
        code,refusal=call(role,'POST','/v1/memories/ingest',{'url':'http://127.0.0.1:28080/health/ready','base_key':'audit-'+uuid.uuid4().hex})
        record('private-address refusal',code in (403,422) and 'public address' in str(refusal.get('detail','')))
        code,connections=call(role,'POST','/v1/memories/connections',{'entity':'amber','depth':1,'limit':5,'include_shared':False})
        record('connections entity contract',code==200 and 'error' not in connections)
        for path,name in [('/v1/memories/library/','scoped library reads'),('/v1/memories/library/membership','scoped membership reads')]:
            code,payload=call(role,'GET',path)
            record(name,code==200 and isinstance(payload,dict) and 'error' not in payload)
        if allow_model:
            for path,body,name in [('/v1/memories/summarize',{'record_ids':ids,'title':'Invented fixtures only'},'return-only model summary'),
                ('/v1/memories/consolidation/candidates',{'record_ids':ids},'report-only consolidation'),
                ('/v1/memories/translate',{'text':'Invented calibration fixture.','target_language':'French'},'return-only translation')]:
                pause(3)
                code,payload=call(role,'POST',path,body)
                if name=='return-only model summary':
                    ok=code==200 and bool(payload.get('summary')) and payload.get('stored') is False and payload.get('record_id') is None
                    # Never clean unknown IDs if an old server wrongly writes a
                    # summary. Explicit-ID schema rejects on the old backend.
                elif name=='report-only consolidation':ok=code==200 and payload.get('report_only') is True
                else:ok=code==200 and bool(payload.get('translation')) and payload.get('stored') is False
                record(name,ok)
        else:
            rows.append({'name':'model fixtures','status':'SKIP','detail':'requires --allow-model-fixtures'})
        code,status=call(role,'GET','/v1/memories/summarization/status')
        record('model status is explicit',code==200 and type(status.get('configured')) is bool)
        cos='chief-of-staff';pause(3)
        code,seed=call(cos,'POST','/v1/memories',{'content':'Invented reviewer-gate fixture.','category':category,'idempotency_key':'audit-'+uuid.uuid4().hex})
        cid=seed.get('id')
        if isinstance(cid,str) and cid:owned.append((cos,cid))
        record('coordinator fixture',code==200 and bool(cid))
        if cid:
            code,pub=call(cos,'POST','/v1/memories/'+cid+'/library',{'expected_version':seed.get('version',1),'library':'team_notes','revoke':False})
            record('reviewer-only publication',code==403 and 'memory:admin' in str(pub.get('detail','')))
    except Exception as error:
        record('execution',False,'fixed error kind: '+type(error).__name__)
    finally:
        for own_role,ident in reversed(owned):
            pause(3)
            try:ok=retract_owned(call,own_role,ident)
            except Exception:ok=False
            record('owned fixture retraction '+str(len(rows)),ok,'versioned acknowledgement and HTTP 404 required')
        code,status=call(role,'GET','/v1/memories/status')
        record('baseline restored',code==200 and type(status.get('active_records')) is int and status['active_records']==baseline_count)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true')
    parser.add_argument('--allow-model-fixtures',action='store_true')
    args=parser.parse_args()
    if not args.run_live:
        print(json.dumps({'complete':False,'not_run':True,'reason':'inspect script and explicitly pass --run-live after deployment'}))
        return 2
    rows=run(allow_model=args.allow_model_fixtures)
    for row in rows:print(json.dumps(row,sort_keys=True),flush=True)
    summary=verdict(rows)
    print(json.dumps(summary,sort_keys=True))
    return exit_status(summary)


if __name__=='__main__':raise SystemExit(main())
