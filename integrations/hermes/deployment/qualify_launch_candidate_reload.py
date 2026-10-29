"""Finish only unresolved live headless reload, reusing scheduled proof.

One fresh ordinary credential creates the file change a retained gateway must
observe. No timer or completed publication test is rerun. Back up changed state.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PREVIOUS = BASE / 'operator-evidence/candidate-renewal-zh_wxllg'
BATCH_SHA = 'f7ce4e8616a323dfecdfd02a5843811bb3812b06941ef7ac214e1de623440e3d'


def require(value):
    if not value:
        raise ValueError('candidate_live_reload_refused')


def accepted_finish(value):
    require(value.get('complete') is True and value.get('publication_replayed') is False
        and value.get('credentials_issued') == 0 and value.get('qualification_units_stopped') is True
        and value.get('candidate_scheduled_publication_component_qualified') is True
        and value.get('current_credential_authenticated') is True
        and value.get('renewed_profile_recovery_qualified') is True
        and value.get('all_admission_policies_preserved_disabled') is True
        and value.get('candidate_headless_gateway_reload_qualified') is False
        and value.get('journal_scheduling_proof',{}).get('verified') is True)


def accepted_reload(value, ident):
    require(isinstance(value,dict) and value.get('complete') is True and value.get('id') == ident
        and all(value.get(k) is True for k in ('retained_native_gateway','unchanged_agent_reused','renewed_agent_rebuilt',
            'candidate_token_bound','replacement_authenticated','settings_and_oauth_preserved'))
        and type(value.get('non_memory_network_attempts')) is int and value['non_memory_network_attempts'] == 0
        and value.get('chat_model_called') is False
        and type(value.get('platform_adapters_started')) is int and value['platform_adapters_started'] == 0)


def terminate(process):
    if process is None:
        return True
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=15)
        return process.poll() is not None
    except Exception:
        return False
    finally:
        for stream in (process.stdin,process.stdout):
            if stream is not None and not stream.closed:
                try:
                    stream.close()
                except OSError:
                    pass


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory = Path(__file__).parent
    path = directory / 'qualify_launch_candidate_renewal.py'
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BATCH_SHA)
    batch = {'__name__':'verified_candidate_reload_components','__file__':str(path)}
    exec(compile(raw,'<verified-reload-components>','exec'),batch)
    shared = batch['definitions'](directory / 'recover_launch_graph_operator.py',batch['SUPPORT_SHA'])
    read,write = shared['read_file'],shared['private_write']
    finished = json.loads(read(PREVIOUS / 'finish-publication.summary.json',0))
    accepted_finish(finished)
    modules = batch['components']()
    entry = batch['entry_policy'](modules)
    driver = modules['renew_fleet_credentials.py']
    require(hashlib.sha256((batch['ARTIFACT'] / path.name).read_bytes()).hexdigest() == BATCH_SHA)
    core = batch['scoped_core'](modules,entry)
    gateway = batch['definitions'](batch['ARTIFACT'] / 'qualify_launch_gateway_renewal_v2.py',batch['GATEWAY_SHA'])
    for target,digest in [(gateway['RELEASE'] / 'repo' / name,digest) for name,digest in gateway['NATIVE'].items()] + [
        (gateway['PROVIDER'] / name,digest) for name,digest in gateway['PROVIDER_FILES'].items()]:
        driver['protected'](target)
        require(hashlib.sha256(target.read_bytes()).hexdigest() == digest)
    for name,digest in batch['PINS'].items():
        driver['protected'](batch['PACKAGE'] / name)
    for target in (batch['BACKUPS'],Path('/usr/local/bin/age'),Path('/etc/enhanced-cognee/age-recovery-identity.txt')):
        driver['protected'](target)
    require(min(batch['shutil'].disk_usage(batch['BACKUPS']).free,batch['shutil'].disk_usage('/tmp').free) >= 128 * 1024 * 1024)
    helper = batch['definitions'](directory / 'qualify_launch_isolated_accounts.py',
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    policies = [batch['PACKAGE'] / 'candidate-policy.json',Path('/etc/enhanced-cognee/fleet-credentials.json')]
    before_policies = {p:read(p,0) for p in policies}
    require(all(row['enabled'] is False for data in before_policies.values()
        for row in modules['fleet_credential_policy.py']['validate'](json.loads(data))['profiles']))
    ident = uuid.uuid4().hex
    evidence = Path(tempfile.mkdtemp(prefix='candidate-live-reload-',dir=BASE / 'operator-evidence'))
    write(batch['PACKAGE'] / 'candidate-live-reload.started.json',json.dumps(dict(evidence=str(evidence))).encode())
    result = dict(complete=False,evidence=str(evidence),source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reused_scheduling_evidence=str(PREVIOUS / 'finish-publication.summary.json'),
        new_timers_created=0,credentials_issued=0,candidate_ordinary_credential_changed=False,
        private_keys_sent_to_owner=False,chat_model_called=False,platform_adapters_started=0,
        canonical_memory_edits=False,existing_launchers_changed=False,production_renewal_timer_enabled=False,
        installed_issuer_qualified=False,scheduled_renewal_qualified=False,actual_profile_admission_qualified=False,
        fleet_launch_approved=False)
    write(evidence / 'started.json',json.dumps(result).encode())
    retained = publisher = None
    phase = 'retained_gateway_preflight'
    try:
        retained = batch['child_process'](entry,'--gateway')
        retained.stdin.write(json.dumps(dict(entry=entry,id=ident)).encode() + b'\n')
        retained.stdin.flush()
        ready = batch['bounded_line'](retained,75)
        diagnostic = batch['failure_diagnostic'](ready)
        if diagnostic:
            result['gateway_failure'] = diagnostic
        require(ready == dict(ready=True,id=ident))
        phase = 'fresh_ordinary_credential'
        key = core['load_signing_key']()
        bundle = core['make_bundle'](key,int(time.time()))
        del key
        result['credentials_issued'] = 2
        ledger = evidence / 'root-ledger'
        ledger.mkdir(mode=0o700)
        driver['LEDGER'] = ledger
        root_id = entry['name'] + '-' + ident
        descriptor = core['open_directory'](ledger,{0})
        try:
            driver['ledger_write'](descriptor,root_id + '.started.json',dict(profile=entry['name'],state='started',source_hashes=driver['SOURCES']))
            driver['ledger_write'](descriptor,root_id + '.issued.json',dict(schema=1,profile=entry['name'],
                entry_sha256=driver['binding_digest'](entry),source_hashes=driver['SOURCES'],driver_sha256=batch['PINS']['renew_fleet_credentials.py'],
                issued_token_sha256=hashlib.sha256(bundle['token'].encode()).hexdigest()))
        finally:
            os.close(descriptor)
        phase = 'owner_credential_publication'
        publisher = batch['child_process'](entry,'--publish')
        output,_ = publisher.communicate(json.dumps(dict(entry=entry,bundle=bundle)).encode() + b'\n',timeout=90)
        if 0 < len(output) <= 4096:
            diagnostic = batch['failure_diagnostic'](json.loads(output))
            if diagnostic:
                result['owner_failure'] = diagnostic
        require(publisher.returncode == 0 and 0 < len(output) <= 4096)
        report = driver['receipt'](output)
        require(report['credential_published'] is True)
        result['candidate_ordinary_credential_changed'] = True
        write(ledger / (root_id + '.done.json'),json.dumps(report).encode())
        require(driver['attempt_closed'](core,entry,ledger / (root_id + '.started.json')))
        # Validate reload immediately. No timer-metadata parser or unrelated
        # evidence step can abort the retained gateway before this handshake.
        phase = 'retained_native_gateway_reload'
        retained.stdin.write(b'check\n')
        retained.stdin.flush()
        retained.stdin.close()
        observed = batch['bounded_line'](retained,75)
        write(evidence / 'gateway.receipt.json',json.dumps(observed).encode())
        diagnostic = batch['failure_diagnostic'](observed)
        if diagnostic:
            result['gateway_failure'] = diagnostic
        require(retained.wait(timeout=10) == 0)
        accepted_reload(observed,ident)
        result['candidate_headless_gateway_reload_qualified'] = True
        phase = 'changed_profile_recovery'
        result['generation'] = batch['fresh_backup'](entry,evidence,helper,read,write)
        require(all(read(p,0) == data for p,data in before_policies.items()))
        result.update(complete=True,renewed_profile_recovery_qualified=True,
            settings_and_oauth_preserved=True,all_admission_policies_preserved_disabled=True)
    except Exception:
        result.update(category='candidate_live_reload_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase)
    finally:
        publisher_stopped,retained_stopped = terminate(publisher),terminate(retained)
        result['qualification_processes_stopped'] = publisher_stopped and retained_stopped
        if not result['qualification_processes_stopped']:
            result.update(complete=False,category='candidate_live_reload_cleanup_incomplete_preserve_evidence')
    write(evidence / 'summary.json',json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"candidate_live_reload_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
