"""Public archive integrity, bounded MCP protocol and trusted service receipts."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import stat
import sys
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
BUNDLE=runpy.run_path(str(FOLDER/'mcp_public_programs.py'))
PROBE=runpy.run_path(str(FOLDER/'probe_main_local_mcp.py'))
ROOT=runpy.run_path(str(FOLDER/'qualify_main_local_mcp.py'))


@pytest.fixture
def library(monkeypatch):
    monkeypatch.setitem(BUNDLE['library'].__globals__,'LIB',FOLDER/'public_program_snapshot.py')
    return BUNDLE['library']()


def package_tree(tmp_path):
    source=tmp_path/'package';source.mkdir(mode=0o700)
    prefix=source/'node_modules/@modelcontextprotocol/server-filesystem';prefix.mkdir(parents=True)
    (prefix/'dist').mkdir();(prefix/'dist/index.js').write_text('// invented public fixture\n')
    (prefix/'package.json').write_text(json.dumps({'name':'@modelcontextprotocol/server-filesystem','version':'2026.8.31'}))
    return source,prefix


@pytest.mark.parametrize('damage',[None,'version','entry','private_file','escape_link','hardlink','unlisted_top'])
def test_public_package_archive_refuses_unsafe_or_unpinned_bytes(library,tmp_path,damage):
    source,prefix=package_tree(tmp_path)
    if damage=='version':(prefix/'package.json').write_text('{"name":"@modelcontextprotocol/server-filesystem","version":"wrong"}')
    if damage=='entry':(prefix/'dist/index.js').rename(prefix/'dist/renamed.js')
    if damage=='private_file':(prefix/'.env').write_text('invented_do_not_publish')
    if damage=='escape_link':(prefix/'escape').symlink_to('/etc/passwd')
    if damage=='hardlink':os.link(prefix/'dist/index.js',prefix/'linked.js')
    if damage=='unlisted_top':(source/'.npmrc').write_text('invented_do_not_publish')
    if damage:
        with pytest.raises(ValueError):library['capture'](source,'filesystem')
    else:
        body,receipt=library['capture'](source,'filesystem')
        manifest=library['validate'](body,'filesystem')
        assert manifest['metadata']['version']=='2026.8.31' and receipt['source_preserved'] is True
        destination=tmp_path/'protected-copy';library['restore'](body,'filesystem',destination)
        library['verify'](destination,manifest)
        (destination/'node_modules/@modelcontextprotocol/server-filesystem/dist/index.js').write_text('changed')
        with pytest.raises(ValueError):library['verify'](destination,manifest)


def test_group_writable_cache_is_copied_privately_without_chmod_source(library,monkeypatch,tmp_path):
    source,prefix=package_tree(tmp_path);source.chmod(0o775)
    original=library['source_root']
    library['source_root']=lambda path,**kw:os.open(source,os.O_RDONLY|os.O_DIRECTORY)
    monkeypatch.setitem(BUNDLE['stage_cache'].__globals__,'library',lambda:library)
    before=(source.stat().st_mode,(prefix/'dist/index.js').read_bytes())
    private=BUNDLE['stage_cache']('filesystem')
    assert stat.S_IMODE(private.stat().st_mode)==0o700
    assert (source.stat().st_mode,(prefix/'dist/index.js').read_bytes())==before
    assert (private/'node_modules/@modelcontextprotocol/server-filesystem/dist/index.js').read_bytes()==before[1]
    library['source_root']=original
    library['validate'](library['capture'](private,'filesystem')[0],'filesystem')


@pytest.mark.parametrize('mode',['ok','sampling','oversize','silent'])
def test_stdio_protocol_is_bounded_and_never_services_server_requests(monkeypatch,tmp_path,mode):
    code='''import json,sys,time
mode=sys.argv[1]
for line in sys.stdin:
 v=json.loads(line)
 if 'id' not in v:continue
 if mode=='silent':continue
 if mode=='sampling':print(json.dumps({'jsonrpc':'2.0','id':77,'method':'sampling/createMessage','params':{}}),flush=True);continue
 result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}}} if v['method']=='initialize' else {'tools':[{'name':'invented_read','inputSchema':{'type':'object'}}]}
 if mode=='oversize':result['padding']='x'*1000
 print(json.dumps({'jsonrpc':'2.0','id':v['id'],'result':result}),flush=True)
'''
    scope=PROBE['Client'].response.__globals__
    if mode=='oversize':monkeypatch.setitem(scope,'MAX_REPLY',128)
    client=PROBE['Client']([sys.executable,'-I','-B','-c',code,mode],{'PATH':'/usr/bin:/bin'},tmp_path)
    if mode=='silent':client.deadline=PROBE['time'].monotonic()+0.1
    try:
        if mode=='ok':assert PROBE['handshake'](client)=={'invented_read'}
        else:
            with pytest.raises((ValueError,TimeoutError)):PROBE['handshake'](client)
    finally:client.close()
    assert client.process.poll() is not None


def component_receipt():
    return dict(complete=True,invocation_id='a'*32,real_profiles_read=False,credentials_read=False,
        model_called=False,memory_api_called=False,external_sends=0,full_main_tool_coverage_qualified=False,
        cases=dict(filesystem=dict(complete=True,initialize_passed=True,tools_list_passed=True,tools_count=14,tools_called=4,
            invented_write_read_passed=True,outside_root_denied=True),
            rea=dict(complete=True,initialize_passed=True,tools_list_passed=True,tools_count=20,tools_called=0,binary_analysis_requested=False)))


@pytest.mark.parametrize('damage',[None,'pid','uid','invocation','duplicate','model','full_coverage','boolean_count','missing_denial','exit_mismatch'])
def test_only_exact_invocation_process_and_bounded_component_receipt_is_accepted(monkeypatch,damage):
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_uid=992))
    value=component_receipt();state=dict(InvocationID='a'*32,ExecMainPID='88',Result='success',ExecMainStatus='0')
    row={'_SYSTEMD_INVOCATION_ID':'a'*32,'_PID':'88','_UID':'992','_TRANSPORT':'stdout'}
    if damage=='pid':row['_PID']='89'
    if damage=='uid':row['_UID']='1000'
    if damage=='invocation':row['_SYSTEMD_INVOCATION_ID']='b'*32
    if damage=='model':value['model_called']=True
    if damage=='full_coverage':value['full_main_tool_coverage_qualified']=True
    if damage=='boolean_count':value['cases']['rea']['tools_count']=True
    if damage=='missing_denial':value['cases']['filesystem']['outside_root_denied']=False
    if damage=='exit_mismatch':state['Result']='exit-code';state['ExecMainStatus']='1'
    row['MESSAGE']=json.dumps(value);rows=[row,row] if damage=='duplicate' else [row]
    if damage:
        with pytest.raises(ValueError):ROOT['journal_receipt'](rows,state)
    else:assert ROOT['journal_receipt'](rows,state)==value


def test_partial_component_pass_is_preserved_without_claiming_full_pass():
    value=component_receipt();value['complete']=False;value['cases']['rea']={'complete':False,'error_kind':'ValueError'}
    assert ROOT['validate_probe'](value,'a'*32)==value
    value['complete']=True
    with pytest.raises(ValueError):ROOT['validate_probe'](value,'a'*32)


@pytest.mark.parametrize('damage',[None,'revision','not_stopped','partial_restore','references','boolean_counter','source_changed','replay'])
def test_completed_main_candidate_pass_is_required_before_new_effects(damage):
    value=dict(source_revision=ROOT['BASE'].name,operator_helper_sha256=ROOT['SUPPORT_SHA'],
        evidence=str(ROOT['PASSED'].parent),checkpoint='complete',
        new_inactive_candidate='/var/lib/enhanced-cognee-profiles/5592956882ea9a13/ec-main-operational-restore-dzqxxbdg',
        mcp_definitions_preserved=6,sqlite_databases_recovered=9,remaining_reference_count=0,credentials_issued=2,encrypted_generations_created=2)
    value.update({k:True for k in ('complete','configured_candidate_restore_qualified','operator_job_stopped',
        'inactive_current_settings_preservation_qualified','prior_dependency_pass_preserved','rea_dependency_execution_qualified',
        'telegram_configuration_preserved_inactive_only','all_admission_policies_preserved_disabled',
        'current_auth_snapshot_preserved','source_current_at_completion')})
    value.update({k:False for k in ('candidate_promoted','source_profiles_changed','previous_candidates_changed',
        'programs_replayed','fleet_launch_approved','fleet_settings_accepted','telegram_activation_qualified')})
    if damage=='revision':value['source_revision']='wrong'
    if damage=='not_stopped':value['operator_job_stopped']=False
    if damage=='partial_restore':value['configured_candidate_restore_qualified']=False
    if damage=='references':value['remaining_reference_count']=1
    if damage=='boolean_counter':value['remaining_reference_count']=False
    if damage=='source_changed':value['source_profiles_changed']=True
    if damage=='replay':value['programs_replayed']=True
    if damage:
        with pytest.raises(ValueError):ROOT['retained'](lambda *a:json.dumps(value).encode())
    else:assert ROOT['retained'](lambda *a:json.dumps(value).encode())==value


def test_proof_uses_kernel_network_and_home_isolation_and_always_stops(monkeypatch,tmp_path):
    scope=ROOT['proof'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir();programs_root=tmp_path/'programs';programs_root.mkdir()
    raw=b'# invented driver fixture\n';(artifact/'probe_main_local_mcp.py').write_bytes(raw)
    for name,value in dict(ARTIFACT=artifact,PROGRAM_ROOT=programs_root,PROBE_SHA=hashlib.sha256(raw).hexdigest()).items():monkeypatch.setitem(scope,name,value)
    state=dict(LoadState='not-found',ActiveState='inactive',SubState='dead')
    called=[];value=component_receipt()
    def run(args,**kw):
        called.append(args)
        if args[0]=='/usr/bin/systemd-run':
            assert '--property=PrivateNetwork=yes' in args and '--property=ProtectHome=yes' in args
            assert '--property=RestrictAddressFamilies=AF_UNIX' in args and '--property=CapabilityBoundingSet=' in args
            assert '--property=StandardError=null' in args and '--property=KillMode=control-group' in args
            assert any(arg.startswith('--property=InaccessiblePaths=/var/lib/enhanced-cognee-profiles ') for arg in args)
            state.update(LoadState='loaded',ActiveState='active',SubState='exited',User='ecbot_5592956882ea9a13',
                PrivateNetwork='yes',ProtectHome='yes',NoNewPrivileges='yes',CapabilityBoundingSet='',AmbientCapabilities='',
                RestrictAddressFamilies='AF_UNIX',IPAddressDeny='any',InvocationID='a'*32,ExecMainPID='88',Result='success',ExecMainStatus='0')
        if args[0]=='/usr/bin/systemctl':state.update(ActiveState='inactive',SubState='dead')
        row={'_SYSTEMD_INVOCATION_ID':'a'*32,'_PID':'88','_UID':'992','_TRANSPORT':'stdout','MESSAGE':json.dumps(value)}
        return SimpleNamespace(stdout=json.dumps(row).encode()+b'\n',returncode=0)
    monkeypatch.setitem(scope,'metadata',lambda unit:copy.deepcopy(state));monkeypatch.setattr(ROOT['subprocess'],'run',run)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_uid=992))
    account=SimpleNamespace(pw_name='ecbot_5592956882ea9a13',pw_gid=984)
    result=ROOT['proof']({'id':'c'*32},account,{'filesystem':'/invented/filesystem','rea':'/invented/rea'},lambda path,data:path.write_bytes(data))
    assert result==value and state['ActiveState']=='inactive'
    assert sum(args[0]=='/usr/bin/systemd-run' for args in called)==1
    assert called[-1][0:2]==['/usr/bin/systemctl','stop']


def test_source_pins_and_archive_protocol():
    assert hashlib.sha256((FOLDER/'mcp_public_programs.py').read_bytes()).hexdigest()==ROOT['OWNER_SHA']
    assert hashlib.sha256((FOLDER/'probe_main_local_mcp.py').read_bytes()).hexdigest()==ROOT['PROBE_SHA']
    assert hashlib.sha256((FOLDER/'public_program_snapshot.py').read_bytes()).hexdigest()==ROOT['SNAPSHOT_SHA']
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'mcp_public_programs.py').read_bytes())
