"""Owner-only bounded migration metadata. Never copy/export profile contents.

Headers identify SQLite without opening a SQLite connection. Unknown links,
mounts, unsafe ownership and changing state prevent copy admission. Nested
profiles are inventoried separately; excluded projects are never traversed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import tempfile
import time

PROVIDER = '/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659'
LIMIT = 100000


class InventoryBudget(ValueError):
    def __init__(self, counts):
        super().__init__('migration_inventory_budget')
        self.counts = dict(counts)


def excluded(name):
    return 'lswa' in name.lower() or 'legal-social-frameworks' in name.lower()


def metadata_tree(root, uid, *, skip_profiles=False, deadline=None):
    deadline = deadline if deadline is not None else time.monotonic() + 45
    device = os.fstat(root).st_dev
    counts = dict.fromkeys(('entries', 'files', 'directories', 'logical_bytes', 'largest_file_bytes',
        'sqlite_databases', 'wal_files', 'shm_files', 'known_provider_links', 'unknown_links',
        'special_files', 'hardlinked_files', 'foreign_owned_entries', 'nested_mounts',
        'changed_entries', 'unreadable_entries', 'excluded_entries', 'separately_inventoried_profiles'), 0)
    def walk(directory, depth):
        if depth > 48 or time.monotonic() >= deadline:
            raise InventoryBudget(counts)
        before = os.fstat(directory)
        with os.scandir(directory) as listing:
            for item in listing:
                if counts['entries'] >= LIMIT or time.monotonic() >= deadline:
                    raise InventoryBudget(counts)
                name = item.name
                counts['entries'] += 1
                if excluded(name):
                    counts['excluded_entries'] += 1
                    continue
                if skip_profiles and depth == 0 and name == 'profiles':
                    counts['separately_inventoried_profiles'] += 1
                    continue
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if info.st_dev != device:
                        counts['nested_mounts'] += 1
                        continue
                    if info.st_uid != uid:
                        counts['foreign_owned_entries'] += 1
                        continue
                    if stat.S_ISLNK(info.st_mode):
                        target = os.readlink(name, dir_fd=directory)
                        known = name == 'enhanced_cognee' and target == PROVIDER
                        counts['known_provider_links' if known else 'unknown_links'] += 1
                    elif stat.S_ISDIR(info.st_mode):
                        counts['directories'] += 1
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        try:
                            opened = os.fstat(child)
                            if (info.st_dev, info.st_ino, info.st_uid) != (opened.st_dev, opened.st_ino, opened.st_uid):
                                counts['changed_entries'] += 1
                                continue
                            walk(child, depth + 1)
                        finally:
                            os.close(child)
                    elif stat.S_ISREG(info.st_mode):
                        counts['files'] += 1
                        counts['logical_bytes'] += info.st_size
                        counts['largest_file_bytes'] = max(counts['largest_file_bytes'], info.st_size)
                        if info.st_nlink != 1:
                            counts['hardlinked_files'] += 1
                            continue
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                        try:
                            opened = os.fstat(fd)
                            if not stat.S_ISREG(opened.st_mode) or (info.st_dev, info.st_ino, info.st_uid) != (opened.st_dev, opened.st_ino, opened.st_uid):
                                counts['changed_entries'] += 1
                                continue
                            header = os.read(fd, 16)
                            counts['sqlite_databases'] += header == b'SQLite format 3\0'
                            counts['wal_files'] += name.endswith('-wal')
                            counts['shm_files'] += name.endswith('-shm')
                            after = os.fstat(fd)
                            if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                                counts['changed_entries'] += 1
                        finally:
                            os.close(fd)
                    else:
                        counts['special_files'] += 1
                except OSError:
                    counts['unreadable_entries'] += 1
        after = os.fstat(directory)
        if (before.st_mtime_ns, before.st_ctime_ns) != (after.st_mtime_ns, after.st_ctime_ns):
            counts['changed_entries'] += 1
    walk(root, 0)
    counts['copy_admission_qualified'] = False
    return counts


def main():
    uid = os.geteuid()
    if uid == 0:
        raise ValueError('owner_only_migration_inventory')
    account = pwd.getpwuid(uid)
    home = Path(account.pw_dir) / '.hermes'
    # Pin all ancestors without following links or requiring directory listing.
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for name in home.parts[1:]:
            child = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if os.fstat(fd).st_uid not in {0, uid}:
                raise ValueError('migration_home_ownership')
        if os.fstat(fd).st_uid != uid:
            raise ValueError('migration_home_owner_required')
        root = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
    finally:
        os.close(fd)
    rows, unresolved = [], 0
    deadline = time.monotonic() + 50
    try:
        selected = [('main', str(home), os.dup(root))]
        try:
            profiles = os.open('profiles', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        except FileNotFoundError:
            profiles = None
        if profiles is not None:
            try:
                for name in sorted(os.listdir(profiles)):
                    if excluded(name):
                        unresolved += 1
                        continue
                    info = os.stat(name, dir_fd=profiles, follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode) and info.st_uid == uid:
                        if len(selected) >= 256:
                            raise ValueError('migration_profile_budget')
                        opened = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=profiles)
                        if os.fstat(opened).st_ino != info.st_ino:
                            os.close(opened)
                            raise ValueError('migration_profile_changed')
                        selected.append((name, str(home / 'profiles' / name), opened))
                    elif stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                        unresolved += 1
            finally:
                os.close(profiles)
        try:
            for name, path, opened in sorted(selected, key=lambda entry: entry[0] == 'main'):
                ident = hashlib.sha256((account.pw_name + '\0' + path).encode()).hexdigest()[:16]
                try:
                    metrics = metadata_tree(opened, uid, skip_profiles=name == 'main', deadline=deadline)
                    rows.append(dict(profile_id=ident, metrics=metrics, observation_complete=True))
                except InventoryBudget as error:
                    rows.append(dict(profile_id=ident, metrics=error.counts,
                        observation_complete=False, category='migration_inventory_budget'))
                    if time.monotonic() >= deadline:
                        break
        finally:
            for _, _, opened in selected:
                os.close(opened)
    finally:
        os.close(root)
    evidence = Path(tempfile.mkdtemp(prefix='ec-profile-migration-', dir='/tmp'))
    os.chmod(evidence, 0o700)
    with (evidence / 'inventory.private.json').open('x') as stream:
        os.chmod(stream.name, 0o600)
        json.dump(rows, stream)
    complete = len(rows) == len(selected) and all(row['observation_complete'] for row in rows)
    totals = {key: sum(row.get('metrics', {}).get(key, 0) for row in rows) for key in
        ('files', 'logical_bytes', 'sqlite_databases', 'wal_files', 'shm_files', 'unknown_links', 'special_files',
         'hardlinked_files', 'foreign_owned_entries', 'nested_mounts', 'changed_entries', 'unreadable_entries', 'excluded_entries')}
    result = dict(complete=complete, evidence=str(evidence), observed_profiles=len(rows), unresolved_profile_entries=unresolved,
        totals=totals, profile_copy_qualified=False, profile_backup_qualified=False, contents_exported=False,
        sqlite_connections_opened=False, profiles_changed=False, fleet_launch_approved=False)
    with (evidence / 'summary.json').open('x') as stream:
        os.chmod(stream.name, 0o600)
        json.dump(result, stream)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"complete":false,"category":"migration_inventory_refused_no_secret_output"}')
        raise SystemExit(1)
