"""Owner-only current-source capture and NEW inactive main reconciliation.

Root sends public backup recipients and ordinary fixed-scope credentials only.
Source and previous candidate files are never changed. Root never traverses
these profiles. Raw libraries/values stay off stdout; encrypted archives alone
cross from an owner to root. Plaintext restore bytes cross only a private pipe.
"""
from __future__ import annotations
import contextlib
import base64
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import socket
import stat
import subprocess
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-main-current-reconciliation-v1'
LEGACY=BASE/'operator-launch-completion-batch-v2'
PROVIDER='/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659'
MAX_ARCHIVE=600*1024**2
MAX_CIPHER=650*1024**2
PINS={'inspect_launch_main_references.py': '3c00d72c7479ab8e037f7c9fe63cf4b603ae84db797f0324a80d81f15f1343dc', 'capture_main_operational_profile_v3.py': 'e32266d8a797eeaca2a32247f861cbf725341cce960eeb73d3db57987c99c106', 'provision_pilot_access.py': 'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e', 'fleet_credential_policy.py': '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102', 'prepare_launch_candidate_provider_v2.py': 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67', 'bind_launch_model_route.py': 'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52', 'main_candidate_environment.py': '1e9e463b524639a28faa1ef17393c8dd16afe2b06cf2c632c8aeb0ebde922bb4', 'main_memory_profile_recovery.py': '6b69674dacfcedafc6bcdad0a11e353265a19705b950e1ca3a492351d5cf78b5', 'renew_pilot_access.py': '8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567', 'fleet_credential_lifecycle.py': 'f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62', 'qualify_launch_gateway_renewal_v2.py': 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2', 'current_main_configuration.py': 'ac8d938c6bb895672d97e63c712e148fb05498206765d1bbf124386fa7a2d2e7'}
PHASE='identity'
FORBIDDEN={'ENCRYPTION_MASTER_KEY','ENHANCED_JWT_SECRET','ENHANCED_INDEX_KEY','ENHANCED_BACKUP_SIGNING_KEY',
 'ENHANCED_MEMORY_DATABASE_URL','ENHANCED_INDEX_DATABASE_URL','ARCADEDB_PASSWORD','POSTGRES_PASSWORD','QDRANT_API_KEY',
 'INDEX_ARCADEDB_PASSWORD','INDEX_QDRANT_API_KEY','INDEX_VALKEY_URL','ENHANCED_BACKUP_SIGNING_KEY_ID'}


def require(value):
    if not value:raise ValueError('main_current_owner_refused')


def public(name):
    path=ARTIFACT/name
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PINS[name])
    scope={'__name__':'verified_main_current_support','__file__':str(path)}
    exec(compile(raw,'<verified-main-current-support>','exec'),scope)
    return scope


def files(profile):
    inspector=public('inspect_launch_main_references.py')
    directory=inspector['open_profile'](profile,os.geteuid())
    try:return {name:inspector['read_at'](directory,name,os.geteuid()) for name in ('config.yaml','.env','auth.json')}
    finally:os.close(directory)


def fingerprints(values):
    return {name:hashlib.sha256(raw).hexdigest() for name,raw in values.items()}


def inspect_source(values):
    transform=public('current_main_configuration.py');config=transform['load'](values['config.yaml'])
    require(isinstance(json.loads(values['auth.json']),dict))
    from dotenv.parser import parse_stream
    bindings=list(parse_stream(io.StringIO(values['.env'].decode())))
    require(not any(row.error or row.key in FORBIDDEN or row.key=='ENHANCED_COGNEE_ACCESS_TOKEN' for row in bindings))
    rows=config.get('mcp_servers')
    require(isinstance(rows,dict) and 1<=len(rows)<=128)
    for server in rows.values():
        require(isinstance(server,dict) and isinstance(server.get('env',{}),dict)
            and not (set(server.get('env',{})) & FORBIDDEN))
    metadata=public('inspect_launch_main_references.py')['classify'](config,Path('/home/vincentspereira/.hermes'),Path('/home/vincentspereira'))
    require(metadata['configured_model_matches'] is True and metadata['multiplex_enabled'] is True
        and metadata['reference_counts']['excluded_project']==metadata['reference_counts']['windows_path']==0)
    return config,metadata


def encrypt(archive,recipient):
    require(re.fullmatch('age1[0-9a-z]{20,100}',recipient) is not None and 0<len(archive)<=MAX_ARCHIVE)
    result=subprocess.run(['/usr/local/bin/age','--encrypt','--recipient',recipient],input=archive,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=90)
    body=result.stdout
    require(0<len(body)<=MAX_CIPHER and body.startswith(b'age-encryption.org/v1\n'))
    return body


def create_at(directory,name,raw):
    require('/' not in name and name not in {'','.','..'} and isinstance(raw,bytes))
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    with os.fdopen(fd,'wb') as output:output.write(raw);output.flush();os.fsync(output.fileno())
    os.fsync(directory)


def publish(profile,name,raw,ident):
    directory=public('inspect_launch_main_references.py')['open_profile'](profile,os.geteuid())
    try:
        inspector=public('inspect_launch_main_references.py')
        original=inspector['read_at'](directory,name,os.geteuid())
        create_at(directory,name+'-before-current-'+ident,original)
        temporary=name+'-current-'+ident
        create_at(directory,temporary,raw)
        require(inspector['read_at'](directory,name,os.geteuid())==original)
        os.replace(temporary,name,src_dir_fd=directory,dst_dir_fd=directory);os.fsync(directory)
        require(inspector['read_at'](directory,name,os.geteuid())==raw)
    finally:os.close(directory)


def bind(entry):
    core=public('provision_pilot_access.py')
    core['IDENTITY']=dict(sub=entry['subject'],agent_id=entry['agent_id'],tenant=entry['tenant'],
        project_id=entry['project_id'],roles=['api_client'],capture_policy='selected')
    core['open_directory']=public('prepare_launch_candidate_provider_v2.py')['open_candidate_directory']
    return core


def prepare_files(saved,bundle,model_key,destination,entry):
    import yaml
    transform=public('current_main_configuration.py');config,metadata=inspect_source(saved)
    updated=transform['transform'](config,destination)
    core=bind(entry)
    environment=core['prepare_environment'](saved['.env'],bundle['token'])
    key_name,endpoint=public('bind_launch_model_route.py')['pointer'](updated)
    environment=public('main_candidate_environment.py')['prepare'](environment,key_name,model_key,endpoint)
    serialized=yaml.safe_dump(updated,sort_keys=False).encode()
    require(transform['load'](serialized)==updated)
    return serialized,environment,len(config['mcp_servers'])


def capture_source(packet,account):
    global PHASE
    profile=Path(account.pw_dir)/'.hermes'
    PHASE='source_configuration'
    before=files(profile);config,metadata=inspect_source(before)
    # Capture settings only: a live telemetry file prevented strict whole-main
    # capture. Never weaken that guard or claim this capsule refreshes sessions.
    archive=json.dumps(dict(schema=1,files={name:base64.b64encode(raw).decode() for name,raw in before.items()}),
        sort_keys=True,separators=(',',':')).encode()
    require(len(archive)<=1100*1024)
    PHASE='source_encryption'
    body=encrypt(archive,packet['recipient'])
    require(files(profile)==before)
    return dict(complete=True,receipt=dict(files=3,source_bytes=sum(map(len,before.values())),plaintext_archive_written=False),fingerprints=fingerprints(before),
        mcp_definitions=len(config['mcp_servers']),source_configuration_preserved=True,ciphertext_bytes=len(body)),body


def capsule(raw):
    require(isinstance(raw,bytes) and 0<len(raw)<=1100*1024)
    def unique(pairs):
        result={}
        for key,value in pairs:require(key not in result);result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    require(isinstance(value,dict) and set(value)=={'schema','files'} and type(value['schema']) is int
        and value['schema']==1 and isinstance(value['files'],dict)
        and set(value['files'])=={'config.yaml','.env','auth.json'})
    result={}
    for name,encoded in value['files'].items():
        require(isinstance(encoded,str) and len(encoded)<=350000)
        try:data=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError):raise ValueError('main_configuration_capsule_refused') from None
        require(0<len(data)<=262144);result[name]=data
    return result


def prepare_candidate(packet,body,account):
    global PHASE
    PHASE='previous_candidate_restore'
    core=public('capture_main_operational_profile_v3.py')
    current=capsule(body[:packet['capsule_bytes']])
    require(fingerprints(current)==packet['fingerprints'])
    destination,receipt=public('main_memory_profile_recovery.py')['restore'](core,body[packet['capsule_bytes']:]);profile=Path(destination)
    transform=public('current_main_configuration.py');transform['candidate'](profile)
    require(profile.parent==Path(account.pw_dir))
    saved=files(profile)
    PHASE='current_configuration_prepare'
    config,environment,count=prepare_files(current,packet['bundle'],packet['model_key'],profile,packet['entry'])
    require(files(profile)==saved)
    require(public('main_memory_profile_recovery.py')['binding'](profile))
    issuer=bind(packet['entry']);issuer['qualify_access'](packet['bundle'])
    PHASE='new_candidate_configuration'
    publish(profile,'config.yaml',config,packet['id']);publish(profile,'.env',environment,packet['id'])
    publish(profile,'auth.json',current['auth.json'],packet['id'])
    for name in ('plugins','workspace'):
        path=profile/name
        if not os.path.lexists(path):path.mkdir(mode=0o700)
        info=path.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==account.pw_uid and not info.st_mode&0o077)
    require(files(profile)==dict(current,**{'config.yaml':config,'.env':environment}))
    issuer['qualify_access'](packet['bundle'])
    metadata=public('inspect_launch_main_references.py')['classify'](transform['load'](config),profile,Path('/home/vincentspereira'))
    return dict(complete=True,destination=destination,receipt=receipt,mcp_definitions=count,
        current_settings_and_oauth_preserved=True,source_fingerprints_match=True,scoped_status_authenticated=True,
        previous_operational_state_reused=True,current_source_operational_refresh_qualified=False,
        remaining_reference_count=metadata['unresolved_reference_count']),b''


def capture_candidate(packet,account):
    global PHASE
    profile=Path(account.pw_dir)/'.hermes' if packet['mode']=='capture_previous' else Path(packet['destination'])
    if packet['mode']!='capture_previous':
        public('current_main_configuration.py')['candidate'](profile);require(profile.parent==Path(account.pw_dir))
    PHASE='configured_candidate_capture'
    archive,receipt=public('main_memory_profile_recovery.py')['capture'](public('capture_main_operational_profile_v3.py'),profile)
    PHASE='configured_candidate_encryption'
    body=encrypt(archive,packet['recipient'])
    return dict(complete=True,receipt=receipt,ciphertext_bytes=len(body)),body


def restore_candidate(packet,body,account):
    global PHASE
    import yaml
    original=Path(packet['destination']);transform=public('current_main_configuration.py');transform['candidate'](original)
    require(original.parent==Path(account.pw_dir))
    PHASE='configured_candidate_restore'
    destination,receipt=public('main_memory_profile_recovery.py')['restore'](public('capture_main_operational_profile_v3.py'),body)
    profile=Path(destination);transform['candidate'](profile);require(profile.parent==Path(account.pw_dir))
    saved=files(profile);config=transform['load'](saved['config.yaml'])
    rebased=transform['rebase'](config,original,profile)
    serialized=yaml.safe_dump(rebased,sort_keys=False).encode();require(transform['load'](serialized)==rebased)
    publish(profile,'config.yaml',serialized,packet['id'])
    require(files(profile)==dict(saved,**{'config.yaml':serialized}))
    issuer=bind(packet['entry']);renewal=public('renew_pilot_access.py')
    token=renewal['environment'](issuer,saved['.env']);claims=renewal['token_claims'](issuer,token)
    require(all(claims.get(key)==value for key,value in issuer['IDENTITY'].items()))
    public('fleet_credential_lifecycle.py')['accepted_status'](issuer,token)
    return dict(complete=True,destination=destination,receipt=receipt,mcp_definitions=len(rebased['mcp_servers']),
        workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True),b''


def guard(packet):
    uid,gid=packet['uid'],packet['gid'];account=pwd.getpwuid(os.geteuid())
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(type(uid) is int and uid>0 and type(gid) is int and gid>0
        and os.getresuid()==(uid,)*3 and os.getresgid()==(gid,)*3 and not os.getgroups()
        and account.pw_uid==uid and account.pw_gid==gid and fields['NoNewPrivs'].strip()=='1'
        and all(fields[key].strip()=='0000000000000000' for key in ('CapEff','CapAmb','CapInh')))
    if packet['mode'] in {'capture_source','verify_source'}:
        require(account.pw_name=='vincentspereira' and account.pw_dir=='/home/vincentspereira')
    else:
        entry=packet['entry'];public('fleet_credential_policy.py')['validate'](dict(schema=1,profiles=[entry]))
        require(account.pw_name==entry['user']=='ecbot_'+Path(account.pw_dir).name
            and entry['uid']==uid and entry['home']==account.pw_dir and entry['enabled'] is False
            and re.fullmatch('ecbot_[a-f0-9]{16}',account.pw_name) and account.pw_shell=='/usr/sbin/nologin')
    os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=account.pw_dir,LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    os.chdir('/')
    return account


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    os.umask(0o077);logging.disable(logging.CRITICAL)
    packet=json.loads(sys.stdin.buffer.readline(65537));require(isinstance(packet,dict))
    schemas={'capture_source':{'recipient'},'verify_source':{'fingerprints'},
        'prepare':{'entry','archive_bytes','capsule_bytes','fingerprints','bundle','model_key','id'},
        'capture_previous':{'entry','recipient'},
        'capture_candidate':{'entry','destination','recipient'},
        'restore_candidate':{'entry','destination','archive_bytes','id'}}
    mode=packet.get('mode');require(mode in schemas and set(packet)==schemas[mode]|{'mode','uid','gid'})
    if 'id' in packet:require(re.fullmatch('[a-f0-9]{32}',packet['id']) is not None)
    account=guard(packet);body=b''
    if 'archive_bytes' in packet:
        require(type(packet['archive_bytes']) is int and 0<packet['archive_bytes']<=MAX_ARCHIVE)
        extra=packet.get('capsule_bytes',0)
        require(type(extra) is int and 0<=extra<=1100*1024)
        body=sys.stdin.buffer.read(packet['archive_bytes']+extra+1);require(len(body)==packet['archive_bytes']+extra)
    with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet),contextlib.redirect_stderr(quiet):
        counts=public('qualify_launch_gateway_renewal_v2.py')['network_guard']()
        if mode=='capture_source':value,output=capture_source(packet,account)
        elif mode=='prepare':value,output=prepare_candidate(packet,body,account)
        elif mode in {'capture_candidate','capture_previous'}:value,output=capture_candidate(packet,account)
        elif mode=='restore_candidate':value,output=restore_candidate(packet,body,account)
        else:
            current=files(Path(account.pw_dir)/'.hermes');require(fingerprints(current)==packet['fingerprints'])
            value=dict(complete=True,source_current_at_completion=True);output=b''
        require(counts['forbidden']==0)
    sys.stdout.buffer.write(json.dumps(value,sort_keys=True).encode()+b'\n'+output);sys.stdout.buffer.flush()
