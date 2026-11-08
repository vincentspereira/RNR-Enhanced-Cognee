"""Bounded owner-only SQLite backup into RAM, including committed WAL data.

This is a single-database component, not an atomic whole-profile backup.
Callers must separately handle profile quiescence, encryption, manifests and
restore admission. No source checkpoint, raw DB/WAL copying or root traversal.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import stat
import time
from urllib.parse import quote

MAX_BYTES = 64 * 1024 * 1024


class SnapshotError(RuntimeError):
    """Fixed category only; no database names, SQL contents or credentials."""


def require(value):
    if not value:
        raise SnapshotError('sqlite_snapshot_refused')


def open_parent(path, uid):
    require(path.is_absolute() and str(path) == str(Path(os.path.normpath(path)))
            and '..' not in path.parts and all(32 <= ord(char) < 127 for char in str(path))
            and not any('lswa' in part.lower() or 'legal-social-frameworks' in part.lower() for part in path.parts))
    directory = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for name in path.parent.parts[1:]:
            child = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            require(info.st_uid in {0, uid} and (not info.st_mode & 0o022 or sticky_root))
        info = os.fstat(directory)
        require(info.st_uid == uid and not info.st_mode & 0o077)
        return directory
    except BaseException:
        os.close(directory)
        raise


def memory_restore(raw):
    """Open an admitted standalone snapshot in RAM without executing its SQL."""
    require(isinstance(raw, bytes) and 512 <= len(raw) <= MAX_BYTES
            and raw[:16] == b'SQLite format 3\0' and raw[18:20] == b'\x01\x01')
    connection = sqlite3.connect(':memory:')
    try:
        connection.deserialize(raw)
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA query_only=ON')
        deadline = time.monotonic() + 10
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        require(connection.execute('PRAGMA quick_check').fetchall() == [('ok',)])
        return connection
    except BaseException:
        connection.close()
        raise SnapshotError('sqlite_snapshot_restore_refused') from None


def snapshot(path):
    uid = os.geteuid()
    require(uid != 0 and isinstance(path, Path))
    directory, opened, source, target = None, None, None, None
    try:
        directory = open_parent(path, uid)
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        info = os.fstat(opened)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
                and 16 <= info.st_size <= MAX_BYTES and os.read(opened, 16) == b'SQLite format 3\0')
        for suffix in ('-wal', '-shm', '-journal'):
            try:
                sidecar = os.stat(path.name + suffix, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                continue
            require(stat.S_ISREG(sidecar.st_mode) and sidecar.st_uid == uid and sidecar.st_nlink == 1)
        # Pin ancestors with a directory descriptor. SQLite itself reads the
        # associated WAL; it is never archived as an independent byte copy.
        uri = 'file:/proc/self/fd/' + str(directory) + '/' + quote(path.name, safe='') + '?mode=ro'
        source = sqlite3.connect(uri, uri=True, timeout=1)
        source.execute('PRAGMA query_only=ON')
        source.execute('PRAGMA trusted_schema=OFF')
        page_size = source.execute('PRAGMA page_size').fetchone()[0]
        require(type(page_size) is int and 512 <= page_size <= 65536)
        target = sqlite3.connect(':memory:')
        deadline = time.monotonic() + 10
        def progress(status, remaining, total):
            require(time.monotonic() < deadline and 0 <= total * page_size <= MAX_BYTES)
        source.backup(target, pages=64, progress=progress, sleep=0.01)
        raw = target.serialize()
        require(512 <= len(raw) <= MAX_BYTES and raw[:16] == b'SQLite format 3\0'
                and raw[18] in (1, 2) and raw[19] in (1, 2))
        # Only normalize the API-produced, complete backup image. SQLite's
        # documented deserialize workaround changes these two mode bytes;
        # NEVER apply this to a live raw database file that still needs its WAL.
        # https://sqlite.org/c3ref/deserialize.html
        raw = raw[:18] + b'\x01\x01' + raw[20:]
        restored = memory_restore(raw)
        restored.close()
        after = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        require((info.st_dev, info.st_ino, info.st_uid, info.st_nlink)
                == (after.st_dev, after.st_ino, after.st_uid, after.st_nlink))
        return raw
    except (OSError, sqlite3.Error, ValueError):
        raise SnapshotError('sqlite_snapshot_refused') from None
    finally:
        for connection in (target, source):
            if connection is not None:
                connection.close()
        for fd in (opened, directory):
            if fd is not None:
                os.close(fd)
