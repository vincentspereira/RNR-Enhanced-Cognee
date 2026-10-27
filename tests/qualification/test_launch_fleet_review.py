"""Disabled fleet issuer preparation and owner-only reference classifications."""
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
REVIEW = runpy.run_path(str(DIRECTORY / 'prepare_launch_fleet_review.py'), run_name='fleet_review_tests')
INSPECT = runpy.run_path(str(DIRECTORY / 'inspect_launch_main_references.py'), run_name='reference_tests')
POLICY = runpy.run_path(str(DIRECTORY / 'fleet_credential_policy.py'), run_name='review_policy_tests')
STAGE = runpy.run_path(str(DIRECTORY / 'stage_launch_candidate_issuer.py'), run_name='review_stage_tests')


def config():
    return dict(model=dict(provider='zai', default='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/coding/paas/v4'),
                gateway=dict(multiplex_profiles=True), mcp_servers={}, platforms={})


def test_config_reference_classification_never_returns_values_or_follows_targets(monkeypatch):
    value = config()
    secret = 'invented-credential-never-returned'
    value['mcp_servers'] = {'private-name-not-returned': dict(secret=secret, args=[
        '/home/vincentspereira/agent-workspace/invented', '/var/lib/invented/profile/workspace',
        '/opt/hermes-runtime/releases/invented', '~/workspace', '/var/unreviewed',
        '/mnt/c/private', 'C:\\private', '/home/vincentspereira/legal-social-frameworks'])}
    monkeypatch.setattr(Path, 'stat', lambda *a, **kw: pytest.fail('configured target followed'))
    monkeypatch.setattr(Path, 'lstat', lambda *a, **kw: pytest.fail('configured target followed'))
    result = INSPECT['classify'](value, Path('/var/lib/invented/profile'), Path('/home/vincentspereira'))
    assert result['reference_counts'] == dict(original_owner_home=1, restored_profile=1, pinned_runtime=1,
        other_absolute=1, home_relative=1, windows_path=2, excluded_project=1)
    assert result['unresolved_reference_count'] == 6 and result['configured_model_matches'] is True
    assert secret not in str(result) and 'private-name-not-returned' not in str(result)
    assert result['reference_coverage_qualified'] is False and result['profile_code_executed'] is False


@pytest.mark.parametrize('damage', ['cycle', 'depth', 'endpoint', 'schema'])
def test_reference_inspection_does_not_execute_or_silently_admit_unknown_config(damage):
    value = config()
    if damage == 'endpoint':
        value['model']['base_url'] = 'https://open.bigmodel.cn/api/paas/v4'
        assert INSPECT['classify'](value, Path('/invented'), Path('/home/vincentspereira'))['configured_model_matches'] is False
        return
    if damage == 'cycle': value['agent'] = value
    elif damage == 'depth':
        nested = value
        for _ in range(40): nested['next'] = {}; nested = nested['next']
    else: value['model'] = ['invalid']
    with pytest.raises(ValueError):
        INSPECT['classify'](value, Path('/invented'), Path('/home/vincentspereira'))


def inspection_fixture():
    result = INSPECT['classify'](config(), Path('/invented'), Path('/home/vincentspereira'))
    result.update(complete=True, source_files_written=False, model_called=False, credentials_issued=0,
                  fingerprints={'config.yaml': 'a' * 64})
    return result


@pytest.mark.parametrize('damage', [None, 'secret_extra', 'count', 'inconsistent', 'fingerprint', 'writes', 'admission'])
def test_root_validates_owner_receipt_before_retaining_it(damage):
    value = inspection_fixture()
    if damage == 'secret_extra': value['raw_config'] = 'invented-secret'
    elif damage == 'count': value['reference_counts']['windows_path'] = True
    elif damage == 'inconsistent': value['reference_counts']['other_absolute'] = 1
    elif damage == 'fingerprint': value['fingerprints']['config.yaml'] = 'not-a-digest'
    elif damage == 'writes': value['source_files_written'] = True
    elif damage == 'admission': value['reference_coverage_qualified'] = True
    if damage is None: REVIEW['validate_inspection'](value)
    else:
        with pytest.raises(ValueError): REVIEW['validate_inspection'](value)


def test_owner_file_read_refuses_links_and_private_file_permission_changes(tmp_path):
    original = tmp_path / 'original'
    original.write_bytes(b'invented-file')
    original.chmod(0o600)
    (tmp_path / 'auth.json').symlink_to(original)
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError): INSPECT['read_at'](directory, 'auth.json', os.geteuid())
        assert INSPECT['read_at'](directory, 'original', os.geteuid()) == b'invented-file'
        original.chmod(0o644)
        with pytest.raises(ValueError): INSPECT['read_at'](directory, 'original', os.geteuid())
    finally: os.close(directory)


def test_reference_inspection_reads_no_environment_or_oauth_file(tmp_path, monkeypatch):
    path = tmp_path / 'config.yaml'
    path.write_text(json.dumps(config()))
    path.chmod(0o600)
    (tmp_path / '.env').symlink_to('/invented/never-follow')
    names = []
    scope = INSPECT['inspect'].__globals__
    original = scope['read_at']
    def read_at(directory, name, uid):
        names.append(name)
        assert name == 'config.yaml'
        return original(directory, name, uid)
    monkeypatch.setitem(scope, 'read_at', read_at)
    monkeypatch.setitem(scope, 'open_profile', lambda *a: os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY))
    result = INSPECT['inspect'](tmp_path, os.geteuid())
    assert result['complete'] is True and names == ['config.yaml', 'config.yaml']
    assert set(result['fingerprints']) == {'config.yaml'}
    REVIEW['validate_inspection'](result)


def test_driver_rebinding_changes_only_two_fixed_package_paths():
    core, driver = STAGE['build_sources']((DIRECTORY / 'provision_pilot_access.py').read_bytes(),
        (DIRECTORY / 'renew_fleet_credentials.py').read_bytes(), (DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    assert hashlib.sha256(core).hexdigest() == REVIEW['COMPONENTS']['provision_pilot_access.py']
    assert hashlib.sha256(driver).hexdigest() == REVIEW['COMPONENTS']['renew_fleet_credentials.py']
    result = REVIEW['rebind_driver'](driver)
    old, new = ast.parse(driver), ast.parse(result)
    for tree in (old, new):
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {'POLICY', 'LEDGER'}:
                node.value = ast.Constant('package-path-only')
    assert ast.dump(old) == ast.dump(new)
    namespace = {'__name__': 'disabled_review_driver_test', '__file__': 'public-source-only'}
    exec(compile(result, '<review-driver-test>', 'exec'), namespace)
    assert namespace['POLICY'] == REVIEW['PACKAGE'] / 'candidate-policy.json'
    assert namespace['LEDGER'] == REVIEW['PACKAGE'] / 'root-ledger'
    with pytest.raises(ValueError): REVIEW['rebind_driver'](driver + b'\n')


def test_forty_real_binding_shapes_stay_disabled_without_invented_admission(monkeypatch):
    rows = []
    for i in range(40):
        ident = format(i, '016x')
        rows.append(dict(profile_id=ident, user='ecbot_' + ident, uid=2000 + i,
            home='/var/lib/enhanced-cognee-profiles/' + ident,
            scope=dict(sub='profile_' + ident, agent_id='profile_' + ident, tenant='qualification', project_id='p_' + ident,
                       roles=['api_client'], capture_policy='selected')))
    def module(path, digest):
        if path.name == 'qualify_launch_named_runtime.py': return {'selected': lambda read: rows}
        if path.name == 'stage_launch_candidate_issuer.py': return STAGE
        if path.name == 'fleet_credential_policy.py': return POLICY
        raise AssertionError('unexpected dependency')
    monkeypatch.setitem(REVIEW['stage_rows'].__globals__, 'definitions', module)
    monkeypatch.setattr(REVIEW['pwd'], 'getpwnam', lambda name: SimpleNamespace(
        pw_name=name, pw_uid=2000 + int(name[6:], 16), pw_dir='/var/lib/enhanced-cognee-profiles/' + name[6:]))
    result = REVIEW['stage_rows'](lambda *a: None, DIRECTORY)
    assert len(result['profiles']) == len({row['uid'] for row in result['profiles']}) == 40
    assert all(not row['enabled'] and not row['reload_qualified'] and not row['launch_binding_qualified'] for row in result['profiles'])
    assert all(row['backup_qualified'] and row['os_boundary_qualified'] for row in result['profiles'])
    result['profiles'][0]['enabled'] = True
    with pytest.raises(ValueError): POLICY['validate'](result)


def test_owner_packet_contains_only_path_mode_and_public_code(monkeypatch):
    seen = []
    def run(args, **kwargs):
        ast.parse(args[-1])
        seen.append(kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps(inspection_fixture()).encode())
    monkeypatch.setattr(REVIEW['subprocess'], 'run', run)
    helper = {'owner_program': lambda source: ('unused bootstrap', b'public code\n'), 'EXECUTABLE': '/invented/pinned/python'}
    account = SimpleNamespace(pw_uid=2001, pw_gid=2001, pw_dir='/invented/home')
    REVIEW['owner_inspection'](helper, b'public source', account, Path('/invented/home/profile'), 'restored')
    packet = json.loads(seen[0]['input'].split(b'\n', 1)[1])
    assert packet == dict(mode='restored', profile='/invented/home/profile')
    assert seen[0]['user'] == seen[0]['group'] == 2001 and seen[0]['extra_groups'] == ()
    assert not any('KEY' in key or 'TOKEN' in key for key in seen[0]['env'])


def test_owner_failure_retains_only_bounded_phase_class_and_errno(monkeypatch):
    private = 'invented-private-path-and-error-message'
    receipt = dict(complete=False, phase='directory_open', error_kind='PermissionError', errno=13,
                   message=private, arbitrary_key=private)
    monkeypatch.setattr(REVIEW['subprocess'], 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stdout=json.dumps(receipt).encode()))
    helper = {'owner_program': lambda source: ('bootstrap', b'public code\n'), 'EXECUTABLE': '/invented/python'}
    account = SimpleNamespace(pw_uid=2001, pw_gid=2001, pw_dir='/invented/home')
    with pytest.raises(ValueError) as failure:
        REVIEW['owner_inspection'](helper, b'public source', account, Path('/invented/home/profile'), 'restored')
    assert failure.value.owner_diagnostic == dict(mode='restored', phase='directory_open', error_kind='PermissionError', errno=13)
    assert private not in str(failure.value.owner_diagnostic)


def test_completed_review_is_returned_without_reissuing_or_reinspecting(monkeypatch,capsys):
    main = REVIEW['main']; scope = main.__globals__; events = []
    monkeypatch.setattr(REVIEW['os'], 'geteuid', lambda: 0)
    monkeypatch.setattr(REVIEW['os'].path, 'lexists', lambda *a: True)
    monkeypatch.setitem(scope, 'definitions', lambda *a: dict(read_file=lambda *a: b'{"complete":true,"credentials_issued":0}', private_write=object()))
    monkeypatch.setitem(scope, 'retained', lambda *a: events.append('unexpected repeat'))
    assert main() == 0 and events == []
    assert json.loads(capsys.readouterr().out)['credentials_issued'] == 0


def test_public_components_are_pinned_and_fit_owner_protocol():
    for name, digest in REVIEW['PINS'].items():
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((DIRECTORY / REVIEW['INSPECT_NAME']).read_bytes()).hexdigest() == REVIEW['INSPECT_SHA']
    helper = runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'), run_name='reference_protocol_test')
    helper['owner_program']((DIRECTORY / REVIEW['INSPECT_NAME']).read_bytes())
    controller = runpy.run_path(str(DIRECTORY / 'launch_control.py'), run_name='review_controller_pin')
    assert controller['FLEET_REVIEW_SHA'] == hashlib.sha256((DIRECTORY / 'prepare_launch_fleet_review.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('damage', [None, 'capture_replayed', 'named_incomplete', 'program_unqualified', 'source', 'context', 'active_unit'])
def test_retained_host_gates_need_matching_frozen_source_and_stopped_jobs(monkeypatch, damage):
    paths = {}
    for name, flags, artifact, filename in [
        ('MODEL', ('current_configured_model_native_capture_qualified', 'current_configured_model_fresh_process_recall_qualified',
                   'canonical_evidence_delivered', 'invented_record_retracted_history_preserved', 'peer_history_denied',
                   'post_retraction_delivery_ready', 'canonical_recall_withdrawn', 'retained_capture_reused'),
         'operator-model-recall-finish-v1', 'finish_launch_model_scope.py'),
        ('NAMED', ('all_admission_policies_preserved_disabled',), 'operator-named-runtime-explicit-route-v4', 'complete_launch_named_runtime.py'),
        ('MAIN', ('main_operational_snapshot_restore_qualified', 'database_snapshots_consistent'),
         'operator-main-operational-recovery-v2', 'continue_launch_main_operational.py'),
        ('PROGRAM', ('program_snapshot_restore_qualified', 'recovered_program_execution_qualified'),
         'operator-program-recovery-v1', 'qualify_launch_program_recovery.py')]:
        raw = (DIRECTORY / filename).read_bytes()
        value = dict(complete=True, source_revision=REVIEW['BASE'].name, operator_helper_sha256=hashlib.sha256(raw).hexdigest(), **dict.fromkeys(flags, True))
        if name == 'MODEL': value.update(capture_replayed=False, reused_capture_model_requests=3, original_failed_fixture_changed=False)
        if name == 'NAMED':
            value.pop('operator_helper_sha256')  # This original receipt has no such field.
            value.update(qualified_profiles=40, selected_profiles=40, candidate_restores_qualified=40, failed_profiles=0, unattempted_profiles=0)
        if damage == 'capture_replayed' and name == 'MODEL': value['capture_replayed'] = True
        if damage == 'named_incomplete' and name == 'NAMED': value['qualified_profiles'] = 39
        if damage == 'program_unqualified' and name == 'PROGRAM': value['recovered_program_execution_qualified'] = False
        paths[REVIEW[name] / 'summary.json'] = json.dumps(value).encode()
        context = {'evidence': str(REVIEW[name])}
        if damage == 'context' and name == 'MODEL': context['evidence'] = '/invented/unrelated'
        paths[REVIEW['BASE'] / artifact / 'context.json'] = json.dumps(context).encode()
        paths[REVIEW['BASE'] / artifact / filename] = b'changed-source' if damage == 'source' and name == 'MODEL' else raw
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda p: paths[p] if p in paths else original(p))
    monkeypatch.setitem(REVIEW['retained'].__globals__, 'stopped', lambda *a: damage != 'active_unit')
    if damage is None:
        assert set(REVIEW['retained'](lambda p, *args: paths[p])) == {'model', 'named', 'main', 'program'}
    else:
        with pytest.raises(ValueError): REVIEW['retained'](lambda p, *args: paths[p])


@pytest.mark.parametrize('owner_succeeds', [True, False])
def test_preparation_stages_only_disabled_policy_and_preserves_partial_work(tmp_path, monkeypatch, capsys, owner_succeeds):
    scope = REVIEW['main'].__globals__; package = tmp_path / 'package'; base = tmp_path / 'base'
    (base / 'operator-evidence').mkdir(parents=True)
    before = b'{"schema":1,"profiles":[{"enabled":false}]}'
    writes = {}; events = []
    _, driver = STAGE['build_sources']((DIRECTORY / 'provision_pilot_access.py').read_bytes(),
        (DIRECTORY / 'renew_fleet_credentials.py').read_bytes(), (DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    def write(path, raw):
        writes[path] = raw
        with path.open('xb') as stream: stream.write(raw)
    def definitions(path, digest):
        if path.name == 'recover_launch_graph_operator.py': return dict(read_file=lambda *a: before, private_write=write)
        return {'_verified_source_bytes': driver if path.name == 'renew_fleet_credentials.py' else b'public-source'}
    def main_refs(*args):
        events.append('owner_inspection')
        if not owner_succeeds: raise ValueError('invented-refusal')
        return dict(main_reference_inspection_complete=True, main_reference_coverage_qualified=False)
    def run(args, **kwargs):
        events.append('disabled_preflight')
        assert args[3] == str(package / 'renew_fleet_credentials.py')
        policy = json.loads(writes[package / 'candidate-policy.json'])
        assert all(row['enabled'] is False for row in policy['profiles'])
        return SimpleNamespace(returncode=0, stdout=b'{"complete":true,"enabled_profiles":0,"credentials_published":0}')
    monkeypatch.setattr(REVIEW['os'], 'geteuid', lambda: 0)
    monkeypatch.setattr(REVIEW['subprocess'], 'run', run)
    for name, value in dict(BASE=base, PACKAGE=package, definitions=definitions,
        retained=lambda read: events.append('reuse_passes'), stage_rows=lambda *a: json.loads(before),
        rebind_driver=lambda raw: raw, main_references=main_refs).items():
        monkeypatch.setitem(scope, name, value)
    assert REVIEW['main']() == (0 if owner_succeeds else 1)
    result = json.loads(capsys.readouterr().out)
    assert result['complete'] is owner_succeeds and result['credentials_issued'] == 0
    assert result['profiles_changed'] is False and result['services_changed'] is False
    assert result['all_admission_policies_preserved_disabled'] is True and result['fleet_launch_approved'] is False
    assert events == ['reuse_passes', 'disabled_preflight', 'owner_inspection']
    assert (package / 'candidate-policy.json').exists() and (package / 'summary.json').exists()
    assert package / 'root-ledger' not in writes
