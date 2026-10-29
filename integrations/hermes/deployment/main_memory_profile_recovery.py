"""Reuse main SQLite recovery with one exact rebuildable provider binding.

The root-owned provider is represented as a reviewed omission and reconstructed
at its fixed target. Its target is never archived or followed. Original V3
backup code and generations remain unchanged. No profile code is executed.
"""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import stat
import tarfile

LINK = 'plugins/enhanced_cognee'
TARGET = '/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659'
REASON = 'program_reference_rebind_pending'


def require(value):
    if not value:
        raise ValueError('main_provider_recovery_refused')


def binding(profile):
    path = profile / LINK
    info = path.lstat()
    require(stat.S_ISLNK(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
            and os.readlink(path) == TARGET)
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)


def capture(core, profile):
    require(os.geteuid() != 0)
    before = binding(profile)
    # Each operation gets its own freshly loaded, pinned V3 namespace.
    namespace = core['capture'].__globals__
    original = namespace['omission_reason']
    def omission(relative, name, info):
        if relative + '/' + name == LINK:
            binding(profile)
            return REASON
        return original(relative, name, info)
    namespace['omission_reason'] = omission
    try:
        archive, receipt = core['capture'](profile, online_databases=True)
        require(binding(profile) == before)
        return archive, receipt
    finally:
        namespace['omission_reason'] = original


def restore(core, archive):
    require(os.geteuid() != 0 and isinstance(archive, bytes) and len(archive) <= core['MAX_ARCHIVE'])
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as source:
        manifests = []
        for index, entry in enumerate(source):
            require(index <= core['MAX_ENTRIES'])
            if entry.name == 'profile-manifest.json':
                manifests.append(entry)
        require(len(manifests) == 1 and manifests[0].isfile() and manifests[0].size <= core['MAX_MANIFEST'])
        manifest = json.loads(source.extractfile(manifests[0]).read(core['MAX_MANIFEST'] + 1))
    require(isinstance(manifest, dict) and isinstance(manifest.get('omitted'), list)
            and sum(item == dict(path=LINK, reason=REASON) for item in manifest['omitted']) == 1
            and isinstance(manifest.get('entries'), list)
            and all(row.get('path') != LINK for row in manifest['entries']))
    # V3 validates all archive members before creating its new destination.
    destination, receipt = core['restore'](archive, owner_home=True)
    profile = Path(destination)
    plugins = profile / 'plugins'
    info = plugins.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077)
    require(json.loads((profile / 'enhanced_cognee.json').read_bytes()) == dict(
        base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True))
    (profile / LINK).symlink_to(TARGET)
    binding(profile)
    receipt = dict(receipt, pinned_provider_binding_reconstructed=True)
    return destination, receipt
