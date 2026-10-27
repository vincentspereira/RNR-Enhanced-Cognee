"""Content-free permission diagnosis, narrowly admitted repair, no replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
REPAIR = runpy.run_path(str(DIRECTORY / 'repair_launch_fleet_backup.py'), run_name='backup_repair_tests')


def old_scope():
    source=(DIRECTORY/'install_launch_fleet_backups.py').read_bytes()
    scope={'__name__':'old_backup_test_scope','__file__':str(DIRECTORY/'install_launch_fleet_backups.py'), '_verified_source_bytes':source}
    exec(compile(source,'<old-backup-test>','exec'),scope)
    return scope


def row():
    return dict(kind='named', entry=dict(executable='/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python'))


def test_probe_replaces_only_owner_body_and_stops_before_any_archive_or_profile_read():
    calls=[]
    def owner(helper, account, source, packet):
        calls.append((source,packet))
        assert source==REPAIR['OWNER_SOURCE'] and packet=={}
        return dict(complete=True,receipt=dict(identity_restricted=True,profile_contents_read=False))
    driver={'definitions':lambda path,digest:{'owner':owner}}
    def capture(actual_driver, actual_row, recipient):
        module=actual_driver['definitions'](Path('/public/backup_launch_candidate_profile.py'),'invented')
        module['owner']({},None,b'must-not-execute-capture-source',{'must-not-read-profile':'invented'})
        pytest.fail('capture continued after content-free probe')
    old={'capture':capture}
    result=REPAIR['diagnose_spawn'](old,driver,row())
    assert result['complete'] and result['child_identity_restricted'] and result['backups_created']==0
    assert not result['profile_contents_read'] and len(calls)==1


def test_permission_diagnostic_retains_errno_and_fixed_path_kind_without_exception_message():
    def owner(*args): raise PermissionError(1,'invented-private-secret-must-not-escape','/usr/bin/setpriv')
    driver={'definitions':lambda path,digest:{'owner':owner}}
    def capture(driver,row,recipient):
        driver['definitions'](Path('/public/backup_launch_candidate_profile.py'),'invented')['owner']({},None,b'ignored',{})
    result=REPAIR['diagnose_spawn']({'capture':capture},driver,row())
    assert result['errno']==1 and result['failed_path_kind']=='identity_launcher'
    assert result['failure_phase']=='restricted_child_spawn' and result['complete'] is False
    assert 'invented-private-secret' not in json.dumps(result)
    assert all(type(line) is int for line in result['helper_lines'])


@pytest.mark.parametrize('damage',[None,'parent_effective','different_phase','different_errno','child_failure',
    'child_privileged','broad_bounding','nnp_missing'])
def test_only_demonstrated_missing_parent_capabilities_and_restricted_child_can_admit_repair(damage):
    baseline=dict(complete=False,failure_phase='restricted_child_spawn',error_kind='PermissionError',errno=1,
        parent_capabilities={'identity_switch_effective':False})
    ambient=dict(complete=True,child_started=True,child_identity_restricted=True,
        parent_capabilities=dict(identity_switch_effective=True,identity_switch_permitted=True,
            bounding_only_identity_switch=True,no_new_privileges=True))
    if damage=='parent_effective':baseline['parent_capabilities']['identity_switch_effective']=True
    if damage=='different_phase':baseline['failure_phase']='public_capture_preflight'
    if damage=='different_errno':baseline['errno']=13
    if damage=='child_failure':ambient['complete']=False
    if damage=='child_privileged':ambient['child_identity_restricted']=False
    if damage=='broad_bounding':ambient['parent_capabilities']['bounding_only_identity_switch']=False
    if damage=='nnp_missing':ambient['parent_capabilities']['no_new_privileges']=False
    assert REPAIR['proven_capability_fix'](baseline,ambient) is (damage is None)


def test_owner_subprocess_only_inserts_capability_drop_for_exact_reviewed_launcher():
    args=['/usr/bin/setpriv','--no-new-privs','--',row()['entry']['executable'],'-I','-B','-c','invented']
    changed=REPAIR['OwnerSubprocess'].arguments(args)
    assert changed==args[:2]+['--inh-caps=-all','--ambient-caps=-all']+args[2:]
    assert args[:3]==['/usr/bin/setpriv','--no-new-privs','--']
    with pytest.raises(ValueError):REPAIR['OwnerSubprocess'].arguments(['/usr/bin/setpriv','--reuid','0'])
    command=['/usr/bin/systemctl','show','invented.service']
    assert REPAIR['OwnerSubprocess'].arguments(command)==command


def test_actual_unprivileged_native_launch_clears_caps_without_reading_any_profile():
    code="import json,os; s=dict(x.split(':',1) for x in open('/proc/self/status') if ':' in x); print(json.dumps({'uid':os.geteuid(),'nnp':s['NoNewPrivs'].strip(),'caps':[s[k].strip() for k in ['CapEff','CapAmb','CapInh']]}))"
    process=REPAIR['OwnerSubprocess']().run(['/usr/bin/setpriv','--no-new-privs','--',row()['entry']['executable'],'-I','-B','-c',code],
        cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    assert process.returncode==0
    value=json.loads(process.stdout)
    assert value['uid']==os.geteuid()!=0 and value['nnp']=='1' and value['caps']==['0000000000000000']*3


def test_repaired_unit_keeps_all_existing_isolation_and_bounding_and_only_changes_parent_ambient():
    old=old_scope()
    members=[dict(entry=dict(home='/var/lib/enhanced-cognee-profiles/'+format(i,'016x'))) for i in range(1,42)]
    before=old['unit_text'](members)[0]
    repaired=REPAIR['repaired_driver'](old)
    after,timer=repaired['unit_text'](members)
    assert b'AmbientCapabilities=CAP_SETUID CAP_SETGID\n' in after
    assert b'CapabilityBoundingSet=CAP_SETUID CAP_SETGID\n' in after
    assert b'InaccessiblePaths=/etc/enhanced-cognee/age-recovery-identity.txt' in after
    assert b'RestrictAddressFamilies=AF_UNIX\n' in after and b'IPAddressDeny=any\n' in after
    assert b'PrivateDevices=yes\n' in after and b'RestrictSUIDSGID=yes\n' in after
    assert b'ProtectHome=yes\n' in after and b'ProtectSystem=strict\n' in after
    assert REPAIR['STATE']!=REPAIR['PREVIOUS'] and REPAIR['UNIT'].encode() in timer
    assert before.replace(b'AmbientCapabilities=\n',b'AmbientCapabilities=CAP_SETUID CAP_SETGID\n').replace(
        b'operator-fleet-daily-backups-v1',b'operator-fleet-daily-backups-v2')==after


def test_finished_probe_is_returned_without_restarting_any_unit(tmp_path, monkeypatch):
    source=tmp_path/'repair_launch_fleet_backup.py';source.write_bytes(b'invented-public-source')
    result=dict(probe='baseline',probe_unit_stopped=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),complete=False)
    (tmp_path/'baseline.finish.json').write_text(json.dumps(result))
    monkeypatch.setitem(REPAIR['run_probe'].__globals__,'DIAGNOSTIC',tmp_path)
    assert REPAIR['run_probe']('baseline',{}, {},lambda path,*args:path.read_bytes(),lambda *a:pytest.fail('rewritten'),[])==result


def test_repair_and_original_sources_match_controller_pins():
    assert hashlib.sha256((DIRECTORY/'install_launch_fleet_backups.py').read_bytes()).hexdigest()==REPAIR['OLD_SHA']
    controller=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='repair_controller_pin')
    assert controller['FLEET_BACKUPS_REPAIR_SHA']==hashlib.sha256((DIRECTORY/'repair_launch_fleet_backup.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('qualified',[True,False])
def test_single_operator_action_never_installs_a_repair_for_an_unproved_failure(tmp_path,monkeypatch,capsys,qualified):
    scope=REPAIR['repair'].__globals__; probe=tmp_path/'probe';probe.mkdir()
    (probe/'repair_launch_fleet_backup.py').write_bytes(b'invented-public-source')
    monkeypatch.setitem(scope,'DIAGNOSTIC',probe);monkeypatch.setitem(scope,'STATE',tmp_path/'new-state')
    monkeypatch.setitem(scope,'_verified_source_bytes',b'invented-public-source')
    calls=[]; driver={}; read=lambda path,*args:path.read_bytes()
    old={'components':lambda:(driver,read,lambda *a:None),'membership':lambda *a:[row()]}
    monkeypatch.setitem(scope,'old_driver',lambda:old)
    monkeypatch.setitem(scope,'retained_failure',lambda *a:calls.append('retained'))
    baseline=dict(complete=False,failure_phase='restricted_child_spawn',error_kind='PermissionError',errno=1,
        parent_capabilities={'identity_switch_effective':not qualified})
    ambient=dict(complete=True,child_started=True,child_identity_restricted=True,
        parent_capabilities=dict(identity_switch_effective=True,identity_switch_permitted=True,
            bounding_only_identity_switch=True,no_new_privileges=True))
    def run_probe(kind,*args): calls.append(kind);return baseline if kind=='baseline' else ambient
    monkeypatch.setitem(scope,'run_probe',run_probe)
    monkeypatch.setitem(scope,'disable_failed_schedule',lambda *a:calls.append('disable'))
    monkeypatch.setitem(scope,'repaired_driver',lambda old:{'install':lambda:calls.append('install') or 0})
    assert REPAIR['repair']()==(0 if qualified else 1)
    assert calls==(['retained','baseline','ambient','disable','install'] if qualified else ['retained','baseline'])
    output=capsys.readouterr().out
    if not qualified:assert json.loads(output)['category']=='backup_permission_diagnosed_no_automatic_repair'


@pytest.mark.parametrize('tamper',[False,True])
def test_failed_timer_is_disabled_only_with_exact_original_units_preserved(tmp_path,monkeypatch,tamper):
    scope=REPAIR['disable_failed_schedule'].__globals__
    units=tmp_path/'units';units.mkdir();probe=tmp_path/'probe';probe.mkdir()
    monkeypatch.setitem(scope,'UNIT_DIRECTORY',units);monkeypatch.setitem(scope,'DIAGNOSTIC',probe)
    name='invented-old-backup';raws=(b'invented-service',b'invented-timer')
    for suffix,raw in zip(('.service','.timer'),raws):(units/(name+suffix)).write_bytes(raw)
    if tamper:(units/(name+'.timer')).write_bytes(b'changed-unit')
    old={'PACKAGE':Path('/public'),'UNIT':name,'unit_text':lambda rows:raws,
        'timer_properties':lambda:dict(ActiveState='inactive',UnitFileState='disabled')}
    driver={'DRIVER_SHA':'invented','definitions':lambda *a:{'protected':lambda path:None}}
    calls=[]
    monkeypatch.setattr(REPAIR['subprocess'],'run',lambda args,**kw:calls.append(args))
    write=lambda path,raw:path.write_bytes(raw)
    if tamper:
        with pytest.raises(ValueError):REPAIR['disable_failed_schedule'](old,driver,write,[])
        assert not calls
    else:
        REPAIR['disable_failed_schedule'](old,driver,write,[])
        assert calls==[['/usr/bin/systemctl','disable','--now',name+'.timer']]
        assert (probe/'original.service').read_bytes()==raws[0] and (probe/'original.timer').read_bytes()==raws[1]
    assert (units/(name+'.service')).read_bytes()==raws[0]
    assert (units/(name+'.timer')).is_file()


@pytest.mark.parametrize('dropin',[False,True])
def test_retained_failure_refuses_unreviewed_unit_overrides(monkeypatch,dropin):
    result=dict(complete=False,error_kind='PermissionError',operator_helper_sha256=REPAIR['OLD_SHA'],
        source_revision=REPAIR['BASE'].name,evidence=str(REPAIR['FAILED']),completed_profiles=0,selected_profiles=41,
        source_profiles_changed=False,keys_changed=False,model_called=False,memory_api_called=False,
        recovery_key_read=False,plaintext_archive_written=False,fleet_launch_approved=False,credentials_issued=0)
    def read(path,*args):
        return json.dumps({'evidence':str(REPAIR['FAILED'])} if path.name=='blocked.json' else result).encode()
    driver={'stopped':lambda value:True,'metadata':lambda unit:{'ActiveState':'inactive'}}
    monkeypatch.setattr(REPAIR['subprocess'],'run',lambda *a,**kw:SimpleNamespace(
        stdout=b'DropInPaths=/unreviewed/override.conf\n' if dropin else b'DropInPaths=\n'))
    monkeypatch.setattr(REPAIR['os'].path,'lexists',lambda path:False)
    if dropin:
        with pytest.raises(ValueError):REPAIR['retained_failure']({'UNIT':'old'},driver,read)
    else:assert REPAIR['retained_failure']({'UNIT':'old'},driver,read)==result
