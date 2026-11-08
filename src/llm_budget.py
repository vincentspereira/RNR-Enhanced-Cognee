"""Persistent, atomic per-tenant/project/UTC-day model reservations.

The service owner provisions ENHANCED_LLM_BUDGET_DB in a private directory.
No unconfigured or in-memory fallback exists. Outstanding reservations remain
charged after failure, cancellation, or process death.
"""
from __future__ import annotations

from contextlib import contextmanager
import datetime as dt
import os
from pathlib import Path
import sqlite3
import stat
import uuid


class BudgetUnavailable(ValueError):
    """Sanitized ledger failure; model calls must fail closed."""


class TokenBudget:
    def __init__(self, path=None):
        configured = path if path is not None else os.environ.get("ENHANCED_LLM_BUDGET_DB")
        if not configured or not Path(configured).is_absolute():
            raise BudgetUnavailable("A persistent model budget ledger is required")
        self.path = Path(configured)
        self._secure_path(create=True)
        with self._connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
                day TEXT NOT NULL, tokens INTEGER NOT NULL CHECK(tokens >= 0),
                settled INTEGER NOT NULL DEFAULT 0 CHECK(settled IN (0,1)))""")
            conn.execute("""CREATE INDEX IF NOT EXISTS budget_scope_day
                ON reservations(tenant,project,day)""")

    @staticmethod
    def _day():
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    def _secure_path(self, *, create=False):
        """Never truncate, follow links, or use an externally writable directory.

        Trust the service UID and root, not other local users. A private ancestor
        may shield intermediate group-readable directories, but the immediate
        database directory must itself be service-owned and private.
        """
        try:
            if ".." in self.path.parts:
                raise OSError
            uid = os.geteuid()
            private = False
            for directory in reversed(self.path.parents):
                info = directory.lstat()
                if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid)
                        or (info.st_mode & 0o022 and not private)):
                    raise OSError
                if info.st_uid == uid and not info.st_mode & 0o077:
                    private = True
            info = self.path.parent.lstat()
            if info.st_uid != uid or info.st_mode & 0o077:
                raise OSError
            for suffix in ("-journal", "-wal", "-shm"):
                candidate = Path(str(self.path) + suffix)
                try:
                    self._check_file(candidate.lstat(), uid)
                except FileNotFoundError:
                    pass
            if create:
                try:
                    fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                except FileExistsError:
                    pass
                else:
                    os.close(fd)
            self._check_file(self.path.lstat(), uid)
        except OSError:
            raise BudgetUnavailable("The model budget ledger path is not service-private") from None

    @staticmethod
    def _check_file(info, uid):
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid
                or info.st_mode & 0o077 or info.st_nlink != 1):
            raise OSError

    @contextmanager
    def _connection(self):
        conn = None
        try:
            self._secure_path()
            conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                   timeout=0.25, isolation_level=None)
            yield conn
        except (OSError, sqlite3.Error):
            raise BudgetUnavailable("The persistent model budget ledger is unavailable") from None
        finally:
            if conn is not None:
                conn.close()  # rolls back any uncommitted transaction

    def used(self, tenant: str, project: str) -> int:
        with self._connection() as conn:
            return conn.execute("""SELECT COALESCE(SUM(tokens),0) FROM reservations
                WHERE tenant=? AND project=? AND day=?""",
                (tenant, project, self._day())).fetchone()[0]

    def reserve(self, tenant: str, project: str, estimate: int, cap: int) -> str:
        if (not tenant or not project or type(estimate) is not int or estimate < 1
                or type(cap) is not int or not 1 <= cap <= 10_000_000):
            raise BudgetUnavailable("Invalid model budget reservation")
        day = self._day()
        ident = uuid.uuid4().hex
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            used = conn.execute("""SELECT COALESCE(SUM(tokens),0) FROM reservations
                WHERE tenant=? AND project=? AND day=?""", (tenant, project, day)).fetchone()[0]
            if used + estimate > cap:
                raise BudgetUnavailable("The daily model budget for this project is exhausted")
            conn.execute("""INSERT INTO reservations(id,tenant,project,day,tokens)
                VALUES(?,?,?,?,?)""", (ident, tenant, project, day, estimate))
            conn.execute("COMMIT")
        return ident

    def reconcile(self, reservation: str, actual) -> None:
        # Missing/malformed/zero usage must never refund a potentially billed call.
        if type(actual) is not int or not 0 < actual <= 1_000_000_000:
            return
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""UPDATE reservations SET tokens=?, settled=1
                WHERE id=? AND settled=0""", (actual, reservation))
            conn.execute("COMMIT")
