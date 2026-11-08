#!/usr/bin/python3
"""Fixed-target stage-only source overlay. Stdlib only; never launch application code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
DEST = Path('/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101')
BUNDLE = Path('/opt/enhanced-cognee-memory/staging/audit-c14f595c-20261101')
SITE = Path('lib/python3.12/site-packages')
EXTERNAL_PYTHON = Path('/opt/enhanced-cognee-memory/python/bin/python3.12')
PYVENV = (
    b'home = /opt/enhanced-cognee-memory/python/bin\n'
    b'include-system-site-packages = false\nversion = 3.12.13\n'
    b'executable = /opt/enhanced-cognee-memory/python/bin/python3.12\n'
    b'command = /opt/enhanced-cognee-memory/python/bin/python3.12 -m venv --copies '
    b'/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime\n')
_lstat = os.lstat

COMMIT = 'c14f595ccd53f432b455b16f116765d9aa6c9a14'
# Reviewed byte bindings, not caller-supplied policy.
BINDINGS = {
    'src/ingestion.py': ('205d1c72ad937db1fa2990f3bcdba29599eceec9c17dae9e467c84b55749a821', 'b814d10674a13ac6e7ed8f1be7de5eec5ae215109dafd85bf524d6f6ba94c32b'),
    'src/llm_summarize.py': ('6a20835307a697ff401138f8fc67a6c3c8bfbb109203070da3f02812df5c78cf', 'e78c3c7fae47afe6c6228d6cab7b45387fb375f8c07ca37261a606e79a4010ae'),
    'src/llm_budget.py': (None, '81a4ddc2ef5aee073b814a428a112cabe3536f4e83cbd7a0e15c83522b8d10a7'),
    'src/memory_api.py': ('e21ba22d0bf02fee1c4ce2b1b0720dfa2fc2130118ac6e54ee0225285edd07d0', '4f125fb6d01719440a0b6c614a7767bbe386c73756b19e232e1fd481a7b64dda'),
    'src/memory_daemon.py': ('64abec3c2883b0efcf718c17e52083156b5db41f1da0bd37b7d2035960b85909', 'c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20'),
    'src/memory_library.py': ('7cb28171050a55d2046e7977c8ab603cc9bfbe3bc748d3efab87d263817cebcd', '9ca8bec14760ca2793b175bf69d088ed1a78eb9a5a06a94a744929ec3aa4ef2f'),
    'src/memory_queries.py': ('0d75ea1dcdc331c28bedfb4c090310035d354820a36a55960cfb7299d77be561', 'be051d645535239d57677a8a9d05bf47929d9c80f5e49d3e3884ea47e9c275a3'),
    'src/security/enterprise_auth.py': ('e9c117d5ab50bb557804ab6b3bb756ce73b918782f1a7e831b90baeabd490993', '78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e'),
}


class Rejected(ValueError):
    """Fail closed, preserving any partial candidate."""


def load_manifest(data):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise Rejected('duplicate JSON key')
            obj[key] = value
        return obj

    def invalid_constant(value):
        raise Rejected('non-finite JSON number')

    try:
        obj = json.loads(data, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise Rejected('invalid manifest JSON') from exc
    expected = {'schema': 1, 'source_commit': COMMIT, 'files': [
        {'path': path, 'old_sha256': old, 'new_sha256': new}
        for path, (old, new) in BINDINGS.items()
    ]}
    if not isinstance(obj, dict) or type(obj.get('schema')) is not int or obj != expected:
        raise Rejected('manifest differs from exact reviewed eight-file payload')
    return obj


def protected(path, kind):
    """Check LEXICAL ancestors before any resolving/opening; no alias directories."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Rejected('non-absolute or traversing protected path')
    for node in [*reversed(path.parents), path]:
        s = _lstat(node)
        if s.st_uid != 0 or s.st_gid != 0 or s.st_mode & 0o022:
            raise Rejected('unprotected owner or mode: ' + str(node))
        want_dir = node != path or kind == 'dir'
        if want_dir and not stat.S_ISDIR(s.st_mode):
            raise Rejected('non-directory lexical ancestor: ' + str(node))
        if not want_dir and (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1):
            raise Rejected('not a single-link regular file: ' + str(node))
    return s


def read_protected(path):
    before = protected(path, 'file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise Rejected('file replaced during open')
        return stream.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_runtime():
    """Read only the fixed runtime and its fixed public interpreter metadata."""
    runtime = BASE / 'runtime'
    protected(runtime, 'dir')
    protected(EXTERNAL_PYTHON, 'file')
    if read_protected(runtime / 'pyvenv.cfg') != PYVENV:
        raise Rejected('unexpected pyvenv configuration')
    protected(runtime / 'bin/python', 'file')
    inventory = {}

    def visit(path):
        rel = str(path.relative_to(runtime))
        s = _lstat(path)
        if stat.S_ISLNK(s.st_mode):
            if (rel != 'lib64' or os.readlink(path) != 'lib'
                    or s.st_uid != 0 or s.st_gid != 0):
                raise Rejected('unsupported runtime link: ' + rel)
            inventory[rel] = {'kind': 'link', 'target': 'lib'}
        elif stat.S_ISDIR(s.st_mode):
            protected(path, 'dir')
            inventory[rel] = {'kind': 'dir', 'mode': stat.S_IMODE(s.st_mode)}
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            data = read_protected(path)
            inventory[rel] = {'kind': 'file', 'mode': stat.S_IMODE(s.st_mode),
                              'sha256': digest(data)}

    visit(runtime)
    for path, (old, _) in BINDINGS.items():
        row = inventory.get(str(SITE / path))
        if (old is None and row is not None) or (old is not None and
                (row is None or row.get('sha256') != old)):
            raise Rejected('old runtime byte hash/absence mismatch: ' + path)
    return inventory


def preflight_payload():
    load_manifest(read_protected(BUNDLE / 'audit_backend_payload.json'))
    result = {}
    for path, (_, new) in BINDINGS.items():
        data = read_protected(BUNDLE / path)
        if digest(data) != new:
            raise Rejected('source byte hash mismatch: ' + path)
        ast.parse(data, filename=path)
        result[path] = data
    return result
