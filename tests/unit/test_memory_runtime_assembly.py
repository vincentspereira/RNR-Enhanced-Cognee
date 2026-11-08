"""Build-root path boundaries and noninteractive runtime selection."""
import importlib.util
from pathlib import Path
import os
import subprocess
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    "memory_runtime_assembly", Path(__file__).resolve().parents[2] / "docker/assemble_memory_runtime.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def test_container_absolute_symlink_never_reads_build_host_file(tmp_path):
    root = tmp_path / "image"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("invented fixture that must stay outside the image")
    (root / "reference").symlink_to(outside)
    result = assembly.rooted(root, "/reference")
    assert result.is_relative_to(root) and result != outside and not result.exists()
    for invalid in ("relative", "/usr/../outside"):
        with pytest.raises(ValueError):
            assembly.rooted(root, invalid)


def test_usrmerge_and_relative_library_links_resolve_inside_image(tmp_path):
    root = tmp_path / "image"
    (root / "usr/lib").mkdir(parents=True)
    library = root / "usr/lib/synthetic.so.1"
    library.write_bytes(b"invented library fixture")
    (root / "lib").symlink_to("usr/lib")
    (root / "usr/lib/synthetic.so").symlink_to("synthetic.so.1")
    (root / "entry").mkdir()
    (root / "entry/library").symlink_to("../usr/lib/synthetic.so")
    assert assembly.rooted(root, "/lib/synthetic.so") == library
    assert assembly.rooted(root, "/entry/library") == library
    (root / "cycle_a").symlink_to("cycle_b")
    (root / "cycle_b").symlink_to("cycle_a")
    with pytest.raises(ValueError, match="cycle"):
        assembly.rooted(root, "/cycle_a")


def test_omissions_do_not_remove_native_api_modules_or_third_party_names():
    names = ["readline.cpython-312.so", "_uuid.cpython-312.so", "_curses.cpython-312.so",
             "_tkinter.cpython-312.so", "_ssl.cpython-312.so", "_sqlite3.cpython-312.so", "_ctypes.cpython-312.so"]
    omitted = assembly.excluded_python_files("/usr/local/lib/python3.12/lib-dynload", names)
    assert omitted == set(names[:4])
    assert not assembly.excluded_python_files("/usr/local/lib/python3.12/site-packages/lib-dynload", names)


def test_assembler_refuses_use_outside_declared_build_before_creating_output(tmp_path):
    env = dict(os.environ)
    env.pop("RNR_BUILD_RUNTIME_ASSEMBLY", None)
    output = tmp_path / "output"
    result = subprocess.run([sys.executable, str(Path(assembly.__file__)), "--destination", str(output),
        "--base-root", str(tmp_path), "--python-reference", "synthetic", "--base-reference", "synthetic"],
        env=env, capture_output=True, text=True, timeout=5, check=False)
    assert result.returncode == 2 and "declared Python build stage" in result.stderr
    assert not output.exists()


def test_native_wheel_rpath_parents_map_to_the_actual_staged_library(tmp_path, monkeypatch):
    destination, base = tmp_path / "runtime", tmp_path / "base"
    native = destination / "usr/local/lib/python3.12/site-packages/pkg/capi/native.so"
    native.parent.mkdir(parents=True)
    native.write_bytes(b"\x7fELFsynthetic fixture")
    bundled = native.parent.parent.parent / "bundled.libs/library.so"
    bundled.parent.mkdir()
    bundled.write_bytes(b"synthetic non-executable library fixture")
    reported = str(native.parent / "../../bundled.libs/library.so")
    monkeypatch.setattr(assembly.subprocess, "run", lambda *a, **kw:
        subprocess.CompletedProcess(a, 0, "library.so => " + reported + " (0x1)\n", ""))
    assembly.check_dependencies(destination, base)
    # A real build-host file outside both final layers must still be rejected.
    outside = tmp_path / "outside.so"
    outside.write_bytes(b"synthetic excluded library fixture")
    monkeypatch.setattr(assembly.subprocess, "run", lambda *a, **kw:
        subprocess.CompletedProcess(a, 0, "library.so => " + str(outside) + " (0x1)\n", ""))
    with pytest.raises(RuntimeError, match="absent from the final runtime"):
        assembly.check_dependencies(destination, base)
