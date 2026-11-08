"""Stage the real named fleet's disabled issuer and inspect main references.

Use retained model/runtime/recovery passes. No credentials are issued, profile
settings changed, units installed or adapters started. This is preparation for
remaining qualification and owner review, not approval of a fleet switch.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import subprocess
import sys
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-named-fleet-issuer-review-v1'
PRIOR_PACKAGE = BASE / 'operator-isolated-issuer-candidate-v3'
MODEL = BASE / 'operator-evidence/model-recall-finish-fdu97vca'
NAMED = BASE / 'operator-evidence/named-runtime-routes-ivk3f5hw'
MAIN = BASE / 'operator-evidence/main-operational-recovery-0xjyrv2b'
PROGRAM = BASE / 'operator-evidence/program-recovery-l49l8f7u'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
INSPECT_NAME = 'inspect_launch_main_references.py'
INSPECT_SHA = '3c00d72c7479ab8e037f7c9fe63cf4b603ae84db797f0324a80d81f15f1343dc'
PINS = {
    'qualify_launch_named_runtime.py': 'd7494b5d7507322b5a0dd731211d3ef00c66122f90a7544961f06d9f75b6933f',
    'stage_launch_candidate_issuer.py': 'b12a126bd28c89097e96e2b7fc1e2a9189d41c9dbcc6a1baeebb7841404f37d6',
    'continue_launch_main_operational.py': '547e5bd40aec13c85b3524e15d5732adbfd59b507464182c47f760f7b20c3a25',
    'qualify_launch_isolated_accounts.py': 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94',
}
COMPONENTS = {
    'provision_pilot_access.py': 'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e',
    'renew_fleet_credentials.py': '945ed77d3791b7bdaefbabc79b7c6e146d4129aefbec881488472f6bffdbd77e',
    'renew_pilot_access.py': '8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567',
    'fleet_credential_policy.py': '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102',
    'fleet_credential_lifecycle.py': 'f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62',
}


def require(value):
    if not value:
        raise ValueError('fleet_review_preparation_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_fleet_review_support', '__file__': str(path), '_verified_source_bytes': raw}
    exec(compile(raw, '<verified-public-fleet-review>', 'exec'), namespace)
    return namespace


def stopped(unit):
    process = subprocess.run(['/usr/bin/systemctl', 'show', unit,
        '--property=ActiveState,MainPID,ControlPID'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=10, check=True)
    require(len(process.stdout) <= 4096)
    value = dict(line.split('=', 1) for line in process.stdout.decode().splitlines() if '=' in line)
    return value.get('ActiveState') in {'inactive', 'failed'} and value.get('MainPID') == value.get('ControlPID') == '0'


def retained(read):
    result = {}
    for label, path, digest, flags, unit, artifact, filename in [
        ('model', MODEL, 'ddf3b82e294b7b723463a82a66098fb6d52edd370f9fd1344696368b500a0123',
         ('current_configured_model_native_capture_qualified', 'current_configured_model_fresh_process_recall_qualified',
          'canonical_evidence_delivered', 'invented_record_retracted_history_preserved', 'peer_history_denied',
          'post_retraction_delivery_ready', 'canonical_recall_withdrawn', 'retained_capture_reused'),
         'ec-launch-model-recall-finish-20261027.service', 'operator-model-recall-finish-v1', 'finish_launch_model_scope.py'),
        ('named', NAMED, '6dbf807c3c4eb4cc9da1834fc3cfc13747f9b7a456997a0e66ce076e6b5fe625',
         ('all_admission_policies_preserved_disabled',), 'ec-launch-named-runtime-routes-20261026.service',
         'operator-named-runtime-explicit-route-v4', 'complete_launch_named_runtime.py'),
        ('main', MAIN, PINS['continue_launch_main_operational.py'],
         ('main_operational_snapshot_restore_qualified', 'database_snapshots_consistent'),
         'ec-launch-main-operational-recovery-20261027.service', 'operator-main-operational-recovery-v2', 'continue_launch_main_operational.py'),
        ('program', PROGRAM, 'cada57c71e6b651078401412f7cb93b750f5ac056375dde84b4573e8a35630f6',
         ('program_snapshot_restore_qualified', 'recovered_program_execution_qualified'),
         'ec-launch-program-recovery-20261027.service', 'operator-program-recovery-v1', 'qualify_launch_program_recovery.py')]:
        value = json.loads(read(path / 'summary.json', 0))
        require(value.get('complete') is True and value.get('source_revision') == BASE.name
                and (label == 'named' or value.get('operator_helper_sha256') == digest)
                and all(value.get(k) is True for k in flags) and stopped(unit))
        require(json.loads(read(BASE / artifact / 'context.json', 0)).get('evidence') == str(path)
                and hashlib.sha256((BASE / artifact / filename).read_bytes()).hexdigest() == digest)
        result[label] = value
    require(result['model'].get('capture_replayed') is False
            and result['model'].get('reused_capture_model_requests') == 3
            and result['model'].get('original_failed_fixture_changed') is False)
    require(result['named'].get('qualified_profiles') == result['named'].get('selected_profiles') == 40
            and result['named'].get('candidate_restores_qualified') == 40
            and result['named'].get('failed_profiles') == result['named'].get('unattempted_profiles') == 0)
    return result


def rebind_driver(raw):
    """Change only two fixed package paths in the already qualified driver."""
    require(hashlib.sha256(raw).hexdigest() == COMPONENTS['renew_fleet_credentials.py'])
    text = raw.decode('ascii')
    for field, suffix in [('POLICY', 'candidate-policy.json'), ('LEDGER', 'root-ledger')]:
        original = field + ' = Path(' + repr(str(PRIOR_PACKAGE / suffix)) + ')'
        replacement = field + ' = Path(' + repr(str(PACKAGE / suffix)) + ')'
        require(text.count(original) == 1)
        text = text.replace(original, replacement)
    encoded = text.encode('ascii')
    ast.parse(encoded)
    require(len(encoded) <= 65536)
    return encoded


def owner_inspection(helper, source, account, profile, mode):
    code, public = helper['owner_program'](source)
    # stderr is never retained. Owner failures cannot emit private exception text.
    code = ("import sys,json\nn={'__name__':'verified_reference_owner'}\n"
            "exec(compile(sys.stdin.buffer.readline(65537),'<verified-reference-owner>','exec'),n)\n"
            "try: n['child']()\n"
            "except Exception as e:\n"
            " k=type(e).__name__; p=n.get('PHASE','identity'); number=getattr(e,'errno',None)\n"
            " v={'complete':False,'phase':p if p in {'identity','directory_open','configuration_read','configuration_classification','configuration_preservation'} else 'other',"
            "'error_kind':k if k in {'ValueError','PermissionError','FileNotFoundError','OSError'} else 'other'}\n"
            " if type(number) is int and number in {1,2,13,20,30,40}: v['errno']=number\n"
            " print(json.dumps(v)); raise SystemExit(1)\n")
    packet = canonical(dict(profile=str(profile), mode=mode)) + b'\n'
    require(len(packet) <= 8192)
    result = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        input=public + packet, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30, cwd='/',
        user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(0 < len(result.stdout) <= 8192)
    value = json.loads(result.stdout)
    if result.returncode != 0 or not isinstance(value, dict) or value.get('complete') is not True:
        error = ValueError('owner_reference_inspection_refused')
        diagnostic = {'mode': mode}
        if isinstance(value, dict):
            for key, allowed in [('phase', {'identity', 'directory_open', 'configuration_read', 'configuration_classification', 'configuration_preservation'}),
                                 ('error_kind', {'ValueError', 'PermissionError', 'FileNotFoundError', 'OSError'})]:
                item = value.get(key)
                diagnostic[key] = item if isinstance(item, str) and item in allowed else 'other'
            if type(value.get('errno')) is int and value['errno'] in {1, 2, 13, 20, 30, 40}:
                diagnostic['errno'] = value['errno']
        error.owner_diagnostic = diagnostic
        raise error
    validate_inspection(value)
    return value


def validate_inspection(value):
    require(isinstance(value, dict) and set(value) == {
        'reference_counts', 'reference_sections', 'unresolved_reference_count', 'configured_model_matches',
        'enhanced_memory_selected', 'multiplex_enabled', 'mcp_definition_count', 'platform_definition_count',
        'reference_targets_followed', 'profile_code_executed', 'raw_values_returned', 'reference_coverage_qualified',
        'complete', 'fingerprints', 'source_files_written', 'model_called', 'credentials_issued'})
    require(value['complete'] is True and all(value[k] is False for k in
        ('reference_targets_followed', 'profile_code_executed', 'raw_values_returned', 'reference_coverage_qualified',
         'source_files_written', 'model_called')) and value['credentials_issued'] == 0)
    for name in ('configured_model_matches', 'enhanced_memory_selected', 'multiplex_enabled'):
        require(type(value[name]) is bool)
    for name in ('unresolved_reference_count', 'mcp_definition_count', 'platform_definition_count'):
        require(type(value[name]) is int and 0 <= value[name] <= 10000)
    kinds = {'original_owner_home', 'restored_profile', 'pinned_runtime', 'other_absolute',
             'home_relative', 'windows_path', 'excluded_project'}
    def counts(count):
        require(isinstance(count, dict) and set(count) == kinds
                and all(type(v) is int and 0 <= v <= 10000 for v in count.values()))
    counts(value['reference_counts'])
    require(isinstance(value['reference_sections'], dict) and set(value['reference_sections']) == {
        'model', 'memory', 'gateway', 'platforms', 'mcp_servers', 'browser', 'terminal', 'agent', 'other'})
    for count in value['reference_sections'].values():
        counts(count)
    require(all(sum(row[k] for row in value['reference_sections'].values()) == value['reference_counts'][k] for k in kinds)
            and value['unresolved_reference_count'] == sum(value['reference_counts'][k] for k in kinds - {'restored_profile', 'pinned_runtime'}))
    require(isinstance(value['fingerprints'], dict) and set(value['fingerprints']) == {'config.yaml'}
            and all(isinstance(v, str) and re.fullmatch('[a-f0-9]{64}', v) for v in value['fingerprints'].values()))


def stage_rows(read, directory):
    runtime = definitions(directory / 'qualify_launch_named_runtime.py', PINS['qualify_launch_named_runtime.py'])
    rows = runtime['selected'](read)
    stage = definitions(directory / 'stage_launch_candidate_issuer.py', PINS['stage_launch_candidate_issuer.py'])
    policy = definitions(PRIOR_PACKAGE / 'fleet_credential_policy.py', COMPONENTS['fleet_credential_policy.py'])
    entries = []
    for row in rows:
        account = pwd.getpwnam(row['user'])
        binding = dict(row, profile=str(Path(row['home']) / '.hermes'))
        entry = stage['policy_entry'](binding, account, policy)
        require(entry['enabled'] is False and entry['reload_qualified'] is False and entry['launch_binding_qualified'] is False)
        entries.append(entry)
    require(len(entries) == 40 and len({row['uid'] for row in entries}) == 40)
    return policy['validate'](dict(schema=1, profiles=entries))


def main_references(read, write, directory, evidence):
    main = definitions(directory / 'continue_launch_main_operational.py', PINS['continue_launch_main_operational.py'])
    _, original, target = main['selected'](read)
    restored = json.loads(read(MAIN / 'restore.private.json', 0))
    require(restored.get('complete') is True and isinstance(restored.get('receipt'), dict)
            and restored['receipt'].get('operational_restore_qualified') is True)
    destination = Path(restored['destination'])
    require(destination.parent == Path(target.pw_dir)
            and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}', destination.name))
    helper = definitions(directory / 'qualify_launch_isolated_accounts.py', PINS['qualify_launch_isolated_accounts.py'])
    inspector = definitions(directory / INSPECT_NAME, INSPECT_SHA)
    print('{"event":"inspect_main_source_configuration"}', flush=True)
    source = owner_inspection(helper, inspector['_verified_source_bytes'], original, Path(original.pw_dir) / '.hermes', 'source')
    write(evidence / 'main-source-reference.private.json', canonical(source))
    print('{"event":"inspect_restored_main_configuration"}', flush=True)
    copy = owner_inspection(helper, inspector['_verified_source_bytes'], target, destination, 'restored')
    write(evidence / 'main-restored-reference.private.json', canonical(copy))
    return dict(main_reference_inspection_complete=True,
        main_configuration_matches_retained_snapshot=source['fingerprints']['config.yaml'] == copy['fingerprints']['config.yaml'],
        main_restored_model_matches=copy['configured_model_matches'],
        main_restored_memory_selected=copy['enhanced_memory_selected'],
        main_restored_mcp_definitions=copy['mcp_definition_count'],
        main_restored_unresolved_references=copy['unresolved_reference_count'],
        main_reference_coverage_qualified=False)


def main():
    require(os.geteuid() == 0)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    directory = Path(__file__).parent
    support = definitions(directory / 'recover_launch_graph_operator.py', SUPPORT_SHA)
    read, write = support['read_file'], support['private_write']
    if os.path.lexists(PACKAGE):
        result = json.loads(read(PACKAGE / 'summary.json', 0))
        print(json.dumps(result), flush=True)
        return 0 if result.get('complete') is True else 1
    retained(read)
    policies = [Path('/etc/enhanced-cognee/fleet-credentials.json'), PRIOR_PACKAGE / 'candidate-policy.json']
    before = {path: read(path, 0) for path in policies}
    require(all(row['enabled'] is False for raw in before.values() for row in json.loads(raw)['profiles']))
    candidate = stage_rows(read, directory)
    sources = {name: definitions(PRIOR_PACKAGE / name, digest)['_verified_source_bytes'] for name, digest in COMPONENTS.items()}
    sources['renew_fleet_credentials.py'] = rebind_driver(sources['renew_fleet_credentials.py'])
    executed = globals().get('_verified_source_bytes')
    if executed is None:
        executed = Path(__file__).read_bytes()
    sources[Path(__file__).name] = executed
    sources[INSPECT_NAME] = definitions(directory / INSPECT_NAME, INSPECT_SHA)['_verified_source_bytes']
    evidence = Path(tempfile.mkdtemp(prefix='fleet-review-', dir=BASE / 'operator-evidence'))
    PACKAGE.mkdir(mode=0o755)
    PACKAGE.chmod(0o755)
    result = dict(complete=False, evidence=str(evidence), issuer_candidate=str(PACKAGE), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(executed).hexdigest(),
        credentials_issued=0, profiles_changed=False, signing_or_recovery_keys_read=False, services_changed=False,
        timers_created=0, source_profiles_changed=False, existing_launchers_changed=False,
        production_renewal_timer_enabled=False, actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(PACKAGE / 'started.json', canonical(result))
    phase = 'disabled_fleet_issuer_staging'
    try:
        for name, raw in sources.items():
            write(PACKAGE / name, raw)
            (PACKAGE / name).chmod(0o644)
        write(PACKAGE / 'candidate-policy.json', canonical(candidate))
        write(PACKAGE / 'sources.json', canonical({name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()}))
        process = subprocess.run(['/usr/bin/python3', '-I', '-B', str(PACKAGE / 'renew_fleet_credentials.py')],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, cwd='/',
            env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        require(process.returncode == 0 and 0 < len(process.stdout) <= 2048)
        probe = json.loads(process.stdout)
        require(probe.get('complete') is True and probe.get('enabled_profiles') == probe.get('credentials_published') == 0)
        write(evidence / 'disabled-issuer-preflight.json', canonical(probe))
        result.update(disabled_issuer_preflight_passed=True, staged_policy_entries=40, admitted_policy_entries=0,
                      distinct_runtime_uids=40, existing_qualification_bindings_deferred=2,
                      main_admission_deferred=True)
        phase = 'main_reference_inspection'
        result.update(main_references(read, write, directory, evidence))
        result['complete'] = True
    except Exception as error:
        result.update(category='fleet_review_preparation_incomplete_preserve_evidence_no_automatic_retry',
                      failure_phase=phase, error_kind=type(error).__name__ if type(error).__name__ in {
                          'ValueError', 'PermissionError', 'FileNotFoundError', 'TimeoutExpired'} else 'other')
        if isinstance(getattr(error, 'owner_diagnostic', None), dict):
            result['owner_diagnostic'] = error.owner_diagnostic
    require(all(read(path, 0) == raw for path, raw in before.items()))
    result['all_admission_policies_preserved_disabled'] = True
    write(evidence / 'summary.json', canonical(result))
    write(PACKAGE / 'summary.json', canonical(result))
    print(json.dumps(result), flush=True)
    return 0 if result['complete'] else 1
