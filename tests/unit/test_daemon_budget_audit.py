"""Daemon ledger-path propagation: temporary invented credentials only."""
import json
from pathlib import Path
import tempfile
import unittest
from src.memory_daemon import credential_environment

class DaemonBudgetTests(unittest.TestCase):
    def test_production_api_gets_fixed_protected_ledger_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for name,data in [('api.json',{'ENHANCED_MEMORY_DATABASE_URL':'invented-database', 'ENCRYPTION_MASTER_KEY':'invented-test-key'}),
                              ('llm.json',{'base_url':'https://model.invalid/v1','api_key':'invented-test-only','model':'invented-model','daily_token_cap':50000})]:
                path=root/name;path.write_text(json.dumps(data));path.chmod(0o600)
            env=credential_environment('api',str(root))
            # 2026-11-06 G2 fix: the plain path is a symlink inside the DynamicUser
            # namespace (incident 2026-11-06); the daemon must provision the
            # namespace-private real directory path instead.
            self.assertEqual(env.get('ENHANCED_LLM_BUDGET_DB'),'/var/lib/private/enhanced-cognee-llm-budget/tokens.sqlite3')

if __name__=='__main__':unittest.main()
