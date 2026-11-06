"""G2 fix regressions: ledger path must match the real DynamicUser namespace layout.

Incident 2026-11-06: the plain /var/lib/enhanced-cognee-llm-budget path is a
symlink inside the unit namespace, so _secure_path refused it and the ledger
was never created (silently, by design). The daemon must point at the private
path, which is a genuine read-write directory in the namespace.
"""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


EXPECTED_LEDGER_PATH = "/var/lib/private/enhanced-cognee-llm-budget/tokens.sqlite3"


class LedgerPathTests(unittest.TestCase):
    def test_daemon_provisions_namespace_private_path(self):
        """The env constant must be the path that is a real dir in-namespace."""
        source = Path(__file__).resolve().parents[2] / "src/memory_daemon.py"
        self.assertIn(EXPECTED_LEDGER_PATH, source.read_text())
        self.assertNotIn('"/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3"', source.read_text())


class SecurePathSemantics(unittest.TestCase):
    """Reproduce both namespace layouts as an unprivileged fixture."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="nsfix-"))
        # ancestor chain like /, /var, /var/lib: owned by us, 0755 (no 022 bits)
        plain = self.root / "lib"
        (plain / "private" / "enhanced-cognee-llm-budget").mkdir(parents=True)
        plain.mkdir(parents=True, exist_ok=True)
        for d in (self.root, plain, plain / "private"):
            os.chmod(d, 0o755)
        budget = plain / "private" / "enhanced-cognee-llm-budget"
        os.chmod(budget, 0o700)  # immediate parent: private, service-owned
        # the host-style symlink at the plain path
        os.symlink("private/enhanced-cognee-llm-budget", plain / "enhanced-cognee-llm-budget")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_budget_module_refuses_symlinked_plain_path(self):
        from src.llm_budget import TokenBudget, BudgetUnavailable
        with self.assertRaises(BudgetUnavailable):
            TokenBudget(path=str(self.root / "lib" / "enhanced-cognee-llm-budget" / "tokens.sqlite3"))
        self.assertFalse((self.root / "lib" / "private" / "enhanced-cognee-llm-budget" / "tokens.sqlite3").exists())

    def test_budget_module_accepts_real_private_path(self):
        from src.llm_budget import TokenBudget
        budget = TokenBudget(path=str(self.root / "lib" / "private" / "enhanced-cognee-llm-budget" / "tokens.sqlite3"))
        ledger = Path(budget.path)
        self.assertTrue(ledger.exists())
        info = ledger.stat()
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        # the daemon constant points at exactly this shape of path
        self.assertTrue(str(budget.path).endswith("/private/enhanced-cognee-llm-budget/tokens.sqlite3"))


if __name__ == "__main__":
    unittest.main()
