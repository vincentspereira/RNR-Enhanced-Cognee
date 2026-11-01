"""Offline acceptance-verifier regressions: no profile reads or live subprocesses."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

DEPLOY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'

def load():
    spec=importlib.util.spec_from_file_location('verification_contracts',DEPLOY/'verification_contracts.py')
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class VerificationContractTests(unittest.TestCase):
    def test_disabled_provider_and_broken_command_cannot_pass(self):
        m=load()
        cfg={'memory':{'provider':'none'},'agent':{'disabled_toolsets':['memory']},
             'mcp_servers':{'enhanced_cognee':{'command':'/bin/false','args':['--tool-groups','memory_read']}}}
        self.assertFalse(m.profile_contract(cfg,groups='memory_read',main=False)[0])

    def test_exact_approved_launch_positive_control_and_main_local_discovery(self):
        m=load()
        cfg={'memory':{'provider':'enhanced_cognee'},'plugins':{'enabled':['enhanced_cognee']},
             'agent':{'disabled_toolsets':[]},'platform_toolsets':{'cli':['memory']},
             'mcp_servers':{'enhanced_cognee':{'command':str(m.PY),'args':['-I',str(m.INSTALL),'--tool-groups','memory_read'],
                                            'env':{'ENHANCED_COGNEE_ACCESS_TOKEN':'${ENHANCED_COGNEE_ACCESS_TOKEN}'}}}}
        with patch.object(Path,'is_file',return_value=True):
            self.assertTrue(m.profile_contract(cfg,groups='memory_read',main=False)[0])
            cfg['plugins']['enabled']=[]
            # Main's local memory plugin is discovered separately from the
            # catalog plugin allowlist; selected config is not runtime proof.
            self.assertTrue(m.profile_contract(cfg,groups='memory_read',main=True)[0])
            self.assertFalse(m.profile_contract(cfg,groups='memory_read',main=False)[0])

    def test_root_receipts_are_explicit_skips_not_crash(self):
        m=load()
        with patch.object(Path,'iterdir',side_effect=PermissionError('invented')):
            rows=m.rotation_checks(Path('/invented'))
        self.assertEqual(len(rows),5)
        self.assertTrue(all(row['status']=='SKIP' for row in rows))

    def test_skip_is_not_complete_or_failed(self):
        m=load();summary=m.summarise([{'name':'root','status':'SKIP','detail':'owner-only'}])
        self.assertFalse(summary['complete'])
        self.assertEqual(summary['failed'],[])
        self.assertEqual(summary['skipped'],['root'])

if __name__=='__main__':unittest.main()
