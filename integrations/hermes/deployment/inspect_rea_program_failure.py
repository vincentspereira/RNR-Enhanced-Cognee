"""Read exact retained REA refusal; start no job and retry no effectful phase."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import tempfile

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-rea-main-programs-v1'
FAILED_SHA='fa213db654f35502ba5bd32b07ae64dea59a6ecb36cd88188eb8805b94d31534'
CHILD_SHA='bbeaaacd7e06679081484a4d5a15cf7f101a55ca1462dbd3e89084ea18596328'


def require(value):
    if not value:raise ValueError('rea_retained_inspection_refused')


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_rea_retained_inspection','__file__':str(path)}
    exec(compile(raw,'<verified-rea-retained-inspection>','exec'),value)
    return value


def retained(read):
    context=json.loads(read(ARTIFACT/'context.private.json',0))
    require(context.get('source_sha256')==FAILED_SHA)
    evidence=Path(context['evidence']);require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('rea-main-programs-'))
    result=json.loads(read(evidence/'finish.summary.json',0))
    require(result.get('operator_helper_sha256')==FAILED_SHA and result.get('source_revision')==BASE.name
        and result.get('complete') is False and result.get('operator_job_stopped') is True
        and result.get('credentials_issued')==0 and result.get('all_admission_policies_preserved_disabled') is True
        and result.get('owner_diagnostic')==dict(error_kind='ValueError',phase='identity')
        and all(result.get(k) is False for k in ('source_profiles_changed','source_programs_changed','previous_candidates_changed',
            'candidate_promoted','daily_backup_registry_changed','canonical_memory_edits','chat_model_called',
            'rea_server_started','fleet_launch_approved','production_renewal_timer_enabled'))
        and not any(os.path.lexists(evidence/(name+'.started.json')) for name in
            ('public_programs','isolated_program_execution','new_candidate','configured_backup','configured_restore'))
        and not any(os.path.lexists(ARTIFACT/(name+'.tar')) for name in ('ghidra','java')))
    return evidence


def main():
    require(os.geteuid()==0);os.umask(0o077)
    original=definitions(ARTIFACT/'stage_rea_main_programs.py',FAILED_SHA)
    c=original['common']();read,write=original['support'](c);previous=retained(read)
    state=original['metadata'](original['UNIT']);require(original['stopped'](state))
    live_context=json.loads(read(original['LIVE']/'context.private.json',0))
    require(live_context['source_sha256']==original['LIVE_SHA'])
    live=Path(live_context['evidence']);require(live.parent==BASE/'operator-evidence' and live.name.startswith('main-live-'))
    fingerprints=json.loads(read(live/'source-configuration.private.json',0))['fingerprints']
    source=Path(__file__).with_name('diagnose_rea_owner_preflight.py').read_bytes()
    require(hashlib.sha256(source).hexdigest()==CHILD_SHA)
    account=pwd.getpwnam('vincentspereira')
    result,body=c['owner'](account,source,c['packet'](account,'inspect',fingerprints=fingerprints),limit=65536)
    require(not body and result.get('complete') is True and result.get('profiles_changed') is False
        and result.get('credentials_issued')==0 and result.get('model_called') is False and result.get('memory_api_called') is False)
    report=dict(complete=True,stage='retained_rea_owner_preflight_inspection',source_revision=BASE.name,
        previous_evidence=str(previous),preflight=result,credentials_issued=0,profiles_changed=False,
        services_started=False,programs_staged=False,prior_failure_preserved=True,effectful_retry=False,fleet_launch_approved=False)
    evidence=Path(tempfile.mkdtemp(prefix='rea-preflight-inspection-',dir=BASE/'operator-evidence'))
    report['evidence']=str(evidence);write(evidence/'summary.json',json.dumps(report,sort_keys=True).encode())
    print(json.dumps(report,sort_keys=True),flush=True);return 0
