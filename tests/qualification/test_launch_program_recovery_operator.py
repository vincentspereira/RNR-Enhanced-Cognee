"""Program recovery uses a new copy and restricted namespace, never live paths."""
import ast
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
MODULE=runpy.run_path(str(DIRECTORY/'qualify_launch_program_recovery.py'),run_name='program_recovery_operator_units')


def test_source_pins_and_public_manifest_are_exact():
    assert hashlib.sha256((DIRECTORY/'program_snapshot_recovery.py').read_bytes()).hexdigest()==MODULE['CORE_SHA']
    assert hashlib.sha256((DIRECTORY/'recover_launch_graph_operator.py').read_bytes()).hexdigest()==MODULE['SUPPORT_SHA']
    assert MODULE['MANIFEST_SHA']=='b8b07343b2e16228c9a2673eecd14cebbf88b327c7c0e1b45bebe3c61d5e67ce'
    control=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='program_recovery_dispatch_contract')
    assert hashlib.sha256((DIRECTORY/'qualify_launch_program_recovery.py').read_bytes()).hexdigest()==control['PROGRAM_RECOVERY_SHA']


def test_repeated_job_only_attaches_without_creating_generations(monkeypatch):
    launch=MODULE['launch'];scope=launch.__globals__;events=[]
    monkeypatch.setattr(MODULE['os'],'geteuid',lambda:0)
    monkeypatch.setattr(MODULE['os'].path,'lexists',lambda *a:True)
    monkeypatch.setitem(scope,'definitions',lambda *a:dict(read_file=object(),private_write=object()))
    monkeypatch.setitem(scope,'watch',lambda *a:events.append('reattach') or 0)
    assert launch()==0 and events==['reattach']


def test_probe_rebinds_only_a_new_program_copy_with_no_profile_or_secret_access(tmp_path,monkeypatch):
    destination=tmp_path/'new-program';fixture=tmp_path/'new-invented-home'
    for name in ('repo/run_agent.py','venv/pyvenv.cfg','python/bin/python3.14'):
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'public program fixture')
    events=[]
    def run(args,**kwargs):
        events.append(args)
        properties={item[len('--property='):].split('=',1)[0]:item.split('=',2)[2] for item in args if item.startswith('--property=')}
        assert properties['BindReadOnlyPaths']==str(destination)+':'+str(MODULE['RELEASE'])
        assert properties['User']==properties['Group']=='hermes-runtime'
        assert properties['ProtectHome']=='yes' and properties['ProtectSystem']=='strict'
        assert properties['PrivateNetwork']=='yes' and properties['RestrictAddressFamilies']=='AF_UNIX'
        assert properties['NoNewPrivileges']=='yes' and properties['CapabilityBoundingSet']==''
        assert properties['ReadWritePaths']==str(fixture)
        for path in ['/etc/enhanced-cognee','/var/lib/hermes-runtime','/var/lib/enhanced-cognee-profiles','/root']:
            assert path in properties['InaccessiblePaths'].split()
        assert args[-4:-1]==['-I','-B','-c']
        ast.parse(args[-1])
        assert 'ENHANCED_JWT_SECRET' not in args[-1] and 'ENHANCED_COGNEE_ACCESS_TOKEN' not in args[-1]
        assert kwargs['stderr'] is MODULE['subprocess'].DEVNULL
        value=dict(complete=True,recovered_program_imported=True,new_copy_inodes_verified=True,
            restricted_identity_verified=True,model_called=False,profiles_read=False,network_used=False)
        return SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())
    monkeypatch.setattr(MODULE['subprocess'],'run',run)
    result=MODULE['native_probe'](destination,fixture,'a'*32)
    assert result['complete'] is True and len(events)==1


@pytest.mark.parametrize('damage',['exit','oversize','private_extra','no_inode_proof','network'])
def test_native_receipt_refuses_failed_or_inflated_claims(tmp_path,monkeypatch,damage):
    destination=tmp_path/'new-program'
    for name in ('repo/run_agent.py','venv/pyvenv.cfg','python/bin/python3.14'):
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'public')
    value=dict(complete=True,recovered_program_imported=True,new_copy_inodes_verified=True,
        restricted_identity_verified=True,model_called=False,profiles_read=False,network_used=False)
    code=0
    if damage=='exit':code=1
    elif damage=='private_extra':value['private_content']='not-accepted'
    elif damage=='no_inode_proof':value['new_copy_inodes_verified']=False
    elif damage=='network':value['network_used']=True
    raw=b'x'*4097 if damage=='oversize' else json.dumps(value).encode()
    monkeypatch.setattr(MODULE['subprocess'],'run',lambda *a,**kw:SimpleNamespace(returncode=code,stdout=raw))
    with pytest.raises(ValueError):MODULE['native_probe'](destination,tmp_path/'unused-fixture','a'*32)


def test_program_probe_code_contains_no_dynamic_caller_command_or_model_route():
    code=MODULE['probe_code'](Path('/var/lib/hermes-renewal-qualification/program_'+'a'*32),{'repo/run_agent.py':(1,2)})
    ast.parse(code)
    assert 'run_conversation' not in code and 'AIAgent(' not in code
    assert 'new_copy_inodes_verified' in code and "socket.getaddrinfo=denied" in code
