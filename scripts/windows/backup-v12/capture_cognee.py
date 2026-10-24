"""Collect completed encrypted database AND restricted-profile backup families.

No keys or plaintext are opened. Hash/manifest shape checks are not signature
verification or decryption. A failed producer must not admit a restic snapshot.
"""
import argparse
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import time

MAGIC = b'age-encryption.org/v1\n'
FAMILIES = {
    'database': (r'memory_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}\.dump\.age', 'postgres-custom+age'),
    'hermes_profile': (r'hermes_profile_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}\.tar\.age', 'hermes-home-tar+age'),
}
COMMON = {'format', 'complete', 'ciphertext_sha256', 'created_utc', 'signing_key_id', 'signature'}
FIELDS = {
    'database': COMMON | {'plaintext_dump_written'},
    'hermes_profile': COMMON | {'plaintext_archive_written', 'scope', 'source_files', 'source_bytes'},
}


class CollectionError(RuntimeError):
    """Fixed public categories only; do not print private exception values."""

    def __init__(self, category, diagnostics=None):
        super().__init__(category)
        self.diagnostics = diagnostics


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def open_root(root):
    if not root.is_absolute() or '..' in root.parts:
        raise CollectionError('backup_root_path_refused')
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            opened = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = opened
            info = os.fstat(fd)
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise CollectionError('backup_root_protection')
        opened = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        info = os.fstat(opened)
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
            os.close(opened)
            raise CollectionError('backup_root_protection')
        return opened
    finally: os.close(fd)


def open_file(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1):
            raise CollectionError('backup_file_protection')
        return fd, info
    except BaseException:
        os.close(fd)
        raise


def manifest_shape(value, family, digest):
    if (not isinstance(value, dict) or set(value) != FIELDS[family]
            or value.get('complete') is not True or value.get('format') != FAMILIES[family][1]
            or value.get('ciphertext_sha256') != digest
            or not isinstance(value.get('signature'), str) or not re.fullmatch('[a-f0-9]{64}', value['signature'])
            or not isinstance(value.get('signing_key_id'), str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}', value['signing_key_id'])
            or not isinstance(value.get('created_utc'), str) or len(value['created_utc']) > 64):
        raise CollectionError('completed_manifest_shape_or_hash_refused')
    created = datetime.fromisoformat(value['created_utc'])
    if created.tzinfo is None: raise CollectionError('manifest_timestamp_required')
    if family == 'database':
        if value['plaintext_dump_written'] is not False: raise CollectionError('plaintext_manifest_refused')
    elif (value['plaintext_archive_written'] is not False or value['scope'] != 'restricted-hermes-home'
            or type(value['source_files']) is not int or not 1 <= value['source_files'] <= 2048
            or type(value['source_bytes']) is not int or not 0 <= value['source_bytes'] <= 16777216):
        raise CollectionError('profile_manifest_refused')


def inspect_pair(directory, name, family):
    fd, info = open_file(directory, name)
    try:
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            if stream.read(len(MAGIC)) != MAGIC: raise CollectionError('age_envelope_required')
            stream.seek(0); digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if stamp(info) != stamp(os.fstat(fd)): raise CollectionError('ciphertext_changed')
    finally: os.close(fd)
    fd, manifest_info = open_file(directory, name + '.json')
    try:
        if manifest_info.st_size > 4096: raise CollectionError('manifest_budget')
        raw = os.read(fd, 4097)
        if len(raw) != manifest_info.st_size or stamp(manifest_info) != stamp(os.fstat(fd)):
            raise CollectionError('manifest_changed')
    finally: os.close(fd)
    value = json.loads(raw)
    manifest_shape(value, family, digest)
    return dict(name=name, family=family, info=info, manifest_info=manifest_info, manifest=raw, digest=digest)


class HashReader:
    def __init__(self, stream):
        self.stream, self.digest = stream, hashlib.sha256()

    def read(self, size):
        value = self.stream.read(size)
        self.digest.update(value)
        return value


def add_file(tar, directory, name, expected, *, manifest=None, digest=None):
    fd, info = open_file(directory, name)
    try:
        if stamp(info) != stamp(expected): raise CollectionError('backup_changed_before_stream')
        member = tarfile.TarInfo(name)
        member.size, member.mode, member.mtime = info.st_size, 0o600, int(info.st_mtime)
        if manifest is not None:
            if os.read(fd, 4097) != manifest: raise CollectionError('manifest_changed')
            tar.addfile(member, io.BytesIO(manifest))
        else:
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                reader = HashReader(stream)
                tar.addfile(member, reader)
                if reader.digest.hexdigest() != digest: raise CollectionError('ciphertext_changed_during_stream')
        if stamp(info) != stamp(os.fstat(fd)): raise CollectionError('backup_changed_during_stream')
    finally: os.close(fd)


def capture(root, maximum_age, *, verify_only=False):
    if type(verify_only) is not bool or type(maximum_age) is not int or not 1 <= maximum_age <= 168:
        raise CollectionError('maximum_age_refused')
    directory = open_root(root)
    try:
        names = sorted(os.listdir(directory))
        if len(names) > 20000: raise CollectionError('backup_directory_entry_budget')
        present = set(names)
        pairs, counts, newest = [], dict.fromkeys(FAMILIES, 0), dict.fromkeys(FAMILIES, 0)
        now = time.time()
        for name in names:
            family = next((key for key, (pattern, _) in FAMILIES.items() if re.fullmatch(pattern, name)), None)
            if family is None or name + '.json' not in present: continue  # Incomplete generations are not admitted.
            pair = inspect_pair(directory, name, family)
            if pair['info'].st_mtime > now + 300: raise CollectionError('future_backup_timestamp')
            pairs.append(pair); counts[family] += 1
            newest[family] = max(newest[family], pair['info'].st_mtime)
        if any(not counts[key] or now - newest[key] > maximum_age * 3600 for key in FAMILIES):
            raise CollectionError('recent_database_and_profile_backups_required', dict(
                database_pairs=counts['database'], profile_pairs=counts['hermes_profile'],
                database_recent=bool(counts['database'] and now - newest['database'] <= maximum_age * 3600),
                profile_recent=bool(counts['hermes_profile'] and now - newest['hermes_profile'] <= maximum_age * 3600)))
        metadata = dict(coverage_schema=2, completed_pairs=len(pairs),
            database_completed_pairs=counts['database'], profile_completed_pairs=counts['hermes_profile'],
            required_families=list(FAMILIES), ciphertext_hashes_verified=True,
            signed_authenticity_and_decryption_verified=False, requires_separate_recovery_keys=True)
        if verify_only:
            print(json.dumps(dict(metadata, complete=True, stage='encrypted_service_collection_inventory',
                files_written=False, backup_started=False, cloud_upload=False, credentials_read=False), sort_keys=True))
            return
        with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as tar:
            for pair in pairs:
                add_file(tar, directory, pair['name'], pair['info'], digest=pair['digest'])
                add_file(tar, directory, pair['name'] + '.json', pair['manifest_info'], manifest=pair['manifest'])
            raw = json.dumps(metadata, sort_keys=True).encode()
            member = tarfile.TarInfo('collection-coverage.json')
            member.size, member.mode = len(raw), 0o600
            tar.addfile(member, io.BytesIO(raw))
        sys.stdout.buffer.flush()
        print(json.dumps({'cognee_completed_pairs': len(pairs), 'database_pairs': counts['database'],
            'profile_pairs': counts['hermes_profile']}), file=sys.stderr)
    finally: os.close(directory)


def verify_inventory(root, maximum_age=48):
    """Return safe diagnostics, never private parser errors/filenames/values."""
    try: capture(root, maximum_age, verify_only=True)
    except Exception as error:
        allowed = {'backup_root_path_refused', 'backup_root_protection', 'backup_file_protection',
            'completed_manifest_shape_or_hash_refused', 'manifest_timestamp_required', 'plaintext_manifest_refused',
            'profile_manifest_refused', 'age_envelope_required', 'ciphertext_changed', 'manifest_budget',
            'manifest_changed', 'maximum_age_refused', 'backup_directory_entry_budget',
            'future_backup_timestamp', 'recent_database_and_profile_backups_required'}
        reason = str(error) if isinstance(error, CollectionError) and str(error) in allowed else 'collection_read_or_parse_failed'
        details = {}
        if isinstance(error, CollectionError) and isinstance(error.diagnostics, dict):
            for key in ('database_pairs', 'profile_pairs'):
                value = error.diagnostics.get(key)
                if type(value) is int and 0 <= value <= 20000: details[key] = value
            for key in ('database_recent', 'profile_recent'):
                value = error.diagnostics.get(key)
                if type(value) is bool: details[key] = value
        number = getattr(error, 'errno', None)
        if type(number) is int and 0 < number < 4096: details['errno'] = number
        print(json.dumps(dict(complete=False, stage='encrypted_service_collection_inventory', category=reason,
            diagnostics=details, files_written=False, backup_started=False, cloud_upload=False, credentials_read=False), sort_keys=True))
        raise SystemExit(1) from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-age-hours', type=int, default=48)
    parser.add_argument('--root', type=Path, default=Path('/var/backups/enhanced-cognee'))
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        verify_inventory(args.root, args.max_age_hours)
        raise SystemExit(0)
    try: capture(args.root, args.max_age_hours)
    except Exception:
        raise SystemExit('ERR: encrypted database/profile collection incomplete; no completed snapshot admitted.') from None
