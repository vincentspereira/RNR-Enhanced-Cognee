"""Bounded staging of remaining named-profile generations into locked accounts.

Reuse all 42 completed encrypted backups and the first candidate's shared passes.
No source recapture, provider activation, new credential, model or gateway call.
Root creates only new empty homes; owner children probe/read/restore private data.
"""
from __future__ import annotations
import base64
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import selectors
import shutil
import stat
import subprocess
import sys
import tempfile
import time

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RECOVERY = BASE / 'operator-evidence/named-profile-backup-24br2v3u'
PARENT = Path('/var/lib/enhanced-cognee-profiles')
PLAN_SHA = 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b'
ACCOUNT_SHA = 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94'
STAGE_SHA = '3bfc6b324ba8ba9e0f80cf7c90bcd605f68649a50c00a7e8d47914400f858f0b'


def require(value):
    if not value:
        raise ValueError('named_fleet_staging_refused')


def definitions(path,digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    value = {'__name__':'verified_named_fleet_staging','__file__':str(path)}
    exec(compile(raw,'<verified-public-support>','exec'),value)
    return value


def selection(plans,current_profile):
    require(isinstance(plans,list) and 0 < len(plans) <= 256)
    named = [row for row in plans if row.get('source_user') == 'vincentspereira'
        and Path(row.get('source_profile','/')).parent == Path('/home/vincentspereira/.hermes/profiles')]
    require(len(named) == 42 and len({row['profile_id'] for row in named}) == 42
        and len([row for row in named if row['profile_id'] == current_profile]) == 1)
    selected = [row for row in named if row['profile_id'] != current_profile]
    require(len(selected) == 41)
    for row in selected:
        ident = row.get('profile_id')
        require(isinstance(ident,str) and re.fullmatch(r'[a-f0-9]{16}',ident)
            and row.get('proposed_user') == 'ecbot_' + ident
            and row.get('proposed_home') == str(PARENT / ident)
            and row.get('proposed_uid') is None and row.get('enabled') is False
            and row.get('admission') == 'pending' and isinstance(row.get('gates'),dict)
            and row['gates'] and all(value is False for value in row['gates'].values()))
    return selected


def no_collision(rows):
    for row in rows:
        for lookup in (pwd.getpwnam,grp.getgrnam):
            try:
                lookup(row['proposed_user'])
            except KeyError:
                pass
            else:
                raise ValueError('existing_identity_preserved')
        require(not os.path.lexists(row['proposed_home']))


def boundary_pair(account,peer,helper,source):
    code,line = helper['owner_program'](source)
    accounts,children = [account,peer],[]
    selector = selectors.DefaultSelector()
    try:
        for identity in accounts:
            children.append(subprocess.Popen(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',code],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd='/',
                user=identity.pw_uid,group=identity.pw_gid,extra_groups=(),
                env={'PATH':'/usr/bin:/bin','HOME':identity.pw_dir,'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'}))
        for index,child in enumerate(children):
            other = 1-index
            packet = dict(user=accounts[index].pw_name,home=accounts[index].pw_dir,
                peer_home=accounts[other].pw_dir,peer_pid=children[other].pid)
            child.stdin.write(line + json.dumps(packet).encode() + b'\n')
            child.stdin.flush()
            os.set_blocking(child.stdout.fileno(),False)
            selector.register(child.stdout,selectors.EVENT_READ,index)
        reports,buffers = {},[bytearray(),bytearray()]
        deadline = time.monotonic() + 30
        while len(reports) != 2:
            require(time.monotonic() < deadline)
            for event,_ in selector.select(max(0.01,deadline-time.monotonic())):
                index = event.data
                chunk = os.read(event.fileobj.fileno(),8193-len(buffers[index]))
                require(chunk)
                buffers[index].extend(chunk)
                require(len(buffers[index]) <= 8192)
                if b'\n' in buffers[index]:
                    reports[index] = helper['receipt'](json.loads(buffers[index]))
                    selector.unregister(event.fileobj)
        for child in children:
            child.stdin.write(b'!')
            child.stdin.flush()
            child.stdin.close()
        require(all(child.wait(timeout=10) == 0 for child in children))
        return dict(candidate=reports[0],peer=reports[1])
    finally:
        selector.close()
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdout.close()
            if not child.stdin.closed:
                child.stdin.close()


def restore_candidate(account,generation,core,stage,helper,read,source,key):
    ciphertext = read(generation,0,stage['MAX_PACKET'])
    manifest = json.loads(read(generation.with_name(generation.name + '.json'),0))
    ident = account.pw_name[6:]
    stage['verify_manifest'](manifest,key,ident,ciphertext)
    plain = subprocess.run([str(stage['AGE']),'--decrypt','--identity',str(stage['IDENTITY'])],input=ciphertext,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=20,cwd='/',
        env={'PATH':'/usr/bin:/bin','HOME':'/','LANG':'C.UTF-8'})
    require(len(plain.stdout) <= 20 * 1024 * 1024)
    stage['privileged_environment_absent'](plain.stdout)
    code,line = helper['owner_program'](source)
    packet = dict(user=account.pw_name,uid=account.pw_uid,home=account.pw_dir,
        archive=base64.b64encode(plain.stdout).decode(),core=core.decode())
    raw = line + json.dumps(packet).encode() + b'\n'
    require(len(raw) <= stage['MAX_PACKET'])
    process = subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',code],
        input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=65,cwd='/',
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= 16384)
    value = json.loads(process.stdout)
    require(set(value) == {'complete','candidate','receipt','known_privileged_environment_fields_absent','profile_started'}
        and value['complete'] is True and value['known_privileged_environment_fields_absent'] is True
        and value['profile_started'] is False and Path(value['candidate']).parent == Path(account.pw_dir)
        and re.fullmatch(r'ec-named-profile-restore-[a-zA-Z0-9_-]{6,64}',Path(value['candidate']).name)
        and all(value['receipt'].get(k) is True for k in ('complete','archived_files_verified','private_restore_verified'))
        and value['receipt'].get('restored_profile_executed') is False
        and value['receipt'].get('sqlite_databases_verified') == manifest['receipt']['sqlite_databases'])
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory = Path(__file__).parent
    helper = definitions(directory / 'qualify_launch_isolated_accounts.py',ACCOUNT_SHA)
    stage = definitions(directory / 'stage_launch_named_candidate.py',STAGE_SHA)
    account_source = (directory / 'qualify_launch_isolated_accounts.py').read_bytes()
    stage_source = (directory / 'stage_launch_named_candidate.py').read_bytes()
    require(hashlib.sha256(account_source).hexdigest() == ACCOUNT_SHA
        and hashlib.sha256(stage_source).hexdigest() == STAGE_SHA)
    shared = definitions(directory / 'recover_launch_graph_operator.py',helper['SUPPORT_SHA'])
    read,write = shared['read_file'],shared['private_write']
    live = json.loads(read(BASE / 'operator-evidence/candidate-live-reload-o40ee8a4/summary.json',0))
    require(live.get('complete') is True and live.get('candidate_headless_gateway_reload_qualified') is True
        and live.get('renewed_profile_recovery_qualified') is True and live.get('qualification_processes_stopped') is True
        and live.get('operator_helper_sha256') == 'e345caf292465cf126c08c2e0b2825048c62a0bee13592446d7fa9a82d0f16ac')
    accepted = json.loads(read(RECOVERY / 'summary.json',0))
    require(accepted.get('complete') is True and accepted.get('named_profile_backup_restore_qualified') is True
        and accepted.get('disposable_restores_qualified') == 42
        and accepted.get('operator_helper_sha256') == 'a684dc78a62c623598ea1529dad9d9c1f305c9212efcd6f6d71f517e50c7ffcf')
    plan = read(helper['PLAN'],0)
    require(hashlib.sha256(plan).hexdigest() == PLAN_SHA)
    current = json.loads(read(BASE / 'operator-evidence/candidate-provider-f8uifc8j/binding.private.json',0))
    chosen = selection(json.loads(plan)['profiles'],current['profile_id'])
    existing = json.loads(read(BASE / 'operator-evidence/isolated-accounts-2eq6h4nn/accounts.private.json',0))
    peers = [row for row in existing if row['profile_id'] != current['profile_id']]
    require(len(peers) == 1)
    peer = pwd.getpwnam(peers[0]['user'])
    require(peer.pw_uid == peers[0]['uid'] and peer.pw_dir == peers[0]['home'] and peer.pw_uid != 0
        and os.getgrouplist(peer.pw_name,peer.pw_gid) == [peer.pw_gid])
    no_collision(chosen)
    helper['protected_parent'](PARENT)
    require(stat.S_IMODE(PARENT.stat().st_mode) == 0o711)
    driver = definitions(stage['BASE'] / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for target in (stage['AGE'],stage['IDENTITY'],stage['BACKUPS'],Path('/usr/sbin/useradd'),Path('/usr/bin/setpriv'),Path('/usr/sbin/nologin')):
        driver['protected'](target)
    driver['protected'](Path(helper['EXECUTABLE']),final_link=True)
    driver['protected'](Path(helper['EXECUTABLE']).resolve())
    core = (directory / 'capture_named_profile.py').read_bytes()
    require(hashlib.sha256(core).hexdigest() == stage['CORE_SHA'])
    key = json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))['ENHANCED_BACKUP_SIGNING_KEY'].encode()
    require(len(key) >= 32 and min(shutil.disk_usage(PARENT).free,shutil.disk_usage('/tmp').free) >= 512 * 1024 * 1024)
    generations = {}
    for row in chosen:
        ident = row['profile_id']
        require(not os.path.lexists(RECOVERY / (ident + '.candidate-stage.started.json')))
        done = json.loads(read(RECOVERY / (ident + '.done.json'),0))
        generation = Path(done['generation'])
        require(done.get('profile_id') == ident and done.get('signed_ciphertext_verified') is True
            and generation.parent == stage['BACKUPS'] and re.fullmatch(r'hermes_named_profile_[a-f0-9]{32}\.tar\.age',generation.name))
        ciphertext = read(generation,0,stage['MAX_PACKET'])
        stage['verify_manifest'](json.loads(read(generation.with_name(generation.name + '.json'),0)),key,ident,ciphertext)
        generations[ident] = generation
    evidence = Path(tempfile.mkdtemp(prefix='named-fleet-stage-',dir=BASE / 'operator-evidence'))
    write(RECOVERY / 'remaining-named-candidates.started.json',json.dumps(dict(evidence=str(evidence))).encode())
    result = dict(complete=False,evidence=str(evidence),source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),selected_named_profiles=len(chosen),
        account_creation_count=0,paired_os_boundaries_qualified=0,inactive_candidates_staged=0,
        previously_qualified_candidate_preserved=True,main_profile_deferred=True,source_profiles_changed=False,
        credentials_issued=0,gateways_started=0,units_installed=0,private_keys_sent_to_owner_children=False,
        scheduled_renewal_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False)
    write(evidence / 'started.json',json.dumps(result).encode())
    accounts = []
    known_uids = {row['uid'] for row in existing}
    phase = 'account_creation'
    try:
        for row in chosen:
            ident = row['profile_id']
            result['current_profile_id'] = ident
            phase = 'account_creation'
            write(RECOVERY / (ident + '.candidate-stage.started.json'),json.dumps(dict(evidence=str(evidence))).encode())
            subprocess.run(['/usr/sbin/useradd','--system','--user-group','--no-create-home',
                '--home-dir',row['proposed_home'],'--shell','/usr/sbin/nologin','--password','!',row['proposed_user']],
                check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            result['account_creation_count'] += 1
            account = pwd.getpwnam(row['proposed_user'])
            require(account.pw_uid != 0 and account.pw_uid not in known_uids and account.pw_dir == row['proposed_home']
                and account.pw_shell == '/usr/sbin/nologin' and os.getgrouplist(account.pw_name,account.pw_gid) == [account.pw_gid]
                and grp.getgrgid(account.pw_gid).gr_name == account.pw_name)
            known_uids.add(account.pw_uid)
            write(evidence / (ident + '.created.private.json'),json.dumps(dict(profile_id=ident,user=account.pw_name,
                uid=account.pw_uid,gid=account.pw_gid,home=account.pw_dir)).encode())
            home = Path(account.pw_dir)
            home.mkdir(mode=0o700)
            (home / '.hermes').mkdir(mode=0o700)
            write(home / '.hermes/.isolation-marker',b'invented-isolation-marker-v1',account.pw_uid)
            os.chown(home / '.hermes',account.pw_uid,account.pw_gid)
            os.chown(home,account.pw_uid,account.pw_gid)
            phase = 'paired_os_boundary'
            boundary = boundary_pair(account,peer,helper,account_source)
            write(evidence / (ident + '.boundary.private.json'),json.dumps(boundary).encode())
            result['paired_os_boundaries_qualified'] += 1
            phase = 'authenticated_owner_restore'
            candidate = restore_candidate(account,generations[ident],core,stage,helper,read,
                stage_source,key)
            record = dict(candidate,profile_id=ident,user=account.pw_name,uid=account.pw_uid,
                home=account.pw_dir,generation=str(generations[ident]),paired_os_boundary_qualified=True,
                existing_binding_preserved=row['existing_binding'] is not None)
            write(evidence / (ident + '.candidate.private.json'),json.dumps(record).encode())
            accounts.append(dict(user=account.pw_name,uid=account.pw_uid,home=account.pw_dir,profile_id=ident))
            result['inactive_candidates_staged'] += 1
        write(evidence / 'accounts.private.json',json.dumps(accounts).encode())
        result.pop('current_profile_id',None)
        result.update(complete=True,all_new_uids_distinct=True,authenticated_candidate_copies_verified=True)
    except Exception:
        result.update(category='named_fleet_staging_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase)
    write(evidence / 'summary.json',json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"named_fleet_preflight_refused_preserve_evidence"}')
        raise SystemExit(1)
