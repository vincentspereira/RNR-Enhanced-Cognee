"""Read-only live launch observations, not fleet admission or process control.

Only owner children inspect their own /proc entries. Raw argv/environment,
credentials, messages and process working directories are never persisted.
Unseen, inaccessible and ambiguous launches remain unresolved. No keys read.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import resource
import stat
import subprocess
import sys
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
EXECUTABLE = '/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
LIMIT = 512


def saved_pm2_definitions(home, uid):
    """Summarize saved configuration only; never contact/start the PM2 daemon."""
    path = Path(home) / '.pm2/dump.pm2'
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return dict(available=False, saved_entries=0, direct_gateway_entries=0)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_size <= 4194304)
        raw = stream.read(4194305)
        after = os.fstat(stream.fileno())
        require(len(raw) == info.st_size and (info.st_ino, info.st_mtime_ns, info.st_ctime_ns)
                == (after.st_ino, after.st_mtime_ns, after.st_ctime_ns))
    entries = json.loads(raw)
    require(isinstance(entries, list) and len(entries) <= LIMIT)
    gateways, pinned_interpreters, explicit_homes = 0, 0, 0
    for entry in entries:
        require(isinstance(entry, dict))
        env = entry.get('pm2_env', entry)
        require(isinstance(env, dict))
        script = env.get('pm_exec_path')
        if not isinstance(script, str) or Path(script).parts[-2:] != ('gateway', 'run.py'):
            continue
        gateways += 1
        interpreter = env.get('exec_interpreter')
        # String equality suffices for this conservative definition check.
        # Do not follow arbitrary saved paths or execute the saved program.
        pinned_interpreters += interpreter == EXECUTABLE
        nested = env.get('env', {})
        home_value = env.get('HERMES_HOME', nested.get('HERMES_HOME') if isinstance(nested, dict) else None)
        explicit_homes += profile_path(home_value, home) is not None
    return dict(available=True, saved_entries=len(entries), direct_gateway_entries=gateways,
                exact_pinned_interpreter_entries=pinned_interpreters, explicit_in_home_profile_entries=explicit_homes,
                live_execution_proven=False)


def require(value):
    if not value:
        raise ValueError('launch_observation_refused')


def profile_path(value, home):
    if not isinstance(value, str) or not value.isascii() or len(value) > 1024:
        return None
    path = PurePosixPath(value)
    root = PurePosixPath(home) / '.hermes'
    if str(path) != value or '..' in path.parts or not path.is_relative_to(root):
        return None
    if any('lswa' in part.lower() or 'legal-social-frameworks' in part.lower() for part in path.parts):
        return None
    return value


def observe(argv, environment, home, pinned_executable):
    """Extract only fixed classifications and an in-home profile binding."""
    direct_gateway = any(Path(arg).parts[-2:] == ('gateway', 'run.py') for arg in argv[:3])
    gateway = direct_gateway or any(a == 'gateway' and b == 'run' for a, b in zip(argv, argv[1:]))
    native = gateway or any(Path(arg).name in {'run_agent.py', 'hermes'} for arg in argv[:3])
    manager = any('pm2' in Path(arg).name.lower() for arg in argv[:2])
    if not native and not manager:
        return None
    selected = []
    for index, arg in enumerate(argv):
        if arg in {'--profile', '-p'} and index + 1 < len(argv):
            selected.append(argv[index + 1])
        elif arg.startswith('--profile='):
            selected.append(arg.split('=', 1)[1])
    selectors_valid = len(selected) <= 1 and all(
        value and len(value) <= 128 and value.isascii()
        and all(c.isalnum() or c in '_-' for c in value) for value in selected)
    env_profiles = [item.split('=', 1)[1] for item in environment if item.startswith('HERMES_HOME=')]
    env_path = profile_path(env_profiles[0], home) if len(env_profiles) == 1 else None
    cli_path = profile_path(str(PurePosixPath(home) / '.hermes/profiles' / selected[0]), home) if selectors_valid and selected else None
    conflict = bool(cli_path and env_path and cli_path != env_path) or bool(env_profiles and env_path is None)
    # Missing env/CLI is intentionally not inferred from the current active profile.
    binding = None if conflict or not selectors_valid else cli_path or env_path
    return dict(kind='gateway' if gateway else 'native' if native else 'manager',
                profile_home=binding, profile_selector_conflict=conflict or not selectors_valid,
                pinned_executable=pinned_executable,
                launch_binding_qualified=False)


def owner_child(*, restricted=True):
    uid = os.geteuid()
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(uid != 0)
    if restricted:
        require(not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
                and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))
    home = pwd.getpwuid(uid).pw_dir
    pinned = Path(EXECUTABLE).resolve(strict=True)
    rows, refused, races, inspected = [], 0, 0, 0
    entries = [path for path in Path('/proc').iterdir() if path.name.isdecimal()]
    require(len(entries) <= 32768)
    for path in entries:
        try:
            before = path.stat()
            if before.st_uid != uid or int(path.name) == os.getpid():
                continue
            inspected += 1
            require(inspected <= 4096)
            # Do not inspect non-runtime processes or other users' processes.
            comm = (path / 'comm').read_text()[:128].strip().lower()
            if not any(word in comm for word in ('python', 'hermes', 'node', 'pm2')):
                continue
            with (path / 'cmdline').open('rb') as stream:
                raw = stream.read(65537)
            require(len(raw) <= 65536)
            argv = raw.decode('utf-8', errors='replace').rstrip('\0').split('\0')
            # First classify with no environment, then read only candidate runtimes.
            if observe(argv, [], home, False) is None:
                continue
            with (path / 'environ').open('rb') as stream:
                raw = stream.read(262145)
            require(len(raw) <= 262144)
            environment = raw.decode('utf-8', errors='replace').rstrip('\0').split('\0')
            row = observe(argv, environment, home, (path / 'exe').resolve(strict=True) == pinned)
            after = path.stat()
            require((before.st_ino, before.st_uid) == (after.st_ino, after.st_uid))
            rows.append(dict(row, pid=int(path.name)))
            require(len(rows) <= LIMIT)
        except (FileNotFoundError, ProcessLookupError):
            races += 1
        except PermissionError:
            refused += 1
    document = dict(rows=rows, refused=refused, races=races)
    if restricted:
        print(json.dumps(document))
    else:
        # Ordinary-owner observation is independent of the protected two-user
        # qualification. Never print paths, arguments or environment contents.
        print(json.dumps(dict(complete=True, stage='ordinary_owner_launch_snapshot', uid=uid,
            live_launch_candidates=len(rows), gateway_candidates=sum(row['kind'] == 'gateway' for row in rows),
            pinned_executable_candidates=sum(row['pinned_executable'] for row in rows),
            explicit_profile_bindings=sum(row['profile_home'] is not None for row in rows),
            selector_conflicts=sum(row['profile_selector_conflict'] for row in rows),
            inaccessible_processes=refused, transient_process_races=races,
            saved_pm2=saved_pm2_definitions(home, uid),
            protected_two_identity_qualification=False, profiles_changed=False, services_changed=False,
            keys_read=False, raw_arguments_or_environment_retained=False, fleet_launch_approved=False)))


def validate_child(document, home):
    require(isinstance(document, dict) and set(document) == {'rows', 'refused', 'races'})
    require(isinstance(document['rows'], list) and len(document['rows']) <= LIMIT)
    require(all(type(document[key]) is int and 0 <= document[key] <= 32768 for key in ('refused', 'races')))
    fields = {'kind', 'profile_home', 'profile_selector_conflict', 'pinned_executable', 'launch_binding_qualified', 'pid'}
    for row in document['rows']:
        require(isinstance(row, dict) and set(row) == fields)
        require(row['kind'] in {'gateway', 'native', 'manager'} and type(row['pid']) is int and 0 < row['pid'] < 2**31)
        require(all(type(row[key]) is bool for key in ('profile_selector_conflict', 'pinned_executable', 'launch_binding_qualified')))
        require(row['launch_binding_qualified'] is False)
        require(row['profile_home'] is None or profile_path(row['profile_home'], home) == row['profile_home'])
    return document


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    source = Path(__file__).read_bytes()
    raw = Path(__file__).with_name('recover_launch_graph_operator.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == SUPPORT_SHA and len(source) <= 65536)
    support = {'__name__': 'verified_launch_observation_files'}
    exec(compile(raw, '<verified-launch-files>', 'exec'), support)
    read, write = support['read_file'], support['private_write']
    gateway = json.loads(read(BASE / 'operator-evidence/gateway-renewal-v2/summary.json', 0))
    require(gateway.get('complete') is True and gateway.get('running_synthetic_gateway_reload_qualified') is True
            and gateway.get('operator_helper_sha256') == 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2')
    registry = json.loads(read(BASE / 'operator-evidence/token-bindings-o7gaywzr/bindings.private.json', 0))['rows']
    known = {(row['uid'], row['profile_home']) for row in registry if 'profile_home' in row}
    documents = []
    for user in ('vincentspereira', 'hermes-runtime'):
        account = pwd.getpwnam(user)
        code = "import sys\nn={'__name__':'owner_launch_observer'}\nexec(compile(sys.stdin.buffer.read(),'<owner-launch-observer>','exec'),n)\nn['owner_child']()\n"
        process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', EXECUTABLE, '-I', '-B', '-c', code],
            input=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30,
            user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd='/',
            env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        require(process.returncode == 0 and len(process.stdout) <= 262144)
        document = validate_child(json.loads(process.stdout), account.pw_dir)
        for row in document['rows']:
            row['matches_inventoried_profile'] = (account.pw_uid, row['profile_home']) in known
            if not row['matches_inventoried_profile']:
                row['profile_home'] = None
        documents.append(dict(document, uid=account.pw_uid))
    evidence = Path(tempfile.mkdtemp(prefix='launch-process-bindings-', dir=BASE / 'operator-evidence'))
    write(evidence / 'observations.private.json', json.dumps(documents).encode())
    rows = [row for document in documents for row in document['rows']]
    summary = dict(complete=True, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), owner_identities_inspected=len(documents),
        live_launch_candidates=len(rows), candidates_matching_inventory=sum(row['matches_inventoried_profile'] for row in rows),
        pinned_executable_candidates=sum(row['pinned_executable'] for row in rows),
        candidates_without_profile_binding=sum(row['profile_home'] is None for row in rows),
        selector_conflicts=sum(row['profile_selector_conflict'] for row in rows),
        inaccessible_processes=sum(document['refused'] for document in documents),
        transient_process_races=sum(document['races'] for document in documents),
        profiles_changed=False, services_changed=False, credentials_issued=0, keys_read=False,
        raw_arguments_or_environment_retained=False, launch_binding_qualified=False,
        dormant_launches_qualified=False, fleet_launch_approved=False)
    write(evidence / 'summary.json', json.dumps(summary).encode())
    print(json.dumps(summary))


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--owner-snapshot']:
            owner_child(restricted=False)
        else:
            main()
    except Exception:
        print('{"complete":false,"category":"launch_observation_refused_no_secret_output"}')
        raise SystemExit(1)
