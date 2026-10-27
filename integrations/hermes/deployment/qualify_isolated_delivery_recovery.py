"""One retained native adapter/crash/peer-boundary qualification, no live sends."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import subprocess
import tempfile
import uuid

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE=BASE/'operator-launch-completion-batch-v2'
ARTIFACT=BASE/'operator-isolated-delivery-recovery-v1'
NATIVE_QUAL_SHA='024c69cdf3f097624dd17948fe502e898b16a5e8cece5233d23e3d6ff31acdb9'
PUBLIC={'isolated_gateway_transport.py': '543a712ebe8ab95bdd9ab48bb202e71be116e5a51ea138236f0a4baa6acf9711', 'isolated_native_text_ingress.py': '579122e02485597535f71fd6f8f40250a6a231e1dd6e99a4bab7f95689fa88a9', 'probe_isolated_native_text_ingress.py': '7afcbc1804bb1eca4d4ff95f244abea615f52074b6f8c4165d478100c84536b3', 'isolated_delivery_journal.py': 'e047170f33f87ab7788c29d8ad4c41d9748a6a641341404d7c3d6e8f241551d4', 'probe_isolated_delivery_recovery.py': '690f21e53e757da388ce5bdb11b5a9f1cb1878bb6b923413bd9396dbedcf8d7d'}
BASE_ADAPTER_SHA='e2ab51d8ae41933741644d65b87bdeabbf20a641d218b055f681ea96d245340e'
PHASES={
    'initial':(73,{'native_base_adapter_text_component_qualified','reservation_fsynced_before_forced_exit'}),
    'restart':(74,{'completed_handler_not_replayed','interrupted_reservation_not_replayed','send_started_fsynced_before_forced_exit'}),
    'finish':(0,{'ambiguous_send_not_replayed','journal_metadata_only','interrupted_evidence_preserved'}),
    'peer':(0,{'peer_os_access_denied'}),
}


def require(value):
    if not value:raise ValueError('isolated_delivery_recovery_refused')


def definitions(path,digest):
    raw=path.read_bytes()
    require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    scope={'__name__':'verified_delivery_recovery_support','__file__':str(path)}
    exec(compile(raw,'<verified-delivery-recovery-support>','exec'),scope)
    return scope


def prior_native_pass(read,native,transport,rows):
    context=json.loads(read(native['ARTIFACT']/'context.private.json',0))
    require(context.get('source_sha256')==NATIVE_QUAL_SHA and context.get('component_hashes')==native['PUBLIC']
        and context.get('native_source_hashes')==native['NATIVE']
        and read(native['ARTIFACT']/'selected-bindings.private.json',0)==transport['canonical'](rows))
    binding=hashlib.sha256(transport['canonical'](rows)).hexdigest()
    require(context.get('bindings_sha256')==binding)
    evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('isolated-native-text-'))
    result=json.loads(read(evidence/'summary.json',0))
    require(result.get('complete') is True and result.get('operator_helper_sha256')==NATIVE_QUAL_SHA
        and result.get('source_revision')==BASE.name and result.get('component_hashes')==native['PUBLIC']
        and result.get('binding_manifest_sha256')==binding and result.get('distinct_restricted_uids')==2
        and result.get('native_dm_text_ingress_component_qualified') is True
        and result.get('native_authorization_and_pending_clarification_preserved') is True
        and result.get('all_admission_policies_preserved_disabled') is True
        and result.get('fleet_launch_approved') is False)
    return str(evidence)


def receipt(value,phase,status):
    expected,flags=PHASES[phase]
    require(status==expected and isinstance(value,dict) and set(value)==flags|{'complete','phase'}
        and value.get('phase')==phase and value.get('complete') is True
        and all(value.get(key) is True for key in flags))
    return value


def run_phase(phase,rows,run_id,transport,helper):
    account=pwd.getpwnam(rows[0 if phase=='peer' else 1]['user'])
    packet=dict(uid=account.pw_uid,gid=account.pw_gid,worker_uid=rows[1]['uid'],
        profile_id=rows[1]['user'][6:],run_id=run_id,phase=phase)
    source=("def child():\n import sys\n sys.path.insert(0,"+repr(str(ARTIFACT))+")\n"
        " from probe_isolated_delivery_recovery import main\n raise SystemExit(main())\n").encode()
    code,line=helper['owner_program'](source)
    process=subprocess.Popen(['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--',
        transport['EXECUTABLE'],'-I','-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        cwd='/',user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    try:
        process.stdin.write(line+transport['canonical'](packet)+b'\n');process.stdin.flush();process.stdin.close()
        process.wait(timeout=80)
        raw=process.stdout.read(4097)
        require(len(raw)<=4096)
        try:value=json.loads(raw)
        except (ValueError,UnicodeError):value=None
        try:return receipt(value,phase,process.returncode)
        except ValueError:
            diagnostic=dict(phase=phase,exit_code=process.returncode,error_kind='other')
            if isinstance(value,dict):
                if isinstance(value.get('phase'),str) and value['phase'] in {*PHASES,'identity','native_imports','native_adapter_pipeline'}:
                    diagnostic['child_phase']=value['phase']
                if isinstance(value.get('error_kind'),str) and value['error_kind'] in {
                        'ValueError','PermissionError','JournalError','AttributeError','TypeError','TimeoutError'}:
                    diagnostic['error_kind']=value['error_kind']
                counts=value.get('denied_attempt_counts')
                if isinstance(counts,dict) and set(counts)=={'network','real_profile','subprocess'} and all(
                        type(number) is int and 0<=number<=4096 for number in counts.values()):
                    diagnostic['denied_attempt_counts']=counts
            error=ValueError('delivery_owner_phase_incomplete');error.child_diagnostic=diagnostic;raise error
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        for stream in (process.stdin,process.stdout):
            if stream:stream.close()


def main():
    require(os.geteuid()==0)
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory=Path(__file__).parent
    native=definitions(directory/'qualify_isolated_native_text_ingress.py',NATIVE_QUAL_SHA)
    transport=definitions(directory/'qualify_isolated_gateway_transport.py',native['TRANSPORT_QUAL_SHA'])
    support=definitions(PACKAGE/'recover_launch_graph_operator.py',transport['SUPPORT_SHA'])
    read,write,canonical=support['read_file'],support['private_write'],transport['canonical']
    source=globals()['_verified_source_bytes'];source_sha=hashlib.sha256(source).hexdigest()
    require(set(PUBLIC)=={'isolated_gateway_transport.py','isolated_native_text_ingress.py',
        'probe_isolated_native_text_ingress.py','isolated_delivery_journal.py','probe_isolated_delivery_recovery.py'})
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0))
        require(context.get('source_sha256')==source_sha and context.get('component_hashes')==PUBLIC
            and hashlib.sha256(read(ARTIFACT/'qualify_isolated_delivery_recovery.py',0)).hexdigest()==source_sha
            and hashlib.sha256(read(ARTIFACT/'selected-bindings.private.json',0)).hexdigest()==context.get('bindings_sha256'))
        for name,digest in PUBLIC.items():require(hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==digest)
        evidence=Path(context['evidence'])
        require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('isolated-delivery-'))
        result=json.loads(read(evidence/'summary.json',0))
        require(result.get('operator_helper_sha256')==source_sha and result.get('source_revision')==BASE.name
            and result.get('binding_manifest_sha256')==context['bindings_sha256'])
        print(json.dumps(result),flush=True)
        return 0 if result.get('complete') is True else 1
    policy=definitions(PACKAGE/'fleet_credential_policy.py',transport['POLICY_SHA'])
    rows=transport['admission'](read,policy)
    previous=prior_native_pass(read,native,transport,rows)
    protected=definitions(PACKAGE/'renew_fleet_credentials.py',
        '146f340ad9258179bf3555f8949ce08ba66aff5554264537603244018d4e7495')['protected']
    executable=Path(transport['EXECUTABLE'])
    protected(executable,final_link=True);protected(executable.resolve(strict=True));protected(Path('/usr/bin/setpriv'))
    native_pins=dict(native['NATIVE'],**{'gateway/platforms/base.py':BASE_ADAPTER_SHA})
    for name,digest in native_pins.items():
        path=executable.parent.parent.parent/'repo'/name
        protected(path);require(hashlib.sha256(path.read_bytes()).hexdigest()==digest)
    components={name:(directory/name).read_bytes() for name in PUBLIC}
    require(all(hashlib.sha256(raw).hexdigest()==PUBLIC[name] for name,raw in components.items()))
    require(not os.path.lexists(ARTIFACT));ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    write(ARTIFACT/'qualify_isolated_delivery_recovery.py',source)
    for name,raw in components.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    bindings=canonical(rows);write(ARTIFACT/'selected-bindings.private.json',bindings)
    evidence=Path(tempfile.mkdtemp(prefix='isolated-delivery-',dir=BASE/'operator-evidence'))
    context=dict(source_sha256=source_sha,component_hashes=PUBLIC,bindings_sha256=hashlib.sha256(bindings).hexdigest(),
        evidence=str(evidence),run_id=uuid.uuid4().hex,native_source_hashes=native_pins)
    write(ARTIFACT/'context.private.json',canonical(context))
    helper=definitions(PACKAGE/'qualify_launch_isolated_accounts.py',transport['HELPER_SHA'])
    before=read(BASE/'operator-named-fleet-issuer-review-v1/candidate-policy.json',0)
    result=dict(complete=False,source_revision=BASE.name,evidence=str(evidence),operator_helper_sha256=source_sha,
        component_hashes=PUBLIC,binding_manifest_sha256=context['bindings_sha256'],reused_native_evidence=previous,
        qualification_surface='invented_native_adapter_and_process_crash_recovery',completed_phases=0,
        automatic_retry=False,credentials_issued=0,keys_read=False,source_profiles_changed=False,
        real_profile_contents_read=False,services_installed=False,platform_adapters_started=0,
        external_platform_sends=0,model_called=False,memory_api_called=False,canonical_memory_edits=False,
        production_dispatch_qualified=False,native_gateway_integration_qualified=False,
        actual_profile_admission_qualified=False,fleet_launch_approved=False)
    try:
        for phase in PHASES:
            print(json.dumps(dict(event='isolated_delivery_progress',phase=phase)),flush=True)
            write(evidence/(phase+'.started.json'),canonical(dict(phase=phase)))
            report=run_phase(phase,rows,context['run_id'],transport,helper)
            write(evidence/(phase+'.receipt.json'),canonical(report));result['completed_phases']+=1
        require(read(BASE/'operator-named-fleet-issuer-review-v1/candidate-policy.json',0)==before)
        result.update(complete=True,durable_no_replay_component_qualified=True,
            native_base_adapter_text_component_qualified=True,peer_journal_os_denial_qualified=True,
            two_actual_forced_process_exits=True,all_admission_policies_preserved_disabled=True)
    except (Exception,KeyboardInterrupt) as error:
        result.update(category='delivery_recovery_incomplete_preserve_evidence_no_automatic_retry',
            error_kind=type(error).__name__ if type(error).__name__ in
                {'ValueError','PermissionError','TimeoutExpired','KeyboardInterrupt'} else 'other')
        if isinstance(getattr(error,'child_diagnostic',None),dict):result['child_diagnostic']=error.child_diagnostic
    write(evidence/'summary.json',canonical(result));print(json.dumps(result),flush=True)
    return 0 if result['complete'] else 1
