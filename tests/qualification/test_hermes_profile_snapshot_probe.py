"""Probe uses exact published code and bounded, sanitized synthetic launch outcomes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import io
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def probe():
    path = Path('integrations/hermes/deployment/probe_profile_snapshot.py')
    spec = importlib.util.spec_from_file_location('profile_snapshot_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def published(probe):
    names = sorted(probe.HASHES)
    raw = subprocess.check_output(['git', 'archive', 'd7c7880c692f9c90c1a4c84974835abf0fcb3e3a', *names])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        sources = {name: archive.extractfile(name).read() for name in names}
    namespace = {'__name__': 'published_definitions'}
    exec(compile(sources[probe.BASE + 'backup_pilot_profile.py'], '<public-backup>', 'exec'), namespace)
    runner, program, *_ = namespace['schedule_payloads'](sources)
    assert runner == probe.RUNNER
    return sources, program


def test_published_runner_is_parsed_as_literal_sources_without_execution(probe, published):
    sources, raw = published
    assert probe.verified_sources(raw) == sources
    assert hashlib.sha256(raw).hexdigest() == probe.RUNNER_HASH
    compiled = probe.program(sources)
    assert len(compiled.encode()) <= 120000
    compile(compiled, '<public-probe>', 'exec')
    assert 'backup_only=True' not in compiled[-len(probe.INSTRUMENT):]


@pytest.mark.parametrize('mutation', ['hash', 'size', 'type'])
def test_unknown_runner_rejected_before_ast_or_execution(probe, published, mutation):
    _, raw = published
    if mutation == 'hash': raw = raw[:-1] + b'x'
    if mutation == 'size': raw += b'PRIVATE'
    if mutation == 'type': raw = 'PRIVATE'
    with pytest.raises(probe.ProbeError): probe.verified_sources(raw)


@pytest.mark.parametrize('mutation', [None, 'permission', 'missing', 'too-long', 'timeout', 'stderr', 'budget', 'child-report', 'setgroups'])
def test_instrument_records_errno_and_exception_type_without_secret_values(probe, monkeypatch, capsys, mutation):
    class BackupError(RuntimeError): pass
    def original(argv, **kwargs):
        assert argv[:8] == ['/usr/bin/setpriv', '--reuid=993', '--regid=985', '--clear-groups',
            '--ambient-caps=-all', '--inh-caps=-all', '--no-new-privs', '--']
        assert not {'user', 'group', 'extra_groups'}.intersection(kwargs)
        if mutation == 'permission': raise PermissionError(13, 'PRIVATE_SECRET', '/private/filename')
        if mutation == 'missing': raise FileNotFoundError(2, 'PRIVATE_SECRET')
        if mutation == 'too-long': raise OSError(7, 'PRIVATE_SECRET')
        if mutation == 'timeout': raise subprocess.TimeoutExpired('PRIVATE_COMMAND', 90, output=b'PRIVATE')
        return NS(returncode=1 if mutation in {'stderr', 'child-report', 'setgroups'} else 0,
            stderr=b'PermissionError: [Errno 13] PRIVATE_KEY_AND_PATH\n' if mutation == 'stderr'
                else json.dumps(dict(complete=False, phase='source_snapshot', category='permission_denied', PRIVATE='SECRET')).encode() if mutation == 'child-report'
                else b'setpriv: setgroups failed: PRIVATE_SECRET\n' if mutation == 'setgroups' else b'',
            stdout=b'PRIVATE_PROFILE_BYTES_NEVER_PRINTED')
    monkeypatch.setattr(subprocess, 'run', original)
    monkeypatch.setattr(probe.pwd, 'getpwnam', lambda *a: NS(pw_uid=993, pw_dir='/var/lib/hermes-runtime'))
    def run_child(core, inspector, sources, account, mode):
        assert mode == 'snapshot'
        if mutation == 'budget': raise BackupError('child_program_budget')
        result = backup['subprocess'].run(['/public/child'], user=993, group=985, extra_groups=())
        if result.returncode: raise BackupError('restricted_child_refused')
        return result.stdout, dict(complete=True)
    backup = {'BackupError': BackupError, 'run_child': run_child, 'CHILD_PHASES': probe.CHILD_PHASES,
              'CHILD_CATEGORIES': probe.CHILD_CATEGORIES}
    exec(compile(probe.INSTRUMENT, '<probe-instrument>', 'exec'), dict(backup=backup, core={}, inspector={}, sources={}))
    output = capsys.readouterr().out
    assert 'PRIVATE' not in output and '/private/' not in output
    report = probe.safe_result(output.encode())
    assert report is not None and report['snapshot_completed'] is (mutation is None)
    if mutation == 'permission': assert report['popen_errno'] == 13 and report['exception_type'] == 'PermissionError'
    if mutation == 'missing': assert report['popen_errno'] == 2
    if mutation == 'too-long': assert report['popen_errno'] == 7
    if mutation == 'timeout': assert report['exception_type'] == 'TimeoutExpired'
    if mutation == 'stderr': assert report['stderr_errno'] == 13 and report['stderr_exception_type'] == 'PermissionError'
    if mutation == 'budget': assert report['failure_category'] == 'child_program_budget' and not report['launch_attempted']
    if mutation == 'child-report': assert report['child_phase'] == 'source_snapshot' and report['child_category'] == 'permission_denied'
    if mutation == 'setgroups': assert report['setpriv_failure_stage'] == 'setgroups'


@pytest.mark.parametrize('mutation', ['extra', 'private-exception', 'private-category', 'numeric-bool', 'range', 'raw', 'size'])
def test_probe_report_values_are_strictly_allowlisted(probe, mutation):
    value = dict.fromkeys(probe.FIELDS)
    value.update(dict.fromkeys(probe.FLAGS, False))
    if mutation == 'extra': value['PRIVATE'] = 'SECRET'
    if mutation == 'private-exception': value['exception_type'] = 'PRIVATE'
    if mutation == 'private-category': value['failure_category'] = 'PRIVATE'
    if mutation == 'numeric-bool': value['snapshot_completed'] = 1
    if mutation == 'range': value['popen_errno'] = 9999
    raw = json.dumps(value).encode()
    if mutation == 'raw': raw = b'PRIVATE_TRACEBACK'
    if mutation == 'size': raw = b'x' * 4097
    assert probe.safe_result(raw) is None


@pytest.mark.parametrize('mutation', [None, 'no-report', 'nonzero'])
def test_transient_probe_keeps_original_units_and_has_no_persistent_write_exception(probe, published, monkeypatch, capsys, mutation):
    _, raw = published
    monkeypatch.setattr(probe.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    monkeypatch.setattr(Path, 'read_text', lambda *a, **kw: 'systemd\n')
    monkeypatch.setattr(probe, 'read_runner', lambda: raw)
    value = dict.fromkeys(probe.FIELDS)
    value.update(dict.fromkeys(probe.FLAGS, False))
    def run(argv, **kwargs):
        assert argv[0] == '/usr/bin/systemd-run'
        assert '--collect' in argv and '--pipe' in argv and '--wait' in argv
        assert '--expand-environment=no' in argv
        assert '--property=ProtectSystem=strict' in argv and '--property=PrivateNetwork=yes' in argv
        assert '--property=CapabilityBoundingSet=CAP_SETUID CAP_SETGID' in argv
        assert '--property=AmbientCapabilities=CAP_SETUID' in argv
        assert '--property=NoNewPrivileges=yes' in argv
        assert not any('ReadWritePaths' in item for item in argv[:-1])
        assert kwargs['stdin'] is subprocess.DEVNULL and kwargs['close_fds'] is True
        assert len(argv[-1].encode()) <= 120000
        return NS(returncode=1 if mutation == 'nonzero' else 0,
            stdout=b'PRIVATE_STARTUP_TEXT' if mutation == 'no-report' else json.dumps(value).encode(), stderr=b'PRIVATE_MANAGER_TEXT')
    monkeypatch.setattr(probe.subprocess, 'run', run)
    if mutation == 'no-report':
        with pytest.raises(SystemExit): probe.main()
    else: probe.main()
    output = capsys.readouterr().out
    assert 'PRIVATE' not in output
    report = json.loads(output)
    assert report['complete'] is (mutation != 'no-report')
    assert not report['installed_job_rerun'] and not report['installed_units_changed']
    assert not report['backup_created'] and not report['service_signing_or_recovery_keys_read']
    assert report['candidate_parent_ambient_setuid_requested'] is True
    assert report['child_capability_clear_requested'] is True


def test_operator_guard_prevents_any_public_program_read_or_transient_launch(probe, monkeypatch, capsys):
    monkeypatch.setattr(probe.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(probe, 'read_runner', lambda: pytest.fail('No file read'))
    monkeypatch.setattr(probe.subprocess, 'run', lambda *a, **kw: pytest.fail('No transient launch'))
    with pytest.raises(SystemExit): probe.main()
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


def test_process_creation_is_distinguished_from_later_communication_error(probe, monkeypatch, capsys):
    class BackupError(RuntimeError): pass
    sentinel = object()
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: sentinel)
    def run(argv, **kwargs):
        assert subprocess.Popen(argv) is sentinel
        raise PermissionError(1, 'PRIVATE_CLEANUP_FAILURE')
    monkeypatch.setattr(subprocess, 'run', run)
    monkeypatch.setattr(probe.pwd, 'getpwnam', lambda *a: NS(pw_uid=993, pw_dir='/var/lib/hermes-runtime'))
    def child(core, inspector, sources, account, mode):
        return backup['subprocess'].run(['/public/child'], user=993, group=985, extra_groups=(), timeout=90)
    backup = {'BackupError': BackupError, 'run_child': child}
    exec(compile(probe.INSTRUMENT, '<tracked-process-probe>', 'exec'), dict(backup=backup, core={}, inspector={}, sources={}))
    output = capsys.readouterr().out
    assert 'PRIVATE' not in output
    report = probe.safe_result(output.encode())
    assert report['process_created'] is True and report['launch_returned'] is False
    assert report['exception_type'] == 'PermissionError' and report['popen_errno'] == 1
    assert not report['error_after_timeout_window']


def test_native_process_observation_works_without_root_or_profile_access(probe, monkeypatch, capsys):
    import os
    class BackupError(RuntimeError): pass
    before = (os.getuid(), os.getgid(), os.getgroups())
    uid, gid = os.getuid() or 65534, os.getgid() or 65534
    monkeypatch.setattr(probe.pwd, 'getpwnam', lambda *a: NS(pw_uid=uid, pw_dir='/var/lib/hermes-runtime'))
    def child(core, inspector, sources, account, mode):
        result = backup['subprocess'].run(['/usr/bin/true'], user=uid, group=gid, extra_groups=(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=5)
        if result.returncode: raise BackupError('restricted_child_refused')
        return b'', {}
    backup = {'BackupError': BackupError, 'run_child': child}
    exec(compile(probe.INSTRUMENT, '<native-process-observation>', 'exec'), dict(backup=backup, core={}, inspector={}, sources={}))
    output = capsys.readouterr().out
    report = probe.safe_result(output.encode())
    assert report['process_created'] is True and report['launch_returned'] is True
    assert report['child_exit_status'] is not None and report['popen_errno'] is None
    assert (os.getuid(), os.getgid(), os.getgroups()) == before


def test_native_explicit_capability_clear_runs_with_no_new_privileges():
    """Exercise the real tool flags as this ordinary user, without profile access.

    This validates CLI support and the no-capability result, not a privileged
    systemd/UID transition or removal of an initially nonzero capability set.
    """
    import os
    import sys
    before = (os.getuid(), os.getgid(), os.getgroups())
    code = """import json
from pathlib import Path
fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
print(json.dumps({key: fields[key].strip() for key in ('CapEff', 'CapAmb', 'CapInh', 'NoNewPrivs')}))
"""
    result = subprocess.run(['/usr/bin/setpriv', '--ambient-caps=-all', '--inh-caps=-all',
        '--no-new-privs', '--', sys.executable, '-I', '-B', '-c', code],
        cwd='/tmp', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, close_fds=True)
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout) == dict(CapEff='0000000000000000',
        CapAmb='0000000000000000', CapInh='0000000000000000', NoNewPrivs='1')
    assert (os.getuid(), os.getgid(), os.getgroups()) == before
