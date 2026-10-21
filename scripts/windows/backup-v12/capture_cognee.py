"""Stream only completed, encrypted Cognee backups, never service/recovery keys."""
import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import time
from pathlib import Path


def capture(root, maximum_age):
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or root.resolve() != root:
        raise RuntimeError('Service backup directory must be a protected root-owned directory')
    pairs = []
    for archive in sorted(root.glob('memory_*.dump.age')):
        if not re.fullmatch(r'memory_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}\.dump\.age', archive.name):
            continue
        manifest = Path(str(archive) + '.json')
        if not manifest.exists():
            continue
        for path in (archive, manifest):
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                raise RuntimeError('Service backup file permissions failed')
        if manifest.stat().st_size > 4096:
            raise RuntimeError('Unexpected service manifest size')
        value = json.loads(manifest.read_text())
        digest = hashlib.sha256()
        with archive.open('rb') as handle:
            if handle.read(22) != b'age-encryption.org/v1\n':
                raise RuntimeError('Service archive is not an age envelope')
            handle.seek(0)
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        if (value.get('complete') is not True or value.get('format') != 'postgres-custom+age'
            or value.get('ciphertext_sha256') != digest.hexdigest()
            or not re.fullmatch('[a-f0-9]{64}', str(value.get('signature', '')))):
            raise RuntimeError('Service manifest or ciphertext hash failed')
        pairs.append((archive, manifest, digest.hexdigest()))
    if not pairs or time.time() - max(a.stat().st_mtime for a, _, _ in pairs) > maximum_age * 3600:
        raise RuntimeError('No recent completed service backup; nothing admitted')
    with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as tar:
        for archive, manifest, expected in pairs:
            # Verify again while reading; a changed file aborts this producer.
            for path in (archive, manifest):
                tar.add(path, arcname=path.name, recursive=False)
            with archive.open('rb') as handle:
                if hashlib.file_digest(handle, 'sha256').hexdigest() != expected:
                    raise RuntimeError('Service archive changed during capture')
        metadata = json.dumps({'completed_pairs': len(pairs), 'ciphertext_hashes_verified': True,
                               'signed_authenticity_and_decryption_verified': False,
                               'requires_separate_recovery_keys': True}, sort_keys=True).encode()
        info = tarfile.TarInfo('collection-coverage.json')
        info.size, info.mode = len(metadata), 0o600
        tar.addfile(info, io.BytesIO(metadata))
    sys.stdout.buffer.flush()
    print(json.dumps({'cognee_completed_pairs': len(pairs)}), file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-age-hours', type=int, default=48)
    parser.add_argument('--root', type=Path, default=Path('/var/backups/enhanced-cognee'))
    args = parser.parse_args()
    capture(args.root, args.max_age_hours)
