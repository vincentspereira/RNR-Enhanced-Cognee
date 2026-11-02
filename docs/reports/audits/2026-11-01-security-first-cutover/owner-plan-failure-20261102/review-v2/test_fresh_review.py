"""Fresh independent offline probes. Root blocks evaluated ONLY in a fake VFS.
No source, app, protected path, service or credential operations are performed.
"""
import ast
import builtins
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[6]
HELPER = ROOT / 'integrations/hermes/deployment/prepare_security_first_cutover_v2.py'
PIN = 'a8b333c156f03aa32ac3c69d8475f5978f9651bb3547b9ececca61be18e97365'
OWNER = ROOT / 'docs/reports/audits/2026-11-01-security-first-cutover/owner-plan-failure-20261102/repair-v2/OWNER-V2-PLAN.md'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == PIN
assert hashlib.sha256(OWNER.read_bytes()).hexdigest() == 'cbebb9eb0ae50451e5df431312ce9c7776dc90cabad1c5ec39ab2d3955bbeba0'
spec = importlib.util.spec_from_file_location('fresh_review_v2', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
BLOCKS = re.findall(r'```bash\n(.*?)```', OWNER.read_text(), re.S)
TOKENS = shlex.split(BLOCKS[0])
SCRIPTS = [TOKENS[i+1] for i, x in enumerate(TOKENS) if x == '-c']
assert len(BLOCKS) == 2 and len(SCRIPTS) == 3


def snap(monkeypatch):
    raw = dict(zip(h.SOURCES, [
        b'[Service]\nDynamicUser=yes\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n',
        b'[Service]\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n',
        ('[Service]\nWorkingDirectory='+h.OLD+'\nExecStart=\nExecStart='+h.OLD+'/runtime/bin/python -m src.memory_daemon api\n').encode(),
        b'[Service]\nLoadCredential=llm.json:/etc/enhanced-cognee/llm.json\n']))
    s = {'inventory': list(h.SOURCES), 'loaded': dict(h.EXPECTED_LOADED), 'source_bytes': raw,
         'candidate': h.CANDIDATE, 'candidate_hashes': dict(h.MODULE_HASHES), 'helper_sha256': PIN,
         'startup_interpreter': {'lexical':h.CANDIDATE+'/runtime/bin/python', 'resolved':'/usr/bin/python3.12', 'sha256':'b'*64}}
    repin(monkeypatch, s)
    return s


def repin(monkeypatch, s):
    monkeypatch.setattr(h, 'SOURCE_HASHES', {p:h.digest(s['source_bytes'][p]) for p in h.SOURCES if p != h.SOURCES[2]})


@pytest.mark.parametrize('case', ['implicit', 'user-only', 'group-only', 'split-explicit', 'all-fragments-explicit'])
def test_identity_positive_controls(monkeypatch, case):
    s = snap(monkeypatch)
    additions = {'implicit':[], 'user-only':[(0,'User')], 'group-only':[(3,'Group')],
                 'split-explicit':[(1,'Group'),(2,'User')],
                 'all-fragments-explicit':[(i,k) for i in range(4) for k in ('User','Group')]}
    for i,key in additions[case]:
        s['source_bytes'][h.SOURCES[i]] += (key+'=enhanced-cognee-api\n').encode()
    repin(monkeypatch, s)
    plan = h.plan_from_snapshot(s)
    assert plan['loaded'] == h.EXPECTED_LOADED
    assert plan['bundle'].endswith('-v2') and plan['retained_credentials'] == ['api.json','index.json']
    assert plan['omitted_credentials'] == ['llm.json']
    assert plan['activated'] is False and plan['installation_pending'] is True


@pytest.mark.parametrize('case', ['overridden-user', 'overridden-group', 'missing-dynamic', 'overridden-dynamic-no',
                                  'duplicate-dynamic-yes', 'loaded-bool', 'invalid-unit-default', 'launch-trailer'])
def test_identity_negative_controls(monkeypatch, case):
    s = snap(monkeypatch)
    if case.startswith('overridden-') and case != 'overridden-dynamic-no':
        key = 'User' if case.endswith('user') else 'Group'
        s['source_bytes'][h.SOURCES[0]] += (key+'=root\n').encode()
        s['source_bytes'][h.SOURCES[3]] += (key+'=enhanced-cognee-api\n').encode()
    elif case == 'missing-dynamic':
        s['source_bytes'][h.SOURCES[0]] = s['source_bytes'][h.SOURCES[0]].replace(b'DynamicUser=yes\n',b'')
    elif case == 'overridden-dynamic-no':
        s['source_bytes'][h.SOURCES[0]] = s['source_bytes'][h.SOURCES[0]].replace(b'DynamicUser=yes',b'DynamicUser=no')
        s['source_bytes'][h.SOURCES[3]] += b'DynamicUser=yes\n'
    elif case == 'duplicate-dynamic-yes':
        s['source_bytes'][h.SOURCES[0]] += b'DynamicUser=yes\n'
    elif case == 'loaded-bool':
        s['loaded']['DynamicUser'] = True
    elif case == 'invalid-unit-default':
        monkeypatch.setattr(h,'UNIT','enhanced-cognee-api@evil.service')
    else:
        s['source_bytes'][h.SOURCES[2]] += b'[Service]\nUser=enhanced-cognee-api\n'
    repin(monkeypatch, s)
    with pytest.raises(h.Refusal): h.plan_from_snapshot(s)


@pytest.mark.parametrize('case',['missing-reset','changed-command','source-pin','credential-rebind'])
def test_old_source_guards(monkeypatch, case):
    s=snap(monkeypatch)
    if case=='missing-reset': s['source_bytes'][h.SOURCES[2]]=s['source_bytes'][h.SOURCES[2]].replace(b'ExecStart=\n',b'')
    elif case=='changed-command': s['source_bytes'][h.SOURCES[2]]=s['source_bytes'][h.SOURCES[2]].replace(b' api\n',b' api --unsafe\n')
    elif case=='source-pin': s['source_bytes'][h.SOURCES[1]]+=b'# changed bytes\n'
    else:
        s['source_bytes'][h.SOURCES[3]]=b'[Service]\nLoadCredential=llm.json:/invented.json\n'
        repin(monkeypatch,s)
    with pytest.raises(h.Refusal): h.plan_from_snapshot(s)


def test_installed_site8_and_manager_recheck(monkeypatch):
    s=snap(monkeypatch); content=dict(s['source_bytes']); reads=[]
    for p,pin in h.MODULE_HASHES.items():
        data=(ROOT/p).read_bytes(); assert h.digest(data)==pin
        content[h.CANDIDATE+'/runtime/lib/python3.12/site-packages/'+p]=data
        content[h.CANDIDATE+'/'+p]=b'INVENTED_DECOY'
    content[h.INSTALLED_HELPER]=HELPER.read_bytes(); content['/usr/bin/python3.12']=b'INVENTED_INTERPRETER'
    def reader(p): reads.append(p); return content[p]
    def guard(p,**kw): return '/usr/bin/python3.12' if kw.get('allow_alias') else p
    result=h.collect_snapshot(reader=reader,guard=guard,inventory=lambda:list(h.SOURCES),loaded=lambda:dict(h.EXPECTED_LOADED))
    assert h.plan_from_snapshot(result)['candidate_hashes']==h.MODULE_HASHES
    assert set(reads)==set(content)-{h.CANDIDATE+'/'+p for p in h.MODULE_HASHES}
    content[h.CANDIDATE+'/runtime/lib/python3.12/site-packages/src/memory_api.py']=b'INVENTED_CHANGED'
    with pytest.raises(h.Refusal):
        h.plan_from_snapshot(h.collect_snapshot(reader=reader,guard=guard,inventory=lambda:list(h.SOURCES),loaded=lambda:dict(h.EXPECTED_LOADED)))
    calls=[]
    def loaded():
        calls.append(1); d=dict(h.EXPECTED_LOADED)
        if len(calls)>1: d['NeedDaemonReload']='yes'
        return d
    with pytest.raises(h.Refusal,match='snapshot_changed'):
        h.collect_snapshot(reader=reader,guard=guard,inventory=lambda:list(h.SOURCES),loaded=loaded)


def test_inventory_generic_runtime_dropin_refused():
    present={'/run/systemd/system','/run/systemd/system/service.d'}
    with pytest.raises(h.Refusal,match='unanticipated_dropin_directory'):
        h.inventory_sources(roots=h.UNIT_ROOTS,exists=lambda p:p in present,children=lambda p:['z.conf'],guard=lambda *a,**kw:None)


@pytest.mark.parametrize('case',['safe-alias','writable-alias-parent','hidden-symlink-dotdot'])
def test_lexical_interpreter_trust(case):
    def metadata(p):
        mode=stat.S_IFDIR|0o755
        if p=='/safe/bin/python': mode=stat.S_IFLNK|0o777
        if p=='/usr/bin/python3.12': mode=stat.S_IFREG|0o755
        if p=='/usr/bin/bridge' and case=='hidden-symlink-dotdot': mode=stat.S_IFLNK|0o777
        if p=='/safe/bin' and case=='writable-alias-parent': mode|=0o020
        return os.stat_result((mode,1,1,1,0,0,10,0,0,0))
    target='/usr/bin/bridge/../python3.12' if case=='hidden-symlink-dotdot' else '/usr/bin/python3.12'
    call=lambda:h.trusted_path('/safe/bin/python',allow_alias=True,executable=True,stat_fn=metadata,readlink=lambda p:target)
    if case=='safe-alias': assert call()=='/usr/bin/python3.12'
    else:
        with pytest.raises(h.Refusal): call()


def test_approval_exact_and_exception_redaction(monkeypatch,capsys):
    s=snap(monkeypatch); p=h.plan_from_snapshot(s); approved=h.digest(h.canonical(p)); writes=[]
    def no_write(*a): writes.append(a)
    def changed():
        d=copy.deepcopy(s); d['helper_sha256']='f'*64; return d
    calls=[]
    def collector(): calls.append(1); return s if len(calls)==1 else changed()
    assert h.main(['--prepare','--expected-plan-sha256',approved],runtime=lambda:None,output_guard=lambda:None,collector=collector,writer=no_write)==1
    assert len(calls)==2 and writes==[]
    assert capsys.readouterr().err=='ERR stage_only_refused\n'
    def fail(): raise OSError('INVENTED_PRIVATE_TEXT')
    assert h.main(['--plan'],runtime=fail,collector=fail,output_guard=fail,writer=no_write)==1
    got=capsys.readouterr(); assert got.out=='' and got.err=='ERR stage_only_refused\n'
    assert h.main(['--plan','--output=/invented'],runtime=fail)==1
    assert capsys.readouterr().err=='ERR stage_only_refused\n'


def test_plan_no_write_and_finite_fixed_payload(monkeypatch,capsys):
    s=snap(monkeypatch); writes=[]
    assert h.main(['--plan'],runtime=lambda:None,output_guard=lambda:None,collector=lambda:s,writer=lambda *a:writes.append(a))==0
    response=json.loads(capsys.readouterr().out)
    assert response['plan_sha256']==h.digest(h.canonical(response['plan'])) and writes==[]
    p=response['plan']
    for key in ['activated','services_restarted','ledger_created','model_analysis_expected_enabled','model_usage_reset','state_directory_proposed']:
        assert p[key] is False
    assert type(p['credentials_issued']) is int and p['credentials_issued']==0
    proposal=h.proposed_dropin()
    assert b'LoadCredential=\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n' in proposal
    assert b'llm.json' not in proposal and b'StateDirectory' not in proposal


def test_bundle_partial_and_no_overwrite(tmp_path):
    parent=tmp_path/'private';parent.mkdir(mode=0o700); dest=parent/'bundle'
    files={'40-audit-security-first.conf':b'INVENTED','manifest.json':b'{}','receipt.json':b'{}'}
    def guard(p,kind='file',private=False,**kw):
        s=os.lstat(p); assert not stat.S_ISLNK(s.st_mode)
        assert stat.S_IMODE(s.st_mode)==(0o700 if kind=='directory' else 0o600)
    def fail(fd,name,data):
        if name=='receipt.json': raise OSError('INVENTED_FAILURE')
        h.write_new(fd,name,data)
    with pytest.raises(OSError): h.write_bundle(str(dest),files,guard=guard,writer=fail)
    before={p.name:p.read_bytes() for p in dest.iterdir()}
    assert set(before)=={'40-audit-security-first.conf','manifest.json'}
    with pytest.raises(FileExistsError):h.write_bundle(str(dest),files,guard=guard)
    assert {p.name:p.read_bytes() for p in dest.iterdir()}==before


def test_owner_shell_ast_and_commands(tmp_path):
    for i,block in enumerate(BLOCKS):
        p=tmp_path/('block-'+str(i)+'.sh');p.write_text(block)
        result=subprocess.run(['/usr/bin/bash','-n',str(p)],capture_output=True,timeout=10)
        assert (result.returncode,result.stdout,result.stderr)==(0,b'',b'')
    for script in SCRIPTS: ast.parse(script)
    assert shlex.split(BLOCKS[1])==['/usr/bin/sudo','/usr/bin/python3','-I','-S','-B',h.INSTALLED_HELPER,'--plan']
    assert '--prepare' not in ''.join(BLOCKS) and 'systemctl' not in ''.join(BLOCKS)
    for forbidden in ('/bin/sh','eval ','source ','tee ','chmod ','chown ','rm ','restart','daemon-reload'):
        assert forbidden not in ''.join(BLOCKS)
    install=['/usr/bin/sudo','/usr/bin/install','-o','root','-g','root','-m','0644','/dev/stdin',h.INSTALLED_HELPER]
    idx=TOKENS.index('/usr/bin/install')-1
    assert TOKENS[idx:idx+len(install)]==install
    assert TOKENS[idx-1]=='|' and 'set -euo pipefail' in BLOCKS[0]
    assert SCRIPTS[1].index('hashlib.sha256') < SCRIPTS[1].index('sys.stdout.buffer.write')


@pytest.mark.parametrize('case',['exact-reader','wrong-hash','symlink-reader'])
def test_owner_unprivileged_reader_actual(tmp_path,case):
    p=tmp_path/'invented.py';data=b'# INVENTED NONEXECUTED PAYLOAD\n';p.write_bytes(data)
    if case=='symlink-reader':
        alias=tmp_path/'link';alias.symlink_to(p);p=alias
    expected=h.digest(data) if case!='wrong-hash' else '0'*64
    result=subprocess.run(['/usr/bin/python3','-I','-S','-B','-c',SCRIPTS[1],str(p),expected],capture_output=True,timeout=10,env={'PATH':'/usr/bin:/bin'})
    if case=='exact-reader': assert (result.returncode,result.stdout,result.stderr)==(0,data,b'')
    else: assert result.returncode!=0 and result.stdout==b''


BASE='/opt/enhanced-cognee-memory'
HF=BASE+'/security-first-helper-v2'
INST=HF+'/prepare_security_first_cutover_v2.py'


def root_double(script_index,changes=None,existing_parent=True,existing_helper=False):
    """Evaluate exact owner Python in controlled imports; no real path operations."""
    dirs=['/','/opt',BASE]
    if existing_parent:dirs.append(BASE+'/cutover')
    if existing_helper or script_index==2:dirs.append(HF)
    fs={p:{'mode':stat.S_IFDIR|(0o700 if p.endswith('/cutover') else 0o755),'uid':0,'gid':0,'nlink':1} for p in dirs}
    if script_index==2:fs[INST]={'mode':stat.S_IFREG|0o644,'uid':0,'gid':0,'nlink':1,'data':HELPER.read_bytes()}
    for p,values in (changes or {}).items():fs[p].update(values)
    writes=[]
    class P:
        def __init__(self,p): self.p=str(p)
        def __truediv__(self,x):return P(self.p+'/'+x)
        def __str__(self):return self.p
        @property
        def parents(self):return [P(str(p)) for p in PurePosixPath(self.p).parents]
        def lstat(self):
            v=fs[self.p];return SimpleNamespace(st_mode=v['mode'],st_uid=v['uid'],st_gid=v['gid'],st_nlink=v['nlink'])
        def mkdir(self,mode):
            assert self.p in (HF,BASE+'/cutover') and self.p not in fs
            writes.append((self.p,mode));fs[self.p]={'mode':stat.S_IFDIR|mode,'uid':0,'gid':0,'nlink':1}
        def read_bytes(self):return fs[self.p]['data']
    modules={'os':SimpleNamespace(path=SimpleNamespace(lexists=lambda p:str(p) in fs)),
             'stat':stat,'pathlib':SimpleNamespace(Path=P),'hashlib':hashlib,'json':json,
             'sys':SimpleNamespace(argv=['-c',PIN])}
    def importing(name,*a,**kw):
        assert name in modules, 'unexpected import in owner boundary'
        return modules[name]
    env={'__builtins__':dict(vars(builtins),__import__=importing)}
    # Exact hash-bound owner code; all its OS, Path and sys imports are no-launch doubles.
    try:exec(compile(SCRIPTS[script_index],'<owner-script-double>','exec'),env)
    except SystemExit as exc:return {'error':str(exc),'writes':writes,'fs':fs}
    return {'error':None,'writes':writes,'fs':fs}


@pytest.mark.parametrize('case',['new-private-parent','existing-private-parent','existing-helper','nonprivate-parent','unsafe-ancestor'])
def test_owner_installer_prerequisites_doubles(case):
    changes={}
    if case=='nonprivate-parent':changes[BASE+'/cutover']={'mode':stat.S_IFDIR|0o755}
    if case=='unsafe-ancestor':changes['/opt']={'mode':stat.S_IFDIR|0o777}
    result=root_double(0,changes,existing_parent=case!='new-private-parent',existing_helper=case=='existing-helper')
    if case in ('new-private-parent','existing-private-parent'):
        assert result['error'] is None
        assert result['writes']==([(BASE+'/cutover',0o700)] if case=='new-private-parent' else [])+[(HF,0o755)]
    else:assert result['error'] and result['writes']==[]


@pytest.mark.parametrize('case',['exact-installed','wrong-hash','wrong-owner','hardlink','wrong-mode'])
def test_owner_installed_readback_doubles(case,capsys):
    changes={}
    if case=='wrong-hash':changes[INST]={'data':b'INVENTED_WRONG'}
    elif case=='wrong-owner':changes[INST]={'uid':1234}
    elif case=='hardlink':changes[INST]={'nlink':2}
    elif case=='wrong-mode':changes[INST]={'mode':stat.S_IFREG|0o666}
    result=root_double(2,changes)
    got=capsys.readouterr()
    assert result['writes']==[]
    if case=='exact-installed':
        assert result['error'] is None
        assert json.loads(got.out)=={'helper_sha256':PIN,'helper_installed':True,'api_override_installed':False,'services_restarted':False}
    else:assert result['error'] and got.out==''
