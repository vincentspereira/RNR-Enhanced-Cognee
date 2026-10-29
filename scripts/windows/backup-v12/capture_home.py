"""Stream a Linux home as tar without mounts or following compatibility links.

Hermes' native per-database images are merged into the stream, rather than
backing up both a compressed ZIP and the same profile data a second time.
Only metadata/counts go to stderr; archive bytes go exclusively to stdout.
"""
import argparse
import datetime
import fnmatch
import hashlib
import io
import json
import os
import platform
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PRUNE = {'.cache', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache',
         '.mypy_cache', '.ruff_cache', '.next', '.nuxt', '.tox', '.turbo'}
REBUILDABLE = {'.rustup/toolchains', '.cargo/registry', '.cargo/git',
               '.local/share/uv', '.local/share/pnpm/store', '.nvm/.cache',
               '.local/share/rnr-backup-tools/powershell-parser',
               '.local/share/rnr-backup-tools/restic/0.19.1'}
HERMES_CACHE = {'cache', 'checkpoints'}


def recovery_inventory():
    """Local-only recovery metadata; values enter encrypted tar, never logs."""
    result = {'python': sys.version, 'kernel': platform.release(), 'commands': {}}
    environment = dict(os.environ, LC_ALL='C', PIP_DISABLE_PIP_VERSION_CHECK='1',
                       PIP_NO_INDEX='1', NPM_CONFIG_UPDATE_NOTIFIER='false')
    environment['PATH'] = ':'.join(p for p in environment.get('PATH', '').split(':')
                                   if p and not __import__('re').match(r'^/mnt/[a-zA-Z]/', p))
    commands = {
        'packages': ['dpkg-query', '-W', '-f=${Package}\t${Version}\n'],
        'crontab': ['crontab', '-l'],
    }
    if __import__('importlib.util').util.find_spec('pip'):
        commands['pip'] = [sys.executable, '-I', '-m', 'pip', 'list', '--format=json', '--disable-pip-version-check']
    else:
        result['commands']['pip'] = {'state': 'not_installed'}
    for name, arguments in commands.items():
        if not shutil.which(arguments[0], path=environment['PATH']):
            result['commands'][name] = {'state': 'not_installed'}
            continue
        completed = subprocess.run(arguments, env=environment, capture_output=True, text=True, timeout=180)
        empty_cron = name == 'crontab' and completed.returncode == 1 and 'no crontab for' in completed.stderr.lower()
        if completed.returncode and not empty_cron:
            raise RuntimeError('System recovery inventory failed: ' + name)
        result['commands'][name] = {'state': 'empty' if empty_cron else 'ok', 'content': completed.stdout,
                                     'diagnostics': completed.stderr}
    # Reuse the installed native nvm default; never install/update a runtime.
    npm_code = r'''
set -e
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
 . "$NVM_DIR/nvm.sh"
 nvm use --silent default >/dev/null
fi
command -v npm >/dev/null 2>&1 || { printf '{"state":"not_installed"}'; exit 0; }
npm_path="$(command -v npm)"; node_path="$(command -v node)"
case "$npm_path:$node_path" in *'/mnt/'*|*'.exe'*|*'.cmd'*|*'.bat'*) exit 7;; esac
case "$npm_path" in /*) ;; *) exit 8;; esac
case "$node_path" in /*) ;; *) exit 9;; esac
printf '%s\n%s\n' "$npm_path" "$node_path"
npm list --global --json --depth=0
'''
    completed = subprocess.run(['/bin/bash', '-lc', npm_code], env=environment,
                               capture_output=True, text=True, timeout=180)
    if completed.returncode:
        raise RuntimeError('Native Linux npm recovery inventory failed')
    npm_missing = completed.stdout.strip() == '{"state":"not_installed"}'
    result['commands']['npm'] = {'state': 'not_installed' if npm_missing else 'ok',
                                 'content': completed.stdout, 'diagnostics': completed.stderr}
    for path in ('/etc/os-release', '/etc/wsl.conf', '/etc/fstab'):
        if Path(path).is_file():
            result[path] = Path(path).read_text()
    return result


def combined_fingerprint(home, inventory):
    payload = {'home': fingerprint_home(home), 'system': inventory}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def excluded(relative, is_directory=False):
    parts = PurePosixPath(relative).parts
    if any(part in PRUNE for part in parts):
        return True
    if any(relative == p or relative.startswith(p + '/') for p in REBUILDABLE):
        return True
    if len(parts) >= 2 and parts[0] == '.hermes':
        if parts[1] in HERMES_CACHE or parts[1] == 'backups':
            return True
        if len(parts) >= 4 and parts[1] == 'profiles' and parts[3] in HERMES_CACHE:
            return True
    return parts[-1].endswith(('.sock', '.pid')) or parts[-1].startswith('.s.PGSQL.')


def walk(root, prefix=''):
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda e: e.name)
        for entry in ordered:
            path = Path(entry.path)
            relative = (PurePosixPath(prefix) / path.relative_to(root)).as_posix()
            is_directory = entry.is_dir(follow_symlinks=False)
            if excluded(relative, is_directory):
                continue
            yield path, relative
            if is_directory:
                pending.append(path)


def fingerprint_hermes(home):
    digest = hashlib.sha256()
    for path, relative in walk(home / '.hermes', prefix='.hermes'):
        info = path.lstat()
        digest.update(json.dumps([relative, info.st_mode, info.st_size,
                                  info.st_mtime_ns, info.st_ctime_ns], ensure_ascii=True).encode())
    return digest.hexdigest()


def fingerprint_home(home):
    digest = hashlib.sha256()
    for path, relative in walk(home):
        info = path.lstat()
        if stat.S_ISSOCK(info.st_mode) or stat.S_ISFIFO(info.st_mode):
            continue
        digest.update(json.dumps([relative, info.st_mode, info.st_uid, info.st_gid,
                                  info.st_size, info.st_mtime_ns, info.st_ctime_ns,
                                  info.st_ino, os.readlink(path) if path.is_symlink() else None],
                                 ensure_ascii=True).encode())
    return digest.hexdigest()


def native_hermes_zip(home, cache):
    hermes = home / '.hermes'
    if not hermes.is_dir() or hermes.is_symlink():
        raise RuntimeError('Hermes home requires a real, owner-accessible directory')
    # This fingerprint is an optimisation, not a consistency assertion. Any
    # changed file metadata recreates the native, WAL-safe database images.
    fingerprint = fingerprint_hermes(home)
    state_path, cached = cache / 'native-state.json', cache / 'native-last.zip'
    if state_path.exists() and cached.exists():
        state = json.loads(state_path.read_text())
        if state.get('fingerprint') == fingerprint:
            return cached, True
    output = cache / ('native-' + next(tempfile._get_candidate_names()) + '.zip')
    env = dict(os.environ)
    env['HERMES_HOME'] = str(hermes)
    result = subprocess.run(['/bin/bash', '-lc',
        'hermes backup --keep 0 --output "$RNR_BACKUP_NATIVE_OUTPUT"'],
        env=dict(env, RNR_BACKUP_NATIVE_OUTPUT=str(output)), stdout=sys.stderr,
        stderr=sys.stderr, timeout=3600)
    if result.returncode or not output.is_file():
        raise RuntimeError('Native Hermes backup failed; existing generations preserved')
    # CRC is checked when every admitted entry is streamed to tar below.
    with zipfile.ZipFile(output) as archive:
        if not archive.namelist():
            raise RuntimeError('Native Hermes archive is empty')
    os.chmod(output, 0o600)
    os.replace(output, cached)
    state_path.write_text(json.dumps({'fingerprint': fingerprint}))
    os.chmod(state_path, 0o600)
    return cached, False


def snapshot_database(path, scratch):
    with path.open('rb') as handle:
        if handle.read(16) != b'SQLite format 3\0':
            return None
    if any(p in {'tests', 'test', 'fixtures', '.git'} for p in path.parts):
        return None  # Test fixtures must retain their original exact bytes.
    destination = scratch / ('sqlite-' + next(tempfile._get_candidate_names()))
    source = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=30)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        if target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite snapshot did not pass quick_check')
    finally:
        target.close()
        source.close()
    os.chmod(destination, 0o600)
    return destination


def capture(home, hermes=False, supplied_zip=None, inventory=None):
    if not home.is_dir() or home.is_symlink():
        raise RuntimeError('Home root must be a real directory')
    cache = home / '.cache/rnr-backup-v12'
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(cache, 0o700)
    coverage = {'format': 'rnr-home-tar-v12', 'hermes': hermes, 'files': 0,
                'symlinks': 0, 'sqlite_snapshots': 0, 'profiles': {},
                'native_zip_reused': False, 'profile_backups_included': True,
                'hermes_generated_backup_directory_excluded': True,
                'archive_is_not_a_complete_distro_image': True,
                'runtime_special_files_omitted': 0, 'external_symlinks': 0}
    zip_names = set()
    database_names = set()
    journal_names = set()
    native = None
    if hermes:
        if supplied_zip:
            native_path = Path(supplied_zip)
        else:
            native_path, coverage['native_zip_reused'] = native_hermes_zip(home, cache)
        native = zipfile.ZipFile(native_path)
        raw_names = native.namelist()
        if len(raw_names) != len(set(raw_names)):
            raise RuntimeError('Duplicate native ZIP entries require review')
        for entry in raw_names:
            parts = PurePosixPath(entry).parts
            if PurePosixPath(entry).is_absolute() or '..' in parts or '\\' in entry:
                raise RuntimeError('Unsafe native ZIP path')
            if excluded('.hermes/' + entry.rstrip('/')):
                continue
            zip_names.add(entry)
            if len(parts) >= 3 and parts[0] == 'profiles':
                row = coverage['profiles'].setdefault(parts[1], {'config': False, 'files': 0, 'skills': 0, 'plugins': 0, 'databases': 0})
                row['config'] |= parts[-1] in ('config.yaml', 'config.yml', 'config.json')
                row['files'] += int(not entry.endswith('/'))
                row['skills'] += int('skills' in parts)
                row['plugins'] += int('plugins' in parts)
                row['databases'] += int(entry.endswith(('.db', '.sqlite', '.sqlite3')))
        profiles = home / '.hermes/profiles'
        for profile in profiles.iterdir() if profiles.exists() else ():
            if profile.is_dir() and any((profile / name).exists() for name in ('config.yaml', 'config.yml', 'config.json')):
                if not coverage['profiles'].get(profile.name, {}).get('config'):
                    raise RuntimeError('An active profile is absent from the native archive')
    try:
        with tempfile.TemporaryDirectory(prefix='sqlite-', dir=cache) as temporary:
            scratch = Path(temporary)
            with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                if native:
                    for name in sorted(zip_names):
                        item = native.getinfo(name)
                        if item.is_dir():
                            continue
                        full_name = '.hermes/' + name
                        info = tarfile.TarInfo(full_name)
                        info.size = item.file_size
                        info.mode = 0o600
                        info.uid, info.gid = os.getuid(), os.getgid()
                        live_path = home / full_name
                        if live_path.is_file() and not live_path.is_symlink():
                            live_info = live_path.stat()
                            info.mode = stat.S_IMODE(live_info.st_mode)
                            info.uid, info.gid = live_info.st_uid, live_info.st_gid
                        info.mtime = datetime.datetime(*item.date_time).timestamp()
                        with native.open(item) as content:
                            archive.addfile(info, content)
                        if name.endswith(('.db', '.sqlite', '.sqlite3')):
                            database_names.add(full_name)
                            journal_names.update(full_name + suffix for suffix in ('-wal', '-shm', '-journal'))
                        coverage['files'] += 1
                for path, relative in walk(home):
                    if relative.startswith('.hermes/') and relative[8:] in zip_names:
                        continue
                    # Do not add a live symlink over a directory expanded by
                    # the native archive, or a live WAL over a DB snapshot.
                    if relative.startswith('.hermes/') and path.is_symlink() and any(n.startswith(relative[8:] + '/') for n in zip_names):
                        continue
                    if relative in journal_names:
                        continue
                    details = path.lstat()
                    if stat.S_ISLNK(details.st_mode):
                        archive.add(path, arcname=relative, recursive=False)
                        coverage['symlinks'] += 1
                        try:
                            path.resolve().relative_to(home.resolve())
                        except ValueError:
                            coverage['external_symlinks'] += 1
                    elif stat.S_ISDIR(details.st_mode):
                        archive.add(path, arcname=relative, recursive=False)
                    elif stat.S_ISREG(details.st_mode):
                        snap = snapshot_database(path, scratch) if path.suffix in ('.db', '.sqlite', '.sqlite3') else None
                        if snap:
                            info = archive.gettarinfo(path, arcname=relative)
                            info.size = snap.stat().st_size
                            with snap.open('rb') as content:
                                archive.addfile(info, content)
                            snap.unlink()  # Only this helper's disposable snapshot.
                            database_names.add(relative)
                            journal_names.update(relative + suffix for suffix in ('-wal', '-shm', '-journal'))
                            coverage['sqlite_snapshots'] += 1
                        else:
                            archive.add(path, arcname=relative, recursive=False)
                        coverage['files'] += 1
                    elif stat.S_ISSOCK(details.st_mode) or stat.S_ISFIFO(details.st_mode):
                        coverage['runtime_special_files_omitted'] += 1
                    else:
                        # Runtime sockets are excluded, never mistaken for data.
                        raise RuntimeError('Unclassified special file requires backup policy review')
                content = json.dumps(coverage, sort_keys=True, ensure_ascii=True).encode()
                info = tarfile.TarInfo('.rnr-backup-v12/coverage.json')
                info.size, info.mode, info.mtime = len(content), 0o600, 0
                archive.addfile(info, io.BytesIO(content))
                metadata = json.dumps(inventory, sort_keys=True, ensure_ascii=True).encode()
                info = tarfile.TarInfo('.rnr-backup-v12/system-recovery.json')
                info.size, info.mode, info.mtime = len(metadata), 0o600, 0
                archive.addfile(info, io.BytesIO(metadata))
        sys.stdout.buffer.flush()
    finally:
        if native:
            native.close()
    print(json.dumps({'home_capture_complete': True, 'profiles': len(coverage['profiles']),
                      'files': coverage['files'], 'sqlite_snapshots': coverage['sqlite_snapshots']}), file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes', action='store_true')
    parser.add_argument('--root', type=Path, default=Path.home())
    parser.add_argument('--hermes-zip')
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--test-no-system-inventory', action='store_true')
    options = parser.parse_args()
    inventory = {'synthetic_test': True} if options.test_no_system_inventory else recovery_inventory()
    if options.inventory_only:
        print(json.dumps({'fingerprint': combined_fingerprint(options.root, inventory)}))
    else:
        capture(options.root, options.hermes, options.hermes_zip, inventory)
