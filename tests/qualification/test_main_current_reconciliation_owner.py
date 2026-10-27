"""Settings capsule, authority rejection and preservation before any publication.

These use invented file contents and public helper implementations; they do
not claim protected profile capture or installed API/recovery qualification.
"""
import base64
import copy
import json
import os
from pathlib import Path
import runpy
import tempfile

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'main_current_reconciliation_owner.py'))
CONFIG=runpy.run_path(str(FOLDER/'current_main_configuration.py'))
DEST=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16+'/ec-main-operational-restore-invented')


def settings():
    return dict(model={'provider':'zai','default':'glm-5.3-flash','key_env':'GLM_API_KEY',
        'base_url':'https://open.bigmodel.cn/api/coding/paas/v4'},gateway={'multiplex_profiles':True},
        mcp_servers={'filesystem':dict(command='npx',args=['-y','@modelcontextprotocol/server-filesystem',CONFIG['SOURCE_WORKSPACE']]),
            **{f'invented-{i}':dict(url=f'https://example.invalid/{i}',headers={'Authorization':'invented-private-value'}) for i in range(5)}},
        opaque={'keep':[1,2,'invented'], 'owner_reference':'/home/vincentspereira/invented-current-path'})


def files():
    return {'config.yaml':yaml.safe_dump(settings()).encode(),
        '.env':b'UNRELATED="invented-preserve"\nGLM_API_KEY="invented-model-key-123456789"\nGLM_BASE_URL="https://api.z.ai/api/coding/paas/v4"\n',
        'auth.json':b'{"invented_oauth":"preserve-byte-for-byte"}'}


@pytest.fixture
def public(monkeypatch):
    loaded={}
    def load(name):
        if name not in loaded:loaded[name]=runpy.run_path(str(FOLDER/name))
        return loaded[name]
    monkeypatch.setitem(OWNER['prepare_files'].__globals__,'public',load)
    return load


def test_prepare_preserves_all_current_settings_credentials_and_auth_bytes(public):
    saved=files();before=copy.deepcopy(saved)
    config,environment,count=OWNER['prepare_files'](saved,{'token':'invented.scoped.token'},
        'invented-model-key-123456789',DEST,dict(subject='invented',agent_id='invented',tenant='invented',project_id='invented'))
    assert saved==before and count==6
    assert yaml.safe_load(config)==CONFIG['transform'](settings(),DEST)
    assert b'UNRELATED="invented-preserve"' in environment
    assert b'GLM_API_KEY="invented-model-key-123456789"' in environment
    assert b'ENHANCED_COGNEE_ACCESS_TOKEN=invented.scoped.token' in environment
    assert saved['auth.json']==b'{"invented_oauth":"preserve-byte-for-byte"}'


@pytest.mark.parametrize('key',['ENHANCED_JWT_SECRET','ENCRYPTION_MASTER_KEY','ARCADEDB_PASSWORD','INDEX_VALKEY_URL',
    'ENHANCED_BACKUP_SIGNING_KEY','ENHANCED_COGNEE_ACCESS_TOKEN'])
def test_source_authority_or_existing_scope_cannot_be_silently_copied(public,key):
    saved=files();saved['.env']+=(key+'=invented-private-value\n').encode()
    with pytest.raises(ValueError):OWNER['inspect_source'](saved)


def test_inline_mcp_privileged_credentials_are_refused(public):
    saved=files();value=settings();value['mcp_servers']['invented-0']['env']={'ENHANCED_INDEX_KEY':'invented-private-value'}
    saved['config.yaml']=yaml.safe_dump(value).encode()
    with pytest.raises(ValueError):OWNER['inspect_source'](saved)


def test_model_route_change_is_refused_before_publication(public):
    saved=files();value=settings();value['model']['provider']='unreviewed';saved['config.yaml']=yaml.safe_dump(value).encode()
    with pytest.raises(ValueError):OWNER['prepare_files'](saved,{'token':'invented.token'},'invented-key',DEST,{})


@pytest.mark.parametrize('damage',[None,'unknown_file','duplicate_file','wrong_version','invalid_base64','oversized','empty'])
def test_current_configuration_capsule_is_closed_and_bounded(damage):
    original=files();value=dict(schema=1,files={name:base64.b64encode(raw).decode() for name,raw in original.items()})
    if damage=='unknown_file':value['files']['../../invented']=value['files']['auth.json']
    if damage=='wrong_version':value['schema']=True
    if damage=='invalid_base64':value['files']['auth.json']='invalid!'
    if damage=='oversized':value['files']['auth.json']=base64.b64encode(b'x'*262145).decode()
    if damage=='empty':value['files']['auth.json']=''
    raw=json.dumps(value).encode()
    if damage=='duplicate_file':raw=raw.replace(b'"files": {',b'"files": {"auth.json":"aW52ZW50ZWQ=",',1)
    if damage:
        with pytest.raises((ValueError,TypeError)):OWNER['capsule'](raw)
    else:assert OWNER['capsule'](raw)==original


def test_capture_reads_only_settings_and_never_calls_whole_live_capture(monkeypatch,public):
    calls=[];original=files();scope=OWNER['capture_source'].__globals__
    monkeypatch.setitem(scope,'files',lambda profile:(calls.append(profile) or copy.deepcopy(original)))
    monkeypatch.setitem(scope,'encrypt',lambda raw,recipient:(OWNER['capsule'](raw)==original and b'age-encryption.org/v1\ninvented'))
    from types import SimpleNamespace
    value,body=OWNER['capture_source']({'recipient':'invented-public-recipient'},SimpleNamespace(pw_dir='/home/vincentspereira'))
    assert value['mcp_definitions']==6 and value['receipt']['files']==3 and body.startswith(b'age-encryption.org/v1\n')
    assert calls==[Path('/home/vincentspereira/.hermes')]*2
    assert value['source_configuration_preserved'] is True


def test_configuration_changed_during_capture_refuses_encrypted_result(monkeypatch,public):
    scope=OWNER['capture_source'].__globals__;values=files();calls=[]
    def read(profile):
        result=copy.deepcopy(values)
        if calls:result['auth.json']=b'{"invented_oauth":"changed"}'
        calls.append(True);return result
    monkeypatch.setitem(scope,'files',read);monkeypatch.setitem(scope,'encrypt',lambda *a:b'age-encryption.org/v1\ninvented')
    from types import SimpleNamespace
    with pytest.raises(ValueError):OWNER['capture_source']({'recipient':'invented'},SimpleNamespace(pw_dir='/home/vincentspereira'))


@pytest.fixture
def private_profile():
    # Retain invented originals/partial files in an ignored private archive.
    # Avoid /tmp's writable ancestor because the actual inspector forbids it.
    parent=ROOT/'.archive/main-current-reconciliation-tests'
    parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    profile=Path(tempfile.mkdtemp(prefix='fixture-',dir=parent))
    for name,raw in files().items():
        fd=os.open(profile/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as output:output.write(raw)
    return profile


def test_private_publication_preserves_original_and_refuses_an_existing_marker(public,private_profile):
    original=(private_profile/'config.yaml').read_bytes()
    OWNER['publish'](private_profile,'config.yaml',b'invented-updated-settings', 'a'*32)
    assert (private_profile/('config.yaml-before-current-'+'a'*32)).read_bytes()==original
    assert (private_profile/'config.yaml').read_bytes()==b'invented-updated-settings'
    with pytest.raises(FileExistsError):OWNER['publish'](private_profile,'config.yaml',b'invented-second-settings','a'*32)
    assert (private_profile/'config.yaml').read_bytes()==b'invented-updated-settings'


def test_named_symlink_is_refused_without_touching_target(public,private_profile):
    victim=private_profile/'invented-target'
    victim.write_bytes(b'invented-preserve-target');victim.chmod(0o600)
    (private_profile/'invented-link').symlink_to(victim)
    with pytest.raises(OSError):OWNER['publish'](private_profile,'invented-link',b'invented-change','b'*32)
    assert victim.read_bytes()==b'invented-preserve-target' and (private_profile/'invented-link').is_symlink()


def test_concurrent_owner_edit_is_preserved_instead_of_overwritten(monkeypatch,public,private_profile):
    inspector=public('inspect_launch_main_references.py');original=inspector['read_at'];calls=[]
    def changed(directory,name,uid):
        calls.append(True)
        if len(calls)==2:(private_profile/name).write_bytes(b'invented-concurrent-owner-edit')
        return original(directory,name,uid)
    monkeypatch.setitem(inspector,'read_at',changed)
    with pytest.raises(ValueError):OWNER['publish'](private_profile,'config.yaml',b'invented-candidate-edit','c'*32)
    assert (private_profile/'config.yaml').read_bytes()==b'invented-concurrent-owner-edit'
    assert (private_profile/('config.yaml-current-'+'c'*32)).exists()
