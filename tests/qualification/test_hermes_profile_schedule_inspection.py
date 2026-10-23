"""Bounded private-log sanitization; installed journal/root identity are simulated."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS

import pytest

PATH = Path('integrations/hermes/deployment/inspect_profile_schedule.py')
INVOCATION = 'a' * 32


@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location('profile_schedule_inspection', PATH)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def failure(**changes):
    value = dict(complete=False, stage='profile_backup_only', failure_stage='restricted_snapshot',
        category='profile_backup_or_restore_incomplete_preserve_evidence', encrypted_backup_created=False,
        encrypted_backup='PRIVATE_PATH_NEVER_PRINTED', disposable_restore=None,
        restricted_diagnostics=dict(complete=False, phase='provider', category='permission_denied',
            checks=dict(archive_validated=None)), PRIVATE='RAW_SECRET')
    value.update(changes)
    return value


def journal(module, messages, invocation=INVOCATION, unit=None):
    return b'\n'.join(json.dumps(dict(_SYSTEMD_UNIT=unit or module.SERVICE,
        _SYSTEMD_INVOCATION_ID=invocation, MESSAGE=message)).encode() for message in messages)


@pytest.mark.parametrize('split', [False, True])
def test_failed_report_is_recovered_from_whole_or_split_stdout_without_private_fields(module, split):
    value = json.dumps(failure(), indent=2)
    raw = journal(module, value.splitlines() if split else [value])
    result = module.journal_report(raw, INVOCATION)
    assert result == dict(complete=False, stage='profile_backup_only', failure_stage='restricted_snapshot',
        encrypted_backup_created=False, restricted_phase='provider', restricted_category='permission_denied',
        checks=dict(archive_validated=None))
    assert 'PRIVATE' not in json.dumps(result) and 'RAW_SECRET' not in json.dumps(result)


@pytest.mark.parametrize('mutation', ['other-unit', 'other-invocation', 'raw-traceback', 'no-report'])
def test_unrelated_or_unstructured_logs_are_never_exposed(module, mutation):
    if mutation == 'other-unit': raw = journal(module, [json.dumps(failure())], unit='other.service')
    elif mutation == 'other-invocation': raw = journal(module, [json.dumps(failure())], invocation='b' * 32)
    else: raw = journal(module, ['PRIVATE_EXCEPTION_AND_SECRET'])
    assert module.journal_report(raw, INVOCATION) is None


@pytest.mark.parametrize('mutation', ['raw-size', 'entry-count', 'parse-count', 'bad-invocation', 'invalid-json'])
def test_log_and_parse_budgets_fail_closed(module, mutation):
    raw, invocation = journal(module, ['plain']), INVOCATION
    if mutation == 'raw-size': raw = b'x' * 524289
    if mutation == 'entry-count': raw = journal(module, ['plain'] * 161)
    if mutation == 'parse-count': raw = journal(module, ['{' * 257])
    if mutation == 'bad-invocation': invocation = 'unsafe/PRIVATE'
    if mutation == 'invalid-json': raw = b'PRIVATE_MALFORMED_LOG'
    with pytest.raises((module.InspectionError, ValueError)):
        module.journal_report(raw, invocation)


@pytest.mark.parametrize('mutation', ['stage', 'phase', 'category', 'complete', 'child-category', 'child-phase', 'checks'])
def test_only_allowlisted_failure_values_can_be_reported(module, mutation):
    value = failure()
    if mutation == 'stage': value['stage'] = 'PRIVATE'
    if mutation == 'phase': value['failure_stage'] = 'PRIVATE'
    if mutation == 'category': value['category'] = 'PRIVATE'
    if mutation == 'complete': value['complete'] = 1
    if mutation == 'child-category': value['restricted_diagnostics']['category'] = 'PRIVATE'
    if mutation == 'child-phase': value['restricted_diagnostics']['phase'] = 'PRIVATE'
    if mutation == 'checks': value['restricted_diagnostics']['checks'] = {'PRIVATE': 'SECRET', 'archive_validated': 1}
    result = module.safe_report(value)
    assert 'PRIVATE' not in json.dumps(result) and 'SECRET' not in json.dumps(result)
    if mutation in {'stage', 'phase', 'category', 'complete'}: assert result is None
    if mutation in {'child-category', 'child-phase'}: assert 'restricted_category' not in result
    if mutation == 'checks': assert result['checks'] == {}


def test_latest_allowlisted_report_wins_without_copying_other_messages(module):
    raw = journal(module, ['PRIVATE_TRACE', json.dumps(failure(failure_stage='operator_preflight')),
        json.dumps(failure(failure_stage='encrypted_snapshot'))])
    assert module.journal_report(raw, INVOCATION)['failure_stage'] == 'encrypted_snapshot'


def test_installed_expected_bytes_reconstruct_exact_published_bundle(module):
    # Explicit Git revision, not dict/set insertion order from an unverified tree.
    base = 'integrations/hermes/deployment/'
    names = [base + name for name in ('backup_pilot_profile.py', 'inspect_pilot_recovery.py', 'provision_pilot_access.py')]
    import io
    import tarfile
    raw = subprocess.check_output(['git', 'archive', 'd7c7880c692f9c90c1a4c84974835abf0fcb3e3a', *names])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        sources = {name: archive.extractfile(name).read() for name in names}
    backup = {'__name__': 'public_definitions'}
    exec(compile(sources[names[0]], '<published-public-backup>', 'exec'), backup)
    runner, program, service, timer = backup['schedule_payloads'](sources)
    assert runner == module.RUNNER
    for path, value in ((runner, program), (Path('/etc/systemd/system') / module.SERVICE, service),
                        (Path('/etc/systemd/system') / module.TIMER, timer)):
        _, size, expected = module.EXPECTED[path]
        assert len(value) == size and hashlib.sha256(value).hexdigest() == expected


@pytest.mark.parametrize('mutation', [None, 'missing-report', 'no-invocation', 'artifact-drift'])
def test_inspector_does_not_run_or_modify_any_service_or_read_credentials(module, monkeypatch, capsys, mutation):
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    monkeypatch.setattr(Path, 'read_text', lambda *a, **kw: 'systemd\n')
    monkeypatch.setattr(module, 'public_file', lambda *a: mutation != 'artifact-drift')
    calls = []
    def command(argv, **kwargs):
        calls.append(argv)
        assert 'start' not in argv and 'enable' not in argv and 'restart' not in argv
        assert 'cat' not in argv and not any('/etc/enhanced-cognee' in arg for arg in argv)
        if argv[0].endswith('journalctl'):
            assert '_SYSTEMD_INVOCATION_ID=' + INVOCATION in argv
            return journal(module, ['PRIVATE_EXCEPTION'] if mutation == 'missing-report' else [json.dumps(failure())])
        assert argv[:2] == ['/usr/bin/systemctl', 'show']
        if '--property=NoNewPrivileges' in argv:
            return b'NoNewPrivileges=yes\nPrivateNetwork=yes\nProtectHome=yes\nProtectSystem=strict\nCapabilityBoundingSet=cap_setgid cap_setuid\nDropInPaths=\n'
        if module.TIMER in argv: return b'ActiveState=inactive\nUnitFileState=disabled\n'
        invocation = '' if mutation == 'no-invocation' else INVOCATION
        return ('InvocationID=' + invocation + '\nResult=exit-code\nExecMainStatus=1\nActiveState=failed\nPRIVATE=SECRET\n').encode()
    monkeypatch.setattr(module, 'command', command)
    if mutation == 'no-invocation':
        with pytest.raises(SystemExit): module.main()
    else: module.main()
    output = capsys.readouterr().out
    assert 'PRIVATE' not in output and 'SECRET' not in output
    value = json.loads(output)
    assert value['complete'] is (mutation != 'no-invocation')
    assert not value['files_written'] and not value['credentials_read']
    assert not value['service_started_or_restarted'] and not value['timer_changed']
    if mutation != 'no-invocation':
        assert not value['timer_enabled'] and not value['timer_active']
        assert value['retained_backup_report_found'] is (mutation != 'missing-report')
        assert all(value['effective_policy'].values())
        assert all(value['published_artifacts'].values()) is (mutation != 'artifact-drift')


def test_operator_guard_stops_before_any_file_or_journal_read(module, monkeypatch, capsys):
    monkeypatch.setattr(module.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(module, 'command', lambda *a, **kw: pytest.fail('No journal access'))
    monkeypatch.setattr(module, 'public_file', lambda *a: pytest.fail('No file access'))
    with pytest.raises(SystemExit): module.main()
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


def test_upgraded_expected_artifacts_reconstruct_qualified_candidate(module):
    base = 'integrations/hermes/deployment/'
    sources = {base + name: subprocess.check_output(['git', 'show',
        '47b20e4d72df368f41e11f38a6741dcf2464a303:' + base + name]) for name in
        ('backup_pilot_profile.py', 'inspect_pilot_recovery.py', 'provision_pilot_access.py')}
    backup = {'__name__': 'published_definitions'}
    exec(compile(sources[base + 'backup_pilot_profile.py'], '<public-qualified-backup>', 'exec'), backup)
    runner, program, service, timer = backup['schedule_payloads'](sources)
    assert runner == module.UPGRADED_RUNNER
    for path, raw in ((runner, program), (Path('/etc/systemd/system') / module.SERVICE, service),
                      (Path('/etc/systemd/system') / module.TIMER, timer)):
        _, size, expected = module.UPGRADED_EXPECTED[path]
        assert len(raw) == size and hashlib.sha256(raw).hexdigest() == expected
    assert len(PATH.read_bytes()) <= 16384


def success():
    return dict(complete=True, stage='profile_backup_only', source_files=60, source_bytes=205571,
        signed_ciphertext_verified=True, decryption_tested=False, recovery_identity_read=False,
        plaintext_archive_written=False, model_called=False, memory_records_written=False,
        encrypted_backup='/var/backups/enhanced-cognee/hermes_profile_20261023T140000Z_1234abcd.tar.age')


@pytest.mark.parametrize('mutation', [None, 'missing-flag', 'invalid-path', 'files-bool', 'files-large', 'bytes-large', 'model-called'])
def test_complete_report_distinguished_from_upgrader_contract_and_private_values_removed(module, mutation):
    value = success()
    value['PRIVATE'] = 'SECRET'
    if mutation == 'missing-flag': value.pop('plaintext_archive_written')
    if mutation == 'invalid-path': value['encrypted_backup'] = '/PRIVATE/SECRET'
    if mutation == 'files-bool': value['source_files'] = True
    if mutation == 'files-large': value['source_files'] = 2049
    if mutation == 'bytes-large': value['source_bytes'] = 16777217
    if mutation == 'model-called': value['model_called'] = True
    result = module.safe_report(value)
    assert result['complete'] is True
    assert result['upgrade_completion_contract_passed'] is (mutation is None)
    assert 'PRIVATE' not in json.dumps(result) and 'SECRET' not in json.dumps(result)
    assert 'encrypted_backup' not in result


@pytest.mark.parametrize('count', [0, 1, 2])
def test_journal_diagnostics_distinguish_absent_and_duplicate_completed_reports(module, count):
    diagnostics = {}
    messages = ['PRIVATE_TRACE'] + [json.dumps(success(), indent=2)] * count
    raw = journal(module, messages)
    result = module.journal_report(raw, INVOCATION, diagnostics=diagnostics)
    assert (result is not None) is (count > 0)
    assert diagnostics == dict(matching_journal_messages=count + 1,
        allowlisted_backup_reports=count, upgrade_contract_completed_reports=count)
    assert 'PRIVATE' not in json.dumps(diagnostics)


@pytest.mark.parametrize('mutation', [None, 'failed-service', 'missing-report', 'wrong-runner', 'policy-drift', 'timer-active'])
def test_upgraded_inspection_reads_only_pinned_public_files_and_retained_status(module, monkeypatch, capsys, mutation):
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    monkeypatch.setattr(Path, 'read_text', lambda *a, **kw: 'systemd\n')
    inspected = []
    def public_file(path, size, expected):
        inspected.append(path)
        assert path in module.UPGRADED_EXPECTED
        return not (mutation == 'wrong-runner' and path == module.UPGRADED_RUNNER)
    monkeypatch.setattr(module, 'public_file', public_file)
    def command(argv, **kw):
        assert argv[0] in {'/usr/bin/systemctl', '/usr/bin/journalctl'}
        assert not {'start', 'stop', 'enable', 'restart', 'daemon-reload', 'cat'}.intersection(argv)
        assert not any('/etc/enhanced-cognee' in arg for arg in argv)
        if argv[0].endswith('journalctl'):
            value = failure(failure_stage='encrypted_snapshot') if mutation == 'failed-service' else success()
            return journal(module, ['PRIVATE_ERROR'] if mutation == 'missing-report' else [json.dumps(value)])
        assert argv[1] == 'show' and '--all' in argv
        if '--property=NoNewPrivileges' in argv:
            ambient = '' if mutation == 'policy-drift' else 'cap_setuid'
            return ('NoNewPrivileges=yes\nPrivateNetwork=yes\nProtectHome=yes\nProtectSystem=strict\n'
                'CapabilityBoundingSet=cap_setuid cap_setgid\nDropInPaths=\nAmbientCapabilities=' + ambient +
                '\nFragmentPath=/etc/systemd/system/' + module.SERVICE + '\n').encode()
        if module.TIMER in argv:
            return b'ActiveState=active\nUnitFileState=enabled\n' if mutation == 'timer-active' else b'ActiveState=inactive\nUnitFileState=disabled\n'
        return ('InvocationID=' + INVOCATION + '\nResult=' + ('exit-code' if mutation == 'failed-service' else 'success') +
            '\nExecMainStatus=' + ('1' if mutation == 'failed-service' else '0') + '\nActiveState=' +
            ('failed' if mutation == 'failed-service' else 'inactive') + '\nPRIVATE=SECRET\n').encode()
    monkeypatch.setattr(module, 'command', command)
    module.main(upgraded=True)
    text = capsys.readouterr().out
    result = json.loads(text)
    assert result['complete'] and result['reviewed_schedule'] == 'upgraded_ab8c990b'
    assert set(inspected) == set(module.UPGRADED_EXPECTED)
    assert not result['credentials_read'] and not result['files_written']
    assert not result['service_started_or_restarted'] and not result['timer_changed']
    assert result['timer_active'] is (mutation == 'timer-active')
    assert result['timer_enabled'] is (mutation == 'timer-active')
    if mutation == 'failed-service': assert result['retained_backup_report']['failure_stage'] == 'encrypted_snapshot'
    assert 'PRIVATE' not in text and 'SECRET' not in text


def test_upgraded_mode_must_be_boolean_before_any_file_access(module, monkeypatch, capsys):
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(module, 'public_file', lambda *a: pytest.fail('No file access'))
    with pytest.raises(SystemExit): module.main(upgraded='PRIVATE')
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'
