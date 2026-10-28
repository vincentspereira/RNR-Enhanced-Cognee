"""Consolidated launch control: reconcile interrupted state before resuming.

Inspection changes no profile, credential, canonical record or service. Private
observations stay root-only; terminal output contains bounded progress/counts.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile
import time

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
STAGED = BASE / 'operator-evidence/named-fleet-stage-funaka9d'
BATCH_SHA = '46aea4874b06ffe23bf21a8a5ce8f08cd695dd63557e46d26c6ebc559900a86c'
PROVIDER_SHA = 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
RESUME_SHA = '9d1d87ad5e8695494f2f184b9e32d4112b0aae70315fedf3f0167e1467a1501c'
RUNTIME_SHA = 'd7494b5d7507322b5a0dd731211d3ef00c66122f90a7544961f06d9f75b6933f'
REPAIR_SHA = '1e73ee58a276960130c7f118a63bfbd2e1ea1a81c0e2ab33bfd6b83abd936192'
FINISH_SHA = '6310e49d7d8b4128e3b24d73fcf1093e93433ab702e853a05a0513edbfd8003e'
ROUTES_SHA = '6dbf807c3c4eb4cc9da1834fc3cfc13747f9b7a456997a0e66ce076e6b5fe625'
MAIN_BACKUP_SHA = 'a91b128650b80acf8bcc4d369365daad8d0bba8fdd298e80ffa08e6e4d3e0f9a'
MAIN_CONTINUE_SHA = '547e5bd40aec13c85b3524e15d5732adbfd59b507464182c47f760f7b20c3a25'
CURRENT_MODEL_SHA = '4a9ba1890c56fcf3806e834ee28c6c28686e6137a4f16c33e08cfa70eb535402'
CURRENT_MODEL_V2_SHA = 'e21579372b94a1a881908e543342fbfcd7582d593ac579d7f2b23a1d805dbda1'
CURRENT_MODEL_V3_SHA = '3d8c9d76fe19067289cf53d9587308b315cb23987a41b3db966f2f08a13b1c63'
CURRENT_MODEL_FINISH_SHA = 'ddf3b82e294b7b723463a82a66098fb6d52edd370f9fd1344696368b500a0123'
PROGRAM_RECOVERY_SHA = 'cada57c71e6b651078401412f7cb93b750f5ac056375dde84b4573e8a35630f6'
FLEET_REVIEW_SHA = '554ac7b170a2d9e1a98557fc7c943cac27e2f23f3569d6bbccb899629cc2ec69'
COMPLETION_BATCH_SHA = 'd99a819e0c64a5e0d60632f15c8ff3fb57cbf294c4ed33865605702b5796becc'
COMPLETION_CONTINUE_SHA = '409de8a25e773489874167f325865c11239ef756e0fa342f1396dcf3f0201a5c'
FLEET_BACKUPS_SHA = 'cfd9eb39d10951d56235b25d111352d6bebe527360007f0fff8bbc65f7a77a13'
FLEET_BACKUPS_REPAIR_SHA = '19956e7f031a0e70d9758bb8e9aede7c13f631f44ebfb8b7e50727eec8dcb16b'
ISOLATED_TRANSPORT_SHA = '0fc198a6942a5b37ad2535504f6544e3652f41a728e3d3a470eebf8b4e007e57'
NATIVE_TEXT_INGRESS_SHA = '024c69cdf3f097624dd17948fe502e898b16a5e8cece5233d23e3d6ff31acdb9'
DELIVERY_RECOVERY_SHA = 'd325f3f4f5c82aa672cc7f390491a0ee2018729e63c9a1576878bec2f402790d'
CURRENT_MAIN_SHA = 'a97d14c49ca7ebc41b9935e2f296479226c76f37d690eee0203ccb3e5cb7efea'
LIVE_MAIN_SHA = 'eab1072a0906d6bf48d6bc6e7450948130187abf88fd591fb3f8db286971387a'
REA_PROGRAMS_SHA = 'fa213db654f35502ba5bd32b07ae64dea59a6ecb36cd88188eb8805b94d31534'
REA_FAILURE_INSPECTION_SHA = '03af5e44f43b2b7f3d1e1944653335347a1d6990cf056e15ee6282385b458e29'
REA_CONTINUATION_SHA = 'bce3399d071eb69f9d1a4a95dd52a6aab255d67f6dd96a1a71d739fcf85e3a41'
REA_CONTINUATION_INSPECTION_SHA = '96a7b2541541f7be5c1f2b05eee0d78e8aba706218166c9ed9e8e6c53dc92e6d'
REA_CONFIGURATION_RECONCILIATION_SHA = '914ae91644bebb8e07094fed59c176b1c02e043750d6fc286eef3a6624bbc5e9'


def require(value):
    if not value:
        raise ValueError('launch_control_refused')


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__':'verified_launch_control_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-public-support>','exec'),namespace)
    return namespace


def private_read(path,uid,limit=65536):
    fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1
            and not before.st_mode & 0o077 and before.st_size <= limit)
        raw = stream.read(limit+1)
        after = os.fstat(stream.fileno())
        fields = ('st_dev','st_ino','st_uid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        require(len(raw) == before.st_size and all(getattr(before,k) == getattr(after,k) for k in fields))
        return raw


def nonce_from_names(names):
    env = {match.group(1) for name in names if (match := re.fullmatch(r'\.env-before-provider-([a-f0-9]{16})',name))}
    config = {match.group(1) for name in names if (match := re.fullmatch(r'\.config-before-provider-([a-f0-9]{16})\.yaml',name))}
    require(len(env) <= 1 and len(config) <= 1)
    return next(iter(env & config)) if len(env & config) == 1 else None


def inspect_profile(packet,account):
    home = Path(account.pw_dir)
    require(packet['uid'] == account.pw_uid and packet['home'] == str(home)
        and home == Path('/var/lib/enhanced-cognee-profiles') / packet['profile_id'])
    profile,original = home / '.hermes',Path(packet['candidate'])
    require(original.parent == home and re.fullmatch(r'ec-named-profile-restore-[A-Za-z0-9_-]{6,64}',original.name))
    value = dict(complete=True,profile_id=packet['profile_id'],original_candidate_exists=os.path.lexists(original),
        default_profile_exists=os.path.lexists(profile),layout='ambiguous',nonce=None,env_has_token=False,
        token_scope_matches=False,provider_configured=False,api_status_http=0,api_ready=False)
    if not os.path.lexists(profile):
        value['layout'] = 'partial_layout'
        return value
    info = profile.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == account.pw_uid and stat.S_IMODE(info.st_mode) == 0o700)
    names = os.listdir(profile)
    require(len(names) <= 512)
    if set(names) == {'.isolation-marker'}:
        require(private_read(profile / '.isolation-marker',account.pw_uid) == b'invented-isolation-marker-v1')
        value['layout'] = 'staged' if value['original_candidate_exists'] else 'ambiguous'
        return value
    require(not value['original_candidate_exists'])
    value['layout'] = 'configured_or_partial'
    value['nonce'] = nonce_from_names(names)
    from dotenv.parser import parse_stream
    bindings = list(parse_stream(io.StringIO(private_read(profile / '.env',account.pw_uid).decode())))
    require(not any(item.error for item in bindings))
    tokens = [item.value for item in bindings if item.key == 'ENHANCED_COGNEE_ACCESS_TOKEN']
    require(len(tokens) <= 1)
    if tokens:
        token = tokens[0]
        require(isinstance(token,str) and len(token) <= 4096)
        value['env_has_token'] = True
        parts = token.split('.')
        require(len(parts) == 3)
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + '='*((4-len(parts[1])%4)%4)))
        scope = packet['scope']
        value['token_scope_matches'] = all(claims.get(k) == v for k,v in scope.items())
        if type(claims.get('exp')) is int:
            value['seconds_remaining'] = max(-86400,min(86400,claims['exp']-int(time.time())))
        if value['token_scope_matches']:
            client_path = Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659/client.py')
            client_module = definitions(client_path,'8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64')
            try:
                status = client_module['MemoryClient']('http://127.0.0.1:28080',token).request('GET','/v1/memories/status')
                value['api_status_http'] = 200
                value['api_ready'] = status.get('ready') is True and all(status.get(field) == scope[key]
                    for field,key in (('tenant_id','tenant'),('project_id','project_id'),('subject','sub')))
            except Exception as error:
                code = getattr(error,'status_code',None)
                value['api_status_http'] = code if type(code) is int and 100 <= code <= 599 else 0
    settings = profile / 'enhanced_cognee.json'
    if os.path.lexists(settings):
        value['provider_configured'] = json.loads(private_read(settings,account.pw_uid)) == dict(
            base_url='http://127.0.0.1:28080',capture_policy='selected',include_shared=True)
    link = profile / 'plugins/enhanced_cognee'
    value['provider_link_pinned'] = link.is_symlink() and os.readlink(link) == '/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659'
    return value


def inspect_main(account):
    """Bounded owner-only metadata; no linked targets/private instructions read."""
    require(account.pw_name == 'vincentspereira')
    profile = Path(account.pw_dir) / '.hermes'
    core = definitions(BASE / 'operator-isolated-issuer-candidate-v3/provision_pilot_access.py',
        'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e')
    root = core['open_directory'](profile,{0,account.pw_uid})
    info = os.fstat(root)
    require(info.st_uid == account.pw_uid)
    try:
        return inspect_main_descriptor(account,root)
    finally:
        os.close(root)


def inspect_main_descriptor(account,root):
    info = os.fstat(root)
    value = dict(complete=True,source_profiles_changed=False,top_levels=[],named_profiles_separately_accounted=True)
    deadline = time.monotonic()+20
    def measure(root_fd):
        count = dict(entries=0,bytes=0,links=0,hardlinks=0,foreign=0,special=0,excluded=0,sqlite_headers=0,observation_complete=True)
        def walk(directory,depth):
            if depth > 32 or count['entries'] >= 5000 or time.monotonic() >= deadline:
                count['observation_complete'] = False
                return
            with os.scandir(directory) as listing:
                for item in listing:
                    if count['entries'] >= 5000 or time.monotonic() >= deadline:
                        count['observation_complete'] = False
                        break
                    count['entries'] += 1
                    if 'lswa' in item.name.lower() or 'legal-social-frameworks' in item.name.lower():
                        count['excluded'] += 1
                        continue
                    try:
                        entry = os.stat(item.name,dir_fd=directory,follow_symlinks=False)
                        if entry.st_uid != account.pw_uid:
                            count['foreign'] += 1
                        elif entry.st_dev != info.st_dev:
                            count['special'] += 1
                        elif stat.S_ISLNK(entry.st_mode):
                            count['links'] += 1
                        elif stat.S_ISDIR(entry.st_mode):
                            nested = os.open(item.name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=directory)
                            try:
                                opened = os.fstat(nested)
                                require((opened.st_dev,opened.st_ino) == (entry.st_dev,entry.st_ino))
                                walk(nested,depth+1)
                            finally:
                                os.close(nested)
                        elif stat.S_ISREG(entry.st_mode):
                            count['bytes'] += entry.st_size
                            count['hardlinks'] += int(entry.st_nlink != 1)
                            if entry.st_nlink == 1:
                                fd = os.open(item.name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=directory)
                                try:
                                    opened = os.fstat(fd)
                                    require((opened.st_dev,opened.st_ino,opened.st_uid) == (entry.st_dev,entry.st_ino,account.pw_uid))
                                    count['sqlite_headers'] += int(os.read(fd,16) == b'SQLite format 3\0')
                                finally:
                                    os.close(fd)
                        else:
                            count['special'] += 1
                    except (OSError,ValueError):
                        count['observation_complete'] = False
        walk(root_fd,0)
        return count
    names = sorted(os.listdir(root))
    require(len(names) <= 256)
    for name in names:
        if 'lswa' in name.lower() or 'legal-social-frameworks' in name.lower() or name == 'profiles':
            continue
        item = os.stat(name,dir_fd=root,follow_symlinks=False)
        row = dict(name=name,owner_matches=item.st_uid == account.pw_uid,mode=stat.S_IMODE(item.st_mode))
        if stat.S_ISLNK(item.st_mode):
            row['kind'] = 'link_not_followed'
        elif stat.S_ISDIR(item.st_mode):
            row['kind'] = 'directory'
            if item.st_uid == account.pw_uid and item.st_dev == info.st_dev:
                nested = os.open(name,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=root)
                try:
                    row['metadata'] = measure(nested)
                finally:
                    os.close(nested)
        elif stat.S_ISREG(item.st_mode):
            row.update(kind='file',bytes=item.st_size,hardlinked=item.st_nlink != 1)
        else:
            row['kind'] = 'special'
        value['top_levels'].append(row)
    # Only predetermined key names, never secret values.
    try:
        from dotenv.parser import parse_stream
        forbidden = {'ENCRYPTION_MASTER_KEY','ENHANCED_JWT_SECRET','ENHANCED_INDEX_KEY','ENHANCED_BACKUP_SIGNING_KEY',
            'ENHANCED_MEMORY_DATABASE_URL','ENHANCED_INDEX_DATABASE_URL','ARCADEDB_PASSWORD','POSTGRES_PASSWORD','QDRANT_API_KEY'}
        bindings = list(parse_stream(io.StringIO(private_read(Path('/proc/self/fd') / str(root) / '.env',account.pw_uid).decode())))
        value['privileged_environment_field_names'] = sorted({item.key for item in bindings if item.key in forbidden})
        value['environment_parse_valid'] = not any(item.error for item in bindings)
    except (OSError,ValueError,UnicodeError):
        value['environment_inspection_needs_review'] = True
    return value


def child():
    packet = json.loads(sys.stdin.buffer.readline(16385))
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_uid == packet['uid'] and not os.getgroups()
        and status['NoNewPrivs'].strip() == '1' and status['CapEff'].strip() == status['CapAmb'].strip() == '0000000000000000')
    try:
        result = inspect_main(account) if packet['mode'] == 'main' else inspect_profile(packet,account)
    except Exception as error:
        result = dict(complete=False,category='owner_inspection_needs_review',
            error_kind=type(error).__name__ if type(error).__name__ in {'ValueError','PermissionError','FileNotFoundError'} else 'other')
    print(json.dumps(result),flush=True)


def owner_observation(helper,source,account,packet):
    code,line = helper['owner_program'](source)
    data = dict(packet,uid=account.pw_uid)
    process = subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',code],
        input=line+json.dumps(data).encode()+b'\n',stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=45,cwd='/',
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= 131072)
    return json.loads(process.stdout)


def classification(owner,completed,receipt,record):
    if not owner.get('complete'):
        return 'needs_review'
    if completed:
        if record is not None and (record.get('state'),record.get('version')) != ('retracted',2):
            return 'completed_changed_requires_review'
        return 'completed_preserve'
    if owner.get('layout') == 'staged':
        return 'not_started_or_no_effects'
    if owner.get('layout') != 'configured_or_partial':
        return 'partial_layout_needs_reconciliation'
    if record is not None and record.get('state') == 'retracted' and record.get('version') == 2:
        return 'finish_evidence_only' if receipt else 'finished_record_preserve_missing_proof'
    if record is not None and record.get('state') == 'active' and record.get('version') == 1:
        return 'unfinished_invented_probe'
    if record is not None:
        return 'unexpected_record_state_needs_review'
    return 'configured_probe_not_observed'


def active_profile_processes(uids):
    observations = []
    for item in os.scandir('/proc'):
        if not item.name.isdecimal():
            continue
        try:
            raw = (Path(item.path)/'status').read_text()
            match = re.search(r'^Uid:\s+(\d+)',raw,re.MULTILINE)
            if match is None or int(match.group(1)) not in uids:
                continue
            state = re.search(r'^State:\s+([A-Z])',raw,re.MULTILINE)
            if state and state.group(1) == 'Z':
                continue
            observations.append(dict(pid=int(item.name),uid=int(match.group(1))))
        except (OSError,ValueError):
            continue
    require(len(observations) <= 512)
    return observations


def resumed_attempt(read):
    try:
        context = json.loads(read(BASE / 'operator-consolidated-provider-resume/context.json',0))
    except FileNotFoundError:
        return None
    path = Path(context['evidence'])
    require(context.get('unit') == 'ec-launch-provider-resume-20261026.service'
        and path.parent == BASE / 'operator-evidence'
        and re.fullmatch(r'provider-resume-[A-Za-z0-9_-]{6,64}',path.name))
    return path


async def read_record_metadata(read,profiles):
    import asyncpg
    selected = [row for row in profiles if row.get('owner',{}).get('nonce')]
    if not selected:
        return
    config = json.loads(read(Path('/etc/enhanced-cognee/operator.json'),0))
    connection = await asyncpg.connect(config['ENHANCED_MEMORY_DATABASE_URL'],timeout=10,command_timeout=10,
        server_settings={'default_transaction_read_only':'on','application_name':'ec_launch_readonly_reconcile'})
    del config
    try:
        async with connection.transaction(readonly=True):
            for row in selected:
                scope = row['scope']
                key = 'candidate-'+row['owner']['nonce']
                data = await connection.fetch('SELECT id,version,state,owner_subject,writer_agent FROM shared_memory.records WHERE tenant=$1 AND project=$2 AND idempotency_key=$3 LIMIT 2',
                    scope['tenant'],scope['project_id'],key)
                require(len(data) <= 1)
                if data:
                    record = dict(data[0])
                    require(record.pop('owner_subject') == scope['sub'] and record.pop('writer_agent') == scope['agent_id'])
                    row['record'] = record
    finally:
        await connection.close()


def inspect():
    require(os.geteuid() == 0)
    directory = Path(__file__).parent
    shared = definitions(directory / 'recover_launch_graph_operator.py',SUPPORT_SHA)
    read,write = shared['read_file'],shared['private_write']
    helper = definitions(directory / 'qualify_launch_isolated_accounts.py',
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    provider = definitions(directory / 'prepare_launch_candidate_provider_v2.py',PROVIDER_SHA)
    previous = definitions(directory / 'qualify_launch_named_providers.py',BATCH_SHA)
    ticket = json.loads(read(STAGED / 'new-private-provider-batch.started.json',0))
    attempt = Path(ticket['evidence'])
    require(attempt.parent == BASE / 'operator-evidence' and re.fullmatch(r'named-provider-batch-[A-Za-z0-9_-]{6,64}',attempt.name))
    started = json.loads(read(attempt / 'started.json',0))
    require(started.get('operator_helper_sha256') == BATCH_SHA and started.get('complete') is False)
    plan = read(previous['PLAN'],0)
    require(hashlib.sha256(plan).hexdigest() == previous['PLAN_SHA'])
    records = [json.loads(read(path,0)) for path in STAGED.glob('*.candidate.private.json')]
    selected,deferred = previous['selection'](json.loads(plan)['profiles'],records,provider)
    evidence = Path(tempfile.mkdtemp(prefix='launch-control-inspect-',dir=BASE / 'operator-evidence'))
    source = Path(__file__).read_bytes()
    helper['owner_program'](source)
    result = dict(complete=False,phase='inspect',run_mode='readonly_reconciliation',
        evidence=str(evidence),previous_attempt=str(attempt),source_revision=BASE.name,
        profiles_inspected=0,existing_bindings_deferred=len(deferred),credentials_issued=0,
        profiles_changed=False,canonical_memory_edits=False,services_changed=False,fleet_launch_approved=False)
    profiles = []
    newer_attempt = resumed_attempt(read)
    if newer_attempt is not None:
        result['resumed_attempt'] = str(newer_attempt)
    write(evidence / 'started.json',json.dumps(result).encode())
    try:
        active = active_profile_processes({record['uid'] for record,_ in selected})
        write(evidence / 'active-processes.private.json',json.dumps(active).encode())
        result['active_profile_process_count'] = len(active)
        for index,(record,scope) in enumerate(selected,1):
            ident = record['profile_id']
            print(json.dumps(dict(event='inspect_profile',current=index,total=len(selected))),flush=True)
            account = pwd.getpwnam(record['user'])
            require(account.pw_uid == record['uid'] and account.pw_dir == record['home'])
            observation = owner_observation(helper,source,account,dict(mode='profile',profile_id=ident,
                home=account.pw_dir,candidate=record['candidate'],scope=scope))
            per_profile = attempt / ident
            if newer_attempt is not None and os.path.lexists(newer_attempt / ident):
                per_profile = newer_attempt / ident
            completed,receipt = False,False
            try:
                done = json.loads(read(per_profile / 'summary.json',0))
                require(done.get('profile_id') == ident)
                completed = all(done.get(key) is True for key in ('complete','candidate_provider_api_qualified','peer_history_denied','post_configuration_backup_qualified'))
            except FileNotFoundError:
                pass
            try:
                previous['verified_owner'](json.loads(read(per_profile / 'owner-result.private.json',0)))
                receipt = True
            except (FileNotFoundError,ValueError):
                pass
            item = dict(profile_id=ident,user=account.pw_name,uid=account.pw_uid,scope=scope,
                owner=observation,completed_summary=completed,owner_receipt_complete=receipt,record=None,
                qualification_evidence=str(per_profile))
            profiles.append(item)
            write(evidence / (ident+'.private.json'),json.dumps(item).encode())
            result['profiles_inspected'] += 1
        print('{"event":"inspect_main_metadata_bounded"}',flush=True)
        main = owner_observation(helper,source,pwd.getpwnam('vincentspereira'),dict(mode='main'))
        write(evidence / 'main.private.json',json.dumps(main).encode())
        result['main_metadata_collected'] = main.get('complete') is True
        print('{"event":"inspect_canonical_metadata_readonly"}',flush=True)
        asyncio.run(read_record_metadata(read,profiles))
        counts = {}
        for row in profiles:
            state = classification(row['owner'],row['completed_summary'],row['owner_receipt_complete'],row['record'])
            row['classification'] = state
            counts[state] = counts.get(state,0)+1
        write(evidence / 'profiles.private.json',json.dumps(profiles).encode())
        result.update(complete=True,profile_states=counts,main_metadata_collected=main.get('complete') is True,
            main_privileged_environment_field_count=len(main.get('privileged_environment_field_names',[])),
            main_environment_needs_review=main.get('environment_inspection_needs_review') is True,
            ready_for_resume_planning=True)
    except KeyboardInterrupt:
        result['category'] = 'inspection_interrupted_partial_evidence_preserved'
    except Exception as error:
        result['category'] = 'inspection_incomplete_preserve_evidence'
        result['error_kind'] = type(error).__name__ if type(error).__name__ in {'ValueError','FileNotFoundError','PermissionError','ModuleNotFoundError'} else 'other'
    write(evidence / 'summary.json',json.dumps(result).encode())
    print(json.dumps(result),flush=True)
    return 0 if result['complete'] else 1


def qualify_prerequisites():
    """Finish both independent finite jobs, reusing any retained result."""
    require(os.geteuid()==0)
    support=definitions(Path(__file__).with_name('recover_launch_graph_operator.py'),SUPPORT_SHA)
    read=support['read_file'];results={}
    for label,name,digest in [('current_model','finish_launch_model_scope.py',CURRENT_MODEL_FINISH_SHA),
        ('program_recovery','qualify_launch_program_recovery.py',PROGRAM_RECOVERY_SHA)]:
        module=definitions(Path(__file__).with_name(name),digest)
        try:code=module['launch']()
        except Exception:code=1
        try:
            context=json.loads(read(module['ARTIFACT']/'context.json',0))
            evidence=Path(context['evidence'])
            require(evidence.parent==BASE/'operator-evidence')
            value=json.loads(read(evidence/'summary.json',0))
            value['complete']=value.get('complete') is True and code==0
            value['command_exit_code']=code
        except Exception:
            value=dict(complete=False,category='component_preflight_or_receipt_incomplete_preserve_evidence',command_exit_code=code)
        results[label]=value
    passed=all(value.get('complete') is True for value in results.values())
    print(json.dumps(dict(complete=passed,phase='qualify_prerequisites',components=results,
        fleet_launch_approved=False,actual_profile_admission_qualified=False,source_revision=BASE.name)),flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        if sys.argv[1:] == ['inspect']:
            raise SystemExit(inspect())
        if sys.argv[1:] == ['qualify']:
            runtime = definitions(Path(__file__).with_name('qualify_launch_named_runtime.py'), RUNTIME_SHA)
            raise SystemExit(runtime['launch']())
        if sys.argv[1:] == ['repair-model-bindings']:
            repair = definitions(Path(__file__).with_name('repair_launch_named_runtime.py'), REPAIR_SHA)
            raise SystemExit(repair['launch']())
        if sys.argv[1:] == ['finish-model-bindings']:
            finish = definitions(Path(__file__).with_name('finish_launch_named_runtime.py'), FINISH_SHA)
            raise SystemExit(finish['launch']())
        if sys.argv[1:] == ['pin-model-routes']:
            routes = definitions(Path(__file__).with_name('complete_launch_named_runtime.py'), ROUTES_SHA)
            raise SystemExit(routes['launch']())
        if sys.argv[1:] == ['backup-main']:
            main = definitions(Path(__file__).with_name('backup_launch_main_operational.py'), MAIN_BACKUP_SHA)
            raise SystemExit(main['launch']())
        if sys.argv[1:] == ['continue-main-backup']:
            main = definitions(Path(__file__).with_name('continue_launch_main_operational.py'), MAIN_CONTINUE_SHA)
            raise SystemExit(main['launch']())
        if sys.argv[1:] == ['qualify-current-model']:
            model = definitions(Path(__file__).with_name('qualify_launch_current_model.py'), CURRENT_MODEL_SHA)
            raise SystemExit(model['launch']())
        if sys.argv[1:] == ['continue-current-model']:
            model = definitions(Path(__file__).with_name('qualify_launch_current_model_v2.py'), CURRENT_MODEL_V2_SHA)
            raise SystemExit(model['launch']())
        if sys.argv[1:] == ['qualify-model-scope']:
            model = definitions(Path(__file__).with_name('qualify_launch_current_model_v3.py'), CURRENT_MODEL_V3_SHA)
            raise SystemExit(model['launch']())
        if sys.argv[1:] == ['finish-model-scope']:
            model = definitions(Path(__file__).with_name('finish_launch_model_scope.py'), CURRENT_MODEL_FINISH_SHA)
            raise SystemExit(model['launch']())
        if sys.argv[1:] == ['prepare-fleet-review']:
            review = definitions(Path(__file__).with_name('prepare_launch_fleet_review.py'), FLEET_REVIEW_SHA)
            raise SystemExit(review['main']())
        if sys.argv[1:] == ['reconcile-main-candidate']:
            current = definitions(Path(__file__).with_name('reconcile_current_main_candidate.py'), CURRENT_MAIN_SHA)
            raise SystemExit(current['launch']())
        if sys.argv[1:] == ['inspect-rea-failure']:
            inspection = definitions(Path(__file__).with_name('inspect_rea_program_failure.py'), REA_FAILURE_INSPECTION_SHA)
            raise SystemExit(inspection['main']())
        if sys.argv[1:] == ['reconcile-rea-capture']:
            rea = definitions(Path(__file__).with_name('reconcile_rea_configuration.py'), REA_CONFIGURATION_RECONCILIATION_SHA)
            raise SystemExit(rea['launch']())
        if sys.argv[1:] == ['inspect-rea-continuation']:
            inspection = definitions(Path(__file__).with_name('inspect_rea_continuation_failure.py'), REA_CONTINUATION_INSPECTION_SHA)
            raise SystemExit(inspection['main']())
        if sys.argv[1:] == ['continue-rea-programs']:
            rea = definitions(Path(__file__).with_name('continue_rea_main_programs.py'), REA_CONTINUATION_SHA)
            raise SystemExit(rea['launch']())
        if sys.argv[1:] == ['qualify-rea-programs']:
            rea = definitions(Path(__file__).with_name('stage_rea_main_programs.py'), REA_PROGRAMS_SHA)
            raise SystemExit(rea['launch']())
        if sys.argv[1:] == ['refresh-main-live-state']:
            live = definitions(Path(__file__).with_name('refresh_live_main_candidate.py'), LIVE_MAIN_SHA)
            raise SystemExit(live['launch']())
        if sys.argv[1:] == ['qualify-delivery-recovery']:
            delivery = definitions(Path(__file__).with_name('qualify_isolated_delivery_recovery.py'), DELIVERY_RECOVERY_SHA)
            raise SystemExit(delivery['main']())
        if sys.argv[1:] == ['qualify-native-text-ingress']:
            native = definitions(Path(__file__).with_name('qualify_isolated_native_text_ingress.py'), NATIVE_TEXT_INGRESS_SHA)
            raise SystemExit(native['main']())
        if sys.argv[1:] == ['qualify-isolated-transport']:
            transport = definitions(Path(__file__).with_name('qualify_isolated_gateway_transport.py'), ISOLATED_TRANSPORT_SHA)
            raise SystemExit(transport['main']())
        if sys.argv[1:] == ['repair-fleet-backups']:
            backup = definitions(Path(__file__).with_name('repair_launch_fleet_backup.py'), FLEET_BACKUPS_REPAIR_SHA)
            raise SystemExit(backup['repair']())
        if sys.argv[1:] == ['install-fleet-backups']:
            backup = definitions(Path(__file__).with_name('install_launch_fleet_backups.py'), FLEET_BACKUPS_SHA)
            raise SystemExit(backup['install']())
        if sys.argv[1:] in (['continue-implementation-batch'], ['continue-qualification-batch']):
            batch = definitions(Path(__file__).with_name('launch_completion_batch_v2.py'), COMPLETION_CONTINUE_SHA)
            raise SystemExit(batch['launch']('implementation' if sys.argv[1] == 'continue-implementation-batch' else 'qualification'))
        if sys.argv[1:] in (['implementation-batch'], ['qualification-batch']):
            batch = definitions(Path(__file__).with_name('launch_completion_batch.py'), COMPLETION_BATCH_SHA)
            raise SystemExit(batch['launch']('implementation' if sys.argv[1] == 'implementation-batch' else 'qualification'))
        if sys.argv[1:] == ['qualify-program-recovery']:
            program = definitions(Path(__file__).with_name('qualify_launch_program_recovery.py'), PROGRAM_RECOVERY_SHA)
            raise SystemExit(program['launch']())
        if sys.argv[1:] == ['qualify-prerequisites']:
            raise SystemExit(qualify_prerequisites())
        require(sys.argv[1:] in (['resume'],['status']))
        resume = definitions(Path(__file__).with_name('resume_launch_named_providers.py'),RESUME_SHA)
        raise SystemExit(resume['launch' if sys.argv[1] == 'resume' else 'status']())
    except Exception:
        print('{"complete":false,"category":"launch_control_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
