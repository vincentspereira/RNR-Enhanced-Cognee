"""Independent contract challenges. All filesystem writes stay in review sandboxes.

No real service commands, credentials, application imports, or root execution.
Only the helper is imported. Public accepted source bytes are hashed, not imported.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
HELPER = ROOT / 'integrations/hermes/deployment/prepare_security_first_cutover.py'
PIN = 'cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == PIN
spec = importlib.util.spec_from_file_location('independent_cutover_review', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def evidence(name, value):
    with (OUT / (name + '.json')).open('x', encoding='ascii') as f:
        json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write('\n')


def launch(extra=b''):
    return ('[Service]\nUser=enhanced-cognee-api\nGroup=enhanced-cognee-api\nWorkingDirectory=' + h.OLD +
            '\nExecStart=\nExecStart=' + h.OLD + '/runtime/bin/python -m src.memory_daemon api\n').encode() + extra


def invented_snapshot(monkeypatch):
    source = dict(zip(h.SOURCES, [b'[Service]\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n',
        b'[Service]\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n', launch(),
        b'[Service]\nLoadCredential=llm.json:/etc/enhanced-cognee/llm.json\n']))
    monkeypatch.setattr(h, 'SOURCE_HASHES', {p: h.digest(source[p]) for p in (h.SOURCES[0], h.SOURCES[1], h.SOURCES[3])})
    return {'inventory': list(h.SOURCES), 'source_bytes': source, 'loaded': dict(h.EXPECTED_LOADED),
            'candidate': h.CANDIDATE, 'candidate_hashes': dict(h.MODULE_HASHES), 'helper_sha256': PIN,
            'startup_interpreter': {'lexical': h.CANDIDATE + '/runtime/bin/python',
                                    'resolved': h.CANDIDATE + '/runtime/bin/python', 'sha256': h.digest(b'invented interpreter')}}


def exact_content(snap, installed=True):
    content = dict(snap['source_bytes'])
    for rel, pin in h.MODULE_HASHES.items():
        data = (ROOT / rel).read_bytes()
        assert h.digest(data) == pin
        prefix = h.CANDIDATE + ('/runtime/lib/python3.12/site-packages/' if installed else '/')
        content[prefix + rel] = data
    content[h.INSTALLED_HELPER] = HELPER.read_bytes()
    content[h.CANDIDATE + '/runtime/bin/python'] = b'invented interpreter'
    return content


def test_L01_installed_site_packages_layout_is_readable(monkeypatch):
    """Contract assertion deliberately fails when helper looks in candidate root."""
    snap = invented_snapshot(monkeypatch)
    content = exact_content(snap, installed=True)
    reads = []
    def reader(path):
        reads.append(path)
        if path not in content:
            raise FileNotFoundError(path)
        return content[path]
    try:
        result = h.collect_snapshot(reader=reader, guard=lambda p, **kw: p,
                                    inventory=lambda: list(h.SOURCES), loaded=lambda: dict(h.EXPECTED_LOADED))
    except FileNotFoundError as exc:
        evidence('L01-installed-layout', {'helper_sha256': PIN, 'expected': 'collect hashes from runtime/lib/python3.12/site-packages/src',
            'actual_missing_request': str(exc), 'reads': reads, 'exact_available_inputs': sorted(content),
            'accepted_module_hashes': dict(h.MODULE_HASHES), 'source_hash_pins_rebound_for_invented_units_only': dict(h.SOURCE_HASHES)})
        pytest.fail('L01: collect_snapshot requests nonexistent candidate-root module: ' + str(exc))
    assert result['candidate_hashes'] == h.MODULE_HASHES


def test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules(monkeypatch):
    """Wrong physical binding is one defect with L01, not a second count."""
    snap = invented_snapshot(monkeypatch)
    content = exact_content(snap, installed=False)
    for rel in h.MODULE_HASHES:
        content[h.CANDIDATE + '/runtime/lib/python3.12/site-packages/' + rel] = b'invented unreviewed runtime module'
    reads = []
    def reader(path):
        reads.append(path)
        return content[path]
    result = h.collect_snapshot(reader=reader, guard=lambda p, **kw: p,
                                inventory=lambda: list(h.SOURCES), loaded=lambda: dict(h.EXPECTED_LOADED))
    accepted = h.plan_from_snapshot(result)
    evidence('L02-runtime-decoys', {'helper_sha256': PIN, 'accepted': accepted, 'reads': reads,
        'runtime_module_sha256': h.digest(b'invented unreviewed runtime module'),
        'expected': 'reject unreviewed runtime module bytes', 'actual': 'accepted candidate-root decoys; never read runtime modules'})
    assert accepted['candidate_hashes'] != h.MODULE_HASHES, 'L02: approved hashes do not bind the modules selected by -I -m'


def rootish_metadata(path):
    s = os.lstat(path)
    values = list(s)
    values[4] = values[5] = 0
    if stat.S_ISDIR(s.st_mode):
        values[0] = stat.S_IFDIR | 0o755
    return os.stat_result(values)


def test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor(tmp_path, monkeypatch):
    """A real lexical alias resolves to untrusted bytes; guard hashes another file."""
    snap = invented_snapshot(monkeypatch)
    content = exact_content(snap, installed=False)
    virtual_root = tmp_path / 'vfs'
    virtual_root.mkdir()
    def local(path):
        assert path.startswith('/')
        return virtual_root / path.lstrip('/')
    lexical = h.CANDIDATE + '/runtime/bin/python'
    safe = '/usr/bin/python3.12'
    bridge = '/usr/bin/bridge'
    unsafe = '/outside/python3.12'
    for path, data in content.items():
        if path == lexical:
            continue
        p = local(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(0o644)
    local(safe).parent.mkdir(parents=True, exist_ok=True)
    local(safe).write_bytes(b'invented safe interpreter')
    local(safe).chmod(0o755)
    local('/outside/nested').mkdir(parents=True)
    local(unsafe).write_bytes(b'invented unsafe interpreter')
    local(unsafe).chmod(0o777)
    local(bridge).symlink_to('../../outside/nested')
    local(lexical).parent.mkdir(parents=True, exist_ok=True)
    alias_target = os.path.relpath(local(bridge), local(lexical).parent) + '/../python3.12'
    local(lexical).symlink_to(alias_target)
    assert os.path.realpath(local(lexical)) == str(local(unsafe))
    checked = []
    def metadata(path):
        checked.append(path)
        return rootish_metadata(local(path))
    def guard(path, **kwargs):
        return h.trusted_path(path, stat_fn=metadata, readlink=lambda p: os.readlink(local(p)), **kwargs)
    reads = []
    def reader(path):
        reads.append(path)
        if path == safe:
            return local(safe).read_bytes()
        return content[path]
    result = h.collect_snapshot(reader=reader, guard=guard,
                                inventory=lambda: list(h.SOURCES), loaded=lambda: dict(h.EXPECTED_LOADED))
    accepted = h.plan_from_snapshot(result)
    evidence('S01-alias-normalization', {'helper_sha256': PIN, 'lexical': lexical, 'alias_target': alias_target,
        'actual_sandbox_resolution': os.path.realpath(local(lexical)), 'safe_sandbox_file': str(local(safe)),
        'unsafe_sandbox_file': str(local(unsafe)), 'unsafe_mode': oct(stat.S_IMODE(local(unsafe).stat().st_mode)),
        'guard_checked_paths': checked, 'reads': reads, 'accepted_startup_interpreter': accepted['startup_interpreter'],
        'expected': 'reject the intermediate symlink ancestor or bind the real unsafe target',
        'actual': 'accepted; resolved field and hash describe the different safe file'})
    assert accepted['startup_interpreter']['resolved'] != safe, 'S01: normpath erased a symlink ancestor and fingerprinted the wrong executable'


@pytest.mark.parametrize('mutation', [b'[Service]\n', b'[Unit]\nDescription=trailing\n', b'User=enhanced-cognee-api\n',
    b'ExecStart=/invented\n', b'ExecStart=\n', b'Environment=HF_HUB_OFFLINE=1\nEnvironment=PYTHONUNBUFFERED=1\n',
    b'Environment=HF_HUB_OFFLINE=1\n[Install]\nWantedBy=multi-user.target\n', b'Environment=HF_HUB_OFFLINE=1\nUnknown=canary\n',
    b'Environment=HF_HUB_OFFLINE=1\n\x00', b'Environment=HF_HUB_OFFLINE=1\n\r',
    b'Environment=HF_HUB_OFFLINE=1 # comment\n', b'Environment="HF_HUB_OFFLINE=1"junk\n',
    b'Environment=HF_HUB_OFFLINE=1\\\n', b'Environment=HF_HUB_OFFLINE=1\t\n',
    b'Environment=HF_HUB_OFFLINE=1\n User=root\n', b'Environment=HF_HUB_OFFLINE=1\n;comment\nUser=root\n'])
def test_P01_full_input_parser_rejects_suffix_mutations(mutation):
    with pytest.raises(h.Refusal):
        h.parse_unit(launch(mutation), launch=True)


@pytest.mark.parametrize('value', [b'Environment="HF_HUB_OFFLINE=1"\n', b"Environment='HF_HUB_OFFLINE=1'\n", b'Environment=HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1\n'])
def test_P02_supported_environment_positive_controls(value):
    assert h.parse_unit(launch(value), launch=True)['Environment']


@pytest.mark.parametrize('which', ['inventory', 'loaded'])
def test_C01_snapshot_rechecks_both_manager_views(monkeypatch, which):
    snap = invented_snapshot(monkeypatch)
    content = exact_content(snap, installed=True)
    calls = {'inventory': 0, 'loaded': 0}
    def inventory():
        calls['inventory'] += 1
        result = list(h.SOURCES)
        if which == 'inventory' and calls['inventory'] == 2:
            result.append('/invented.conf')
        return result
    def loaded():
        calls['loaded'] += 1
        result = dict(h.EXPECTED_LOADED)
        if which == 'loaded' and calls['loaded'] == 2:
            result['NeedDaemonReload'] = 'yes'
        return result
    with pytest.raises(h.Refusal, match='snapshot_changed'):
        h.collect_snapshot(reader=lambda p: content[p], guard=lambda p, **kw: p, inventory=inventory, loaded=loaded)


@pytest.mark.parametrize('key', ['helper_sha256', 'startup_interpreter'])
def test_C02_prepare_rechecks_unpinned_but_approved_hashes(monkeypatch, key, capsys):
    original = invented_snapshot(monkeypatch)
    changed = copy.deepcopy(original)
    changed[key] = ('f' * 64 if key == 'helper_sha256' else {**original[key], 'sha256': 'e' * 64})
    calls = []
    def collector():
        calls.append(1)
        return original if len(calls) == 1 else changed
    writes = []
    approved = h.digest(h.canonical(h.plan_from_snapshot(original)))
    assert h.main(['--prepare', '--expected-plan-sha256', approved], runtime=lambda: None, output_guard=lambda: None,
                  collector=collector, writer=lambda *a: writes.append(a)) == 1
    assert writes == []
    assert capsys.readouterr().err == 'ERR stage_only_refused\n'


@pytest.mark.parametrize('error', [OSError('INVENTED_PRIVATE_CANARY'), PermissionError('INVENTED_PRIVATE_CANARY'), UnicodeDecodeError('ascii', b'\xff', 0, 1, 'INVENTED_PRIVATE_CANARY')])
def test_E01_metadata_error_is_not_echoed(error, capsys):
    def fail():
        raise error
    assert h.main(['--plan'], runtime=lambda: None, output_guard=lambda: None, collector=fail) == 1
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == 'ERR stage_only_refused\n'


@pytest.mark.parametrize('which', ['service.d', 'enhanced-.service.d', 'enhanced-cognee-.service.d', h.UNIT + '.d'])
def test_I01_runtime_source_override_is_not_ignored(which):
    root = '/run/systemd/system'
    directory = root + '/' + which
    present = {'/etc/systemd/system', h.SOURCE, h.SOURCE + '.d', *h.SOURCES[1:], root, directory}
    children = {h.SOURCE + '.d': [Path(p).name for p in h.SOURCES[1:]], directory: ['99-invented.conf']}
    with pytest.raises(h.Refusal):
        h.inventory_sources(roots=h.UNIT_ROOTS, exists=lambda p: p in present, children=lambda p: children[p], guard=lambda p, **kw: p)


@pytest.mark.parametrize('problem', ['link', 'hardlink', 'owner', 'ancestor-owner', 'ancestor-write', 'fifo'])
def test_T01_reader_guard_rejects_untrusted_inputs(tmp_path, problem):
    directory = tmp_path / 'safe'
    directory.mkdir()
    file = directory / 'source'
    file.write_bytes(b'invented source')
    file.chmod(0o600)
    requested = file
    if problem == 'link':
        requested = directory / 'alias'
        requested.symlink_to(file)
    if problem == 'hardlink':
        os.link(file, directory / 'other')
    if problem == 'fifo':
        requested = directory / 'fifo'
        os.mkfifo(requested)
    def metadata(path):
        values = list(rootish_metadata(path))
        if problem == 'owner' and path == str(requested) or problem == 'ancestor-owner' and path == str(directory):
            values[4] = 1234
        if problem == 'ancestor-write' and path == str(directory):
            values[0] |= 0o002
        return os.stat_result(values)
    def guard(path):
        return h.trusted_path(path, stat_fn=metadata)
    with pytest.raises(h.Refusal):
        h.read_protected(str(requested), guard=guard)


def sandbox_guard(path, *, kind='file', private=False, **kw):
    s = os.lstat(path)
    assert not stat.S_ISLNK(s.st_mode)
    assert stat.S_ISDIR(s.st_mode) if kind == 'directory' else stat.S_ISREG(s.st_mode)
    if private:
        assert stat.S_IMODE(s.st_mode) == (0o700 if kind == 'directory' else 0o600)
    return path


@pytest.mark.parametrize('failure_at', ['40-audit-security-first.conf', 'manifest.json', 'receipt.json'])
def test_W01_partial_artifacts_are_preserved(tmp_path, failure_at):
    parent = tmp_path / 'private'
    parent.mkdir(mode=0o700)
    target = parent / 'bundle'
    files = {'40-audit-security-first.conf': b'invented proposal', 'manifest.json': b'{}\n', 'receipt.json': b'{"complete":true}\n'}
    def writer(fd, name, data):
        if name == failure_at:
            raise OSError('INVENTED_WRITE_CANARY')
        h.write_new(fd, name, data)
    with pytest.raises(OSError):
        h.write_bundle(str(target), files, guard=sandbox_guard, writer=writer)
    keys = list(files)
    expected = set(keys[:keys.index(failure_at)])
    assert {p.name for p in target.iterdir()} == expected
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    with pytest.raises(FileExistsError):
        h.write_bundle(str(target), files, guard=sandbox_guard)
    assert {p.name: p.read_bytes() for p in target.iterdir()} == before


def test_M01_plan_does_not_call_writer_or_change_sandbox(monkeypatch, tmp_path, capsys):
    snap = invented_snapshot(monkeypatch)
    writes = []
    assert h.main(['--plan'], runtime=lambda: None, collector=lambda: snap, output_guard=lambda: None,
                  writer=lambda *a: writes.append(a)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['plan']['activated'] is False
    assert result['plan']['model_analysis_expected_enabled'] is False
    assert result['plan']['loaded'] == h.EXPECTED_LOADED
    assert writes == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('args', [ ['--prepare', '--expected-plan-sha256', 'a' * 64 + '\x00'], ['--prepare', '--expected-plan-sha256', '\t' + 'a' * 64],
    ['--expected-plan-sha256', 'a' * 64, '--prepare'], ['--prepare', '--expected-plan-sha256=' + 'a' * 64],
    ['--plan', '--plan'], ['--plan\n'], ['--prepare', '--expected-plan-sha256', '0' * 64, '--plan'] ])
def test_A01_literal_cli_args_fail_before_inspection(args, capsys):
    def forbidden():
        pytest.fail('malformed arguments reached runtime')
    assert h.main(args, runtime=forbidden) == 1
    assert capsys.readouterr().err == 'ERR stage_only_refused\n'
