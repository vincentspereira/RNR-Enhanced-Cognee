"""Content-free native observations; all non-memory networking stays denied.

Denied discovery calls from pinned metadata modules are visible limitations.
Unexpected attempts fail qualification. Catalog/context/model capability is
never claimed verified from a constructor or a fallback context window.
"""
from __future__ import annotations
import base64
import copy
from datetime import datetime
import io
import json
import math
import os
from pathlib import Path
import pwd
import socket
import sys
import tarfile
import threading

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-named-runtime-finish-v3'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
FILES = ('.env', 'config.yaml', 'auth.json', 'enhanced_cognee.json')
BINDING_SHA = 'bf24f095bc8ccfb037a4278e3f5efd72c33de14195367d1bb727fc809b454b01'
DISCOVERY_MODULES = {'agent.'+name:str(RELEASE/'repo/agent'/(name+'.py')) for name in
                     ('model_metadata','model_metadata_http','models_dev')}
DISCOVERY_HOSTS = {'models.dev','openrouter.ai','open.bigmodel.cn','api.z.ai'}
CAPTURE_SHA = '40bbfab7605c3e26d5e075265dc251ca5cb08487c3d84d4b908839ba161ab92a'
COMPARISON_FLAGS = {'complete','auth_sensitive_state_preserved','auth_usage_metadata_changed',
                    'preserved','bound_model_key_matches','endpoint_matches','source_profile_changed'}


class ComparisonError(ValueError):
    def __init__(self, observation):
        super().__init__('retained_profile_comparison_refused')
        self.phase = 'retained_profile_comparison'
        self.observation = validate_comparison(observation)


def require(value):
    if not value:
        raise ValueError('native_observation_refused')


def trusted_discovery_frame(frame=None):
    # co_filename can retain an old build path in admitted pyc files. Check
    # the actual imported module globals and protected source path instead.
    current=sys._getframe(1) if frame is None else frame
    for _ in range(96):
        if current is None:
            return False
        name=current.f_globals.get('__name__')
        module=sys.modules.get(name) if name in DISCOVERY_MODULES else None
        if module is not None and module.__dict__ is current.f_globals and getattr(module,'__file__',None) == DISCOVERY_MODULES[name]:
            return True
        current=current.f_back
    return False


def network_guard():
    """Permit only memory loopback. No discovery address reaches the resolver."""
    original_connect, original_connect_ex, original_resolve = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
    counts = dict(memory=0, discovery_blocked=0, unexpected_blocked=0, controls_blocked=0)
    control = threading.local()
    lock = threading.Lock()
    def increase(key):
        with lock: counts[key] += 1
    def deny(host=None, port=None):
        if getattr(control, 'active', False):
            increase('controls_blocked')
        elif isinstance(host, str) and host in DISCOVERY_HOSTS and isinstance(port,(int,str)) and port in {443,'443'} and trusted_discovery_frame():
            increase('discovery_blocked')
        else:
            increase('unexpected_blocked')
        raise RuntimeError('non_memory_network_forbidden')
    def address(value):
        if not isinstance(value, tuple) or len(value) < 2 or value[:2] != ('127.0.0.1',28080):
            deny()
        increase('memory')
    def connect(sock, value):
        address(value)
        return original_connect(sock, value)
    def connect_ex(sock, value):
        address(value)
        return original_connect_ex(sock, value)
    def resolve(host, port, *args, **kwargs):
        if (host,port) != ('127.0.0.1',28080):
            deny(host,port)
        increase('memory')
        return original_resolve(host,port,*args,**kwargs)
    socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, resolve
    control.active = True
    try:
        with socket.socket() as probe:
            for call in (lambda:probe.connect(('192.0.2.1',443)), lambda:probe.connect_ex(('192.0.2.1',443)),
                         lambda:socket.getaddrinfo('invalid.example',443)):
                try:
                    call()
                except RuntimeError:
                    continue
                raise ValueError('network_denial_control_failed')
    finally:
        control.active = False
    require(counts['controls_blocked'] == 3)
    return counts


def timestamp(value):
    if isinstance(value, (int,float)) and not isinstance(value, bool):
        require(math.isfinite(value) and value >= 0)
        return float(value)
    require(isinstance(value, str))
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    require(result.tzinfo is not None)
    return result.timestamp()


def auth_preserved(before, after):
    """Exact secrets/OAuth/state; only bounded native ZAI usage bookkeeping may move."""
    require(isinstance(before,bytes) and isinstance(after,bytes) and max(len(before),len(after)) <= 262144)
    if before == after:
        return True
    try:
        canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
        old, new = json.loads(before), json.loads(after)
        if canonical(old) == canonical(new):
            return True
        require(isinstance(old, dict) and isinstance(new, dict) and set(old) == set(new))
        a,b = copy.deepcopy(old),copy.deepcopy(new)
        if 'updated_at' in a:
            require(timestamp(b['updated_at']) >= timestamp(a['updated_at']))
            a.pop('updated_at'); b.pop('updated_at')
        ap,bp = a.get('credential_pool'),b.get('credential_pool')
        require(isinstance(ap, dict) and isinstance(bp, dict) and set(ap) == set(bp) and 'zai' in ap)
        ar,br = ap.pop('zai'),bp.pop('zai')
        require(canonical(a) == canonical(b) and isinstance(ar,list) and isinstance(br,list) and len(ar) == len(br) <= 16)
        def indexed(rows):
            require(all(isinstance(r,dict) and isinstance(r.get('id'),str) for r in rows))
            result={r['id']:r for r in rows}
            require(len(result) == len(rows))
            return result
        aa,bb=indexed(ar),indexed(br)
        require(set(aa) == set(bb))
        delta=0
        old_priorities,new_priorities=[],[]
        for ident, row in aa.items():
            other=bb[ident]
            require(set(row) == set(other))
            c,d=dict(row),dict(other)
            if 'request_count' in c:
                x,y=c.pop('request_count'),d.pop('request_count')
                require(type(x) is int and type(y) is int and 0 <= x <= y)
                delta += y-x
            if 'priority' in c:
                x,y=c.pop('priority'),d.pop('priority')
                require(type(x) is int and type(y) is int and x >= 0 and y >= 0)
                old_priorities.append(x);new_priorities.append(y)
            require(canonical(c) == canonical(d))
        require(0 <= delta <= 8 and sorted(old_priorities) == sorted(new_priorities))
        return True
    except (ValueError,TypeError,KeyError,OverflowError):
        return False


def preservation(before, after):
    require(set(before) == set(after) == set(FILES))
    equal={name:before[name] == after[name] for name in FILES}
    auth=auth_preserved(before['auth.json'],after['auth.json'])
    return dict(files_equal=equal, auth_sensitive_state_preserved=auth,
        auth_usage_metadata_changed=not equal['auth.json'],
        preserved=all(equal[n] for n in FILES if n != 'auth.json') and auth)


def validate_comparison(value):
    require(isinstance(value, dict) and set(value) == COMPARISON_FLAGS | {'files_equal'})
    require(all(type(value[k]) is bool for k in COMPARISON_FLAGS)
        and isinstance(value['files_equal'], dict) and set(value['files_equal']) == set(FILES)
        and all(type(x) is bool for x in value['files_equal'].values())
        and value['auth_usage_metadata_changed'] is (not value['files_equal']['auth.json']))
    return value


def validate_observation(value):
    require(isinstance(value,dict) and set(value) == {'files_equal','auth_sensitive_state_preserved',
        'auth_usage_metadata_changed','preserved','memory_operations','blocked_context_discovery_attempts',
        'unexpected_network_attempts','network_denial_controls_passed'})
    require(isinstance(value['files_equal'],dict) and set(value['files_equal']) == set(FILES)
        and all(type(x) is bool for x in value['files_equal'].values())
        and all(value['files_equal'][n] is True for n in FILES if n != 'auth.json')
        and value['auth_sensitive_state_preserved'] is True and value['preserved'] is True
        and type(value['auth_usage_metadata_changed']) is bool
        and value['auth_usage_metadata_changed'] is (not value['files_equal']['auth.json'])
        and value['network_denial_controls_passed'] is True
        and type(value['unexpected_network_attempts']) is int and value['unexpected_network_attempts'] == 0
        and type(value['memory_operations']) is int and 1 <= value['memory_operations'] <= 64
        and type(value['blocked_context_discovery_attempts']) is int
        and 0 <= value['blocked_context_discovery_attempts'] <= 64)
    return value


def archived_files(payload):
    require(isinstance(payload,bytes) and len(payload) <= 20*1024*1024)
    result={}
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as archive:
        for member in archive:
            if member.name not in FILES:
                continue
            require(member.name not in result and member.isfile() and member.size <= 262144)
            raw=archive.extractfile(member).read(262145)
            require(len(raw) == member.size)
            result[member.name]=raw
    require(set(result) == set(FILES))
    return result


def child():
    """Compare a retained authenticated generation in RAM; no extraction or writes."""
    import hashlib
    packet=json.loads(sys.stdin.buffer.readline(32*1024*1024+1))
    require(set(packet) == {'archive','key','endpoint_path'})
    account=pwd.getpwuid(os.geteuid())
    status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and not os.getgroups() and status['NoNewPrivs'].strip() == '1'
        and all(status[k].strip() == '0000000000000000' for k in ('CapEff','CapAmb'))
        and account.pw_name.startswith('ecbot_')
        and account.pw_dir == '/var/lib/enhanced-cognee-profiles/'+account.pw_name[6:])
    raw=(ARTIFACT/'bind_launch_model_credential.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BINDING_SHA)
    module={'__name__':'verified_retained_model_comparison'}
    exec(compile(raw,'<verified-public-model-binding>','exec'),module)
    os.environ.clear()
    profile=Path(account.pw_dir)/'.hermes'
    os.environ.update(HOME=str(profile),HERMES_HOME=str(profile),PATH='/usr/bin:/bin',LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0,str(RELEASE/'repo'))
    import yaml
    from agent.secret_scope import _parse_env_text,_decode_env_bytes
    after={name:module['owner_file'](profile,name) for name in FILES}
    key_env, endpoint=module['pointer'](yaml.safe_load(after['config.yaml']))
    env=_parse_env_text(_decode_env_bytes(after['.env']))
    observation=preservation(archived_files(base64.b64decode(packet['archive'],validate=True)),after)
    observation.update(complete=True,bound_model_key_matches=env.get(key_env) == packet['key'],
                       endpoint_matches=endpoint == packet['endpoint_path'],source_profile_changed=False)
    print(json.dumps(observation))


def compare_generation(row, prior, authority, helper, source, read, write, evidence):
    """Root authenticates/decrypts; only this profile's plaintext goes to its owner."""
    import hashlib,hmac,re,subprocess
    recovery=json.loads(read(prior/'model-profile-recovery.json',0))
    require(recovery.get('complete') is True)
    generation=Path(recovery['generation'])
    require(generation.parent == Path('/var/backups/enhanced-cognee')
        and re.fullmatch(r'hermes_candidate_renewed_[a-f0-9]{32}\.tar\.age',generation.name))
    saved=read(generation,0,32*1024*1024)
    signed=json.loads(read(generation.with_name(generation.name+'.json'),0))
    backup=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
    key=backup['ENHANCED_BACKUP_SIGNING_KEY'].encode()
    unsigned={k:v for k,v in signed.items() if k != 'signature'}
    canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    require(signed.get('complete') is True and signed.get('source_profile_id') == row['profile_id']
        and signed.get('format') == 'hermes-candidate-profile-sqlite-tar+age-v2'
        and signed.get('capture_component_sha256') == CAPTURE_SHA
        and signed.get('signing_key_id') == backup['ENHANCED_BACKUP_SIGNING_KEY_ID']
        and signed.get('ciphertext_sha256') == hashlib.sha256(saved).hexdigest()
        and hmac.compare_digest(signed['signature'],hmac.new(key,canonical(unsigned),hashlib.sha256).hexdigest()))
    del key,backup
    decrypted=subprocess.run(['/usr/local/bin/age','--decrypt','--identity','/etc/enhanced-cognee/age-recovery-identity.txt'],
        input=saved,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=True,cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
    require(len(decrypted.stdout) <= 20*1024*1024)
    code,line=helper['owner_program'](source)
    packet=dict(archive=base64.b64encode(decrypted.stdout).decode(),key=authority['key'],endpoint_path=authority['endpoint_path'])
    frame=line+json.dumps(packet).encode()+b'\n'
    require(len(frame) <= 32*1024*1024)
    account=pwd.getpwnam(row['user'])
    result=subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',str(RELEASE/'venv/bin/python'),'-I','-B','-c',code],
        input=frame,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=40,cwd='/',user=account.pw_uid,
        group=account.pw_gid,extra_groups=(),env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    require(result.returncode == 0 and 0 < len(result.stdout) <= 8192)
    value=json.loads(result.stdout)
    validate_comparison(value)
    write(evidence/'retained-profile-comparison.json',json.dumps(value).encode())
    if not (all(value.get(k) is True for k in ('complete','preserved','bound_model_key_matches','endpoint_matches','auth_sensitive_state_preserved'))
            and value['source_profile_changed'] is False):
        raise ComparisonError(value)
    return value
