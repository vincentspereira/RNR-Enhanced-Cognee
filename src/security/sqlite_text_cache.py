"""Small transactional text cache with no Python-object deserialization.

Legacy diskcache files are never opened or migrated implicitly.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


class SqliteTextCache:
    def __init__(self, directory):
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink() or root.stat().st_mode & 0o077:
            raise PermissionError("Text cache requires a private directory without a symlink")
        if (root / "cache.db").exists():
            raise RuntimeError("Legacy diskcache data is preserved; explicit trusted migration is required")
        path = root / "text-cache.sqlite3"
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS entries (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL)")

    @contextmanager
    def transact(self):
        with self._lock:
            outer = not self._db.in_transaction
            if outer:
                self._db.execute("BEGIN IMMEDIATE")
            try:
                yield
                if outer:
                    self._db.execute("COMMIT")
            except BaseException:
                if outer:
                    self._db.execute("ROLLBACK")
                raise

    def get(self, key, default=None):
        with self._lock:
            row = self._db.execute("SELECT value, expires FROM entries WHERE key=?", (key,)).fetchone()
            if row is None:
                return default
            if row[1] is not None and row[1] <= time.time():
                self._db.execute("DELETE FROM entries WHERE key=?", (key,))
                return default
            return row[0]

    def set(self, key, value, expire=None):
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("The safe cache accepts text keys and values only")
        expiry = time.time() + expire if expire is not None else None
        with self._lock:
            self._db.execute("INSERT INTO entries VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,expires=excluded.expires", (key, value, expiry))
        return True

    def delete(self, key):
        with self._lock:
            return self._db.execute("DELETE FROM entries WHERE key=?", (key,)).rowcount > 0

    def expire(self):
        with self._lock:
            return self._db.execute("DELETE FROM entries WHERE expires IS NOT NULL AND expires <= ?", (time.time(),)).rowcount

    def clear(self):
        with self._lock:
            return self._db.execute("DELETE FROM entries").rowcount

    def close(self):
        with self._lock:
            self._db.close()
