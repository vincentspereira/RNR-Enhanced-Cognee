"""Owner-only main operational-state recovery, not full-home recovery.

V3 records reviewed live process-coordination files as explicit omissions and
checks durable directory membership independently of their atomic updates.
Original V1/V2 components remain unchanged. Durable content remains strict.

Derived from reviewed named capture e3dd6b934c6975b99d54f9042ed7aa7eb8204a6ba14f04e2d0364f6ecfdc0b48.
The original component remains unchanged. SQLite uses the backup API, not a
file copy. Root never walks this tree. Explicit omissions stay in the encrypted
manifest and originals remain in place. No model, program or restored profile
is executed. Full coverage and dependency rebuild remain separate gates.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import sqlite3
import stat
import tarfile
import tempfile
import time
from urllib.parse import quote

MAX_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE = 600 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_MANIFEST = 8 * 1024 * 1024
# Existing generations and rebuildable/legacy programs are not recursively
# copied into a new operational generation. Their exclusion never means delete.
OMITTED_TOP = {
    'profiles': 'separate_named_profile_generations',
    'backups': 'historical_generations_retained_in_place',
    'state-snapshots': 'historical_snapshots_retained_in_place',
    'cache': 'cache_rebuild_pending',
    'logs': 'diagnostic_logs_retained_in_place',
    'installs': 'program_environment_rebuild_pending',
    'lsp': 'program_environment_rebuild_pending',
    'tools': 'program_environment_rebuild_pending',
    'enhanced-cognee': 'legacy_checkout_retained_review_pending',
    'hermes-agent': 'program_reference_rebind_pending',
}
RUNTIME_FILES = {'spawn-ledger.json', 'gateway_state.json', 'gateway.pid',
                 'gateway.lock', 'state/gateway.heartbeat', 'state/dashboard_clients.heartbeat'}
CHECKPOINTS = {'guard', 'source_walk', 'sqlite_snapshot', 'payload_read',
               'stability_verification', 'archive_encoding'}
REASONS = {'capture_guard_refused', 'durable_file_changed_before_read',
           'durable_file_changed_during_read', 'durable_file_changed_after_read',
           'durable_directory_changed', 'database_committed_during_capture',
           'source_io_or_sqlite_error'}


def coordination_path(relative, name):
    path = relative + '/' + name if relative else name
    if path in RUNTIME_FILES:
        return True
    # Pinned utils.atomic_json_write uses .<stem>_<random>.tmp beside its
    # target. Only the reviewed coordination stems are treated this way.
    pattern = r'\.(?:spawn-ledger|gateway_state)_[a-z0-9_]{6,64}\.tmp' if not relative else (
        r'\.gateway_[a-z0-9_]{6,64}\.tmp' if relative == 'state' else None)
    return pattern is not None and re.fullmatch(pattern, name) is not None


def omission_reason(relative, name, info):
    if 'lswa' in name.lower() or 'legal-social-frameworks' in name.lower():
        return 'excluded_project_not_traversed'
    if not relative and name in OMITTED_TOP:
        return OMITTED_TOP[name]
    if name in {'__pycache__', '.pytest_cache'} and stat.S_ISDIR(info.st_mode):
        return 'generated_bytecode_cache'
    if coordination_path(relative, name) and stat.S_ISREG(info.st_mode):
        return 'live_process_coordination_not_restored'
    path = relative + '/' + name if relative else name
    if stat.S_ISSOCK(info.st_mode) and (path in {'bot-desktop/rfb.sock', 'gateway.sock'}
            or re.fullmatch(r'state/gateway\.loop-tick\.[0-9]+\.sock', path)):
        return 'runtime_socket_not_restored'
    return None


class CaptureError(RuntimeError):
    def __init__(self, reason='capture_guard_refused', checkpoint='guard'):
        super().__init__('main_operational_capture_refused')
        self.reason = reason if reason in REASONS else 'capture_guard_refused'
        self.checkpoint = checkpoint if checkpoint in CHECKPOINTS else 'guard'


def require(value, reason='capture_guard_refused'):
    if not value:
        raise CaptureError(reason)


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def capture(profile, *, online_databases=False):
    uid = os.geteuid()
    require(uid != 0 and isinstance(profile, Path) and profile.is_absolute() and '..' not in profile.parts
            and type(online_databases) is bool)
    root = os.open('/', os.O_PATH | os.O_DIRECTORY)
    directories, files, connections, directory_stamps, omissions = [], [], [], [], []
    deadline = time.monotonic() + 180
    checkpoint = 'source_walk'
    sidecars = set()
    database_names = {}
    snapshot_count = 0
    try:
        for name in profile.parts[1:]:
            require(not ('lswa' in name.lower() or 'legal-social-frameworks' in name.lower()))
            child = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            os.close(root)
            root = child
            require(os.fstat(root).st_uid in {0, uid})
        require(os.fstat(root).st_uid == uid)
        readable = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=root)
        directories.append(('', readable))
        def record_omission(path, reason):
            if not any(row['path'] == path for row in omissions):
                require(len(omissions) < MAX_ENTRIES)
                omissions.append(dict(path=path, reason=reason))

        def known_sidecar(directory, name):
            names = database_names.get(directory, set())
            return any(name.endswith(suffix) and name[:-len(suffix)] in names
                       for suffix in ('-wal','-shm','-journal'))

        def validate_sidecar(info):
            require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
                    and info.st_dev == os.fstat(root).st_dev and info.st_size <= MAX_BYTES
                    and not info.st_mode & 0o7000)

        def visible_names(directory, relative):
            visible = set()
            names = os.listdir(directory)
            require(len(names) <= MAX_ENTRIES and time.monotonic() < deadline)
            for name in names:
                require(len(name) <= 255 and all(32 <= ord(char) < 127 for char in name))
                path = relative + '/' + name if relative else name
                require(len(path) <= 255)
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    if online_databases and known_sidecar(directory, name):
                        sidecars.add(path)
                        continue
                    if coordination_path(relative, name):
                        record_omission(path, 'live_process_coordination_not_restored')
                        continue
                    raise
                reason = omission_reason(relative, name, info)
                if reason is not None:
                    record_omission(path, reason)
                elif online_databases and known_sidecar(directory, name):
                    validate_sidecar(info)
                    sidecars.add(path)
                else:
                    visible.add(name)
            return visible

        def walk(directory, relative, depth):
            require(depth <= 24 and time.monotonic() < deadline)
            names = sorted(os.listdir(directory))
            identity = stamp(os.fstat(directory))[:5]
            included = set()
            for name in names:
                require(len(files) + len(directories) + len(omissions) < MAX_ENTRIES
                        and time.monotonic() < deadline and name not in {'.', '..'}
                        and all(32 <= ord(char) < 127 for char in name))
                path = relative + '/' + name if relative else name
                require(len(path) <= 255 and path != 'profile-manifest.json')
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    if online_databases and known_sidecar(directory, name):
                        sidecars.add(path)
                        continue
                    if coordination_path(relative, name):
                        record_omission(path, 'live_process_coordination_not_restored')
                        continue
                    raise
                reason = omission_reason(relative, name, info)
                if reason is not None:
                    record_omission(path, reason)
                    continue
                if online_databases and known_sidecar(directory, name):
                    validate_sidecar(info)
                    sidecars.add(path)
                    continue
                included.add(name)
                require(info.st_uid == uid and info.st_dev == os.fstat(root).st_dev and not info.st_mode & 0o7000)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    require(stamp(os.fstat(child)) == stamp(info))
                    directories.append((path, child))
                    walk(child, path, depth + 1)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_BYTES)
                    opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                    try:
                        require(stamp(os.fstat(opened)) == stamp(info))
                        header = os.read(opened, 16)
                        wal_mode = header == b'SQLite format 3\0' and os.read(opened, 4)[2:4] == b'\x02\x02'
                    finally:
                        os.close(opened)
                    files.append(dict(path=path, name=name, directory=directory, info=info,
                                      database=header == b'SQLite format 3\0', wal_mode=wal_mode))
                    if header == b'SQLite format 3\0':
                        database_names.setdefault(directory, set()).add(name)
            require(stamp(os.fstat(directory))[:5] == identity, 'durable_directory_changed')
            directory_stamps.append((directory, identity, included, relative))
        walk(readable, '', 0)
        checkpoint = 'sqlite_snapshot'
        database_paths = {row['path'] for row in files if row['database']}
        for row in files:
            if row['path'].endswith(('-wal', '-shm', '-journal')):
                base = row['path'].rsplit('-', 1)[0]
                require(base in database_paths)
                sidecars.add(row['path'])
            if row['database']:
                uri = 'file:/proc/self/fd/' + str(row['directory']) + '/' + quote(row['name'], safe='') + '?mode=ro'
                connection = sqlite3.connect(uri, uri=True, timeout=1)
                connections.append(connection)
                connection.execute('PRAGMA query_only=ON')
                connection.execute('PRAGMA trusted_schema=OFF')
                row['connection'] = connection
                row['version'] = connection.execute('PRAGMA data_version').fetchone()[0]
        # Monitor all DBs before capturing any payload. Sidecars are rebuildable
        # SQLite bookkeeping, never independent archive members.
        for index, (fd, before, names, relative) in enumerate(directory_stamps):
            current = stamp(os.fstat(fd))[:5]
            now = visible_names(fd, relative)
            added = now - names
            if added:
                # A cold WAL database may create read-bookkeeping files on
                # open, even with mode=ro. Admit ONLY new regular owner files
                # for already identified WAL DBs. No removals or other new
                # members are allowed. Original payload checks stay unchanged.
                allowed = {row['name'] + suffix for row in files
                    if row['directory'] == fd and row['database'] and row['wal_mode']
                    for suffix in ('-wal', '-shm')}
                require(names <= now and added <= allowed and current == before, 'durable_directory_changed')
                for name in added:
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    require(stat.S_ISREG(info.st_mode) and info.st_uid == uid
                            and info.st_nlink == 1 and info.st_dev == os.fstat(root).st_dev
                            and info.st_size <= MAX_BYTES and not info.st_mode & 0o7000)
                    sidecars.add(relative + '/' + name if relative else name)
                directory_stamps[index] = (fd, current, now, relative)
            else:
                require(current == before and now == names, 'durable_directory_changed')
        blobs, manifest, used = {}, [], 0
        checkpoint = 'payload_read'
        for path, _ in directories:
            if path:
                manifest.append(dict(path=path, kind='directory', mode=0o700))
        for row in files:
            require(time.monotonic() < deadline)
            if row['path'] in sidecars:
                continue
            if row['database']:
                target = sqlite3.connect(':memory:')
                try:
                    source = row['connection']
                    if online_databases:
                        source.execute('BEGIN')
                        source.execute('SELECT count(*) FROM sqlite_schema').fetchone()
                        pinned_version = source.execute('PRAGMA data_version').fetchone()[0]
                    page_size = row['connection'].execute('PRAGMA page_size').fetchone()[0]
                    def progress(status, remaining, total):
                        require(time.monotonic() < deadline and 0 <= total * page_size <= MAX_BYTES - used)
                    try:
                        source.backup(target, pages=64, progress=progress, sleep=0.01)
                        if online_databases:
                            require(source.execute('PRAGMA data_version').fetchone()[0] == pinned_version,
                                    'database_committed_during_capture')
                        snapshot_count += 1
                    finally:
                        if online_databases:
                            source.rollback()  # End the read transaction immediately after copying.
                    raw = target.serialize()
                    require(raw[:16] == b'SQLite format 3\0' and raw[18] in (1, 2) and raw[19] in (1, 2))
                    # SQLite's documented completed-backup deserialize workaround.
                    raw = raw[:18] + b'\x01\x01' + raw[20:]
                    check = sqlite3.connect(':memory:')
                    try:
                        check.deserialize(raw)
                        check.execute('PRAGMA trusted_schema=OFF')
                        check.execute('PRAGMA query_only=ON')
                        check.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                        require(check.execute('PRAGMA quick_check').fetchall() == [('ok',)])
                    finally:
                        check.close()
                finally:
                    target.close()
            else:
                fd = os.open(row['name'], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=row['directory'])
                with os.fdopen(fd, 'rb') as stream:
                    require(stamp(os.fstat(stream.fileno())) == stamp(row['info']), 'durable_file_changed_before_read')
                    raw = stream.read(MAX_BYTES - used + 1)
                    require(stamp(os.fstat(stream.fileno())) == stamp(row['info']), 'durable_file_changed_during_read')
            used += len(raw)
            require(used <= MAX_BYTES)
            blobs[row['path']] = raw
            manifest.append(dict(path=row['path'], kind='sqlite' if row['database'] else 'file',
                mode=0o700 if row['info'].st_mode & stat.S_IXUSR else 0o600,
                size=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        checkpoint = 'stability_verification'
        changed_databases = 0
        for row in files:
            if row['database']:
                changed = row['connection'].execute('PRAGMA data_version').fetchone()[0] != row['version']
                changed_databases += int(changed)
                require(online_databases or not changed, 'database_committed_during_capture')
                after = os.stat(row['name'], dir_fd=row['directory'], follow_symlinks=False)
                require((after.st_dev, after.st_ino, after.st_uid, after.st_nlink)
                        == (row['info'].st_dev, row['info'].st_ino, uid, 1))
            elif row['path'] not in sidecars:
                require(stamp(os.stat(row['name'], dir_fd=row['directory'], follow_symlinks=False)) == stamp(row['info']), 'durable_file_changed_after_read')
        for fd, before, names, relative in directory_stamps:
            require(stamp(os.fstat(fd))[:5] == before and visible_names(fd, relative) == names, 'durable_directory_changed')
        checkpoint = 'archive_encoding'
        internal = dict(schema=2, format='hermes-main-operational-profile-sqlite-v2', entries=manifest,
                        sqlite_databases=len(database_paths), sqlite_sidecars_rebuilt=len(sidecars),
                        omitted=omissions, full_profile_recovery_qualified=False,
                        executable_rebuild_qualified=False,
                        database_snapshot_mode='read_transaction_per_database' if online_databases else 'stable_source',
                        snapshot_database_count=snapshot_count, global_atomic_snapshot_qualified=False)
        payload = io.BytesIO()
        encoded_manifest = json.dumps(internal, sort_keys=True).encode()
        require(len(encoded_manifest) <= MAX_MANIFEST)
        with tarfile.open(fileobj=payload, mode='w', format=tarfile.GNU_FORMAT) as archive:
            rows = [dict(path='profile-manifest.json', kind='file', mode=0o600,
                         raw=encoded_manifest)] + manifest
            for entry in rows:
                item = tarfile.TarInfo(entry['path'])
                item.mode = entry['mode']
                item.uid = item.gid = 0
                if entry['kind'] == 'directory':
                    item.type = tarfile.DIRTYPE
                    archive.addfile(item)
                else:
                    raw = entry['raw'] if 'raw' in entry else blobs[entry['path']]
                    item.size = len(raw)
                    archive.addfile(item, io.BytesIO(raw))
        result = payload.getvalue()
        require(len(result) <= MAX_ARCHIVE)
        return result, dict(files=len(blobs), source_bytes=used, sqlite_databases=len(database_paths),
            sidecars_rebuilt=len(sidecars), database_versions_stable=changed_databases == 0, plain_files_stable=True,
            plaintext_archive_written=False, omitted_entries=len(omissions),
            source_profiles_preserved=True, source_logical_writes_performed=False, sqlite_read_bookkeeping_may_change=True,
            full_profile_recovery_qualified=False, executable_rebuild_qualified=False,
            database_snapshots_consistent=snapshot_count == len(database_paths),
            database_snapshot_mode=internal['database_snapshot_mode'], live_database_changes_observed=changed_databases,
            global_atomic_snapshot_qualified=False)
    except CaptureError as error:
        error.checkpoint = checkpoint
        raise
    except (OSError, sqlite3.Error, ValueError, tarfile.TarError):
        raise CaptureError('source_io_or_sqlite_error', checkpoint) from None
    finally:
        for connection in connections:
            connection.close()
        for _, fd in reversed(directories):
            os.close(fd)
        os.close(root)


def restore(payload, *, owner_home=False):
    """Validate completely, then write only into a NEW owner-private tree."""
    require(os.geteuid() != 0 and type(owner_home) is bool and isinstance(payload, bytes) and len(payload) <= MAX_ARCHIVE)
    members = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:') as archive:
        total = 0
        for index, member in enumerate(archive):
            require(index <= MAX_ENTRIES and member.name not in members and (member.isfile() or member.isdir())
                    and not member.pax_headers and member.sparse is None and not member.name.startswith('/')
                    and len(member.name) <= 255
                    and all(part not in {'', '.', '..'} for part in member.name.split('/'))
                    and all(32 <= ord(char) < 127 for char in member.name)
                    and member.mode in {0o600, 0o700})
            raw = archive.extractfile(member).read(MAX_BYTES + 1) if member.isfile() else None
            if raw is not None:
                total += len(raw)
                require(len(raw) == member.size and total <= MAX_BYTES + MAX_MANIFEST)
            members[member.name] = (member, raw)
    require('profile-manifest.json' in members)
    require(len(members['profile-manifest.json'][1]) <= MAX_MANIFEST)
    manifest = json.loads(members.pop('profile-manifest.json')[1])
    require(isinstance(manifest, dict) and set(manifest) == {'schema', 'format', 'entries', 'sqlite_databases', 'sqlite_sidecars_rebuilt', 'omitted',
            'full_profile_recovery_qualified', 'executable_rebuild_qualified', 'database_snapshot_mode',
            'snapshot_database_count', 'global_atomic_snapshot_qualified'}
            and type(manifest['schema']) is int and manifest['schema'] == 2 and manifest['format'] == 'hermes-main-operational-profile-sqlite-v2'
            and isinstance(manifest['entries'], list) and len(manifest['entries']) <= MAX_ENTRIES)
    require(manifest['full_profile_recovery_qualified'] is False
            and manifest['executable_rebuild_qualified'] is False
            and manifest['global_atomic_snapshot_qualified'] is False
            and manifest['database_snapshot_mode'] in {'stable_source','read_transaction_per_database'}
            and isinstance(manifest['omitted'], list) and len(manifest['omitted']) <= MAX_ENTRIES)
    for omission in manifest['omitted']:
        require(isinstance(omission, dict) and set(omission) == {'path', 'reason'}
                and isinstance(omission['path'], str) and len(omission['path']) <= 255
                and not omission['path'].startswith('/')
                and all(part not in {'', '.', '..'} for part in omission['path'].split('/'))
                and all(32 <= ord(c) < 127 for c in omission['path'])
                and omission['reason'] in set(OMITTED_TOP.values()) | {'generated_bytecode_cache',
                    'runtime_socket_not_restored', 'excluded_project_not_traversed', 'live_process_coordination_not_restored'})
    names = set()
    for entry in manifest['entries']:
        require(isinstance(entry, dict) and entry.get('path') in members and entry['path'] not in names
                and entry.get('kind') in {'file', 'sqlite', 'directory'})
        names.add(entry['path'])
        member, raw = members[entry['path']]
        require(member.mode == entry.get('mode') and (entry['kind'] == 'directory') == member.isdir())
        if raw is not None:
            require(set(entry) == {'path', 'kind', 'mode', 'size', 'sha256'}
                    and entry['size'] == len(raw) and hashlib.sha256(raw).hexdigest() == entry['sha256'])
        else:
            require(set(entry) == {'path', 'kind', 'mode'})
        parent = str(Path(entry['path']).parent)
        require(parent == '.' or parent in {row.get('path') for row in manifest['entries'] if row.get('kind') == 'directory'})
    require(names == set(members))
    require(type(manifest['sqlite_databases']) is int
            and manifest['sqlite_databases'] == sum(row['kind'] == 'sqlite' for row in manifest['entries'])
            and type(manifest['snapshot_database_count']) is int
            and manifest['snapshot_database_count'] == manifest['sqlite_databases']
            and type(manifest['sqlite_sidecars_rebuilt']) is int and manifest['sqlite_sidecars_rebuilt'] >= 0)
    parent = '/tmp'
    if owner_home:
        # The caller cannot select another account/path. A candidate restore
        # is created exclusively under this process owner's protected HOME.
        parent = pwd.getpwuid(os.geteuid()).pw_dir
        fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
        try:
            for name in Path(parent).parts[1:]:
                child = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                info = os.fstat(fd)
                require(info.st_uid in {0, os.geteuid()} and not info.st_mode & 0o022)
            require(os.fstat(fd).st_uid == os.geteuid() and stat.S_IMODE(os.fstat(fd).st_mode) == 0o700)
        finally:
            os.close(fd)
    destination = Path(tempfile.mkdtemp(prefix='ec-main-operational-restore-', dir=parent))
    os.chmod(destination, 0o700)
    # All members were validated first. No links are admitted, no source code
    # or profile startup action is executed from this restored data.
    for entry in sorted(manifest['entries'], key=lambda row: (row['kind'] != 'directory', row['path'].count('/'))):
        path = destination / entry['path']
        if entry['kind'] == 'directory':
            path.mkdir(mode=0o700)
        else:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, entry['mode'])
            with os.fdopen(fd, 'wb') as stream:
                stream.write(members[entry['path']][1])
                stream.flush()
                os.fsync(stream.fileno())
            require(path.stat().st_uid == os.geteuid() and stat.S_IMODE(path.stat().st_mode) == entry['mode'])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'])
            if entry['kind'] == 'sqlite':
                database = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
                try:
                    database.execute('PRAGMA query_only=ON')
                    database.execute('PRAGMA trusted_schema=OFF')
                    require(database.execute('PRAGMA quick_check').fetchall() == [('ok',)])
                finally:
                    database.close()
    return str(destination), dict(complete=True, archived_files_verified=True, private_restore_verified=True,
        sqlite_databases_verified=sum(row['kind'] == 'sqlite' for row in manifest['entries']),
        restored_profile_executed=False, operational_restore_qualified=True,
        full_profile_recovery_qualified=False, executable_rebuild_qualified=False,
        database_snapshot_mode=manifest['database_snapshot_mode'], global_atomic_snapshot_qualified=False)
