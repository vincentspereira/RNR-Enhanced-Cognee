"""Real restic + POSIX stream qualification. Native Windows is separate.

Run with RNR_RESTIC and RNR_BACKUP_V12_SUPPORT pointing to installed tools.
No real passwords, source data, repositories or cloud destinations are used.
"""
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace
import zipfile
from pathlib import Path

SUPPORT = Path(os.environ.get('RNR_BACKUP_V12_SUPPORT', '/mnt/c/Scripts/backup-v12'))
RESTIC = Path(os.environ.get('RNR_RESTIC', str(Path.home() / '.local/share/rnr-backup-tools/restic/0.19.1/restic')))


class BackupV12Qualification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rnr-v12-synthetic-')
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('RESTIC_')}
        self.env['RESTIC_PASSWORD'] = 'synthetic-test-only-not-an-owner-credential'
        self.repo = self.root / 'repo'

    def tearDown(self):
        self.temp.cleanup()  # Only this test's disposable synthetic fixtures.

    def restic(self, *args, good=True):
        result = subprocess.run([str(RESTIC), '-r', str(self.repo), '--no-cache', *args],
                                env=self.env, capture_output=True)
        if good:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def stream(self, *args, good=True):
        output = self.root / 'home.tar'
        with output.open('wb') as handle:
            result = subprocess.run([sys.executable, '-I', str(SUPPORT / 'capture_home.py'),
                                     '--test-no-system-inventory', '--root', str(self.home), *args], stdout=handle, stderr=subprocess.PIPE)
        if good:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        else:
            self.assertNotEqual(result.returncode, 0)
        return output

    def test_posix_names_links_and_exclusions(self):
        (self.home / 'Projects/data').mkdir(parents=True)
        (self.home / 'Projects/data/file:linux.txt').write_bytes(b'original')
        (self.home / 'legacy').symlink_to('Projects/data', target_is_directory=True)
        (self.home / '.cache').mkdir()
        (self.home / '.cache/rebuildable').write_bytes(b'cache')
        (self.home / 'output.7z').write_bytes(b'original archive')
        (self.home / 'benchmark.log').write_bytes(b'valuable evidence')
        runtime = self.home / '.local/share/rnr-backup-tools/powershell-parser'
        runtime.mkdir(parents=True)
        (runtime / 'pwsh').write_bytes(b'redownloadable qualification runtime')
        os.mkfifo(self.home / 'live-runtime-pipe')
        with tarfile.open(self.stream()) as tar:
            self.assertEqual(tar.extractfile('Projects/data/file:linux.txt').read(), b'original')
            self.assertTrue(tar.getmember('legacy').issym())
            self.assertNotIn('legacy/file:linux.txt', tar.getnames())
            self.assertNotIn('.cache/rebuildable', tar.getnames())
            self.assertIn('output.7z', tar.getnames())
            self.assertIn('benchmark.log', tar.getnames())
            self.assertNotIn('.local/share/rnr-backup-tools/powershell-parser/pwsh', tar.getnames())
            coverage = json.load(tar.extractfile('.rnr-backup-v12/coverage.json'))
            self.assertEqual(coverage['runtime_special_files_omitted'], 1)

    def test_live_sqlite_snapshot_and_fixture_bytes(self):
        db = sqlite3.connect(self.home / 'live.db')
        db.execute('pragma journal_mode=wal')
        db.execute('create table t(value text)')
        db.execute("insert into t values ('committed-in-wal')")
        db.commit()
        fixtures = self.home / 'tests/fixtures'
        fixtures.mkdir(parents=True)
        fixture = fixtures / 'exact.db'
        con = sqlite3.connect(fixture)
        con.execute('create table x(y)')
        con.close()
        original = fixture.read_bytes()
        try:
            with tarfile.open(self.stream()) as tar:
                restored = self.root / 'restored.db'
                restored.write_bytes(tar.extractfile('live.db').read())
                with sqlite3.connect(restored) as check:
                    self.assertEqual(check.execute('select value from t').fetchone()[0], 'committed-in-wal')
                self.assertNotIn('live.db-wal', tar.getnames())
                self.assertEqual(tar.extractfile('tests/fixtures/exact.db').read(), original)
        finally:
            db.close()

    def profile_fixture(self):
        profile = self.home / '.hermes/profiles/bot-one'
        (profile / 'skills').mkdir(parents=True)
        (profile / 'plugins').mkdir()
        (profile / 'backups').mkdir()
        (profile / 'config.yaml').write_text('synthetic: true')
        (profile / 'skills/custom.md').write_text('synthetic skill')
        (profile / 'plugins/plugin.py').write_text('# synthetic')
        (profile / 'backups/retained.txt').write_text('retained older profile backup')
        generated = self.home / '.hermes/backups'
        generated.mkdir()
        (generated / 'old.zip').write_bytes(b'not included again')
        native = self.root / 'native.zip'
        with zipfile.ZipFile(native, 'w') as zip_file:
            for file in profile.rglob('*'):
                if file.is_file() and 'backups' not in file.parts:
                    zip_file.write(file, file.relative_to(self.home / '.hermes'))
        return native

    def test_hermes_profiles_skills_plugins_history_no_duplicate_zip(self):
        native = self.profile_fixture()
        with tarfile.open(self.stream('--hermes', '--hermes-zip', str(native))) as tar:
            names = tar.getnames()
            self.assertEqual(names.count('.hermes/profiles/bot-one/config.yaml'), 1)
            self.assertIn('.hermes/profiles/bot-one/skills/custom.md', names)
            self.assertIn('.hermes/profiles/bot-one/plugins/plugin.py', names)
            self.assertIn('.hermes/profiles/bot-one/backups/retained.txt', names)
            self.assertNotIn('.hermes/backups/old.zip', names)
            coverage = json.load(tar.extractfile('.rnr-backup-v12/coverage.json'))
            self.assertTrue(coverage['profiles']['bot-one']['config'])

    def test_missing_profile_rejected(self):
        native = self.profile_fixture()
        (self.home / '.hermes/profiles/bot-two').mkdir()
        (self.home / '.hermes/profiles/bot-two/config.yaml').write_text('synthetic: true')
        self.stream('--hermes', '--hermes-zip', str(native), good=False)

    def test_unsafe_archive_rejected(self):
        native = self.profile_fixture()
        with zipfile.ZipFile(native, 'a') as archive:
            archive.writestr('../escape', 'bad')
        self.stream('--hermes', '--hermes-zip', str(native), good=False)

    def test_restic_reuse_correction_deletion_and_recovery(self):
        self.restic('init')
        source = self.home / 'source'
        source.mkdir()
        (source / 'unchanged').write_bytes(os.urandom(3 * 1024 * 1024))
        (source / 'change').write_text('before')
        (source / 'delete').write_text('retained only in older snapshot')
        def backup():
            result = self.restic('backup', '--json', str(source))
            return [json.loads(line) for line in result.stdout.splitlines() if json.loads(line)['message_type'] == 'summary'][0]
        first = backup()
        second = backup()
        self.assertEqual(second['data_blobs'], 0)
        # Small tree/snapshot metadata may change even when no data blob does.
        self.assertLess(second['data_added'], 8192)
        (source / 'change').write_text('after-correction')
        (source / 'delete').rename(self.root / 'preserved-delete-fixture')
        third = backup()
        self.assertLess(third['data_added'], 8192)
        self.restic('check', '--read-data')
        restored = self.root / 'restored'
        self.restic('restore', third['snapshot_id'], '--target', str(restored))
        actual = restored / source.relative_to('/')
        self.assertEqual((actual / 'change').read_text(), 'after-correction')
        self.assertFalse((actual / 'delete').exists())
        older = self.root / 'older'
        self.restic('restore', first['snapshot_id'], '--target', str(older))
        self.assertTrue((older / source.relative_to('/') / 'delete').exists())

    def test_failed_producer_admits_no_snapshot_and_retry_recovers(self):
        self.restic('init')
        self.restic('backup', '--stdin-from-command', '--stdin-filename', 'home.tar', '--',
                    sys.executable, '-c', "import sys;sys.stdout.buffer.write(b'partial-data');sys.exit(7)", good=False)
        self.assertEqual(json.loads(self.restic('snapshots', '--json').stdout), [])
        (self.home / 'valuable.txt').write_bytes(b'synthetic-complete')
        self.restic('backup', '--stdin-from-command', '--stdin-filename', 'home.tar', '--',
                    sys.executable, '-I', str(SUPPORT / 'capture_home.py'), '--test-no-system-inventory', '--root', str(self.home))
        self.restic('restore', 'latest', '--target', str(self.root / 'recovery'))
        with tarfile.open(self.root / 'recovery/home.tar') as tar:
            self.assertEqual(tar.extractfile('valuable.txt').read(), b'synthetic-complete')
        self.restic('check', '--read-data')

    def test_wrong_password_denied(self):
        self.restic('init')
        self.env['RESTIC_PASSWORD'] = 'wrong-synthetic-password'
        self.restic('snapshots', good=False)

    def test_home_fingerprint_unchanged_cache_skipped_and_correction_detected(self):
        spec = importlib.util.spec_from_file_location('v12home', SUPPORT / 'capture_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        file = self.home / 'original'
        file.write_text('first')
        first = helper.fingerprint_home(self.home)
        self.assertEqual(helper.fingerprint_home(self.home), first)
        cache = self.home / '.cache'
        cache.mkdir()
        (cache / 'rebuildable').write_text('cache must not trigger full backup')
        self.assertEqual(helper.fingerprint_home(self.home), first)
        file.write_text('later')
        self.assertNotEqual(helper.fingerprint_home(self.home), first)

    def test_reorganisation_moves_exact_bytes_and_preserves_old_link(self):
        spec = importlib.util.spec_from_file_location('v12move', SUPPORT / 'reorganize_hermes_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        source, destination = self.home / 'original-folder', self.home / 'Projects/moved-folder'
        source.mkdir()
        (source / 'evidence.log').write_bytes(b'private synthetic original evidence')
        (source / 'alias').symlink_to('evidence.log')
        before = helper.signature(source)
        journal = []
        helper.move(source, destination, True, journal)
        self.assertTrue(source.is_symlink())
        self.assertEqual(before, helper.signature(destination))
        self.assertTrue(journal[0]['file_bytes_modes_ownership_and_links_verified'])

    def test_reorganisation_collision_preserves_both_originals(self):
        spec = importlib.util.spec_from_file_location('v12move', SUPPORT / 'reorganize_hermes_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        source, destination = self.home / 'original', self.home / 'existing'
        source.mkdir()
        destination.mkdir()
        (source / 'original.txt').write_bytes(b'original')
        (destination / 'different.txt').write_bytes(b'preserve separately')
        journal = []
        helper.move(source, destination, True, journal)
        self.assertEqual(journal[0]['state'], 'destination_exists_preserved')
        self.assertTrue((source / 'original.txt').exists())
        self.assertTrue((destination / 'different.txt').exists())

    def test_private_instruction_archive_refuses_git_parent(self):
        spec = importlib.util.spec_from_file_location('v12move', SUPPORT / 'reorganize_hermes_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        source = self.home / 'hermes-instructions-before-synthetic'
        source.mkdir()
        (source / 'AGENTS.md').write_text('synthetic private instruction archive')
        projects = self.home / 'Projects'
        projects.mkdir()
        (projects / '.git').mkdir()
        destination = projects / '_LocalArchives/Hermes-Agent-Instructions' / source.name
        journal = []
        helper.move(source, destination, True, journal)
        self.assertEqual(journal[0]['state'], 'private_archive_requires_destination_outside_git')
        self.assertTrue((source / 'AGENTS.md').is_file())
        self.assertFalse(destination.exists())

    def test_system_inventory_retains_empty_cron_and_invalidates_home_reuse(self):
        spec = importlib.util.spec_from_file_location('v12inventory', SUPPORT / 'capture_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        def fake_run(command, **kwargs):
            if command[0] == 'crontab':
                return SimpleNamespace(returncode=1, stdout='', stderr='no crontab for synthetic')
            return SimpleNamespace(returncode=0, stdout='synthetic-local-inventory', stderr='')
        with mock.patch.object(helper.subprocess, 'run', side_effect=fake_run), \
             mock.patch.object(helper.shutil, 'which', return_value='/usr/bin/synthetic'), \
             mock.patch.object(helper.Path, 'is_file', return_value=False):
            inventory = helper.recovery_inventory()
        self.assertEqual(inventory['commands']['crontab']['state'], 'empty')
        first = helper.combined_fingerprint(self.home, inventory)
        inventory['commands']['packages']['content'] = 'newer-synthetic-package-version'
        self.assertNotEqual(first, helper.combined_fingerprint(self.home, inventory))

    def test_system_inventory_failure_is_not_suppressed(self):
        spec = importlib.util.spec_from_file_location('v12inventory', SUPPORT / 'capture_home.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        with mock.patch.object(helper.subprocess, 'run', return_value=SimpleNamespace(returncode=7, stdout='', stderr='synthetic failure')), \
             mock.patch.object(helper.shutil, 'which', return_value='/usr/bin/synthetic'):
            with self.assertRaisesRegex(RuntimeError, 'System recovery inventory failed'):
                helper.recovery_inventory()


if __name__ == '__main__':
    unittest.main(verbosity=2)
