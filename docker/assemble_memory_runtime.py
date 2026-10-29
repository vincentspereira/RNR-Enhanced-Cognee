"""Build-only assembly of the noninteractive canonical memory runtime.

The final image retains complete Debian inventories for every copied library
package. No vulnerability record or package database is filtered. Interactive
GUI/terminal extensions and the optional libuuid accelerator are outside this API's
contract; UUID4 continues to use Python's operating-system randomness path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import sysconfig


LIBRARY_PACKAGES = (
    "libbz2-1.0", "libcrypt1", "libdb5.3t64", "libffi8", "libgdbm6t64",
    "liblzma5", "libsqlite3-0",
)
OMITTED_EXTENSIONS = {"_curses", "_curses_panel", "readline", "_uuid", "_tkinter"}


def rooted(root: Path, virtual: str) -> Path:
    """Resolve container symlinks inside their root, never in the build host."""
    parts = list(PurePosixPath(virtual).parts)
    if not parts or parts.pop(0) != "/" or ".." in parts:
        raise ValueError("Use an absolute normalized container path")
    current = root
    hops = 0
    while parts:
        current /= parts.pop(0)
        if current.is_symlink():
            hops += 1
            if hops > 32:
                raise ValueError("Container symlink cycle")
            link = os.readlink(current)
            target = PurePosixPath(link)
            if ".." in target.parts:
                # Debian package links are normally relative basenames; permit
                # parent traversal only while it remains inside this root.
                parent = current.parent.relative_to(root)
                normalized = os.path.normpath("/" + str(parent) + "/" + link)
                target = PurePosixPath(normalized)
            if target.is_absolute():
                current = root
                parts = list(target.parts[1:]) + parts
            else:
                current = current.parent
                parts = list(target.parts) + parts
    return current


def excluded_python_files(directory: str, names: list[str]) -> set[str]:
    path = Path(directory)
    ignored = {name for name in names if name == "__pycache__"}
    if path == Path("/usr/local/lib/python3.12/lib-dynload"):
        ignored.update(name for name in names if name.split(".", 1)[0] in OMITTED_EXTENSIONS)
    if path == Path("/usr/local/lib/python3.12"):
        ignored.update({"ensurepip"} & set(names))
    return ignored


def copy_package(package: str, destination: Path) -> dict:
    control = subprocess.check_output(["dpkg-query", "-s", package], text=True)
    fields = dict(line.split(": ", 1) for line in control.splitlines()
                  if ": " in line and not line.startswith(" "))
    if fields.get("Status") != "install ok installed":
        raise RuntimeError("Required runtime library package is not installed")
    names = subprocess.check_output(["dpkg-query", "-L", package], text=True).splitlines()
    for name in names:
        if name == "/.":
            continue
        item = PurePosixPath(name)
        if not item.is_absolute() or ".." in item.parts:
            raise ValueError("Invalid Debian payload path")
        source = Path(name)
        target = destination.joinpath(*item.parts[1:])
        # Refuse to write through any symlink already copied into the staging
        # tree. Package files must stay within the newly created destination.
        for parent in target.parents:
            if parent == destination:
                break
            if parent.is_symlink():
                raise ValueError("Runtime payload has a symlink parent")
        if source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(os.readlink(source))
        elif source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif name.startswith(("/usr/share/doc/", "/usr/share/man/", "/usr/share/lintian/")):
            # The official slim input omits documentation while retaining full
            # dpkg inventories. Keep those records; never omit a missing library.
            continue
        else:
            raise RuntimeError("Debian runtime payload is missing or special: " + name)
    inventory = destination / "var/lib/dpkg/status.d"
    inventory.mkdir(parents=True, exist_ok=True)
    (inventory / package).write_text(control, encoding="utf-8")
    metadata = Path("/var/lib/dpkg/info")
    candidates = [metadata / (package + suffix + ".md5sums")
                  for suffix in (":" + fields["Architecture"], "")]
    checksums = next((path for path in candidates if path.is_file()), None)
    if checksums is None:
        raise RuntimeError("Runtime package checksum inventory is missing")
    shutil.copy2(checksums, inventory / (package + ".md5sums"))
    return {"name": package, "version": fields["Version"], "architecture": fields["Architecture"]}


def check_dependencies(destination: Path, base: Path) -> None:
    """Every dynamically linked library must exist in the final two layers."""
    architecture = sysconfig.get_config_var("MULTIARCH")
    environment = dict(os.environ)
    # Inspect against the retained layers, including C++/OpenMP libraries from
    # the pinned final base that the slim Python build input need not contain.
    environment["LD_LIBRARY_PATH"] = ":".join(str(root / directory)
        for root in (destination, base)
        for directory in ("usr/local/lib", "usr/lib/" + architecture))
    for path in (destination / "usr/local").rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            if handle.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(["ldd", str(path)], capture_output=True, text=True,
                                check=False, env=environment)
        output = result.stdout + result.stderr
        if "not found" in output:
            raise RuntimeError("Unresolved native dependency for " + str(path) + ": " + output.strip())
        if result.returncode and "not a dynamic executable" not in output and "statically linked" not in output:
            raise RuntimeError("Cannot inspect native runtime dependency " + str(path)
                               + ": " + output.strip())
        for line in result.stdout.splitlines():
            words = line.split()
            library = words[2] if len(words) > 2 and words[1] == "=>" else words[0] if words else ""
            if not library.startswith("/"):
                continue
            # Wheel RPATHs can contain $ORIGIN-relative parent components. Resolve
            # the actual build-stage file before mapping it into the final image;
            # the container resolver still rejects caller-supplied traversal.
            library = str(Path(library).resolve(strict=True))
            # ldd can report the staging path for bundled wheel libraries.
            for root in (destination, base):
                if library.startswith(str(root) + "/"):
                    library = "/" + str(Path(library).relative_to(root))
                    break
            if not rooted(destination, library).is_file() and not rooted(base, library).is_file():
                raise RuntimeError("A native dependency is absent from the final runtime: " + library)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--python-reference", required=True)
    parser.add_argument("--base-reference", required=True)
    args = parser.parse_args()
    if (os.environ.get("RNR_BUILD_RUNTIME_ASSEMBLY") != "1" or os.geteuid() != 0
            or sys.prefix != "/usr/local" or sys.version_info[:2] != (3, 12)):
        parser.error("This assembler runs only in the declared Python build stage")
    destination, base = args.destination, args.base_root
    if (not destination.is_absolute() or destination.parent != destination.parent.resolve(strict=True)
            or destination.exists() or destination.is_symlink() or not base.is_absolute()
            or base != base.resolve(strict=True) or not rooted(base, "/etc/os-release").is_file()):
        parser.error("Use a new absolute staging directory and the pinned base root")
    destination.mkdir(mode=0o755)
    shutil.copytree("/usr/local", destination / "usr/local", symlinks=True, ignore=excluded_python_files)
    packages = [copy_package(package, destination) for package in LIBRARY_PACKAGES]
    # Preserve the pinned base's identical UsrMerge aliases in this partial
    # layer so dependency inspection resolves /lib to the copied /usr/lib.
    for name in ("bin", "lib", "lib64", "sbin"):
        source = base / name
        if source.is_symlink():
            (destination / name).symlink_to(os.readlink(source))
    # Let the ELF loader find libpython even in a stripped service environment;
    # no inherited LD_LIBRARY_PATH or copied build-host loader cache is needed.
    library_dir = destination / "usr/lib" / sysconfig.get_config_var("MULTIARCH")
    library_dir.mkdir(parents=True, exist_ok=True)
    library = sysconfig.get_config_var("INSTSONAME")
    (library_dir / library).symlink_to("/usr/local/lib/" + library)
    check_dependencies(destination, base)
    report = destination / "usr/share/enhanced-cognee/runtime-inventory.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"python_reference": args.python_reference,
        "base_reference": args.base_reference, "python_version": sys.version.split()[0],
        "additional_debian_packages": packages, "omitted_optional_extensions": sorted(OMITTED_EXTENSIONS),
        "python_binary_sha256": hashlib.sha256(Path("/usr/local/bin/python3.12").read_bytes()).hexdigest(),
        "package_inventories_preserved": True}, indent=2) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
