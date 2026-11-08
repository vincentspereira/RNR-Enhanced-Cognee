"""No-launch tests for the renewal installer safety contract."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

DEPLOY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
SPEC=importlib.util.spec_from_file_location('renewal_installer',DEPLOY/'install_fleet_token_renewal.py')
assert SPEC and SPEC.loader
installer=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def test_unit_uses_os_python_not_checkout_venv(self):
        body=installer.unit_text()
        self.assertIn('ExecStart=/usr/bin/python3 -I -B /opt/',body)
        self.assertNotIn('/.venv-deployment/',body)

    def test_installer_does_not_start_renewal_or_timer(self):
        source=(DEPLOY/'install_fleet_token_renewal.py').read_text()
        self.assertNotIn('systemctl("start"',source)
        self.assertNotIn('"--now"',source)

    def test_unknown_predecessor_is_rejected(self):
        with self.assertRaises(ValueError):
            installer.approved_predecessor('renew_fleet_memory_tokens.py',b'invented unreviewed source',b'invented reviewed source')

    def test_inventory_is_data_not_imported_checkout_code(self):
        source=(DEPLOY/'install_fleet_token_renewal.py').read_text()
        self.assertIn('roles.json',source)
        self.assertNotIn('exec_module',source)

if __name__=='__main__':unittest.main()
