"""Finish the existing scheduled publication without issuing another credential.

Reuse trusted PID-1 proof, confirm stopped units, authenticate the current token,
and recover a new encrypted generation of the already-renewed inactive profile.
The killed original gateway cannot supply a retained-process reload pass.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
FAILED = BASE / 'operator-evidence/candidate-renewal-zh_wxllg'
IDENT = '19ec16bf360645779c8a5bfe82a60905'
BATCH_SHA = 'f7ce4e8616a323dfecdfd02a5843811bb3812b06941ef7ac214e1de623440e3d'
JOURNAL_SHA = '70869e40df75df755b16ddc894e560256087a8ec4b84ba3af63ebc1b9f93c072'


def require(value):
    if not value:
        raise ValueError('retained_candidate_publication_finish_refused')


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    value = {'__name__':'verified_retained_candidate_finish','__file__':str(path)}
    exec(compile(raw,'<verified-public-support>','exec'),value)
    return value


def stopped(value):
    return (value.get('ActiveState') == 'inactive' and value.get('SubState') == 'dead'
        and value.get('LoadState') in {'loaded','not-found'} and value.get('MainPID','0') == '0')


def metadata(unit):
    process = subprocess.run(['/usr/bin/systemctl','show',unit,
        '--property=LoadState,ActiveState,SubState,MainPID,InvocationID,User,Result,ExecMainStatus'],
        capture_output=True,timeout=10)
    require(process.returncode == 0 and len(process.stdout) <= 8192)
    return dict(line.split('=',1) for line in process.stdout.decode().splitlines() if '=' in line)


def retained_binding(prior,context,job):
    require(prior.get('complete') is False and prior.get('operator_helper_sha256') == BATCH_SHA
        and prior.get('failure_phase') == 'scheduled_candidate_publication'
        and prior.get('scheduled_publication_observed') is True
        and prior.get('candidate_ordinary_credential_changed') is True
        and context.get('evidence') == str(FAILED))
    require(job.get('complete') is True and job.get('id') == IDENT and job.get('credential_published') is True
        and job.get('bound_root_completion_verified') is True and job.get('settings_and_oauth_preserved') is True
        and re.fullmatch(r'[a-f0-9]{32}',job.get('invocation_id','')))


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    directory = Path(__file__).parent
    batch = definitions(directory / 'qualify_launch_candidate_renewal.py',BATCH_SHA)
    shared = definitions(directory / 'recover_launch_graph_operator.py',batch['SUPPORT_SHA'])
    read,write = shared['read_file'],shared['private_write']
    prior = json.loads(read(FAILED / 'summary.json',0))
    context = json.loads(read(batch['ARTIFACT'] / ('context-' + IDENT + '.json'),0))
    job = json.loads(read(FAILED / 'scheduled-job.summary.json',0))
    retained_binding(prior,context,job)
    require(hashlib.sha256((batch['ARTIFACT'] / 'qualify_launch_candidate_renewal.py').read_bytes()).hexdigest() == BATCH_SHA)
    modules = batch['components']()
    entry = batch['entry_policy'](modules)
    driver = modules['renew_fleet_credentials.py']
    require(driver['binding_digest'](entry) == context['entry_sha256'])
    core = batch['scoped_core'](modules,entry)
    driver['LEDGER'] = FAILED / 'root-ledger'
    require(driver['attempt_closed'](core,entry,driver['LEDGER'] / (entry['name'] + '-' + IDENT + '.started.json')))
    write(FAILED / 'finish-publication.started.json',json.dumps(dict(helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())).encode())
    result = dict(complete=False,evidence=str(FAILED / 'finish-publication.summary.json'),
        source_revision=BASE.name,previous_failure_preserved=True,credentials_issued=0,
        publication_replayed=False,private_keys_sent_to_owner=False,chat_model_called=False,
        platform_adapters_started=0,production_renewal_timer_enabled=False,
        candidate_headless_gateway_reload_qualified=False,installed_issuer_qualified=False,
        scheduled_renewal_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False)
    phase = 'retained_scheduling_proof'
    try:
        unit = 'ec-candidate-renewal-' + IDENT
        journal = subprocess.run(['/usr/bin/journalctl','--no-pager','--output=json','--lines=128',
            '--unit=' + unit + '.service','--unit=' + unit + '.timer'],capture_output=True,check=True,timeout=15)
        require(len(journal.stdout) <= 262144)
        rows = [json.loads(line) for line in journal.stdout.splitlines()]
        verifier = definitions(directory / 'qualify_launch_issuer_publication.py',JOURNAL_SHA)
        proof = verifier['journal_scheduling_proof'](rows,unit,job['invocation_id'])
        require(proof.get('verified') is True)
        result['journal_scheduling_proof'] = proof
        # Retain bounded metadata from the actual failed predicate evaluation.
        for name in ('service','timer'):
            try:
                saved = json.loads(read(FAILED / (name + '.metadata.json'),0))
            except FileNotFoundError:
                saved = {}
            fields = {'LoadState','ActiveState','SubState','Result','ExecMainStatus','User','InvocationID',
                'ExecMainStartTimestampMonotonic','LastTriggerUSecMonotonic','NoNewPrivileges','ProtectSystem','ProtectHome'}
            result['retained_' + name + '_metadata'] = {k:v for k,v in saved.items() if k in fields}
        phase = 'qualification_unit_cleanup'
        outcomes = {}
        for suffix in ('timer','service'):
            name = unit + '.' + suffix
            before = metadata(name)
            attempted = False
            if not stopped(before):
                require(before.get('LoadState') == 'loaded')
                if suffix == 'service':
                    require(before.get('InvocationID') == job['invocation_id'] and before.get('User') == 'root')
                attempted = True
                # Exit code alone is not proof of current activity: collected
                # transient units can return nonzero despite already stopping.
                subprocess.run(['/usr/bin/systemctl','stop',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
            after = metadata(name)
            require(stopped(after))
            outcomes[suffix] = dict(stop_attempted=attempted,verified_stopped=True,metadata=after)
        result['qualification_units_stopped'] = True
        result['cleanup'] = outcomes
        phase = 'current_credential_authentication'
        # The newly published 24h token is not due. This exercises the installed
        # authenticated no-op branch without signing or publishing another token.
        source = driver['sources']()
        status = driver['run_child'](entry,{},source)
        require(status.get('complete') is True and status.get('credential_published') is False)
        result['current_credential_authenticated'] = True
        policies = [batch['PACKAGE'] / 'candidate-policy.json',Path('/etc/enhanced-cognee/fleet-credentials.json')]
        before_policies = {path:read(path,0) for path in policies}
        require(all(row['enabled'] is False for raw in before_policies.values()
            for row in modules['fleet_credential_policy.py']['validate'](json.loads(raw))['profiles']))
        phase = 'renewed_profile_recovery'
        helper = definitions(directory / 'qualify_launch_isolated_accounts.py',
            'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
        result['generation'] = batch['fresh_backup'](entry,FAILED,helper,read,write)
        require(all(read(path,0) == raw for path,raw in before_policies.items()))
        result.update(complete=True,candidate_scheduled_publication_component_qualified=True,
            renewed_profile_recovery_qualified=True,all_admission_policies_preserved_disabled=True,
            retained_gateway_process_was_stopped=True)
    except Exception:
        result.update(category='retained_candidate_publication_finish_incomplete_preserve_evidence',failure_phase=phase)
    write(FAILED / 'finish-publication.summary.json',json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"retained_candidate_publication_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
