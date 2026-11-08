"""Offline stage-only tests. Never invoke a protected interpreter or service."""
import hashlib
import importlib.util
import json
import os
import stat
import socket
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'integrations/hermes/deployment/stage_audit_backend.py'
MANIFEST = HELPER.with_name('audit_backend_payload.json')


@pytest.fixture
def stage():
    if not HELPER.is_file():
        return None
    spec = importlib.util.spec_from_file_location('stage_backend_under_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_c14_payload(stage):
    assert stage is not None, 'stage-only helper is not implemented'
    manifest = stage.load_manifest(MANIFEST.read_bytes())
    assert manifest['source_commit'] == 'c14f595ccd53f432b455b16f116765d9aa6c9a14'
    assert len(manifest['files']) == 8
    for row in manifest['files']:
        assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['new_sha256']
    added = [r['path'] for r in manifest['files'] if r['old_sha256'] is None]
    assert added == ['src/llm_budget.py']


@pytest.mark.parametrize('attack', [
    'unknown', 'missing', 'duplicate', 'nested-duplicate', 'extra-row',
    'missing-row', 'row-field', 'traversal', 'wrong-commit', 'wrong-hash',
    'malformed-hash', 'bool-schema', 'float-schema', 'nan', 'not-object',
])
def test_manifest_is_closed_schema(stage, attack):
    stage.load_manifest(MANIFEST.read_bytes())  # genuine positive control first
    obj = json.loads(MANIFEST.read_bytes())
    if attack == 'unknown':
        obj['environment'] = '/private/config'
    elif attack == 'missing':
        del obj['source_commit']
    elif attack == 'extra-row':
        obj['files'].append(obj['files'][0])
    elif attack == 'missing-row':
        obj['files'].pop()
    elif attack == 'row-field':
        obj['files'][0]['extra'] = True
    elif attack == 'traversal':
        obj['files'][0]['path'] = 'src/../../etc/shadow'
    elif attack == 'wrong-commit':
        obj['source_commit'] = '0' * 40
    elif attack == 'wrong-hash':
        obj['files'][0]['new_sha256'] = '0' * 64
    elif attack == 'malformed-hash':
        obj['files'][0]['old_sha256'] += 'x'
    elif attack == 'bool-schema':
        obj['schema'] = True
    elif attack == 'float-schema':
        obj['schema'] = 1.0
    elif attack == 'not-object':
        obj = []
    data = json.dumps(obj)
    if attack == 'duplicate':
        data = data.replace('"schema": 1', '"schema": 1, "schema": 1')
    elif attack == 'nested-duplicate':
        data = data.replace('"path": "src/ingestion.py"',
                            '"path": "src/ingestion.py", "path": "src/ingestion.py"')
    elif attack == 'nan':
        data = data.replace('"schema": 1', '"schema": NaN')
    with pytest.raises(stage.Rejected):
        stage.load_manifest(data)


@pytest.fixture
def layout(stage, tmp_path, monkeypatch):
    """REAL small filesystem; ONLY ownership/above-fixture modes are synthetic.

    Invented Python files have explicitly rebound old/new fixture hashes. Never
    claim these bytes are the c14 payload or that synthetic stat proves OS isolation.
    """
    base = tmp_path / 'candidates/old'
    dest = tmp_path / 'candidates/new'
    bundle = tmp_path / 'staging/reviewed'
    runtime = base / 'runtime'
    site = runtime / 'lib/python3.12/site-packages'
    for path in [site / 'src/security', runtime / 'bin', bundle / 'src/security']:
        path.mkdir(parents=True, mode=0o755)
    (runtime / 'bin/python').write_bytes(b'fixture binary, never execute')
    (runtime / 'bin/python').chmod(0o755)
    (runtime / 'lib64').symlink_to('lib', target_is_directory=True)
    (runtime / 'pyvenv.cfg').write_bytes(
        b'home = /opt/enhanced-cognee-memory/python/bin\n'
        b'include-system-site-packages = false\nversion = 3.12.13\n'
        b'executable = /opt/enhanced-cognee-memory/python/bin/python3.12\n'
        b'command = /opt/enhanced-cognee-memory/python/bin/python3.12 -m venv --copies '
        b'/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime\n')
    external = tmp_path / 'python/bin/python3.12'
    external.parent.mkdir(parents=True)
    external.write_bytes(b'fixture external binary, never execute')
    external.chmod(0o755)
    bindings = {}
    for i, path in enumerate(stage.BINDINGS):
        old = None if path == 'src/llm_budget.py' else f'VALUE = {i}\n'.encode()
        new = f'VALUE = {i + 100}\n'.encode()
        if old is not None:
            (site / path).write_bytes(old)
        (bundle / path).write_bytes(new)
        bindings[path] = (None if old is None else hashlib.sha256(old).hexdigest(),
                          hashlib.sha256(new).hexdigest())
    for p in [tmp_path, *tmp_path.rglob('*')]:
        if p.is_dir() and not p.is_symlink():
            p.chmod(0o755)
    manifest = {'schema': 1, 'source_commit': stage.COMMIT, 'files': [
        {'path': p, 'old_sha256': old, 'new_sha256': new}
        for p, (old, new) in bindings.items()]}
    (bundle / 'audit_backend_payload.json').write_text(json.dumps(manifest))
    script = bundle / 'stage_audit_backend.py'
    script.write_bytes(HELPER.read_bytes())
    for p in tmp_path.rglob('*'):
        if p.is_file() and not p.is_symlink() and p not in [external, runtime / 'bin/python']:
            p.chmod(0o644)
    monkeypatch.setattr(stage, 'BINDINGS', bindings)
    monkeypatch.setattr(stage, 'BASE', base, raising=False)
    monkeypatch.setattr(stage, 'DEST', dest, raising=False)
    monkeypatch.setattr(stage, 'BUNDLE', bundle, raising=False)
    monkeypatch.setattr(stage, 'EXTERNAL_PYTHON', external, raising=False)

    def root_stat(path):
        s = os.lstat(path)
        mode = s.st_mode
        if not Path(path).is_relative_to(tmp_path):
            mode = stat.S_IFDIR | 0o755  # trusted ancestor double only
        return SimpleNamespace(st_uid=0, st_gid=0, st_mode=mode, st_nlink=s.st_nlink,
                               st_size=s.st_size, st_dev=s.st_dev, st_ino=s.st_ino)

    monkeypatch.setattr(stage, '_lstat', root_stat, raising=False)
    return SimpleNamespace(base=base, dest=dest, bundle=bundle, runtime=runtime,
                           site=site, external=external, root_stat=root_stat,
                           script=script, tmp=tmp_path)


def test_preflight_protected_runtime_and_payload(stage, layout):
    assert hasattr(stage, 'inspect_runtime'), 'protected preflight is missing'
    inventory = stage.inspect_runtime()
    assert 'bin/python' in inventory
    assert inventory['lib64']['target'] == 'lib'
    payload = stage.preflight_payload()
    assert set(payload) == set(stage.BINDINGS)
    assert not layout.dest.exists()
    for path, data in payload.items():
        assert data == (layout.bundle / path).read_bytes()


@pytest.fixture
def stage_ready(stage, layout, monkeypatch):
    monkeypatch.setattr(stage.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(stage, '__file__', str(layout.script))
    monkeypatch.setattr(stage, 'EXECUTOR', layout.external, raising=False)
    monkeypatch.setattr(stage, 'sys', SimpleNamespace(
        executable=str(layout.external), flags=SimpleNamespace(
            isolated=1, no_site=1, dont_write_bytecode=1)), raising=False)
    return layout


def test_stage_new_candidate_only(stage, stage_ready):
    assert hasattr(stage, 'stage_candidate'), 'stage-only clone is missing'
    layout = stage_ready
    before = stage.inspect_runtime()
    # Sibling private/large directories must NEVER be traversed or copied.
    for name in ['model-cache', 'artifacts', 'credential-cycle', 'operator-private']:
        (layout.base / name).mkdir()
        (layout.base / name / 'DO-NOT-READ').write_text('private fixture')
    result = stage.stage_candidate()
    assert result['complete'] is True
    assert result['activated'] is False
    assert result['services_restarted'] is False
    assert result['credentials_issued'] == 0
    assert result['ledger_created'] is False
    assert set(p.name for p in layout.dest.iterdir()) == {
        'runtime', 'INCOMPLETE.json', 'COMPLETE.json'}
    assert json.loads((layout.dest / 'COMPLETE.json').read_text()) == result
    assert stage.inspect_runtime() == before  # old bytes, topology and modes preserved
    cloned = layout.dest / 'runtime'
    assert (cloned / 'lib64').is_symlink()
    assert os.readlink(cloned / 'lib64') == 'lib'
    for path, (_, new) in stage.BINDINGS.items():
        p = cloned / stage.SITE / path
        assert hashlib.sha256(p.read_bytes()).hexdigest() == new
        assert stat.S_IMODE(p.stat().st_mode) == 0o644
    assert result['overlay_source_commit'] == stage.COMMIT
    assert result['wheel_metadata_rebuilt'] is False
    assert result['runtime_inventory']
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()  # no overwrite/reuse, even a completed candidate


@pytest.mark.parametrize('attack', [
    'old-hash', 'new-module-present', 'source-change', 'writable-runtime',
    'writable-bin', 'external-bin-writable', 'wrong-owner', 'hardlink',
    'source-symlink', 'lexical-alias-dir', 'lib64-escape', 'fifo',
    'pyvenv-change', 'pth', 'setuid', 'runtime-private-dir',
])
def test_preflight_rejects_attacks_before_writes(stage, stage_ready, monkeypatch, attack):
    layout = stage_ready
    stage.inspect_runtime()
    stage.preflight_payload()  # positive controls before every mutation
    oldfile = layout.site / 'src/ingestion.py'
    if attack == 'old-hash':
        oldfile.write_text('VALUE = 999\n')
    elif attack == 'new-module-present':
        (layout.site / 'src/llm_budget.py').write_text('VALUE = 1\n')
        (layout.site / 'src/llm_budget.py').chmod(0o644)
    elif attack == 'source-change':
        (layout.bundle / 'src/ingestion.py').write_text('VALUE = 999\n')
    elif attack == 'writable-runtime':
        layout.runtime.chmod(0o775)
    elif attack == 'writable-bin':
        (layout.runtime / 'bin').chmod(0o777)
    elif attack == 'external-bin-writable':
        layout.external.parent.chmod(0o777)
    elif attack == 'wrong-owner':
        def bad_owner(path):
            s = layout.root_stat(path)
            if Path(path) == oldfile:
                s.st_uid = 1000
            return s
        monkeypatch.setattr(stage, '_lstat', bad_owner)
    elif attack == 'hardlink':
        os.link(oldfile, layout.tmp / 'alias')
    elif attack == 'source-symlink':
        source = layout.bundle / 'src/ingestion.py'
        source.rename(layout.tmp / 'saved-source')
        source.symlink_to(layout.tmp / 'saved-source')
    elif attack == 'lexical-alias-dir':
        directory = layout.bundle / 'src/security'
        directory.rename(layout.tmp / 'saved-security')
        directory.symlink_to(layout.tmp / 'saved-security', target_is_directory=True)
    elif attack == 'lib64-escape':
        (layout.runtime / 'lib64').rename(layout.tmp / 'saved-lib64')
        (layout.runtime / 'lib64').symlink_to('/private/secret')
    elif attack == 'fifo':
        os.mkfifo(layout.runtime / 'surprise')
    elif attack == 'pyvenv-change':
        (layout.runtime / 'pyvenv.cfg').write_text('home = /private/interpreter\n')
    elif attack == 'pth':
        p = layout.site / 'takeover.pth'
        p.write_text('import danger\n')
        p.chmod(0o644)
    elif attack == 'setuid':
        (layout.runtime / 'bin/python').chmod(0o4755)
    elif attack == 'runtime-private-dir':
        (layout.runtime / 'operator-private').mkdir(mode=0o755)
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()
    assert not layout.dest.exists()


def test_stale_overlay_bytecode_is_not_cloned(stage, stage_ready):
    layout = stage_ready
    cached = layout.site / 'src/__pycache__'
    cached.mkdir(mode=0o755)
    stale = cached / 'ingestion.cpython-312.pyc'
    stale.write_bytes(b'stale timestamp-valid bytecode must not survive overlay')
    stale.chmod(0o644)
    legacy = layout.site / 'src/llm_budget.pyc'
    legacy.write_bytes(b'sourceless cached new-module impostor')
    legacy.chmod(0o644)
    stage.stage_candidate()
    for path in [stale, legacy]:
        assert path.exists()  # original immutable
        assert not (layout.dest / 'runtime' / path.relative_to(layout.runtime)).exists()


@pytest.mark.parametrize('attack', [
    'not-root', 'no-isolation', 'site-enabled', 'bytecode-enabled', 'checkout-script',
    'writable-bundle-parent', 'writable-interpreter-parent', 'interpreter-dir-alias',
    'writable-executable-alias', 'wrong-interpreter', 'script-hardlink',
])
def test_root_execution_trust(stage, stage_ready, monkeypatch, attack):
    layout = stage_ready
    stage.execution_trust()  # positive control before mutating trust inputs
    if attack == 'not-root':
        monkeypatch.setattr(stage.os, 'geteuid', lambda: 1000)
    elif attack == 'no-isolation':
        stage.sys.flags.isolated = 0
    elif attack == 'site-enabled':
        stage.sys.flags.no_site = 0
    elif attack == 'bytecode-enabled':
        stage.sys.flags.dont_write_bytecode = 0
    elif attack == 'checkout-script':
        monkeypatch.setattr(stage, '__file__', str(HELPER))
    elif attack == 'writable-bundle-parent':
        layout.bundle.parent.chmod(0o777)
    elif attack in {'writable-interpreter-parent', 'writable-executable-alias'}:
        if attack == 'writable-executable-alias':
            safe = layout.tmp / 'safe-python'
            safe.write_bytes(b'protected executable target')
            safe.chmod(0o755)
            layout.external.rename(layout.tmp / 'saved-python')
            layout.external.symlink_to(safe)
        layout.external.parent.chmod(0o777)
    elif attack == 'interpreter-dir-alias':
        directory = layout.external.parent
        directory.rename(layout.tmp / 'saved-bin')
        directory.symlink_to(layout.tmp / 'saved-bin', target_is_directory=True)
    elif attack == 'wrong-interpreter':
        stage.sys.executable = '/private/python'
    elif attack == 'script-hardlink':
        os.link(layout.script, layout.tmp / 'hardlinked-script')
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()
    assert not layout.dest.exists()


@pytest.mark.parametrize('existing', ['directory', 'file', 'dangling-link'])
def test_destination_refuses_every_existing_shape(stage, stage_ready, existing):
    layout = stage_ready
    if existing == 'directory':
        layout.dest.mkdir()
    elif existing == 'file':
        layout.dest.write_text('preserve existing')
    else:
        layout.dest.symlink_to(layout.tmp / 'absent')
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()
    assert os.path.lexists(layout.dest)


@pytest.mark.parametrize('failure', ['clone-io', 'readback-tamper'])
def test_partial_preserved_without_complete_or_reuse(stage, stage_ready, monkeypatch, failure):
    layout = stage_ready
    original = stage.inspect_runtime()
    if failure == 'clone-io':
        write = stage.write_new
        def fail(path, data, mode):
            if path == layout.dest / 'runtime/bin/python':
                raise OSError('injected clone failure')
            return write(path, data, mode)
        monkeypatch.setattr(stage, 'write_new', fail)
        expected_error = OSError
    else:
        read = stage.read_protected
        target = layout.dest / 'runtime' / stage.SITE / 'src/ingestion.py'
        new = (layout.bundle / 'src/ingestion.py').read_bytes()
        def tamper(path):
            data = read(path)
            if path == target and data == new:
                Path(path).write_bytes(data + b'# tampered\n')  # real filesystem mutation
                return read(path)
            return data
        monkeypatch.setattr(stage, 'read_protected', tamper)
        expected_error = stage.Rejected
    with pytest.raises(expected_error):
        stage.stage_candidate()
    assert layout.dest.is_dir()
    assert json.loads((layout.dest / 'INCOMPLETE.json').read_text())['complete'] is False
    assert not (layout.dest / 'COMPLETE.json').exists()
    assert stage.inspect_runtime() == original
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()


def test_no_launch_network_service_or_private_config_reads(stage, stage_ready, monkeypatch):
    layout = stage_ready
    opened = []
    open_fd = os.open
    def confined_open(path, *args, **kwargs):
        path = Path(path)
        assert any(path.is_relative_to(tree) for tree in [
            layout.runtime, layout.bundle, layout.dest]), str(path)
        opened.append(path)
        return open_fd(path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError('no subprocess, pip, service, credentials or network allowed')
    monkeypatch.setattr(stage.os, 'open', confined_open)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(stage.os, 'system', forbidden)
    monkeypatch.setattr(stage.os, 'execve', forbidden)
    result = stage.stage_candidate()
    assert opened
    assert result['ledger_created'] is False
    assert not any('ledger' in str(p) or '.hermes' in str(p.relative_to(layout.tmp))
                   for p in opened)


def test_readonly_cli_inspection_requires_no_root_bundle(stage, layout, capsys):
    assert hasattr(stage, 'main'), 'bounded CLI is missing'
    assert stage.main(['--inspect-runtime']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['mode'] == 'inspect-runtime'
    assert result['runtime_entries'] > 0
    assert result['mutated'] is False
    assert not layout.dest.exists()


@pytest.mark.parametrize('args', [[], ['--stage', '/untrusted'],
                                  ['--profile', 'private'], ['--activate']])
def test_cli_has_no_user_controlled_paths(stage, layout, capsys, args):
    assert hasattr(stage, 'main'), 'bounded CLI is missing'
    assert stage.main(args) == 1
    assert json.loads(capsys.readouterr().out)['complete'] is False
    assert not layout.dest.exists()


def test_final_marker_readback_is_checked(stage, stage_ready, monkeypatch):
    layout = stage_ready
    rename = stage.os.rename
    def corrupt_after_rename(source, target):
        rename(source, target)
        if Path(target) == layout.dest / 'COMPLETE.json':
            Path(target).write_text('{"complete": true, "corrupted": true}\n')
    monkeypatch.setattr(stage.os, 'rename', corrupt_after_rename)
    with pytest.raises(stage.Rejected):
        stage.stage_candidate()
    assert layout.dest.exists()
    assert not (layout.dest / 'COMPLETE.json').exists()
    assert (layout.dest / 'COMPLETE.failed').exists()
