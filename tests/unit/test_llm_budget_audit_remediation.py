"""Offline F04 ledger regressions: actual SQLite, threads, and reopen."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from src import llm_summarize as llm


def test_budget_requires_persistent_path(monkeypatch):
    monkeypatch.delenv("ENHANCED_LLM_BUDGET_DB", raising=False)
    with pytest.raises(ValueError):
        llm.TokenBudget()


def test_ledger_reopen_and_tenant_project_isolation(tmp_path):
    path = tmp_path / "budget.sqlite3"
    budget = llm.TokenBudget(path)
    reservation = budget.reserve("tenant-a", "project", 800, 1000)
    reopened = llm.TokenBudget(path)
    assert reopened.used("tenant-a", "project") == 800
    assert reopened.used("tenant-b", "project") == 0
    assert reopened.used("tenant-a", "other") == 0
    with pytest.raises(ValueError):
        reopened.reserve("tenant-a", "project", 201, 1000)
    reopened.reconcile(reservation, 125)
    assert budget.used("tenant-a", "project") == 125
    reopened.reconcile(reservation, 1)  # idempotent, not a repeatable refund
    assert budget.used("tenant-a", "project") == 125


def test_real_concurrent_reservations_are_atomic_across_connections(tmp_path):
    path = tmp_path / "budget.sqlite3"
    llm.TokenBudget(path)
    start = Barrier(12)

    def reserve(_):
        budget = llm.TokenBudget(path)
        start.wait(timeout=10)
        try:
            budget.reserve("tenant", "project", 400, 1000)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(reserve, range(12)))
    assert results.count(True) == 2
    assert llm.TokenBudget(path).used("tenant", "project") == 800


@pytest.mark.parametrize("usage", [None, 0, -1, True, "20", 1.5, {}, 10**20])
def test_unreliable_usage_retains_reserved_charge(tmp_path, usage):
    budget = llm.TokenBudget(tmp_path / "budget.sqlite3")
    reservation = budget.reserve("tenant", "project", 800, 1000)
    budget.reconcile(reservation, usage)
    assert budget.used("tenant", "project") == 800


def test_reliable_overage_is_accounted_not_clipped(tmp_path):
    budget = llm.TokenBudget(tmp_path / "budget.sqlite3")
    reservation = budget.reserve("tenant", "project", 800, 1000)
    budget.reconcile(reservation, 1200)
    assert budget.used("tenant", "project") == 1200
    with pytest.raises(ValueError):
        budget.reserve("tenant", "project", 1, 1000)


def test_reconcile_uses_original_utc_day(tmp_path, monkeypatch):
    budget = llm.TokenBudget(tmp_path / "budget.sqlite3")
    monkeypatch.setattr(budget, "_day", lambda: "2026-11-01")
    reservation = budget.reserve("tenant", "project", 800, 1000)
    monkeypatch.setattr(budget, "_day", lambda: "2026-11-02")
    assert budget.used("tenant", "project") == 0
    budget.reconcile(reservation, 120)
    assert budget.used("tenant", "project") == 0
    monkeypatch.setattr(budget, "_day", lambda: "2026-11-01")
    assert budget.used("tenant", "project") == 120


@pytest.mark.parametrize("kind", ["file-symlink", "parent-symlink", "hardlink", "unsafe-parent",
                                  "unsafe-file", "directory", "journal-symlink"])
def test_ledger_refuses_unsafe_paths_without_touching_target(tmp_path, kind):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    target = tmp_path / "sentinel"
    llm.TokenBudget(target).reserve("tenant", "project", 500, 1000)
    target.chmod(0o600)
    original = target.read_bytes()
    path = parent / "budget.sqlite3"
    if kind == "file-symlink":
        path.symlink_to(target)
    elif kind == "parent-symlink":
        link = tmp_path / "linked"
        link.symlink_to(parent, target_is_directory=True)
        path = link / "budget.sqlite3"
    elif kind == "hardlink":
        path.hardlink_to(target)
    elif kind == "unsafe-parent":
        parent.chmod(0o777)
    elif kind == "unsafe-file":
        path.touch(mode=0o666)
        path.chmod(0o666)
    elif kind == "directory":
        path.mkdir()
    else:
        (parent / "budget.sqlite3-journal").symlink_to(target)
    with pytest.raises(ValueError):
        llm.TokenBudget(path)
    assert target.read_bytes() == original


def test_new_database_is_private_and_reopens_without_truncation(tmp_path):
    path = tmp_path / "budget.sqlite3"
    first = llm.TokenBudget(path)
    first.reserve("tenant", "project", 500, 1000)
    assert path.stat().st_mode & 0o777 == 0o600
    assert llm.TokenBudget(path).used("tenant", "project") == 500


def test_corrupt_ledger_fails_closed_without_truncation(tmp_path):
    path = tmp_path / "budget.sqlite3"
    path.write_bytes(b"not a database")
    path.chmod(0o600)
    with pytest.raises(ValueError):
        llm.TokenBudget(path)
    assert path.read_bytes() == b"not a database"


def test_ledger_lock_wait_is_bounded(tmp_path):
    import sqlite3
    import time
    path = tmp_path / "budget.sqlite3"
    budget = llm.TokenBudget(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        with pytest.raises(ValueError):
            budget.reserve("tenant", "project", 1, 1000)
        assert time.monotonic() - started < 1.5
    finally:
        connection.close()
    assert budget.used("tenant", "project") == 0
