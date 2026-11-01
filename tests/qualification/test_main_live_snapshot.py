"""Real invented backup boundaries; no installed profile or service is used."""
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
import sqlite3
import tarfile
import tempfile

import pytest

FOLDER = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
V4 = runpy.run_path(str(FOLDER / 'capture_main_operational_profile_v4.py'))


@pytest.fixture
def tmp_path():
    # Keep Unix socket addresses short; retain invented fixtures for review.
    return Path(tempfile.mkdtemp(prefix='ec-m4-'))


def fixture_profile(tmp_path):
    (tmp_path / 'telemetry').mkdir()
    (tmp_path / 'telemetry/enforcement_mode').write_bytes(b'observe\n')
    (tmp_path / 'telemetry/budget.yaml').write_bytes(b'invented_limit: 7\n')
    (tmp_path / 'config.yaml').write_bytes(b'invented_guard: enforce\n')
    with sqlite3.connect(tmp_path / 'state.db') as db:
        db.execute('CREATE TABLE invented(x)')
        db.execute('INSERT INTO invented VALUES (7)')


def mutate_at_database_open(monkeypatch, change):
    original = sqlite3.connect
    done = False

    def connect(*args, **kwargs):
        nonlocal done
        if 'mode=ro' in str(args[0]) and not done:
            done = True
            change()
        return original(*args, **kwargs)

    monkeypatch.setattr(sqlite3, 'connect', connect)


def test_atomic_display_rotation_preserves_actual_settings_and_sqlite(tmp_path, monkeypatch):
    fixture_profile(tmp_path)
    marker = tmp_path / 'telemetry/enforcement_mode'
    previous_inode = marker.stat().st_ino

    def rotate():
        stage = marker.with_name('.enforcement_mode.abcdefgh.tmp')
        stage.write_bytes(b'observe\n')
        os.replace(stage, marker)

    mutate_at_database_open(monkeypatch, rotate)
    archive, receipt = V4['capture'](tmp_path, online_databases=True)
    assert marker.stat().st_ino != previous_inode
    assert marker.read_bytes() == b'observe\n'
    destination, proof = V4['restore'](archive)
    target = Path(destination)
    assert not (target / 'telemetry/enforcement_mode').exists()
    assert (target / 'config.yaml').read_bytes() == b'invented_guard: enforce\n'
    assert (target / 'telemetry/budget.yaml').read_bytes() == b'invented_limit: 7\n'
    with sqlite3.connect(target / 'state.db') as db:
        assert db.execute('SELECT x FROM invented').fetchall() == [(7,)]
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        manifest = json.load(source.extractfile('profile-manifest.json'))
    assert manifest['omitted'] == [{'path': 'telemetry/enforcement_mode',
                                   'reason': 'live_process_coordination_not_restored'}]
    assert receipt['plain_files_stable'] and receipt['database_snapshots_consistent']
    assert proof['operational_restore_qualified']
    assert receipt['global_atomic_snapshot_qualified'] is False


@pytest.mark.parametrize('name', ['config.yaml', 'telemetry/budget.yaml',
                                'telemetry/another_policy', 'enforcement_mode'])
def test_durable_changes_remain_refused(tmp_path, monkeypatch, name):
    fixture_profile(tmp_path)
    target = tmp_path / name
    target.write_bytes(b'invented-before')
    mutate_at_database_open(monkeypatch, lambda: target.write_bytes(b'invented-after'))
    with pytest.raises(V4['CaptureError']) as error:
        V4['capture'](tmp_path, online_databases=True)
    assert error.value.reason == 'durable_file_changed_before_read'


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'oversized', 'writable', 'socket'])
def test_display_exception_cannot_hide_unsafe_objects(tmp_path, kind):
    import socket
    fixture_profile(tmp_path)
    marker = tmp_path / 'telemetry/.enforcement_mode.abcdefgh.tmp'
    ipc = None
    if kind == 'symlink':
        marker.symlink_to('/invented/secret')
    elif kind == 'hardlink':
        os.link(tmp_path / 'telemetry/enforcement_mode', marker)
    elif kind == 'socket':
        ipc = socket.socket(socket.AF_UNIX)
        ipc.bind(str(marker))
    else:
        marker.write_bytes(b'x' * (17 if kind == 'oversized' else 8))
        if kind == 'writable':
            marker.chmod(0o666)
    try:
        with pytest.raises(V4['CaptureError']):
            V4['capture'](tmp_path, online_databases=True)
    finally:
        if ipc:
            ipc.close()


def test_unknown_atomic_temp_remains_durable(tmp_path, monkeypatch):
    fixture_profile(tmp_path)
    target = tmp_path / 'telemetry/.enforcement_mode.not-reviewed.tmp'
    target.write_bytes(b'invented')
    mutate_at_database_open(monkeypatch, lambda: target.write_bytes(b'changed!'))
    with pytest.raises(V4['CaptureError']):
        V4['capture'](tmp_path, online_databases=True)


def test_known_log_stays_in_place_while_budget_remains_in_archive(tmp_path, monkeypatch):
    fixture_profile(tmp_path)
    log = tmp_path / 'telemetry/telemetry.log'
    log.write_bytes(b'invented-diagnostic-before')
    mutate_at_database_open(monkeypatch, lambda: log.write_bytes(b'invented-diagnostic-after'))
    payload, receipt = V4['capture'](tmp_path, online_databases=True)
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        assert 'telemetry/telemetry.log' not in archive.getnames()
        assert archive.extractfile('telemetry/budget.yaml').read() == b'invented_limit: 7\n'
        manifest = json.load(archive.extractfile('profile-manifest.json'))
        assert {'path': 'telemetry/telemetry.log', 'reason': 'diagnostic_logs_retained_in_place'} in manifest['omitted']
    assert log.read_bytes() == b'invented-diagnostic-after'
    assert receipt['plain_files_stable']


def test_v3_is_unchanged_and_still_refuses_the_original_rotation(tmp_path, monkeypatch):
    fixture_profile(tmp_path)
    marker = tmp_path / 'telemetry/enforcement_mode'
    mutate_at_database_open(monkeypatch, lambda: marker.write_bytes(b'observe\n'))
    v3 = runpy.run_path(str(FOLDER / 'capture_main_operational_profile_v3.py'))
    assert hashlib.sha256((FOLDER / 'capture_main_operational_profile_v3.py').read_bytes()).hexdigest() == V4['V3_SHA']
    with pytest.raises(v3['CaptureError']):
        v3['capture'](tmp_path, online_databases=True)


def test_live_sources_are_pinned_and_fit_the_existing_owner_protocol():
    owner = runpy.run_path(str(FOLDER / 'main_live_reconciliation_owner.py'))
    root = runpy.run_path(str(FOLDER / 'refresh_live_main_candidate.py'))
    assert root['OWNER_SHA'] == hashlib.sha256((FOLDER / 'main_live_reconciliation_owner.py').read_bytes()).hexdigest()
    controller = runpy.run_path(str(FOLDER / 'launch_control.py'))
    assert controller['LIVE_MAIN_SHA'] == hashlib.sha256((FOLDER / 'refresh_live_main_candidate.py').read_bytes()).hexdigest()
    for name in ('capture_main_operational_profile_v3.py', 'capture_main_operational_profile_v4.py',
                 'current_main_configuration.py', 'inspect_launch_main_references.py'):
        digest = owner['PINS'][name]
        assert hashlib.sha256((FOLDER / name).read_bytes()).hexdigest() == digest
    protocol = runpy.run_path(str(FOLDER / 'qualify_launch_isolated_accounts.py'))
    protocol['owner_program']((FOLDER / 'main_live_reconciliation_owner.py').read_bytes())


@pytest.mark.parametrize('damage', [None, 'contents', 'symlink', 'writable', 'public_profile'])
def test_only_reviewed_plugin_bytes_can_authorize_runtime_projection_omissions(monkeypatch, damage):
    scratch = FOLDER.parents[2] / '.pytest_cache'
    scratch.mkdir(exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix='live-plugin-', dir=scratch))
    plugin = profile / 'plugins/hermes-telemetry'
    plugin.mkdir(parents=True, mode=0o775)
    for name in ('budget.py', '__init__.py'):
        (plugin / name).write_bytes(b'raise RuntimeError("invented-code-must-not-run")\n')
        (plugin / name).chmod(0o664)
    expected = hashlib.sha256((plugin / 'budget.py').read_bytes()).hexdigest()
    if damage == 'contents': (plugin / 'budget.py').write_bytes(b'invented-other-code')
    if damage == 'writable': (plugin / 'budget.py').chmod(0o666)
    if damage == 'public_profile': profile.chmod(0o755)
    if damage == 'symlink':
        (plugin / 'original-budget.py').write_bytes((plugin / 'budget.py').read_bytes())
        (plugin / 'budget.py').rename(plugin / 'budget-preserved.py')
        (plugin / 'budget.py').symlink_to(plugin / 'original-budget.py')
    owner = runpy.run_path(str(FOLDER / 'main_live_reconciliation_owner.py'))
    def public(name):
        if name == 'capture_main_operational_profile_v4.py':
            return dict(TELEMETRY_WRITER_SHA=expected, TELEMETRY_REGISTER_SHA=expected)
        assert name == 'inspect_launch_main_references.py'
        return runpy.run_path(str(FOLDER / name))
    monkeypatch.setitem(owner['verify_telemetry_projection'].__globals__, 'public', public)
    if damage:
        with pytest.raises((ValueError, OSError)): owner['verify_telemetry_projection'](profile)
    else:
        owner['verify_telemetry_projection'](profile)
        assert (plugin / 'budget.py').stat().st_mode & 0o777 == 0o664


@pytest.mark.parametrize('damage', [None, 'failed', 'old_source', 'not_stopped', 'promoted', 'renewal_enabled'])
def test_current_settings_pass_is_reused_but_never_assumed(monkeypatch, damage):
    root = runpy.run_path(str(FOLDER / 'refresh_live_main_candidate.py'))
    base = Path('/invented/base')
    monkeypatch.setitem(root['retained_configuration'].__globals__, 'BASE', base)
    context = {'source_sha256': 'a97d14c49ca7ebc41b9935e2f296479226c76f37d690eee0203ccb3e5cb7efea',
               'evidence': str(base / 'operator-evidence/main-current-invented')}
    result = dict(source_revision=base.name, operator_helper_sha256=context['source_sha256'],
                  complete=True, operator_job_stopped=True, main_current_configuration_reconciled=True,
                  configured_candidate_restore_qualified=True, current_settings_and_oauth_preserved=True,
                  all_admission_policies_preserved_disabled=True, candidate_promoted=False,
                  daily_backup_registry_changed=False, fleet_launch_approved=False,
                  source_profiles_changed=False, production_renewal_timer_enabled=False)
    if damage == 'failed': result['complete'] = False
    if damage == 'old_source': context['source_sha256'] = 'wrong'
    if damage == 'not_stopped': result['operator_job_stopped'] = False
    if damage == 'promoted': result['candidate_promoted'] = True
    if damage == 'renewal_enabled': result['production_renewal_timer_enabled'] = True
    read = lambda path, *args: json.dumps(context if path.name == 'context.private.json' else result).encode()
    if damage:
        with pytest.raises(ValueError): root['retained_configuration'](read)
    else:
        assert root['retained_configuration'](read) == context['evidence']


LIVE_ROOT = runpy.run_path(str(FOLDER / 'refresh_live_main_candidate.py'))

@pytest.mark.parametrize('source_changed',[False,True])
def test_full_live_copy_only_passes_after_new_restore_and_final_source_check(monkeypatch,tmp_path,source_changed):
    scope=LIVE_ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-live-invented';evidence.mkdir(parents=True)
    source=b'invented-owner';(artifact/'main_live_reconciliation_owner.py').write_bytes(source)
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='1'*32,restore_id='2'*32)
    entry=dict(user='ecbot_'+'b'*16,uid=3001,home='/var/lib/enhanced-cognee-profiles/'+'b'*16)
    destination=entry['home']+'/ec-main-operational-restore-invented'
    files={artifact/'context.private.json':json.dumps(context).encode(),Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented"}'}
    policy=Path('/invented/policy');files[policy]=b'invented-disabled'
    events=[]
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    driver=dict(policies=lambda read:{policy:b'invented-disabled'},fixed_entry=lambda read:(entry,{}),
        PINS={'continue_launch_main_operational.py':'invented'},definitions=lambda *a:dict(validate_owner_result=lambda *a:None),
        fresh_bundle=lambda entry:{'token':'invented.scoped.token'})
    def owner(account,source,packet,**kwargs):
        mode=packet['mode'];events.append(mode)
        if mode=='capture_source':return dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},
            fingerprints={name:'c'*64 for name in ('config.yaml','.env','auth.json')},mcp_definitions=6,
            source_configuration_preserved=True,ciphertext_bytes=1),b'x'
        if mode=='capture_live_source':assert account.pw_uid==1000 and packet['fingerprints']=={name:'c'*64 for name in ('config.yaml','.env','auth.json')}
        if mode in {'capture_live_source','capture_candidate'}:return dict(complete=True,receipt={'sqlite_databases':9,'plain_files_stable':True,'database_snapshot_mode':'read_transaction_per_database'}),b'x'
        if mode=='prepare':return dict(complete=True,mcp_definitions=6,current_settings_and_oauth_preserved=True,
            source_fingerprints_match=True,scoped_status_authenticated=True,previous_operational_state_reused=False,
            current_source_operational_refresh_qualified=True,destination=destination,remaining_reference_count=2),b''
        if mode=='restore_candidate':
            assert packet['id']=='2'*32
            return dict(complete=True,mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,
                oauth_and_environment_preserved=True,receipt={'operational_restore_qualified':True,
                    'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
        assert mode=='verify_source'
        if source_changed:raise ValueError('invented-source-changed')
        return dict(complete=True,source_current_at_completion=True),b''
    def defs(path,digest):return dict(read_file=read,private_write=write)
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'__file__',str(artifact/'refresh_live_main_candidate.py'))
    monkeypatch.setitem(scope,'OWNER_SHA',hashlib.sha256(source).hexdigest());monkeypatch.setitem(scope,'definitions',defs)
    monkeypatch.setitem(scope,'legacy',lambda:driver);monkeypatch.setitem(scope,'owner',owner)
    monkeypatch.setitem(scope,'runtime_model',lambda *a:'invented-qualified-model-key')
    monkeypatch.setitem(scope,'generation',lambda kind,*args:(Path('/invented/'+kind),b'invented-cipher'))
    monkeypatch.setitem(scope,'decrypt',lambda *a,**kw:b'invented-plain')
    original_lexists=LIVE_ROOT['os'].path.lexists
    monkeypatch.setattr(LIVE_ROOT['os'].path,'lexists',lambda path:Path(path) in files or original_lexists(path))
    monkeypatch.setattr(LIVE_ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','d'*32)
    monkeypatch.setattr(LIVE_ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_uid=1000 if name=='vincentspereira' else 3001,
        pw_gid=1000 if name=='vincentspereira' else 3001,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert LIVE_ROOT['worker']()==(1 if source_changed else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (not source_changed) and result['current_source_operational_refresh_qualified'] is (not source_changed)
    assert result['source_profiles_changed'] is result['previous_candidate_changed'] is result['candidate_promoted'] is False
    assert result['all_admission_policies_preserved_disabled'] is True and result['fleet_launch_approved'] is False
    assert result['encrypted_generations_created']==3 and result['credentials_issued']==2
    assert events==['capture_source','capture_live_source','prepare','capture_candidate','restore_candidate','verify_source']
    if source_changed:assert result['new_candidate_may_exist'] is True
    else:assert result['mcp_definitions_preserved']==6 and result['remaining_reference_count']==2



@pytest.mark.parametrize('complete',[True,False])
def test_finished_reconciliation_is_returned_without_a_new_job(monkeypatch,tmp_path,capsys,complete):
    scope=LIVE_ROOT['watch'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-live-invented';evidence.mkdir(parents=True)
    context=dict(source_sha256='a'*64,evidence=str(evidence))
    (artifact/'context.private.json').write_text(json.dumps(context))
    result=dict(complete=complete,operator_job_stopped=True,operator_helper_sha256='a'*64,source_revision=base.name)
    (evidence/'finish.summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'metadata',lambda:pytest.fail('retained job inspected or restarted'))
    assert LIVE_ROOT['watch'](lambda path,*a:path.read_bytes(),lambda *a:pytest.fail('retained receipt rewritten'))==(0 if complete else 1)
    assert json.loads(capsys.readouterr().out)==result
