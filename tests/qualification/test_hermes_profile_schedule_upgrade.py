"""Exact-source/update guards and real filesystem preservation; no host changes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def upgrade():
    path = Path('integrations/hermes/deployment/upgrade_profile_schedule.py')
    spec = importlib.util.spec_from_file_location('profile_upgrade', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sources(upgrade):
    return {name: subprocess.check_output(['git', 'show', '47b20e4d72df368f41e11f38a6741dcf2464a303:' + name]) for name in upgrade.HASHES}


def test_fixed_candidate_sources_match_published_pins_and_compile(upgrade, sources):
    core, inspector, backup = upgrade.definitions(sources)
    assert callable(core['read_private_at']) and callable(inspector['preflight'])
    runner, program, service, timer = backup['schedule_payloads'](sources)
    compile(program, '<published-candidate>', 'exec')
    assert b'AmbientCapabilities=CAP_SETUID\n' in service
    assert b'--ambient-caps=-all' in program and b'--inh-caps=-all' in program
    assert len(Path('integrations/hermes/deployment/upgrade_profile_schedule.py').read_bytes()) <= 24576
    with pytest.raises(upgrade.UpgradeError): upgrade.definitions(dict(sources, unexpected=b'PRIVATE'))
    sources[next(iter(sources))] += b'PRIVATE'
    with pytest.raises(upgrade.UpgradeError): upgrade.definitions(sources)


def completed():
    return dict(complete=True, stage='profile_backup_only', signed_ciphertext_verified=True,
        decryption_tested=False, recovery_identity_read=False, plaintext_archive_written=False,
        model_called=False, memory_records_written=False, source_files=60, source_bytes=205571,
        encrypted_backup='/var/backups/enhanced-cognee/hermes_profile_20261023T140000Z_1234abcd.tar.age')


def journal(upgrade, value, invocation='a' * 32):
    text = json.dumps(value, indent=2)
    return b'\n'.join(json.dumps(dict(_SYSTEMD_UNIT=upgrade.SERVICE,
        _SYSTEMD_INVOCATION_ID=invocation, MESSAGE=line)).encode() for line in text.splitlines())


@pytest.mark.parametrize('mutation', [None, 'failed', 'recovery-key', 'write', 'count-bool', 'path', 'wrong-invocation', 'duplicate', 'size', 'raw'])
def test_only_exact_invocation_completed_backup_admitted_without_private_output(upgrade, mutation):
    value = completed()
    if mutation == 'failed': value['complete'] = False
    if mutation == 'recovery-key': value['recovery_identity_read'] = True
    if mutation == 'write': value['memory_records_written'] = True
    if mutation == 'count-bool': value['source_files'] = True
    if mutation == 'path': value['encrypted_backup'] = '/private/SECRET'
    raw = journal(upgrade, value, 'b' * 32 if mutation == 'wrong-invocation' else 'a' * 32)
    if mutation == 'duplicate': raw += b'\n' + raw
    if mutation == 'size': raw = b'x' * 65537
    if mutation == 'raw': raw = b'PRIVATE_CREDENTIAL_ERROR'
    if mutation is None: assert upgrade.completed_report(raw, 'a' * 32) == value
    else:
        with pytest.raises((upgrade.UpgradeError, ValueError)): upgrade.completed_report(raw, 'a' * 32)


@pytest.fixture
def installation(upgrade, sources, tmp_path, monkeypatch):
    core, _, backup = upgrade.definitions(sources)
    root, units = tmp_path / 'opt', tmp_path / 'units'
    root.mkdir(); units.mkdir()
    old_runner = root / 'old/run.py'; old_runner.parent.mkdir()
    old_runner.write_bytes(b'OLD PUBLIC RUNNER')
    old_service, old_timer = units / upgrade.SERVICE, units / upgrade.TIMER
    old_service.write_bytes(b'OLD PUBLIC SERVICE')
    old_timer.write_bytes(b'OLD PUBLIC TIMER')
    old = {p: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()) for p in (old_runner, old_service, old_timer)}
    for key, value in dict(ROOT=root, UNITS=units, OLD_RUNNER=old_runner, OLD=old).items(): monkeypatch.setattr(upgrade, key, value)
    monkeypatch.setattr(upgrade.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes'); monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    read_text = Path.read_text
    monkeypatch.setattr(Path, 'read_text', lambda p, *a, **kw: 'systemd\n' if p == Path('/proc/1/comm') else read_text(p, *a, **kw))
    core['open_directory'] = lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    core['read_private_fd'] = lambda *a: (b'', None)
    monkeypatch.setattr(upgrade, 'public_file', lambda c, p: p.read_bytes())
    def read_at(directory, name, **kw):
        fd = os.open(name, os.O_RDONLY, dir_fd=directory)
        try: return os.read(fd, 262145)
        finally: os.close(fd)
    monkeypatch.setattr(upgrade, 'read_at', read_at)
    runner = root / 'new/run.py'
    backup['schedule_payloads'] = lambda s: (runner, b'NEW PUBLIC RUNNER', b'NEW PUBLIC SERVICE', b'OLD PUBLIC TIMER')
    calls, events, state = [], [], {'mutation': None}
    def command(argv, **kw):
        calls.append(argv)
        action = argv[1]
        mutation = state['mutation']
        if argv[0] == '/usr/bin/systemd-analyze':
            if mutation == 'validation': raise upgrade.UpgradeError('PRIVATE_VALIDATION')
            return b''
        if argv[0] == '/usr/bin/journalctl':
            return journal(upgrade, dict(completed(), complete=mutation != 'report'))
        if action == 'start':
            events.append('start')
            if mutation == 'start': raise upgrade.UpgradeError('PRIVATE_START')
            return b''
        if action == 'enable': events.append('enable'); return b''
        if action == 'is-enabled': return b'enabled\n'
        if action == 'is-active': return b'active\n'
        if '--property=NextElapseUSecRealtime' in argv: return b'n/a\n' if mutation == 'deadline' else b'next daily run\n'
        if '--property=FragmentPath' in argv:
            name = argv[2]
            value = dict(FragmentPath=str(units / name), DropInPaths='override' if mutation == 'dropin' else '',
                ActiveState='active' if mutation == 'active' else 'inactive',
                UnitFileState='static' if name == upgrade.SERVICE else 'enabled' if mutation == 'enabled' else 'disabled',
                Job='1 job' if mutation == 'job' else '')
        elif '--property=AmbientCapabilities' in argv:
            value = dict(AmbientCapabilities='' if mutation == 'policy' else 'cap_setuid',
                CapabilityBoundingSet='cap_setuid cap_setgid', NoNewPrivileges='yes', PrivateNetwork='yes')
        elif '--property=InvocationID' in argv:
            if '--property=Result' not in argv:
                value = dict(InvocationID='a' * 32 if mutation == 'stale-invocation' else 'b' * 32)
            else:
                value = dict(Result='exit-code' if mutation == 'result' else 'success', ExecMainStatus='0', ActiveState='inactive', InvocationID='a' * 32)
        else: return b''
        return ''.join(k + '=' + v + '\n' for k, v in value.items()).encode()
    backup['schedule_command'] = command
    monkeypatch.setattr(upgrade, 'definitions', lambda s: (core, {}, backup))
    def authenticate(*a):
        events.append('authenticate')
        if state['mutation'] == 'signature': raise upgrade.UpgradeError('PRIVATE_SIGNATURE')
    monkeypatch.setattr(upgrade, 'authenticate', authenticate)
    return root, units, old_runner, old_service, old_timer, calls, events, state


@pytest.mark.parametrize('mutation', [None, 'old-drift', 'dropin', 'active', 'enabled', 'job', 'validation', 'policy', 'start', 'result', 'stale-invocation', 'report', 'signature', 'deadline'])
def test_upgrade_preserves_originals_refuses_drift_and_enables_only_after_authenticated_run(upgrade, sources, installation, capsys, mutation):
    root, units, old_runner, service, timer, calls, events, state = installation
    state['mutation'] = mutation
    if mutation == 'old-drift': service.write_bytes(b'PRIVATE_CHANGED_UNIT')
    originals = {p: p.read_bytes() for p in (old_runner, service, timer)}
    if mutation:
        with pytest.raises(SystemExit): upgrade.main(sources)
    else: upgrade.main(sources)
    text = capsys.readouterr().out
    report = json.loads(text)
    assert 'PRIVATE' not in text and report['complete'] is (mutation is None)
    assert not report['model_called'] and not report['existing_database_schedule_changed']
    assert old_runner.read_bytes() == originals[old_runner] and timer.read_bytes() == originals[timer]
    if mutation in {'old-drift', 'dropin', 'active', 'enabled', 'job', 'validation'}:
        assert service.read_bytes() == originals[service] and 'start' not in events
    else:
        assert service.read_bytes() == b'NEW PUBLIC SERVICE'
        kept = Path(report['preserved_originals'])
        assert (kept / upgrade.SERVICE).read_bytes() == originals[service]
        assert (kept / 'old-runner.py').read_bytes() == originals[old_runner]
        assert stat.S_IMODE(kept.stat().st_mode) == 0o700
        assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in kept.iterdir())
    assert ('enable' in events) is (mutation in {None, 'deadline'})
    if 'enable' in events: assert events.index('start') < events.index('authenticate') < events.index('enable')
    if mutation is None:
        assert report['daily_profile_timer_active'] and report['signed_ciphertext_verified']
        assert not report['recovery_identity_read'] and not report['windows_collection_qualified']
        # A repeat must preserve the now-changed service rather than start again.
        with pytest.raises(SystemExit): upgrade.main(sources)
        assert events.count('start') == 1


def test_operator_guard_before_any_sources_or_schedule_access(upgrade, monkeypatch, capsys):
    monkeypatch.setattr(upgrade.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(upgrade, 'definitions', lambda s: pytest.fail('No source execution'))
    with pytest.raises(SystemExit): upgrade.main({})
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


def test_exclusive_publication_refuses_existing_file_and_keeps_original(upgrade, tmp_path):
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        upgrade.write_new(directory, 'kept', b'ORIGINAL', mode=0o600)
        with pytest.raises(FileExistsError): upgrade.write_new(directory, 'kept', b'REPLACEMENT')
        assert (tmp_path / 'kept').read_bytes() == b'ORIGINAL'
        assert stat.S_IMODE((tmp_path / 'kept').stat().st_mode) == 0o600
    finally: os.close(directory)


@pytest.mark.parametrize('mutation', [None, 'signature', 'ciphertext', 'counts'])
def test_authenticate_checks_actual_hmac_ciphertext_and_report_counts(upgrade, sources, tmp_path, monkeypatch, mutation):
    core, _, backup = upgrade.definitions(sources)
    backup_root, config_root = tmp_path / 'backups', tmp_path / 'config'
    backup_root.mkdir(mode=0o700); config_root.mkdir(mode=0o700)
    report = completed()
    name = Path(report['encrypted_backup']).name
    # The published verifier validates the encrypted envelope/hash/HMAC without
    # decrypting; native age encryption/restore is covered by the existing suite.
    cipher = b'age-encryption.org/v1\nSYNTHETIC_CIPHERTEXT'
    key = 'K' * 32
    manifest = dict(format=backup['FORMAT'], complete=True, signing_key_id='test',
        ciphertext_sha256=hashlib.sha256(cipher).hexdigest(), source_files=60, source_bytes=205571)
    manifest['signature'] = backup['signature'](manifest, key.encode())
    if mutation == 'signature': manifest['signature'] = '0' * 64
    if mutation == 'ciphertext': cipher += b'MODIFIED'
    if mutation == 'counts': report['source_files'] += 1
    (backup_root / name).write_bytes(cipher); (backup_root / name).chmod(0o600)
    (backup_root / (name + '.json')).write_text(json.dumps(manifest))
    (config_root / 'backup.json').write_text(json.dumps(dict(ENHANCED_BACKUP_SIGNING_KEY=key, ENHANCED_BACKUP_SIGNING_KEY_ID='test')))
    opened = []
    def directory(path, owners):
        opened.append(path)
        return os.open(config_root if path == Path('/etc/enhanced-cognee') else path, os.O_RDONLY | os.O_DIRECTORY)
    def private(directory, name, owner):
        assert name in {'backup.json', Path(report['encrypted_backup']).name + '.json'}
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try: return os.read(fd, 65536), None
        finally: os.close(fd)
    core['open_directory'], core['read_private_at'] = directory, private
    backup['DESTINATION'] = backup_root
    real_fstat = os.fstat
    def root_metadata(fd):
        info = real_fstat(fd)
        return NS(**{name: (0 if name == 'st_uid' else getattr(info, name)) for name in
            ('st_dev', 'st_ino', 'st_uid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')})
    monkeypatch.setattr(os, 'fstat', root_metadata)
    if mutation:
        with pytest.raises((upgrade.UpgradeError, backup['BackupError'])): upgrade.authenticate(core, backup, report)
    else: upgrade.authenticate(core, backup, report)
    assert opened == [Path('/etc/enhanced-cognee'), backup_root]


@pytest.mark.parametrize('mutation', [None, 'writable', 'hardlink', 'symlink', 'budget'])
def test_public_file_metadata_and_no_follow_guards(upgrade, tmp_path, monkeypatch, mutation):
    path = tmp_path / 'public'; path.write_bytes(b'PUBLIC')
    if mutation == 'writable': path.chmod(0o666)
    if mutation == 'hardlink': os.link(path, tmp_path / 'alias')
    if mutation == 'symlink':
        (tmp_path / 'link').symlink_to(path)
        path = tmp_path / 'link'
    real = os.fstat
    def root_owned(fd):
        info = real(fd)
        return NS(**{key: (0 if key == 'st_uid' else getattr(info, key)) for key in
            ('st_dev', 'st_ino', 'st_uid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')})
    monkeypatch.setattr(os, 'fstat', root_owned)
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if mutation:
            with pytest.raises((upgrade.UpgradeError, OSError)):
                upgrade.read_at(directory, path.name, limit=1 if mutation == 'budget' else 262144)
        else: assert upgrade.read_at(directory, path.name) == b'PUBLIC'
    finally: os.close(directory)


def test_original_artifact_hashes_match_exact_historical_installer(upgrade):
    import io
    import tarfile
    names = sorted(upgrade.HASHES)
    raw = subprocess.check_output(['git', 'archive', 'd7c7880c692f9c90c1a4c84974835abf0fcb3e3a', *names])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        sources = {name: archive.extractfile(name).read() for name in names}
    namespace = {'__name__': 'historical_public_definitions'}
    exec(compile(sources[upgrade.BASE + 'backup_pilot_profile.py'], '<historical-installer>', 'exec'), namespace)
    runner, program, service, timer = namespace['schedule_payloads'](sources)
    assert runner == upgrade.OLD_RUNNER
    for path, value in ((runner, program), (upgrade.UNITS / upgrade.SERVICE, service), (upgrade.UNITS / upgrade.TIMER, timer)):
        assert (len(value), hashlib.sha256(value).hexdigest()) == upgrade.OLD[path]


def rooted_journal(upgrade, runner, report=None, *, timestamp=2000000000, **changes):
    value = dict(_SYSTEMD_UNIT=upgrade.SERVICE, _SYSTEMD_INVOCATION_ID='a' * 32,
        _UID='0', _CMDLINE='/usr/bin/python3 -I -B ' + str(runner),
        __REALTIME_TIMESTAMP=str(timestamp), MESSAGE=json.dumps(report or completed(), indent=2))
    value.update(changes)
    return json.dumps(value).encode()


@pytest.mark.parametrize('mutation', [None, 'uid', 'cmdline', 'time', 'timestamp-type', 'message-spoof',
    'later-unbound', 'duplicate', 'incomplete', 'size'])
def test_retained_admission_requires_latest_root_runner_metadata_after_publication(upgrade, mutation):
    runner = upgrade.ROOT / 'a1ffd4c258238847/run.py'
    changes = {}
    if mutation == 'uid': changes['_UID'] = '993'
    if mutation == 'cmdline': changes['_CMDLINE'] = '/usr/bin/python3 -I -B /old/run.py'
    if mutation == 'time': changes['__REALTIME_TIMESTAMP'] = '999'
    if mutation == 'timestamp-type': changes['__REALTIME_TIMESTAMP'] = ['PRIVATE']
    if mutation == 'message-spoof': changes.update(_UID='993', MESSAGE=json.dumps(dict(completed(), _UID='0', _CMDLINE='/usr/bin/python3 -I -B ' + str(runner))))
    report = dict(completed(), complete=False) if mutation == 'incomplete' else completed()
    raw = rooted_journal(upgrade, runner, report, **changes)
    if mutation == 'later-unbound': raw += b'\n' + rooted_journal(upgrade, runner, _SYSTEMD_INVOCATION_ID='b' * 32, _CMDLINE='PRIVATE_OTHER_RUNNER')
    if mutation == 'duplicate': raw += b'\n' + raw
    if mutation == 'size': raw = b'x' * 65537
    if mutation:
        with pytest.raises(upgrade.UpgradeError): upgrade.bound_retained_report(raw, runner, 1000000)
    else: assert upgrade.bound_retained_report(raw, runner, 1000000) == completed()


@pytest.mark.parametrize('mutation', [None, 'preserved-drift', 'preserved-mode', 'service-drift',
    'policy', 'enabled', 'binding', 'signature', 'manifest-old', 'manifest-future', 'post-auth-drift', 'deadline'])
def test_resume_authenticates_existing_generation_before_timer_without_starting_or_replacing_service(
    upgrade, sources, installation, monkeypatch, capsys, mutation):
    import datetime
    root, units, old_runner, service, timer, calls, events, state = installation
    core, _, backup = upgrade.definitions(sources)
    preserved = root / 'before-approved'
    preserved.mkdir(mode=0o700)
    monkeypatch.setattr(upgrade, 'PRESERVED', preserved)
    old_bytes = {path: path.read_bytes() for path in upgrade.OLD}
    for path, raw in old_bytes.items():
        p = preserved / ('old-runner.py' if path == old_runner else path.name)
        p.write_bytes(raw); p.chmod(0o600)
    (root / '.schedule-upgrade.lock').write_bytes(b''); (root / '.schedule-upgrade.lock').chmod(0o600)
    runner, program, service_bytes, timer_bytes = backup['schedule_payloads'](sources)
    runner.parent.mkdir(); runner.write_bytes(program)
    service.write_bytes(service_bytes)
    backup_root = root / 'backups'; backup_root.mkdir(mode=0o700)
    backup['DESTINATION'] = backup_root
    created = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if mutation == 'manifest-old': created = '2000-01-01T00:00:00+00:00'
    if mutation == 'manifest-future': created = '2999-01-01T00:00:00+00:00'
    def read_private(directory, name, uid):
        assert name == Path(completed()['encrypted_backup']).name + '.json'
        return json.dumps(dict(created_utc=created)).encode(), None
    core['read_private_at'] = read_private
    original_command = backup['schedule_command']
    def command(argv, **kw):
        if argv[0] == '/usr/bin/journalctl':
            calls.append(argv)
            return rooted_journal(upgrade, runner, timestamp=service.stat().st_mtime_ns // 1000 + 1000,
                _UID='993' if mutation == 'binding' else '0')
        raw = original_command(argv, **kw)
        if '--property=ProtectHome' in argv: raw += b'ProtectHome=yes\nProtectSystem=strict\n'
        return raw
    backup['schedule_command'] = command
    state['mutation'] = mutation
    if mutation == 'preserved-drift': (preserved / 'old-runner.py').write_bytes(b'PRIVATE_OLD_MODIFIED')
    if mutation == 'preserved-mode': (preserved / 'old-runner.py').chmod(0o644)
    if mutation == 'service-drift': service.write_bytes(b'PRIVATE_SERVICE_CHANGED')
    original_auth = upgrade.authenticate
    def authenticate(*a):
        original_auth(*a)
        if mutation == 'post-auth-drift': service.write_bytes(b'PRIVATE_NEW_UNIT')
    monkeypatch.setattr(upgrade, 'authenticate', authenticate)
    before = {p: p.read_bytes() for p in (runner, service, timer, old_runner)}
    if mutation:
        with pytest.raises(SystemExit): upgrade.main_resume(sources)
    else: upgrade.main_resume(sources)
    text = capsys.readouterr().out; result = json.loads(text)
    assert 'PRIVATE' not in text
    assert result['complete'] is (mutation is None)
    assert not result['new_backup_manually_started'] and not result['recovery_identity_read']
    assert not result['existing_database_schedule_changed'] and not result['model_called']
    assert all('start' not in argv and 'restart' not in argv and 'daemon-reload' not in argv for argv in calls)
    assert ('enable' in events) is (mutation in {None, 'deadline'})
    for p, raw in before.items():
        if mutation == 'post-auth-drift' and p == service: continue
        assert p.read_bytes() == raw
    if 'enable' in events: assert events.index('authenticate') < events.index('enable')
    if mutation is None:
        assert result['retained_upgraded_runner_binding_verified'] and result['signed_ciphertext_verified']
        assert result['daily_profile_timer_enabled'] and result['daily_profile_timer_active']
        assert result['scheduled_catchup_may_run'] and not result['decryption_tested']
    if mutation in {'manifest-old', 'manifest-future'}:
        assert result['category'] == 'signed_generation_predates_service_publication'
        assert result['signed_ciphertext_verified']


def test_resume_operator_guard_precedes_source_execution(upgrade, monkeypatch, capsys):
    monkeypatch.setattr(upgrade.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(upgrade, 'definitions', lambda s: pytest.fail('No source execution'))
    with pytest.raises(SystemExit): upgrade.main_resume({})
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'
