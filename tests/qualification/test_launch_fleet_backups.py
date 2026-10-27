"""Backup membership, signed readback, schedule proof and no-replay checks."""
import base64
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
MODULE = runpy.run_path(str(DIRECTORY / 'install_launch_fleet_backups.py'), run_name='daily_backup_tests')


def rows():
    return [dict(kind='main' if index == 41 else 'named', entry=dict(
        user='ecbot_' + format(index, '016x'), uid=2000+index, home='/var/lib/enhanced-cognee-profiles/' + format(index, '016x'),
        profile='/var/lib/enhanced-cognee-profiles/' + format(index, '016x') + '/.hermes', enabled=False)) for index in range(1, 42)]


def receipt():
    return dict(files=10, source_bytes=100, sqlite_databases=6, sidecars_rebuilt=0,
        database_versions_stable=True, plain_files_stable=True, plaintext_archive_written=False)


@pytest.mark.parametrize('tamper', [None, 'ciphertext', 'signature'])
def test_signed_generation_readback_detects_tamper_without_decrypting_or_removing(tmp_path, monkeypatch, tamper):
    monkeypatch.setitem(MODULE['save_generation'].__globals__, 'BACKUPS', tmp_path)
    def write(path, raw):
        with path.open('xb') as out: out.write(raw)
    def read(path, *args):
        raw = path.read_bytes()
        if tamper == 'ciphertext' and path.suffix == '.age': raw += b'changed'
        if tamper == 'signature' and path.suffix == '.json':
            value = json.loads(raw); value['signature'] = '0' * 64; raw = json.dumps(value).encode()
        return raw
    cipher = b'age-encryption.org/v1\ninvented-ciphertext-only'
    if tamper:
        with pytest.raises(ValueError): MODULE['save_generation'](rows()[0], cipher, receipt(), b'invented-hmac-key', 'invented', 'a'*32, read, write)
    else:
        result = MODULE['save_generation'](rows()[0], cipher, receipt(), b'invented-hmac-key', 'invented', 'a'*32, read, write)
        assert result['signed_ciphertext_verified'] is True
    assert len(list(tmp_path.iterdir())) == 2
    assert next(tmp_path.glob('*.age')).read_bytes() == cipher


@pytest.mark.parametrize('damage', [None, 'extra_field', 'plaintext', 'unstable', 'bad_cipher', 'bad_count'])
def test_strict_named_capture_receipt(damage):
    report = receipt(); cipher = b'age-encryption.org/v1\ninvented'
    value = dict(complete=True, receipt=report, ciphertext=base64.b64encode(cipher).decode())
    if damage == 'extra_field': value['unexpected'] = 'private-data-not-accepted'
    if damage == 'plaintext': report['plaintext_archive_written'] = True
    if damage == 'unstable': report['database_versions_stable'] = False
    if damage == 'bad_cipher': value['ciphertext'] = base64.b64encode(b'not-encrypted').decode()
    if damage == 'bad_count': report['sqlite_databases'] = True
    if damage:
        with pytest.raises(ValueError): MODULE['validate_named_capture'](value)
    else: assert MODULE['validate_named_capture'](value) == (cipher, report)


@pytest.mark.parametrize('failure', [None, 5])
def test_all_members_or_stop_first_failure_preserving_completed_checkpoints(tmp_path, monkeypatch, failure):
    scope = MODULE['execute'].__globals__; seen=[]; saved={}
    def capture(driver, row, recipient):
        seen.append(row['entry']['uid'])
        assert recipient == 'age1'+'a'*30
        if len(seen) == failure: raise ValueError('invented capture refusal')
        return b'invented-ciphertext', receipt()
    def generation(row, body, report, key, key_id, invocation, read, write):
        assert key == b'invented-'*8 and body == b'invented-ciphertext'
        return {'complete': True, 'profile_id': row['entry']['user'][6:]}
    monkeypatch.setitem(scope, 'capture', capture); monkeypatch.setitem(scope, 'save_generation', generation)
    monkeypatch.setattr(MODULE['shutil'], 'disk_usage', lambda path: SimpleNamespace(free=3*1024**3))
    read = lambda *a: json.dumps(dict(ENHANCED_BACKUP_RECIPIENT='age1'+'a'*30,
        ENHANCED_BACKUP_SIGNING_KEY='invented-'*8, ENHANCED_BACKUP_SIGNING_KEY_ID='invented')).encode()
    write = lambda path, raw: saved.update({path.name: json.loads(raw)})
    if failure:
        with pytest.raises(ValueError): MODULE['execute'](rows(), {}, read, write, tmp_path, 'a'*32)
        assert len(seen) == 5 and len([name for name in saved if name.startswith('completed-')]) == 4
    else:
        assert MODULE['execute'](rows(), {}, read, write, tmp_path, 'a'*32) == 41
        assert len(set(seen)) == 41


def test_service_units_bound_to_fixed_members_and_no_network_or_recovery_key():
    service, timer = MODULE['unit_text'](rows())
    assert b'RestrictAddressFamilies=AF_UNIX\n' in service and b'IPAddressDeny=any\n' in service
    assert b'CapabilityBoundingSet=CAP_SETUID CAP_SETGID\n' in service and b'ProtectHome=yes\n' in service
    assert b'InaccessiblePaths=/etc/enhanced-cognee/age-recovery-identity.txt' in service
    assert b'Restart=no\n' in service and b'OnActiveSec=15s\n' in timer and b'OnUnitActiveSec=1d\n' in timer
    assert b'WantedBy=timers.target\n' in timer and b'--worker' in service
    malformed = rows(); malformed[1]['entry']['home'] = malformed[0]['entry']['home']
    with pytest.raises(ValueError): MODULE['unit_text'](malformed)


@pytest.mark.parametrize('damage', [None, 'failed', 'missing_member', 'draft', 'admitted', 'wrong_revision'])
def test_only_actual_qualified_membership_is_admitted(monkeypatch, damage):
    members = rows(); main = members[-1]['entry']; named = [row['entry'] for row in members[:-1]]
    impl = dict(complete=True, phase='implementation', evidence=str(MODULE['IMPLEMENTATION']),
        source_revision=MODULE['BASE'].name, operator_helper_sha256=MODULE['V2_SHA'], operator_job_stopped=True,
        all_admission_policies_preserved_disabled=True, source_profiles_changed=False, existing_launchers_changed=False,
        chat_model_called=False, private_keys_sent_to_owner=False, fleet_launch_approved=False,
        main_candidate_backup_restore_qualified=True, candidate_backup_membership_count=41)
    qual = dict(impl, phase='qualification', evidence=str(MODULE['QUALIFICATION']), selected_profiles=40,
        qualified_profiles=40, failed_profiles=0, unattempted_profiles=0, named_post_renewal_restores_qualified=True,
        scheduled_candidate_fleet_publication_qualified=True, journal_scheduling_proof={'verified': True})
    draft = dict(schema=1, enabled=False, interval_seconds=86400, members=[dict(user=row['entry']['user'],
        uid=row['entry']['uid'], home=row['entry']['home'], profile=row['entry']['profile'],kind=row['kind'],admission_ready=False) for row in members])
    if damage == 'failed': qual['complete'] = False
    if damage == 'missing_member': qual['qualified_profiles'] = 39
    if damage == 'draft': draft['members'].pop()
    if damage == 'admitted': named[0]['enabled'] = True
    if damage == 'wrong_revision': qual['source_revision'] = 'invented-other-revision'
    def read(path, *args):
        if path.parent == MODULE['IMPLEMENTATION']: value=impl if path.name=='finish.summary.json' else draft
        elif path.parent == MODULE['QUALIFICATION']: value=qual
        else: value={'profiles': named}
        return json.dumps(value).encode()
    driver = dict(FLEET=Path('/invented-fleet'), fixed_entry=lambda read: (main, None),
        definitions=lambda *a: {'validate': lambda value: None})
    if damage:
        with pytest.raises(ValueError): MODULE['membership'](driver, read)
    else: assert MODULE['membership'](driver, read) == members


def test_completed_installation_never_starts_services_or_replays_backup(tmp_path, monkeypatch, capsys):
    (tmp_path / 'installed.summary.json').write_text('{}')
    monkeypatch.setitem(MODULE['watch'].__globals__, 'STATE', tmp_path)
    result = dict(complete=True, installed_daily_timer_enabled=True, scheduled_fleet_profile_backup_qualified=True)
    assert MODULE['watch']({}, lambda *a: json.dumps(result).encode(), lambda *a: pytest.fail('receipt rewritten')) == 0
    assert json.loads(capsys.readouterr().out) == result


def test_capture_only_and_installed_source_pins_match():
    assert hashlib.sha256((DIRECTORY/'launch_completion_batch_v2.py').read_bytes()).hexdigest() == MODULE['V2_SHA']
    assert hashlib.sha256((DIRECTORY/'recover_launch_graph_operator.py').read_bytes()).hexdigest() == MODULE['SUPPORT_SHA']
    controller = runpy.run_path(str(DIRECTORY/'launch_control.py'), run_name='fleet_backup_controller_pin')
    assert controller['FLEET_BACKUPS_SHA'] == hashlib.sha256((DIRECTORY/'install_launch_fleet_backups.py').read_bytes()).hexdigest()


def test_failed_worker_preserves_checkpoints_stops_timer_and_blocks_replay(tmp_path, monkeypatch):
    scope = MODULE['worker'].__globals__
    source = tmp_path / 'install_launch_fleet_backups.py'; source.write_bytes(b'invented-public-source')
    (tmp_path / 'members.private.json').write_text(json.dumps(rows()))
    monkeypatch.setitem(scope, 'STATE', tmp_path); monkeypatch.setitem(scope, '__file__', str(source))
    monkeypatch.setattr(MODULE['os'], 'geteuid', lambda: 0)
    real_fstat=MODULE['os'].fstat
    def fixture_fstat(fd):
        value=real_fstat(fd)
        if MODULE['os'].readlink('/proc/self/fd/'+str(fd)).endswith('/job.lock'):
            return SimpleNamespace(st_uid=0,st_nlink=value.st_nlink)
        return value
    monkeypatch.setattr(MODULE['os'], 'fstat', fixture_fstat)
    monkeypatch.setenv('INVOCATION_ID', 'a'*32)
    calls=[]
    monkeypatch.setattr(MODULE['subprocess'], 'run', lambda args, **kwargs: calls.append(args))
    read=lambda path, *a: path.read_bytes()
    def write(path, raw):
        with path.open('xb') as output: output.write(raw)
    driver={'policies': lambda read: {}}
    monkeypatch.setitem(scope, 'components', lambda: (driver, read, write))
    monkeypatch.setitem(scope, 'membership', lambda *a: rows())
    def execute(*args):
        evidence=args[-2]
        write(evidence/'completed-001.json', b'{"complete":true}')
        raise ValueError('invented-failure')
    monkeypatch.setitem(scope, 'execute', execute)
    assert MODULE['worker']() == 1
    assert calls == [['/usr/bin/systemctl', 'stop', MODULE['UNIT']+'.timer']]
    blocked=json.loads((tmp_path/'blocked.json').read_bytes())
    result=json.loads((Path(blocked['evidence'])/'summary.json').read_bytes())
    assert result['complete'] is False and result['completed_profiles']==1
    with pytest.raises(ValueError): MODULE['worker']()
    assert len(list(tmp_path.glob('run-*')))==1 and len(calls)==1


@pytest.mark.parametrize('proof_valid', [True, False])
def test_first_scheduled_run_requires_manager_proof_and_enabled_daily_timer(tmp_path, monkeypatch, proof_valid):
    scope=MODULE['watch'].__globals__; evidence=tmp_path/'run-invented'; evidence.mkdir()
    summary=dict(complete=True, invocation_id='a'*32, completed_profiles=41, fleet_launch_approved=False)
    (evidence/'summary.json').write_text(json.dumps(summary))
    (tmp_path/'first-run.private.json').write_text(json.dumps({'evidence':str(evidence)}))
    monkeypatch.setitem(scope, 'STATE', tmp_path)
    def write(path, raw):
        with path.open('xb') as out: out.write(raw)
    metadata=dict(Result='success',ExecMainStatus='0',User='root',InvocationID='')
    driver=dict(metadata=lambda unit: metadata, stopped=lambda value: True)
    monkeypatch.setattr(MODULE['subprocess'],'run',lambda *a,**kw: SimpleNamespace(stdout=b'{}\n'))
    observed=[]
    def proof(logs,unit,invocation):
        observed.append((logs,unit,invocation)); return {'verified':proof_valid}
    monkeypatch.setitem(scope,'definitions',lambda *a:{'journal_scheduling_proof':proof})
    monkeypatch.setitem(scope,'timer_properties',lambda:dict(LoadState='loaded',ActiveState='active',
        UnitFileState='enabled',Result='success',NextElapseUSecMonotonic='1d'))
    if proof_valid:
        assert MODULE['watch'](driver,lambda path,*a:path.read_bytes(),write)==0
        saved=json.loads((tmp_path/'installed.summary.json').read_bytes())
        assert saved['scheduled_fleet_profile_backup_qualified'] and saved['backup_interval_seconds']==86400
        assert saved['operator_job_stopped'] and saved['backup_service_remains_scheduled']
    else:
        with pytest.raises(ValueError): MODULE['watch'](driver,lambda path,*a:path.read_bytes(),write)
        assert not (tmp_path/'installed.summary.json').exists()
    assert observed==[([{}],MODULE['UNIT'],'a'*32)]
