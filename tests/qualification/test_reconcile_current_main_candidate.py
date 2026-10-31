"""Retained gates, immutable jobs and exact current-settings reconciliation.

Workflow tests use invented owner/crypto results. Real installed execution and
AGE recovery remain an explicit protected operator qualification.
"""
import hashlib
import io
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
ROOT=runpy.run_path(str(FOLDER/'reconcile_current_main_candidate.py'))


@pytest.mark.parametrize('damage',[None,'failed','wrong_source','missing_phase','scope_changed','keys_used','enabled'])
def test_completed_delivery_gate_requires_the_exact_safe_pass(monkeypatch,damage):
    scope=ROOT['retained_delivery'].__globals__;base=Path('/invented/base')
    context=dict(source_sha256=ROOT['DELIVERY_SHA'],evidence=str(base/'operator-evidence/isolated-delivery-invented'),bindings_sha256='a'*64)
    value=dict(complete=True,source_revision=base.name,operator_helper_sha256=ROOT['DELIVERY_SHA'],completed_phases=4,
        binding_manifest_sha256='a'*64,durable_no_replay_component_qualified=True,native_base_adapter_text_component_qualified=True,
        peer_journal_os_denial_qualified=True,two_actual_forced_process_exits=True,all_admission_policies_preserved_disabled=True,
        fleet_launch_approved=False,source_profiles_changed=False,real_profile_contents_read=False,keys_read=False,
        model_called=False,memory_api_called=False,services_installed=False,canonical_memory_edits=False,credentials_issued=0,external_platform_sends=0)
    if damage=='failed':value['complete']=False
    if damage=='wrong_source':context['source_sha256']='wrong'
    if damage=='missing_phase':value['completed_phases']=3
    if damage=='scope_changed':value['binding_manifest_sha256']='b'*64
    if damage=='keys_used':value['keys_read']=True
    if damage=='enabled':value['all_admission_policies_preserved_disabled']=False
    monkeypatch.setitem(scope,'BASE',base)
    def read(path,*args):return json.dumps(context if path.name=='context.private.json' else value).encode()
    if damage:
        with pytest.raises(ValueError):ROOT['retained_delivery'](read)
    else:assert ROOT['retained_delivery'](read)==context['evidence']


@pytest.mark.parametrize('complete',[True,False])
def test_finished_reconciliation_is_returned_without_a_new_job(monkeypatch,tmp_path,capsys,complete):
    scope=ROOT['watch'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-current-invented';evidence.mkdir(parents=True)
    context=dict(source_sha256='a'*64,evidence=str(evidence))
    (artifact/'context.private.json').write_text(json.dumps(context))
    result=dict(complete=complete,operator_job_stopped=True,operator_helper_sha256='a'*64,source_revision=base.name)
    (evidence/'finish.summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'metadata',lambda:pytest.fail('retained job inspected or restarted'))
    assert ROOT['watch'](lambda path,*a:path.read_bytes(),lambda *a:pytest.fail('retained receipt rewritten'))==(0 if complete else 1)
    assert json.loads(capsys.readouterr().out)==result


def test_owner_launch_withholds_privileged_environment_and_redacts_failures(monkeypatch):
    scope=ROOT['owner'].__globals__;captured={}
    helper=dict(EXECUTABLE='/invented/python',owner_program=lambda source:("import sys\nn={}\nn['child']()\n",b'invented-public\n'))
    monkeypatch.setitem(scope,'definitions',lambda *a:helper)
    output=json.dumps(dict(complete=False,phase='new_candidate_configuration',error_kind='ValueError',
        private_path='invented-sensitive-path',private_key='invented-sensitive-key')).encode()+b'\n'
    process=SimpleNamespace(returncode=1,communicate=lambda value,timeout:(captured.update(input=value) or (output,b'')),
        poll=lambda:1,wait=lambda **kwargs:1)
    def spawn(args,**kwargs):captured.update(args=args,**kwargs);return process
    monkeypatch.setattr(ROOT['subprocess'],'Popen',spawn)
    account=SimpleNamespace(pw_uid=3001,pw_gid=3001,pw_dir='/invented/private-home')
    with pytest.raises(ValueError) as error:ROOT['owner'](account,b'invented-source',{'ordinary_token':'invented-private-token'},limit=65536)
    assert error.value.owner_diagnostic==dict(phase='new_candidate_configuration',error_kind='ValueError')
    assert captured['user']==captured['group']==3001 and captured['extra_groups']==()
    assert captured['args'][:5]==['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--']
    assert set(captured['env'])=={'PATH','HOME','LANG','PYTHONDONTWRITEBYTECODE'}
    assert 'invented-private-token' not in repr(captured['args'])+repr(captured['env'])
    assert b'invented-private-token' in captured['input']
    assert 'invented-sensitive' not in str(error.value)+json.dumps(error.value.owner_diagnostic)


@pytest.mark.parametrize('source_changed',[False,True])
def test_new_copy_and_recovery_do_not_claim_live_operational_refresh(monkeypatch,tmp_path,source_changed):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-current-invented';evidence.mkdir(parents=True)
    source=b'invented-owner';(artifact/'main_current_reconciliation_owner.py').write_bytes(source)
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
        if mode in {'capture_previous','capture_candidate'}:return dict(complete=True,receipt={'sqlite_databases':8}),b'x'
        if mode=='prepare':return dict(complete=True,mcp_definitions=6,current_settings_and_oauth_preserved=True,
            source_fingerprints_match=True,scoped_status_authenticated=True,previous_operational_state_reused=True,
            current_source_operational_refresh_qualified=False,destination=destination,remaining_reference_count=2),b''
        if mode=='restore_candidate':
            assert packet['id']=='2'*32
            return dict(complete=True,mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,
                oauth_and_environment_preserved=True,receipt={'operational_restore_qualified':True,
                    'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':8}),b''
        assert mode=='verify_source'
        if source_changed:raise ValueError('invented-source-changed')
        return dict(complete=True,source_current_at_completion=True),b''
    def defs(path,digest):return dict(read_file=read,private_write=write)
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'__file__',str(artifact/'reconcile_current_main_candidate.py'))
    monkeypatch.setitem(scope,'OWNER_SHA',hashlib.sha256(source).hexdigest());monkeypatch.setitem(scope,'definitions',defs)
    monkeypatch.setitem(scope,'legacy',lambda:driver);monkeypatch.setitem(scope,'owner',owner)
    monkeypatch.setitem(scope,'runtime_model',lambda *a:'invented-qualified-model-key')
    monkeypatch.setitem(scope,'generation',lambda kind,*args:(Path('/invented/'+kind),b'invented-cipher'))
    monkeypatch.setitem(scope,'decrypt',lambda *a,**kw:b'invented-plain')
    original_lexists=ROOT['os'].path.lexists
    monkeypatch.setattr(ROOT['os'].path,'lexists',lambda path:Path(path) in files or original_lexists(path))
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','d'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_uid=1000 if name=='vincentspereira' else 3001,
        pw_gid=1000 if name=='vincentspereira' else 3001,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(1 if source_changed else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (not source_changed) and result['current_source_operational_refresh_qualified'] is False
    assert result['source_profiles_changed'] is result['previous_candidate_changed'] is result['candidate_promoted'] is False
    assert result['all_admission_policies_preserved_disabled'] is True and result['fleet_launch_approved'] is False
    assert result['encrypted_generations_created']==3 and result['credentials_issued']==2
    assert events==['capture_source','capture_previous','prepare','capture_candidate','restore_candidate','verify_source']
    if source_changed:assert result['new_candidate_may_exist'] is True
    else:assert result['mcp_definitions_preserved']==6 and result['remaining_reference_count']==2


def test_public_pins_and_native_owner_frame_budget_are_exact():
    source=(FOLDER/'main_current_reconciliation_owner.py').read_bytes()
    assert ROOT['OWNER_SHA']==hashlib.sha256(source).hexdigest()
    owner=runpy.run_path(str(FOLDER/'main_current_reconciliation_owner.py'))
    assert owner['PINS']['current_main_configuration.py']==hashlib.sha256((FOLDER/'current_main_configuration.py').read_bytes()).hexdigest()
    helper=runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))
    helper['owner_program'](source)
    controller=runpy.run_path(str(FOLDER/'launch_control.py'))
    assert controller['CURRENT_MAIN_SHA']==hashlib.sha256((FOLDER/'reconcile_current_main_candidate.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('tamper',[None,'ciphertext','manifest'])
def test_signed_generation_requires_readback_authentication_before_restore(monkeypatch,tmp_path,tamper):
    scope=ROOT['generation'].__globals__;backups=tmp_path/'backups';backups.mkdir(mode=0o700)
    monkeypatch.setitem(scope,'BACKUPS',backups)
    stored={};ciphertext=b'age-encryption.org/v1\ninvented-test-ciphertext'
    def write(path,raw):assert path not in stored;stored[path]=raw
    def read(path,*args):
        raw=stored[path]
        if tamper=='ciphertext' and path.suffix=='.age':return raw+b'invented-corruption'
        if tamper=='manifest' and path.suffix=='.json':
            value=json.loads(raw);value['receipt']={'changed':True};return json.dumps(value).encode()
        return raw
    settings=dict(ENHANCED_BACKUP_SIGNING_KEY='invented-unit-test-key-0000000000000000',ENHANCED_BACKUP_SIGNING_KEY_ID='invented-unit-test')
    value=dict(complete=True,ciphertext_bytes=len(ciphertext),receipt={'files':3,'plaintext_archive_written':False})
    if tamper:
        with pytest.raises(ValueError):ROOT['generation']('configuration',value,ciphertext,settings,read,write)
    else:
        path,saved=ROOT['generation']('configuration',value,ciphertext,settings,read,write)
        assert saved==ciphertext and path.name.endswith('.json.age')
    assert len(stored)==2  # Failed generations are retained, never cleaned up.
