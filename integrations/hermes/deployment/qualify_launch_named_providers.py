"""One provider/API/recovery batch for new private named-profile scopes.

Preserve the qualified first candidate. Defer the retained existing binding
rather than widening/replacing it. Never start chat, gateways or bot adapters.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import sys
import tempfile
import time
import uuid
import subprocess

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
STAGED = BASE / 'operator-evidence/named-fleet-stage-funaka9d'
PLAN = BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json'
PLAN_SHA = 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b'
PROVIDER_SHA = 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67'
BATCH_SHA = 'f7ce4e8616a323dfecdfd02a5843811bb3812b06941ef7ac214e1de623440e3d'


def require(value):
    if not value:
        raise ValueError('named_provider_batch_refused')


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__':'verified_named_provider_support','__file__':str(path)}
    exec(compile(raw,'<verified-public-support>','exec'),namespace)
    return namespace


def selection(plans,records,provider):
    require(isinstance(records,list) and len(records) == 41
        and len({row['profile_id'] for row in records}) == 41)
    selected,deferred = [],[]
    for record in records:
        matches = [plan for plan in plans if plan['profile_id'] == record['profile_id']]
        require(len(matches) == 1)
        plan = matches[0]
        require(plan['enabled'] is False and plan['source_user'] == 'vincentspereira'
            and Path(plan['source_profile']).parent == Path('/home/vincentspereira/.hermes/profiles')
            and record.get('paired_os_boundary_qualified') is True
            and record.get('complete') is True and record.get('profile_started') is False
            and record['user'] == plan['proposed_user'] and record['home'] == plan['proposed_home'])
        if plan['existing_binding'] is not None:
            deferred.append(dict(profile_id=record['profile_id'],reason='existing_binding_non_widening_admission_pending'))
        else:
            selected.append((record,provider['scope_binding'](plan)))
    # The pinned inventory has three existing bindings overall. Account for
    # their actual placement rather than guessing which named homes hold them.
    require(38 <= len(selected) <= 41 and 0 <= len(deferred) <= 3
        and len(selected) + len(deferred) == 41)
    require(len({(scope['tenant'],scope['project_id']) for _,scope in selected}) == len(selected))
    return selected,deferred


def verified_owner(value):
    require(value.get('complete') is True and value.get('candidate_modified') is True
        and value.get('ordinary_credential_published') is True
        and all(value.get(flag) is True for flag in ('native_profile_file_scope_bound','own_scoped_api_verified',
            'semantic_graph_verified','invented_probe_retracted_history_preserved','unrelated_settings_and_oauth_preserved'))
        and type(value.get('forbidden_network_attempts')) is int and value['forbidden_network_attempts'] == 0
        and value.get('chat_model_called') is False
        and type(value.get('gateways_started')) is int and value['gateways_started'] == 0)


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory = Path(__file__).parent
    provider = definitions(directory / 'prepare_launch_candidate_provider_v2.py',PROVIDER_SHA)
    batch = definitions(directory / 'qualify_launch_candidate_renewal.py',BATCH_SHA)
    shared = definitions(directory / 'recover_launch_graph_operator.py',batch['SUPPORT_SHA'])
    read,write = shared['read_file'],shared['private_write']
    accepted = json.loads(read(STAGED / 'summary.json',0))
    require(accepted.get('complete') is True and accepted.get('all_new_uids_distinct') is True
        and accepted.get('authenticated_candidate_copies_verified') is True
        and accepted.get('paired_os_boundaries_qualified') == 41 and accepted.get('inactive_candidates_staged') == 41
        and accepted.get('operator_helper_sha256') == '232db6a6f87705843816880e93995e6466578437e04f204cd6b2ac920006cdeb')
    raw_plan = read(PLAN,0)
    require(hashlib.sha256(raw_plan).hexdigest() == PLAN_SHA)
    records = [json.loads(read(path,0)) for path in STAGED.glob('*.candidate.private.json')]
    selected,deferred = selection(json.loads(raw_plan)['profiles'],records,provider)
    first = json.loads(read(BASE / 'operator-evidence/candidate-provider-f8uifc8j/binding.private.json',0))
    require(all(scope['project_id'] != first['scope']['project_id'] for _,scope in selected))
    helper = definitions(directory / 'qualify_launch_isolated_accounts.py',
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    issuer_path = directory / 'provision_pilot_access.py'
    issuer = definitions(issuer_path,provider['ISSUER_SHA'])
    source = (directory / 'prepare_launch_candidate_provider_v2.py').read_bytes()
    issuer_raw = issuer_path.read_bytes()
    network_raw = (directory / 'qualify_launch_gateway_renewal_v2.py').read_bytes()
    require(hashlib.sha256(source).hexdigest() == PROVIDER_SHA
        and hashlib.sha256(issuer_raw).hexdigest() == provider['ISSUER_SHA']
        and hashlib.sha256(network_raw).hexdigest() == provider['NETWORK_SHA'])
    network = definitions(directory / 'qualify_launch_gateway_renewal_v2.py',provider['NETWORK_SHA'])
    driver = definitions(batch['PACKAGE'] / 'renew_fleet_credentials.py',batch['PINS']['renew_fleet_credentials.py'])
    driver['protected'](Path(helper['EXECUTABLE']),final_link=True)
    driver['protected'](Path(helper['EXECUTABLE']).resolve())
    native = dict(network['NATIVE'],**{
        'agent/memory_provider.py':'ac81dcf489c698891f0edebfe26845a75c50d2bde77ec3be8d7938a85c79f1fc',
        'hermes_constants.py':'870ad9935a62968636d6a14d160c0269dfbefd8091ab3cb71be78b30bef6360f'})
    for path,digest in [(network['RELEASE'] / 'repo' / name,digest) for name,digest in native.items()] + [
        (network['PROVIDER'] / name,digest) for name,digest in network['PROVIDER_FILES'].items()]:
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    for path in (batch['BACKUPS'],Path('/usr/local/bin/age'),Path('/etc/enhanced-cognee/age-recovery-identity.txt')):
        driver['protected'](path)
    require(min(batch['shutil'].disk_usage(batch['BACKUPS']).free,batch['shutil'].disk_usage('/tmp').free) >= 512 * 1024 * 1024)
    accounts = {}
    for record,_ in selected:
        account = pwd.getpwnam(record['user'])
        require(account.pw_uid == record['uid'] and account.pw_dir == record['home']
            and account.pw_uid != 0 and account.pw_shell == '/usr/sbin/nologin'
            and os.getgrouplist(account.pw_name,account.pw_gid) == [account.pw_gid])
        accounts[record['profile_id']] = account
        require(not os.path.lexists(STAGED / (record['profile_id'] + '.provider.started.json')))
    code,line = helper['owner_program'](source)
    owner_code = provider['owner_launcher'](code)
    client_module = definitions(network['PROVIDER'] / 'client.py',provider['CLIENT_SHA'])
    policies = [batch['PACKAGE'] / 'candidate-policy.json',Path('/etc/enhanced-cognee/fleet-credentials.json')]
    before_policies = {p:read(p,0) for p in policies}
    policy = definitions(batch['PACKAGE'] / 'fleet_credential_policy.py',batch['PINS']['fleet_credential_policy.py'])
    require(all(row['enabled'] is False for raw in before_policies.values() for row in policy['validate'](json.loads(raw))['profiles']))
    evidence = Path(tempfile.mkdtemp(prefix='named-provider-batch-',dir=BASE / 'operator-evidence'))
    write(STAGED / 'new-private-provider-batch.started.json',json.dumps(dict(evidence=str(evidence))).encode())
    write(evidence / 'deferred.private.json',json.dumps(deferred).encode())
    result = dict(complete=False,evidence=str(evidence),source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),selected_profiles=len(selected),
        existing_binding_profiles_deferred=len(deferred),providers_qualified=0,peer_history_denials_qualified=0,
        encrypted_candidate_restores_qualified=0,qualification_credentials_issued=0,
        first_qualified_candidate_preserved=True,source_profiles_changed=False,private_keys_sent_to_owner=False,
        chat_model_called=False,gateways_started=0,units_installed=0,
        production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,fleet_launch_approved=False)
    write(evidence / 'started.json',json.dumps(result).encode())
    phase = 'owner_provider_qualification'
    try:
        for record,scope in selected:
            ident = record['profile_id']
            result['current_profile_id'] = ident
            account = accounts[ident]
            per_profile = evidence / ident
            per_profile.mkdir(mode=0o700)
            write(STAGED / (ident + '.provider.started.json'),json.dumps(dict(evidence=str(per_profile))).encode())
            issuer['IDENTITY'] = scope
            key = issuer['load_signing_key']()
            now,nonce = int(time.time()),uuid.uuid4().hex[:16]
            bundle = issuer['make_bundle'](key,now)
            peer_claims = dict(first['scope'],iat=now,exp=now+600)
            peer_token = issuer['sign_claims'](peer_claims,key)
            del key
            result['qualification_credentials_issued'] += 3
            write(per_profile / 'binding.private.json',json.dumps(dict(profile_id=ident,user=account.pw_name,
                uid=account.pw_uid,profile=str(Path(account.pw_dir)/'.hermes'),scope=scope,token_expires_at=bundle['claims']['exp'])).encode())
            packet = dict(uid=account.pw_uid,user=account.pw_name,home=account.pw_dir,candidate=record['candidate'],
                scope=scope,bundle=bundle,nonce=nonce,issuer_source=issuer_raw.decode(),network_source=network_raw.decode())
            raw = line + json.dumps(packet).encode() + b'\n'
            require(len(raw) <= 262144)
            phase = 'owner_provider_qualification'
            process = subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',owner_code],
                input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=210,cwd='/',user=account.pw_uid,
                group=account.pw_gid,extra_groups=(),env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
            require(process.returncode == 0 and 0 < len(process.stdout) <= 16384)
            value = json.loads(process.stdout)
            write(per_profile / 'owner-result.private.json',json.dumps(value).encode())
            if value.get('complete') is not True and value.get('checkpoint') in provider['PHASES']:
                result['owner_failure_phase'] = value['checkpoint']
            verified_owner(value)
            result['providers_qualified'] += 1
            phase = 'actual_peer_scope_history_denial'
            peer_client = client_module['MemoryClient']('http://127.0.0.1:28080',peer_token)
            status = peer_client.request('GET','/v1/memories/status')
            require(status.get('ready') is True and status.get('project_id') == peer_claims['project_id']
                and status.get('subject') == peer_claims['sub'])
            try:
                peer_client.request('GET','/v1/memories/' + value['record_id'] + '/history')
            except Exception as error:
                require(getattr(error,'status_code',None) == 404)
            else:
                raise ValueError('peer_history_boundary_failed')
            result['peer_history_denials_qualified'] += 1
            phase = 'configured_candidate_recovery'
            generation = batch['fresh_backup'](dict(user=account.pw_name,profile=str(Path(account.pw_dir)/'.hermes')),
                per_profile,helper,read,write)
            write(per_profile / 'summary.json',json.dumps(dict(complete=True,profile_id=ident,source_revision=BASE.name,
                candidate_provider_api_qualified=True,peer_history_denied=True,post_configuration_backup_qualified=True,
                generation=generation,invented_probe_retracted_history_preserved=True,
                actual_profile_admission_qualified=False,fleet_launch_approved=False)).encode())
            result['encrypted_candidate_restores_qualified'] += 1
        require(all(read(p,0) == raw for p,raw in before_policies.items()))
        result.pop('current_profile_id',None)
        result.update(complete=True,all_admission_policies_preserved_disabled=True)
    except Exception:
        result.update(category='named_provider_batch_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase)
    write(evidence / 'summary.json',json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"named_provider_preflight_refused_preserve_evidence"}')
        raise SystemExit(1)
