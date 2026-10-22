"""Security regressions for the privileged, preservation-only snapshot builder."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace

import pytest


@pytest.fixture
def builder():
    path = Path("integrations/hermes/deployment/prepare_restricted_runtime.py").resolve()
    spec = importlib.util.spec_from_file_location("snapshot_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(path, members):
    with tarfile.open(path, "w") as output:
        for name, content, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                raw = content.encode()
                info.size = len(raw)
                output.addfile(info, io.BytesIO(raw))
            else:
                info.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                info.linkname = content
                output.addfile(info)


@pytest.mark.parametrize("name", ["../escape", "/absolute-escape", "a/../../escape", "a\\escape"])
def test_archive_cannot_write_outside_new_snapshot(builder, tmp_path, name):
    bundle = tmp_path / "source.tar"
    archive(bundle, [(name, "untrusted", "file")])
    out = tmp_path / "copy"
    with pytest.raises(builder.PreparationError, match="unsafe destination"):
        builder.unpack_source(bundle, out, [(builder.SOURCE, out)])
    assert not list(out.iterdir())


def test_archive_link_cannot_redirect_following_writes(builder, tmp_path):
    outside = tmp_path / "original"
    outside.mkdir()
    bundle = tmp_path / "source.tar"
    archive(bundle, [("jump", str(outside), "symlink"), ("jump/record", "new", "file")])
    out = tmp_path / "copy"
    with pytest.raises(builder.PreparationError, match="outside the selected runtime"):
        builder.unpack_source(bundle, out, [(builder.SOURCE, out)])
    assert not list(outside.iterdir())
    assert (out / "jump/record").read_text() == "new"


def test_archive_duplicate_and_hardlink_never_replace_existing_files(builder, tmp_path):
    bundle = tmp_path / "source.tar"
    archive(bundle, [("record", "first", "file"), ("record", "second", "file")])
    out = tmp_path / "copy"
    with pytest.raises(FileExistsError):
        builder.unpack_source(bundle, out, [(builder.SOURCE, out)])
    assert (out / "record").read_text() == "first"
    linked = tmp_path / "hardlink.tar"
    archive(linked, [("hard", "record", "hardlink")])
    with pytest.raises(builder.PreparationError, match="unsupported member"):
        builder.unpack_source(linked, tmp_path / "hard-copy", [])


def test_copy_detaches_hardlinks_and_omits_private_install_metadata(builder, tmp_path):
    source, target = tmp_path / "original", tmp_path / "copy"
    source.mkdir()
    original = source / "library.py"
    original.write_text("answer = 42\n")
    os.link(original, source / "same-inode.py")
    (source / ".env").write_text("SYNTHETIC_PRIVATE_SETTING=never-copy\n")
    (source / ".env.local").write_text("SYNTHETIC_PRIVATE_SETTING=never-copy-local\n")
    (source / "direct_url.json").write_text('{"url":"https://synthetic:credential@example.invalid"}')
    (source / "__pycache__").mkdir()
    (source / "__pycache__/library.pyc").write_bytes(b"old code")
    (source / "activate.py").write_text("# An ordinary module must survive\n")
    builder.copy_tree(source, target, [(source, target)])
    assert (target / "library.py").read_bytes() == original.read_bytes()
    assert (target / "library.py").stat().st_ino != original.stat().st_ino
    assert (target / "library.py").stat().st_nlink == 1
    assert (target / "activate.py").exists()
    assert not (target / ".env").exists()
    assert not (target / ".env.local").exists()
    assert not (target / "direct_url.json").exists()
    assert not (target / "__pycache__").exists()
    assert "never-copy" in (source / ".env").read_text()


def test_copy_rejects_directory_symlinks_in_ancestors(builder, tmp_path):
    source = tmp_path / "original"
    source.mkdir()
    (source / "library.py").write_text("public library")
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)
    with pytest.raises(OSError):
        builder.copy_tree(alias, tmp_path / "copy", [(source, tmp_path / "copy")])
    assert not (tmp_path / "copy").exists()


def test_copy_rejects_special_files_and_privileged_modes(builder, tmp_path):
    source = tmp_path / "original"
    source.mkdir()
    program = source / "program"
    program.write_text("synthetic, never executed")
    program.chmod(0o4755)
    with pytest.raises(builder.PreparationError, match="privilege bit"):
        builder.copy_tree(source, tmp_path / "copy", [(source, tmp_path / "copy")])
    assert not (tmp_path / "copy/program").exists()
    special = tmp_path / "special"
    special.mkdir()
    os.mkfifo(special / "fifo")
    with pytest.raises(builder.PreparationError, match="special file"):
        builder.copy_tree(special, tmp_path / "special-copy", [(special, tmp_path / "special-copy")])


def test_links_relocated_inside_snapshot_and_escape_rejected(builder, tmp_path):
    source, target = tmp_path / "original", tmp_path / "copy"
    source.mkdir()
    (source / "program").write_text("program bytes")
    (source / "alias").symlink_to(source / "program")
    builder.copy_tree(source, target, [(source, target)])
    assert (target / "alias").resolve() == target / "program"
    assert not os.path.isabs(os.readlink(target / "alias"))
    manifest = builder.snapshot_manifest(target)
    assert manifest["alias"] == {"link": "program"}
    assert manifest["program"]["sha256"] == builder.digest(b"program bytes")
    with pytest.raises(builder.PreparationError, match="outside the selected runtime"):
        builder.make_link(source / "bad", "../../unrelated", target / "bad", [(source, target)])


def test_ast_rebase_does_not_execute_editable_startup_code(builder, tmp_path):
    sentinel = tmp_path / "must-not-exist"
    original = (
        f"MAPPING = {{'hermes_cli': {str(builder.SOURCE / 'hermes_cli')!r}}}\n"
        f"__import__('pathlib').Path({str(sentinel)!r}).write_text('never execute')\n"
    ).encode()
    updated = builder.rebase_finder(original, [(builder.SOURCE, tmp_path / "protected/repo")])
    assert str(tmp_path / "protected/repo/hermes_cli").encode() in updated
    assert str(builder.SOURCE).encode() not in updated
    assert not sentinel.exists()
    assert str(builder.SOURCE).encode() in original
    private_reference = f"MAPPING = {{'bad': {str(builder.HOME / '.hermes/private')!r}}}".encode()
    with pytest.raises(builder.PreparationError, match="outside the selected runtime"):
        builder.rebase_finder(private_reference, [(builder.SOURCE, tmp_path / "protected/repo")])


def test_rewrite_preserves_copied_original_in_private_evidence(builder, tmp_path):
    generated = tmp_path / "finder.py"
    generated.write_bytes(b"original")
    audit = tmp_path / "evidence"
    audit.mkdir(mode=0o700)
    builder.rewrite_generated(generated, b"rebased", audit)
    assert generated.read_bytes() == b"rebased"
    assert (audit / "finder.py.original").read_bytes() == b"original"
    assert (audit / "finder.py.original").stat().st_mode & 0o077 == 0


def test_git_export_drops_root_and_excludes_operator_environment(builder, monkeypatch):
    calls = []
    def capture(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"public revision")
    monkeypatch.setattr(subprocess, "run", capture)
    operator = SimpleNamespace(pw_uid=1234, pw_gid=1234)
    builder.git_as_operator(operator, "rev-parse", "HEAD")
    args, options = calls[0]
    assert args[0] == "/usr/bin/git" and "--no-replace-objects" in args
    assert options["user"] == 1234 and options["group"] == 1234
    assert options["extra_groups"] == () and options["stdin"] == subprocess.DEVNULL
    assert options["env"]["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert "SUDO_USER" not in options["env"] and "ENHANCED_JWT_SECRET" not in options["env"]


def test_atomic_publication_refuses_even_an_empty_existing_directory(builder, tmp_path):
    staged, existing = tmp_path / "staged", tmp_path / "existing"
    staged.mkdir()
    (staged / "new").write_text("new work")
    existing.mkdir()
    with pytest.raises(builder.PreparationError, match="not replaced"):
        builder.publish(staged, existing)
    assert staged.is_dir() and existing.is_dir()
    assert (staged / "new").read_text() == "new work"
    destination = tmp_path / "published"
    builder.publish(staged, destination)
    assert (destination / "new").read_text() == "new work" and not staged.exists()


def test_builder_cannot_be_used_from_workspace(builder, monkeypatch):
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Workspace")
    with pytest.raises(builder.PreparationError, match="approved Ubuntu-Hermes"):
        builder.prepare()


def test_launcher_refuses_wrong_user_before_loading_any_program_code(builder, tmp_path):
    launcher = tmp_path / "hermes"
    launcher.write_bytes(builder.launcher_bytes(os.geteuid() + 1000000))
    assert b"/usr/bin/setpriv --no-new-privs" in launcher.read_bytes()
    assert b"/usr/bin/env -i" in launcher.read_bytes()
    syntax = subprocess.run(["/bin/sh", "-n", str(launcher)], capture_output=True)
    assert syntax.returncode == 0
    result = subprocess.run(["/bin/sh", str(launcher), "--version"], capture_output=True)
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == b"Run this launcher as hermes-runtime.\n"


@pytest.mark.parametrize("mutation", ["changed", "missing", "added", "symlink"])
def test_changed_startup_files_cannot_be_admitted(builder, monkeypatch, tmp_path, mutation):
    site = tmp_path / "site-packages"
    site.mkdir()
    hook = site / "fixture.pth"
    raw = b"import synthetic_fixture_module\n"
    hook.write_bytes(raw)
    monkeypatch.setattr(builder, "PTH_HASHES", {hook.name: builder.digest(raw)})
    builder.check_startup(site)
    if mutation == "changed":
        hook.write_bytes(b"import changed_module\n")
    elif mutation == "missing":
        hook.rename(site / "original.retained")
    elif mutation == "added":
        (site / "unexpected.pth").write_bytes(b"import unexpected_module\n")
    else:
        retained = site / "original.retained"
        hook.rename(retained)
        hook.symlink_to(retained)
    with pytest.raises((builder.PreparationError, OSError)):
        builder.check_startup(site)
