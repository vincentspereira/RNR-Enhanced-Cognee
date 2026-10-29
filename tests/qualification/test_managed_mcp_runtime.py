"""Public build and protected archive-boundary regressions, invented fixtures."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('install_managed_mcp_runtime')
b = load('build_managed_mcp_candidate')
fetch = load('probe_fetch_candidate')
qualify = load('qualify_managed_pm_payload')


def archive(extra=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.GNU_FORMAT) as tar:
        for name in ('python', 'pm-runtime', 'python/python-3.14.7+20260901-linux-x64'):
            row = tarfile.TarInfo(name);row.type = tarfile.DIRTYPE;row.mode = 0o755
            tar.addfile(row)
        row = tarfile.TarInfo('pm-runtime/pm-runtime.json');row.mode = 0o644;row.size = 2
        tar.addfile(row, io.BytesIO(b'{}'))
        for row in extra:
            tar.addfile(row, io.BytesIO(b'x' * row.size) if row.isreg() else None)
    buffer.seek(0)
    return tarfile.open(fileobj=buffer, mode='r:')


def member(name, kind=tarfile.REGTYPE, target='', mode=0o644):
    row = tarfile.TarInfo(name);row.type = kind;row.linkname = target;row.mode = mode
    return row


def test_valid_payload_and_manual_unpack(tmp_path):
    with archive([member('python/python-3.14.7+20260901-linux-x64/data')]) as tar:
        assert len(m.validate_archive(tar)) == 5
        path = tmp_path / 'payload.tar'
        with path.open('wb') as stream:
            stream.write(tar.fileobj.getvalue())
    out = tmp_path / 'new'
    assert m.unpack(path, out) == 5
    assert (out / 'pm-runtime/pm-runtime.json').read_bytes() == b'{}'


@pytest.mark.parametrize('name', [
    '../outside', '/python/file', 'python/../outside', 'python//file',
    'other/file', 'python/unreviewed-tool/file', 'python/a\\b', 'python/\nfile',
])
def test_unsafe_or_unreviewed_paths_refused(name):
    with archive([member(name)]) as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


@pytest.mark.parametrize('target', ['/etc/passwd', '../../outside', 'missing', 'a\\b'])
def test_link_escape_or_missing_target_refused(target):
    with archive([member('pm-runtime/link', tarfile.SYMTYPE, target, 0o777)]) as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


@pytest.mark.parametrize('kind', [tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE])
def test_hardlinks_and_special_files_refused(kind):
    with archive([member('pm-runtime/special', kind, 'pm-runtime/pm-runtime.json')]) as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


@pytest.mark.parametrize('mode', [0o666, 0o777, 0o4755, 0o2755])
def test_writable_or_privileged_files_refused(mode):
    with archive([member('pm-runtime/unsafe', mode=mode)]) as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


def test_duplicate_and_symlink_parent_refused():
    for extra in ([member('pm-runtime/pm-runtime.json')],
                  [member('pm-runtime/link', tarfile.SYMTYPE, 'pm-runtime.json', 0o777),
                   member('pm-runtime/link/file')]):
        with archive(extra) as tar, pytest.raises(ValueError):
            m.validate_archive(tar)


def test_link_cycle_refused():
    with archive([member('pm-runtime/a', tarfile.SYMTYPE, 'b', 0o777),
                  member('pm-runtime/b', tarfile.SYMTYPE, 'a', 0o777)]) as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


def test_bounded_member_count(monkeypatch):
    monkeypatch.setattr(m, 'MAX_MEMBERS', 3)
    with archive() as tar, pytest.raises(ValueError):
        m.validate_archive(tar)


def test_only_empty_native_build_lock_accepted():
    with archive([member('python/.install.lock')]) as tar:
        assert len(m.validate_archive(tar)) == 5
    nonempty = member('python/.install.lock');nonempty.size = 1
    for row in (nonempty, member('python/.install.lock', tarfile.SYMTYPE, 'facts.json', 0o777)):
        with archive([row]) as tar, pytest.raises(ValueError):
            m.validate_archive(tar)


def test_large_shared_library_requires_exact_name_and_size():
    with archive() as tar:
        base = list(tar)
    directory = member('python/python-3.14.7+20260901-linux-x64/lib', tarfile.DIRTYPE, mode=0o755)
    library = member(directory.name + '/libpython3.14.so.1.0', mode=0o755);library.size = 248404536
    assert len(m.validate_archive(base + [directory, library])) == 6
    library.size += 1
    with pytest.raises(ValueError):
        m.validate_archive(base + [directory, library])
    library.name += '.unreviewed';library.size -= 1
    with pytest.raises(ValueError):
        m.validate_archive(base + [directory, library])


def test_no_active_candidate_guard(monkeypatch):
    monkeypatch.setattr(m.pwd, 'getpwall', lambda: [SimpleNamespace(pw_name='ecbot_fixture', pw_uid=987)])
    entry = SimpleNamespace(name='42', stat=lambda: SimpleNamespace(st_uid=987))
    monkeypatch.setattr(m.Path, 'iterdir', lambda self: iter([entry]))
    with pytest.raises(ValueError):
        m.no_active_candidates()


def test_repeated_partial_attempt_never_republishes(tmp_path, monkeypatch, capsys):
    (tmp_path / 'summary.json').write_text(json.dumps({'complete': False, 'checkpoint': 'preserved'}))
    monkeypatch.setattr(m, 'ARTIFACT', tmp_path)
    monkeypatch.setattr(m.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(m.sys, 'argv', ['operator'])
    monkeypatch.setattr(m, 'public_read', lambda p, **k: p.read_bytes())
    monkeypatch.setattr(m, 'preflight', lambda: pytest.fail('replayed failed attempt'))
    assert m.main() == 1
    assert json.loads(capsys.readouterr().out)['checkpoint'] == 'preserved'


@pytest.mark.parametrize('complete', [True, False])
def test_repeated_disposable_finish_preserves_summary(tmp_path, monkeypatch, capsys, complete):
    previous = {'complete': complete, 'evidence': str(tmp_path), 'checkpoint': 'immutable'}
    path = tmp_path / 'finish-summary.json';path.write_text(json.dumps(previous))
    before = path.read_bytes()
    monkeypatch.setattr(qualify.os, 'getuid', lambda: 1000)
    monkeypatch.setattr(sys, 'argv', ['qualify', '--build', str(tmp_path),
                                           '--finish-restored-probe', str(tmp_path)])
    monkeypatch.setattr(qualify.subprocess, 'run', lambda *a, **k: pytest.fail('replayed proof'))
    assert qualify.main() == (0 if complete else 1)
    assert json.loads(capsys.readouterr().out) == previous
    assert path.read_bytes() == before


def test_build_environment_excludes_original_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv('SECRET_FIXTURE', 'invented-secret')
    monkeypatch.setenv('UV_INDEX_URL', 'https://invented:secret@example.invalid/')
    env = b.build_environment(tmp_path)
    assert env['HOME'] == str(tmp_path / 'home')
    assert env['HERMES_RUNTIME_DIR'] == str(tmp_path / 'tools')
    assert 'SECRET_FIXTURE' not in env and 'UV_INDEX_URL' not in env
    assert all('invented-secret' not in v for v in env.values())


@pytest.mark.parametrize('value', [None, {}, {'isError': False}, {'isError': True, 'content': []},
                                   {'isError': True, 'content': [{'type': 'text', 'text': 'connection failed'}]}])
def test_fetch_network_error_cannot_masquerade_as_private_refusal(value):
    assert not fetch.private_denial(value)


def test_fetch_requires_actual_private_address_guard():
    assert fetch.private_denial({'isError': True, 'content': [
        {'type': 'text', 'text': 'Refused: not a public address'}]})


def test_html_extraction_qualified_when_converted_body_is_retained():
    converted = ('Contents of https://example.com/:\n'
                 'This domain is for use in documentation examples without'
                 ' needing permission.')
    assert fetch.expected_html_body(converted)
    for text in ('', None, 42,
                 '<error>Page failed to be simplified from HTML</error>',
                 'Contents of https://example.com/:<html><body>raw</body></html>',
                 'Contents of https://invented.invalid/:words',
                 'Contents of https://example.com/:   '):
        assert not fetch.expected_html_body(text)
