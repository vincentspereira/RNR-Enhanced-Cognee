"""Encrypted recovery of the fixed protected Hermes program, no live switch.

One finite job, one new generation, one new program copy and one transient
namespace probe. Repeating launch reattaches. No owner profiles are traversed;
root handles only its own immutable program files and protected recovery keys.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RELEASE=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
ARTIFACT=BASE/'operator-program-recovery-v1'
UNIT='ec-launch-program-recovery-20261027.service'
BACKUPS=Path('/var/backups/enhanced-cognee')
FIXTURES=Path('/var/lib/hermes-renewal-qualification')
AGE='/usr/local/bin/age'
IDENTITY='/etc/enhanced-cognee/age-recovery-identity.txt'
MANIFEST_SHA='b8b07343b2e16228c9a2673eecd14cebbf88b327c7c0e1b45bebe3c61d5e67ce'
CORE_SHA='9156fa2e2c0b85b110c1f820f6121ca01f2d29e5a5285c29d28d8c6be6843d9b'
SUPPORT_SHA='d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'


def require(value):
    if not value:raise ValueError('program_recovery_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_program_recovery_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-public-program-recovery>','exec'),value);return value


def digest_file(path):
    size=0;hasher=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(1024*1024):
            size+=len(data);require(size<=4*1024**3);hasher.update(data)
    return hasher.hexdigest(),size


def public_manifest(core):
    root=core['directory'](RELEASE,0)
    try:
        fd=os.open('snapshot-files.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=root)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());core['protected'](before,0)
            require(0<before.st_size<=16*1024*1024)
            raw=stream.read(16*1024*1024+1)
            require(len(raw)==before.st_size and core['stamp'](before)==core['stamp'](os.fstat(stream.fileno()))
                and hashlib.sha256(raw).hexdigest()==MANIFEST_SHA)
            return raw
    finally:os.close(root)


def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def probe_code(fixture,expected):
    # Public code and inode metadata only. No credential or owner settings are
    # sent to this restricted process. The original /opt path is rebound ONLY
    # inside this transient unit to the new recovered tree.
    return ("import contextlib,io,json,logging,os,pathlib,pwd,socket,sys\n"
        "logging.disable(logging.CRITICAL)\n"
        "def denied(*a,**k):raise RuntimeError('program_probe_network_refused')\n"
        "socket.socket.connect=socket.socket.connect_ex=socket.getaddrinfo=denied\n"
        f"root=pathlib.Path({str(RELEASE)!r});home=pathlib.Path({str(fixture)!r})\n"
        "os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=str(home),HERMES_HOME=str(home),PYTHONDONTWRITEBYTECODE='1')\n"
        "fields=dict(x.split(':',1) for x in pathlib.Path('/proc/self/status').read_text().splitlines())\n"
        "assert os.geteuid()==pwd.getpwnam('hermes-runtime').pw_uid!=0\n"
        "assert fields['NoNewPrivs'].strip()=='1' and fields['CapEff'].strip()==fields['CapAmb'].strip()=='0000000000000000'\n"
        f"expected={expected!r}\n"
        "for name,value in expected.items():\n"
        " info=(root/name).stat();assert (info.st_dev,info.st_ino)==tuple(value)\n"
        "sys.path.insert(0,str(root/'repo'))\n"
        "with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):\n"
        " import run_agent,hermes_cli.main,sqlite3,ssl,openai\n"
        " assert pathlib.Path(run_agent.__file__).is_relative_to(root/'repo')\n"
        " assert pathlib.Path(openai.__file__).is_relative_to(root/'venv')\n"
        " assert sqlite3.connect(':memory:').execute('SELECT 1').fetchone()==(1,)\n"
        "print(json.dumps({'complete':True,'recovered_program_imported':True,'new_copy_inodes_verified':True,'restricted_identity_verified':True,'model_called':False,'profiles_read':False,'network_used':False}))\n")


def native_probe(destination,fixture,ident):
    expected={}
    for name in ('repo/run_agent.py','venv/pyvenv.cfg','python/bin/python3.14'):
        info=(destination/name).stat();expected[name]=(info.st_dev,info.st_ino)
    settings=dict(User='hermes-runtime',Group='hermes-runtime',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='',AmbientCapabilities='',ProtectHome='yes',ProtectSystem='strict',
        PrivateTmp='yes',PrivateNetwork='yes',RestrictAddressFamilies='AF_UNIX',ProtectProc='invisible',
        InaccessiblePaths='/etc/enhanced-cognee /var/lib/hermes-runtime /var/lib/enhanced-cognee-profiles /root',
        BindReadOnlyPaths=str(destination)+':'+str(RELEASE),ReadWritePaths=str(fixture),
        RuntimeMaxSec='60',MemoryMax='1G',LimitCORE='0',Restart='no')
    args=['/usr/bin/systemd-run','--quiet','--wait','--pipe','--collect','--unit=ec-program-copy-'+ident]
    args+=['--property='+k+'='+v for k,v in settings.items()]
    args+=[str(RELEASE/'venv/bin/python'),'-I','-B','-c',probe_code(fixture,expected)]
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=90,cwd='/',
        env={'PATH':'/usr/bin:/bin','HOME':'/','LANG':'C.UTF-8'})
    require(result.returncode==0 and 0<len(result.stdout)<=4096)
    value=json.loads(result.stdout)
    require(value==dict(complete=True,recovered_program_imported=True,new_copy_inodes_verified=True,
        restricted_identity_verified=True,model_called=False,profiles_read=False,network_used=False))
    return value


def worker(read,write):
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    context=json.loads(read(ARTIFACT/'context.json',0));ident=context['run_id'];require(len(ident)==32 and all(c in '0123456789abcdef' for c in ident))
    evidence=Path(context['evidence']);require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('program-recovery-'))
    fixture=FIXTURES/('program_'+ident)
    core=definitions(ARTIFACT/'program_snapshot_recovery.py',CORE_SHA)
    raw=public_manifest(core)
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,profiles_read=False,
        profiles_changed=False,services_changed=False,model_called=False,credentials_issued=0,
        keys_changed=False,fleet_launch_approved=False,actual_profile_admission_qualified=False,
        full_profile_recovery_qualified=False,fresh_machine_source_build_qualified=False,
        generation_write_started=False,encrypted_generation_created=False,new_program_restore_started=False,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(evidence/'started.json',canonical(result));phase='encrypted_capture';process=None
    try:
        settings=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
        recipient,key,key_id=(settings[k] for k in ('ENHANCED_BACKUP_RECIPIENT','ENHANCED_BACKUP_SIGNING_KEY','ENHANCED_BACKUP_SIGNING_KEY_ID'))
        require(isinstance(key,str) and len(key.encode())>=32 and isinstance(key_id,str));del settings
        generation=BACKUPS/('hermes_program_'+ident+'.tar.age');result['generation_write_started']=True
        write(evidence/'generation.started.json',canonical({'generation':str(generation)}))
        fd=os.open(generation,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as out:
            process=subprocess.Popen([AGE,'--encrypt','--recipient',recipient],stdin=subprocess.PIPE,stdout=out,
                stderr=subprocess.DEVNULL,cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
            try:
                captured=core['capture'](RELEASE,raw,process.stdin)
                process.stdin.close();require(process.wait(timeout=120)==0)
                out.flush();os.fsync(out.fileno())
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
        phase='generation_authentication'
        digest,size=digest_file(generation)
        manifest=dict(complete=True,format='hermes-protected-program+age-v1',ciphertext_sha256=digest,
            ciphertext_bytes=size,program_manifest_sha256=MANIFEST_SHA,capture_component_sha256=CORE_SHA,
            signing_key_id=key_id,receipt=captured)
        manifest['signature']=hmac.new(key.encode(),canonical(manifest),hashlib.sha256).hexdigest()
        write(generation.with_name(generation.name+'.json'),canonical(manifest));sync(BACKUPS)
        saved=json.loads(read(generation.with_name(generation.name+'.json'),0))
        require(saved==manifest and digest_file(generation)==(digest,size)
            and hmac.compare_digest(saved['signature'],hmac.new(key.encode(),canonical({k:v for k,v in saved.items() if k!='signature'}),hashlib.sha256).hexdigest()))
        del key;result['encrypted_generation_created']=True;result['generation']=str(generation)
        phase='new_program_restore';result['new_program_restore_started']=True
        destination=ARTIFACT/'restored-program'
        with generation.open('rb') as encrypted:
            process=subprocess.Popen([AGE,'--decrypt','--identity',IDENTITY],stdin=encrypted,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
            try:
                restored=core['restore'](process.stdout,destination,MANIFEST_SHA)
                while process.stdout.read(1024*1024):pass
                require(process.wait(timeout=120)==0)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
        require(all(restored[k]==captured[k] for k in ('files','links','bytes','manifest_sha256')))
        write(evidence/'restore.summary.json',canonical(restored))
        phase='restricted_namespace_execution'
        probe=native_probe(destination,fixture,ident);write(evidence/'namespace-probe.summary.json',canonical(probe))
        result.update(complete=True,program_snapshot_restore_qualified=True,recovered_program_execution_qualified=True,
            program_files_verified=restored['files'],program_links_verified=restored['links'],program_bytes_verified=restored['bytes'],
            original_program_preserved=True,isolated_namespace_used=True)
    except Exception as error:
        result.update(category='program_recovery_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase,
            error_kind=type(error).__name__ if type(error).__name__ in {'ProgramRecoveryError','ValueError','PermissionError','FileNotFoundError','TimeoutExpired','OSError'} else 'other')
    write(evidence/'summary.json',canonical(result));sync(evidence)
    return 0 if result['complete'] else 1


def properties():
    r=subprocess.run(['/usr/bin/systemctl','show',UNIT,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    return dict(line.split('=',1) for line in r.stdout.decode().splitlines() if '=' in line)


def stopped(value):return value.get('ActiveState') in {'inactive','failed'} and value.get('MainPID')==value.get('ControlPID')=='0'


def watch(read):
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence']);last=0
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('program-recovery-'))
    try:
        while True:
            value=properties()
            try:result=json.loads(read(evidence/'summary.json',0))
            except FileNotFoundError:result=None
            if result is not None or value.get('ActiveState')=='failed' or value.get('SubState')=='exited':
                result=result or dict(complete=False,evidence=str(evidence),category='program_worker_exited_preserve_evidence')
                if not stopped(value):subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=True)
                result['operator_job_stopped']=stopped(properties());result['complete']=result.get('complete') is True and result['operator_job_stopped']
                print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            if stopped(value):print(json.dumps(dict(complete=False,evidence=str(evidence),category='program_job_not_running_preserve_evidence')),flush=True);return 1
            if time.monotonic()-last>=15:
                print('{"event":"program_recovery_running","note":"Ctrl+C detaches; repeat qualify-program-recovery to reattach."}',flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def launch():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    support=definitions(directory/'recover_launch_graph_operator.py',SUPPORT_SHA);read,write=support['read_file'],support['private_write']
    if os.path.lexists(ARTIFACT):return watch(read)
    require(properties().get('LoadState')=='not-found' and stopped(properties()) and shutil.disk_usage(BACKUPS).free>=8*1024**3)
    driver=definitions(BASE/'operator-issuer-candidate-v2/renew_fleet_credentials.py','a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path in (RELEASE/'snapshot-files.json',Path(AGE),Path(IDENTITY),BACKUPS,FIXTURES):driver['protected'](path)
    require(hashlib.sha256((RELEASE/'snapshot-files.json').read_bytes()).hexdigest()==MANIFEST_SHA)
    require(json.loads(read(BASE/'operator-evidence/main-operational-recovery-0xjyrv2b/summary.json',0)).get('complete') is True)
    account=pwd.getpwnam('hermes-runtime');ident=uuid.uuid4().hex;fixture=FIXTURES/('program_'+ident)
    fixture.mkdir(mode=0o700);os.chown(fixture,account.pw_uid,account.pw_gid)
    core=definitions(directory/'program_snapshot_recovery.py',CORE_SHA)
    evidence=Path(tempfile.mkdtemp(prefix='program-recovery-',dir=BASE/'operator-evidence'));ARTIFACT.mkdir(mode=0o700)
    sources={Path(__file__).name:globals()['_verified_source_bytes'],'program_snapshot_recovery.py':core['_verified_source_bytes'],
        'recover_launch_graph_operator.py':support['_verified_source_bytes']}
    for name,raw in sources.items():write(ARTIFACT/name,raw)
    write(ARTIFACT/'sources.json',canonical({k:hashlib.sha256(v).hexdigest() for k,v in sources.items()}))
    write(ARTIFACT/'context.json',canonical(dict(evidence=str(evidence),run_id=ident)));sync(ARTIFACT)
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='',AmbientCapabilities='',ProtectHome='yes',ProtectSystem='strict',PrivateTmp='yes',
        ReadWritePaths=' '.join(map(str,[ARTIFACT,BASE/'operator-evidence',BACKUPS])),Restart='no',TimeoutStartSec='900',MemoryMax='1G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+k+'='+v for k,v in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/Path(__file__).name),'--worker']
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=True)
    return watch(read)


if __name__=='__main__':
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        require(sys.argv[1:]==['--worker'])
        support=definitions(ARTIFACT/'recover_launch_graph_operator.py',SUPPORT_SHA)
        raise SystemExit(worker(support['read_file'],support['private_write']))
    except Exception:
        print('{"complete":false,"category":"program_recovery_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
