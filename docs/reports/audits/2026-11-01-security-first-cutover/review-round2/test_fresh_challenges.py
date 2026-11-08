"""Fresh offline review: exact source; no root, services, network or app imports."""
import ast
import builtins
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
from types import SimpleNamespace

import pytest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
HELPER = ROOT / 'integrations/hermes/deployment/prepare_security_first_cutover.py'
PIN = 'd9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == PIN
spec = importlib.util.spec_from_file_location('round2_fresh_helper', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


@pytest.fixture
def snap(monkeypatch):
    raw = {h.SOURCES[0]: b'[Service]\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n',
           h.SOURCES[1]: b'[Service]\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n',
           h.SOURCES[2]: ('[Service]\nUser=enhanced-cognee-api\nGroup=enhanced-cognee-api\nWorkingDirectory=' + h.OLD + '\nExecStart=\nExecStart=' + h.OLD + '/runtime/bin/python -m src.memory_daemon api\n').encode(),
           h.SOURCES[3]: b'[Service]\nLoadCredential=llm.json:/etc/enhanced-cognee/llm.json\n'}
    monkeypatch.setattr(h, 'SOURCE_HASHES', {p: h.digest(raw[p]) for p in h.SOURCE_HASHES})
    return dict(inventory=list(h.SOURCES), source_bytes=raw, loaded=dict(h.EXPECTED_LOADED), candidate=h.CANDIDATE,
                candidate_hashes=dict(h.MODULE_HASHES), helper_sha256=PIN,
                startup_interpreter=dict(lexical=h.CANDIDATE + '/runtime/bin/python', resolved='/usr/bin/python3.12', sha256=h.digest(b'synthetic exe')))


def metadata(mode, uid=0, gid=0, links=1):
    return SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid, st_nlink=links)


@pytest.mark.parametrize('target,issue', [
    ('/usr/bin/python3.12', None), ('/usr/bin/./python3.12', None),
    ('/usr/bin/stable/../python3.12', None), ('../../usr/bin/python3.12', None),
    ('/usr/bin/python3', None), ('/usr/bin/bridge/../python3.12', 'link'),
    ('/usr/bin/bridge/../../bin/python3.12', 'link'), ('/usr/bin/stable/../python3.12', 'writable'),
    ('/usr/bin/stable/../python3.12', 'owner'), ('/usr/bin/stable/../python3.12', 'notdir'),
    ('/usr/bin/python3.12', 'bin-writable'), ('/safe/bin/python', 'loop'),
])
def test_F01_alias_lexical_chain(target, issue):
    nodes = {'/safe/bin/python': metadata(stat.S_IFLNK | 0o777),
             '/usr/bin/python3': metadata(stat.S_IFLNK | 0o777),
             '/usr/bin/python3.12': metadata(stat.S_IFREG | 0o755),
             '/usr/bin/bridge': metadata(stat.S_IFLNK | 0o777),
             '/usr/bin/stable': metadata(stat.S_IFDIR | 0o755)}
    if issue in ('writable', 'owner', 'notdir'):
        nodes['/usr/bin/stable'] = metadata(stat.S_IFDIR | 0o777 if issue == 'writable' else stat.S_IFREG | 0o755 if issue == 'notdir' else stat.S_IFDIR | 0o755, uid=1000 if issue == 'owner' else 0)
    if issue == 'bin-writable':
        nodes['/safe/bin'] = metadata(stat.S_IFDIR | 0o775)
    checked = []
    def lstat(path):
        checked.append(path)
        return nodes.get(path, metadata(stat.S_IFDIR | 0o755))
    def readlink(path):
        return target if path == '/safe/bin/python' else ('python3.12' if path == '/usr/bin/python3' else '/outside/nested')
    if issue:
        with pytest.raises(h.Refusal):
            h.trusted_path('/safe/bin/python', allow_alias=True, executable=True, stat_fn=lstat, readlink=readlink)
        if issue == 'link':
            assert '/usr/bin/bridge' in checked
            assert '/usr/bin/python3.12' not in checked
    else:
        assert h.trusted_path('/safe/bin/python', allow_alias=True, executable=True, stat_fn=lstat, readlink=readlink) == '/usr/bin/python3.12'


@pytest.mark.parametrize('changed', [None, *range(8)])
def test_F02_exact_installed_reads_and_per_module_decoys(snap, monkeypatch, changed):
    modules = {p: ('unique-installed-' + p).encode() for p in h.MODULE_HASHES}
    monkeypatch.setattr(h, 'MODULE_HASHES', {p: h.digest(b) for p, b in modules.items()})
    content = dict(snap['source_bytes'])
    paths = list(modules)
    for i, (p, b) in enumerate(modules.items()):
        content[h.CANDIDATE + '/' + p] = b
        content[h.CANDIDATE + '/runtime/lib/python3.12/site-packages/' + p] = b'changed-installed' if changed == i else b
    content[h.INSTALLED_HELPER] = HELPER.read_bytes()
    content['/usr/bin/python3.12'] = b'synthetic exe'
    reads = []
    def reader(path):
        reads.append(path)
        return content[path]
    result = h.collect_snapshot(reader=reader, guard=lambda p, **kw: '/usr/bin/python3.12' if kw.get('allow_alias') else p,
                                inventory=lambda: list(h.SOURCES), loaded=lambda: dict(h.EXPECTED_LOADED))
    assert len(reads) == len(h.SOURCES) + len(modules) + 2
    assert not any(h.CANDIDATE + '/' + p in reads for p in modules)
    if changed is None:
        assert h.plan_from_snapshot(result)['candidate_hashes'] == h.MODULE_HASHES
    else:
        assert result['candidate_hashes'][paths[changed]] != h.MODULE_HASHES[paths[changed]]
        with pytest.raises(h.Refusal, match='^inventory_or_loaded_or_candidate_drift$'):
            h.plan_from_snapshot(result)


@pytest.mark.parametrize('value', ['*.json:/etc/enhanced-cognee', 'api.json:/elsewhere/api.json', 'api.json:/etc/enhanced-cognee/api.json:extra',
    'api.json:/etc/enhanced-cognee/api.json index.json:/etc/enhanced-cognee/index.json', 'api.json', '%n:/etc/enhanced-cognee/api.json'])
def test_F03_exact_credential_inventory_after_rehash(snap, monkeypatch, value):
    snap['source_bytes'][h.SOURCES[0]] = ('[Service]\nLoadCredential=' + value + '\n').encode()
    monkeypatch.setattr(h, 'SOURCE_HASHES', {p: h.digest(snap['source_bytes'][p]) for p in h.SOURCE_HASHES})
    with pytest.raises(h.Refusal, match='^credential_inventory_drift$'):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize('tail', [b'\n[Unit]\nDescription=x\n', b'\n[Service]\nEnvironment=HF_HUB_OFFLINE=1\n',
    b'\nEnvironment=HF_HUB_OFFLINE=1\nImportCredential=*\n', b'\nEnvironment="HF_HUB_OFFLINE=1"\nLoadCredentialEncrypted=a:b\n',
    b'\nEnvironment=HF_HUB_OFFLINE=1\nExecStartPost=/bad\n', b'\nEnvironment=HF_HUB_OFFLINE=1\n#x\nSetCredential=a:CANARY\n'])
def test_F04_parser_checks_entire_suffix(snap, tail):
    with pytest.raises(h.Refusal, match='^unit_syntax_or_directive_refused$'):
        h.parse_unit(snap['source_bytes'][h.SOURCES[2]] + tail, launch=True)


@pytest.mark.parametrize('suffix', ['service.d', 'enhanced-.service.d', 'enhanced-cognee-.service.d', h.UNIT + '.d'])
@pytest.mark.parametrize('hidden', ['.40-hidden.conf', '40-audit-security-first.conf', '30-llm.conf~'])
def test_F05_inventory_no_hidden_or_wildcard_exceptions(suffix, hidden):
    directory = '/etc/systemd/system/' + suffix
    present = {'/etc/systemd/system', h.SOURCE, h.SOURCE + '.d', *h.SOURCES[1:], directory}
    entries = {h.SOURCE + '.d': [Path(p).name for p in h.SOURCES[1:]]}
    entries.setdefault(directory, []).append(hidden)
    with pytest.raises(h.Refusal):
        h.inventory_sources(roots=h.UNIT_ROOTS, exists=lambda p: p in present, children=lambda p: entries[p], guard=lambda p, **kw: p)


def sandbox_guard(path, *, kind='file', private=False, **kw):
    info = os.lstat(path)
    assert stat.S_ISDIR(info.st_mode) if kind == 'directory' else stat.S_ISREG(info.st_mode)
    assert not stat.S_ISLNK(info.st_mode)
    if private:
        assert stat.S_IMODE(info.st_mode) == (0o700 if kind == 'directory' else 0o600)
    return path


@pytest.mark.parametrize('bad_index', [0, 1, 2])
def test_F06_readback_corruption_preserves_no_success(snap, tmp_path, bad_index, capsys):
    parent = tmp_path / 'private'
    parent.mkdir(mode=0o700)
    target = parent / 'bundle'
    approved = h.digest(h.canonical(h.plan_from_snapshot(snap)))
    calls = []
    def corrupt(fd, name, data):
        index = len(calls)
        calls.append(name)
        h.write_new(fd, name, data + b'CORRUPTED' if index == bad_index else data)
    def writer(path, files):
        assert path == h.BUNDLE
        h.write_bundle(str(target), files, guard=sandbox_guard, writer=corrupt)
    assert h.main(['--prepare', '--expected-plan-sha256', approved], runtime=lambda: None, output_guard=lambda: None, collector=lambda: snap, writer=writer) == 1
    assert capsys.readouterr() == ('', 'ERR stage_only_refused\n')
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    assert len(before) == bad_index + 1
    with pytest.raises(FileExistsError):
        h.write_bundle(str(target), {name: b'' for name in ('40-audit-security-first.conf', 'manifest.json', 'receipt.json')}, guard=sandbox_guard)
    assert before == {p.name: p.read_bytes() for p in target.iterdir()}


@pytest.mark.parametrize('field', ['helper_sha256', 'startup_interpreter', 'source_bytes', 'loaded', 'candidate_hashes'])
def test_F07_second_snapshot_drift_never_writes(snap, field, capsys):
    changed = copy.deepcopy(snap)
    if field == 'helper_sha256': changed[field] = 'f' * 64
    elif field == 'startup_interpreter': changed[field]['resolved'] = '/usr/bin/python3.13'
    elif field == 'source_bytes': changed[field][h.SOURCES[2]] += b'# suffix drift\n'
    elif field == 'loaded': changed[field]['DynamicUser'] = 'no'
    else: changed[field]['src/ingestion.py'] = 'e' * 64
    seq = iter([snap, changed])
    writes = []
    assert h.main(['--prepare', '--expected-plan-sha256', h.digest(h.canonical(h.plan_from_snapshot(snap)))], runtime=lambda: None,
                  output_guard=lambda: None, collector=lambda: next(seq), writer=lambda *a: writes.append(a)) == 1
    assert not writes
    assert capsys.readouterr() == ('', 'ERR stage_only_refused\n')


def test_F08_plan_strictly_readonly_and_no_sensitive_echo(snap, tmp_path, capsys):
    snap['source_bytes'][h.SOURCES[2]] += b'# INVENTED_SECRET_COMMENT\n'
    original = copy.deepcopy(snap)
    assert h.main(['--plan'], runtime=lambda: None, output_guard=lambda: None, collector=lambda: snap,
                  writer=lambda *a: pytest.fail('writer called by --plan')) == 0
    output = capsys.readouterr()
    assert 'INVENTED_SECRET' not in output.out and output.err == ''
    value = json.loads(output.out)
    assert value['plan_sha256'] == h.digest(h.canonical(value['plan']))
    assert value['plan']['loaded'] == h.EXPECTED_LOADED
    assert value['plan']['model_analysis_expected_enabled'] is False
    assert snap == original and not list(tmp_path.iterdir())


# These doubles execute unchanged embedded Python with ONLY synthetic metadata
# and BytesIO streams. They do not invoke sudo, root, install or a real service.
class FS:
    def __init__(self):
        self.nodes = {p: metadata(stat.S_IFDIR | 0o755) for p in ['/', '/opt', '/opt/enhanced-cognee-memory']}
        self.bytes = {}
        self.created = []
        fs = self
        class P:
            def __init__(self, path): self.p = PurePosixPath(str(path))
            def __str__(self): return str(self.p)
            def __truediv__(self, other): return P(self.p / other)
            @property
            def parents(self): return [P(p) for p in self.p.parents]
            def lstat(self):
                if str(self) not in fs.nodes: raise FileNotFoundError('synthetic missing')
                return fs.nodes[str(self)]
            def mkdir(self, mode):
                if str(self) in fs.nodes: raise FileExistsError('synthetic exists')
                assert str(self.p.parent) in fs.nodes
                fs.nodes[str(self)] = metadata(stat.S_IFDIR | mode)
                fs.created.append(str(self))
            def read_bytes(self): return fs.bytes[str(self)]
        self.Path = P


def embedded(index, fs, data=b'', expected=PIN, uid=1000):
    output = io.BytesIO()
    fake_os = SimpleNamespace(path=SimpleNamespace(lexists=lambda p: str(p) in fs.nodes), geteuid=lambda: uid,
                              O_RDONLY=os.O_RDONLY, O_NOFOLLOW=os.O_NOFOLLOW,
                              open=lambda path, flags: 987, fdopen=lambda fd, mode: io.BytesIO(data))
    fake_sys = SimpleNamespace(argv=['-c', expected] if index == 3 else ['-c', '/synthetic/source.py', expected], stdout=SimpleNamespace(buffer=output))
    modules = {'pathlib': SimpleNamespace(Path=fs.Path), 'os': fake_os, 'sys': fake_sys}
    original_import = builtins.__import__
    def importer(name, *args, **kw):
        return modules[name] if name in modules else original_import(name, *args, **kw)
    local_builtins = dict(vars(builtins), __import__=importer)
    exec(compile((OUT / ('owner-python-%d.py' % index)).read_bytes(), 'exact-owner-block-%d' % index, 'exec'), {'__builtins__': local_builtins})
    return output.getvalue()


BASE = '/opt/enhanced-cognee-memory'
@pytest.mark.parametrize('problem', ['none', 'private-parent-exists', 'missing-base', 'base-symlink', 'base-writable', 'ancestor-owner', 'ancestor-gid', 'ancestor-sticky',
    'parent-symlink', 'parent-not-private', 'helper-existing', 'helper-dangling-link'])
def test_B01_bootstrap_original_code_metadata_matrix(problem):
    fs = FS()
    if problem == 'private-parent-exists': fs.nodes[BASE + '/cutover'] = metadata(stat.S_IFDIR | 0o700)
    if problem == 'missing-base': del fs.nodes[BASE]
    if problem == 'base-symlink': fs.nodes[BASE] = metadata(stat.S_IFLNK | 0o777)
    if problem == 'base-writable': fs.nodes[BASE] = metadata(stat.S_IFDIR | 0o775)
    if problem == 'ancestor-owner': fs.nodes['/opt'] = metadata(stat.S_IFDIR | 0o755, uid=1000)
    if problem == 'ancestor-gid': fs.nodes['/opt'] = metadata(stat.S_IFDIR | 0o755, gid=1000)
    if problem == 'ancestor-sticky': fs.nodes['/opt'] = metadata(stat.S_IFDIR | 0o1755)
    if problem == 'parent-symlink': fs.nodes[BASE + '/cutover'] = metadata(stat.S_IFLNK | 0o777)
    if problem == 'parent-not-private': fs.nodes[BASE + '/cutover'] = metadata(stat.S_IFDIR | 0o755)
    if problem.startswith('helper-'): fs.nodes[BASE + '/security-first-helper'] = metadata((stat.S_IFLNK | 0o777) if problem.endswith('link') else (stat.S_IFDIR | 0o755))
    if problem in ('none', 'private-parent-exists'):
        embedded(1, fs)
        assert fs.created == ([BASE + '/cutover'] if problem == 'none' else []) + [BASE + '/security-first-helper']
        assert stat.S_IMODE(fs.nodes[BASE + '/cutover'].st_mode) == 0o700
    else:
        with pytest.raises((SystemExit, FileNotFoundError)):
            embedded(1, fs)
        assert fs.created == []


@pytest.mark.parametrize('problem', ['none', 'hash-mismatch', 'root-reader'])
def test_B02_unprivileged_byte_handoff_exact_hash(problem):
    fs = FS()
    data = HELPER.read_bytes()
    if problem == 'none':
        assert embedded(2, fs, data=data) == data
    else:
        with pytest.raises(SystemExit):
            embedded(2, fs, data=data, expected='0' * 64 if problem == 'hash-mismatch' else PIN, uid=0 if problem == 'root-reader' else 1000)
    assert not fs.created


@pytest.mark.parametrize('problem', ['none', 'hash-mismatch', 'ancestor-link', 'ancestor-write', 'file-link', 'file-hardlink', 'file-owner', 'file-gid', 'file-mode', 'file-fifo'])
def test_B03_installed_readback_before_root_plan(problem, capsys):
    fs = FS()
    fs.nodes[BASE + '/security-first-helper'] = metadata(stat.S_IFDIR | 0o755)
    path = BASE + '/security-first-helper/prepare_security_first_cutover.py'
    fs.nodes[path] = metadata(stat.S_IFREG | 0o644)
    fs.bytes[path] = HELPER.read_bytes()
    if problem == 'hash-mismatch': fs.bytes[path] += b'\n'
    if problem == 'ancestor-link': fs.nodes[BASE] = metadata(stat.S_IFLNK | 0o777)
    if problem == 'ancestor-write': fs.nodes[BASE] = metadata(stat.S_IFDIR | 0o777)
    if problem == 'file-link': fs.nodes[path] = metadata(stat.S_IFLNK | 0o777)
    if problem == 'file-hardlink': fs.nodes[path].st_nlink = 2
    if problem == 'file-owner': fs.nodes[path].st_uid = 1000
    if problem == 'file-gid': fs.nodes[path].st_gid = 1000
    if problem == 'file-mode': fs.nodes[path].st_mode = stat.S_IFREG | 0o664
    if problem == 'file-fifo': fs.nodes[path].st_mode = stat.S_IFIFO | 0o644
    if problem == 'none':
        embedded(3, fs)
        value = json.loads(capsys.readouterr().out)
        assert value == dict(helper_sha256=PIN, helper_installed=True, api_override_installed=False, services_restarted=False)
    else:
        with pytest.raises(SystemExit):
            embedded(3, fs)
        assert capsys.readouterr().out == ''
    assert not fs.created


def test_B04_shell_privileged_boundary_and_stage_only_ast():
    bash = (OUT / 'owner-block-1.sh').read_text('ascii')
    plan = (OUT / 'owner-block-2.sh').read_text('ascii')
    assert 'set -euo pipefail' in bash and '/usr/bin/test "$(/usr/bin/id -u)" -ne 0' in bash
    assert bash.index('Source hash mismatch; no bytes emitted') < bash.index('/usr/bin/sudo /usr/bin/install') < bash.index('Installed helper hash mismatch; stop')
    assert '/dev/stdin' in bash and '-o root -g root -m 0644' in bash
    assert PIN in bash
    assert '"$repo/integrations/hermes/deployment/prepare_security_first_cutover.py" "$expected" |' in bash
    assert '/usr/bin/python3 -I -S -B' in plan and '--plan' in plan and '--prepare' not in plan
    assert h.INSTALLED_HELPER in plan and str(ROOT) not in plan
    assert 'sudo /usr/bin/python3 -I -S -B -c' in bash
    for text in (bash, plan):
        assert 'daemon-reload' not in text and 'restart' not in text.replace('services_restarted', '')
        assert 'systemctl' not in text and '/etc/systemd' not in text
    tree = ast.parse(HELPER.read_bytes())
    imports = {alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
    assert imports == {'hashlib', 'json', 're', 'shlex', 'os', 'stat', 'subprocess', 'sys'}
    assert all(n.module == 'pathlib' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
    assert b' -I -B -m src.memory_daemon api' in h.proposed_dropin()
    assert b' -S ' not in h.proposed_dropin()
    assert b'LoadCredential=\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n' in h.proposed_dropin()
    assert b'llm.json' not in h.proposed_dropin() and b'StateDirectory' not in h.proposed_dropin()
