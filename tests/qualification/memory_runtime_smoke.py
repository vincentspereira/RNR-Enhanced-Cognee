"""Run inside the exact reduced image; no account data or provider calls."""
import bz2
import ctypes
import dbm.gnu
import importlib.util
import json
import lzma
from pathlib import Path
import shutil
import sqlite3
import ssl
import sys
import tempfile
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def main():
    assert sys.version_info[:2] == (3, 12) and sys.prefix == "/usr/local"
    assert Path("/etc/ssl/certs/ca-certificates.crt").is_file()
    ssl.create_default_context()
    ctypes.CDLL(None)
    fixture = b"invented canonical runtime fixture"
    assert bz2.decompress(bz2.compress(fixture)) == fixture
    assert lzma.decompress(lzma.compress(fixture)) == fixture
    with sqlite3.connect(":memory:") as connection:
        assert connection.execute("SELECT 42").fetchone() == (42,)
    with tempfile.TemporaryDirectory(prefix="cognee-runtime-fixture-") as directory:
        with dbm.gnu.open(str(Path(directory) / "fixture"), "c") as store:
            store[b"fixture"] = fixture
            assert store[b"fixture"] == fixture
    key = AESGCM.generate_key(bit_length=256)
    cipher, nonce = AESGCM(key), b"synthetic123"
    assert cipher.decrypt(nonce, cipher.encrypt(nonce, fixture, None), None) == fixture
    assert uuid.uuid4().version == 4
    # Noninteractive server scope, not a general-purpose Python/OS image.
    for name in ("_curses", "_curses_panel", "readline", "_uuid", "_tkinter"):
        assert importlib.util.find_spec(name) is None
    for name in ("sh", "bash", "su", "mount", "apt", "dpkg", "pip"):
        assert shutil.which(name) is None
    import asyncpg
    import onnxruntime
    import tokenizers
    import redis
    import src.memory_api
    import src.index_runtime
    assert asyncpg and onnxruntime and tokenizers and redis and src.memory_api and src.index_runtime
    for name in ("fastembed", "PIL"):
        assert importlib.util.find_spec(name) is None
    report = json.loads(Path("/usr/share/enhanced-cognee/runtime-inventory.json").read_text())
    assert report["package_inventories_preserved"]
    for package in report["additional_debian_packages"]:
        path = Path("/var/lib/dpkg/status.d") / package["name"]
        assert (path.with_name(path.name + ".md5sums")).is_file()
        assert "Version: " + package["version"] in path.read_text()
    assert not any(path.is_file() and path.stat().st_mode & 0o6000
                   for directory in ("/usr/local", "/usr/bin", "/usr/lib")
                   for path in Path(directory).rglob("*"))
    print("Reduced runtime: TLS, compression, SQLite, dbm, AES, UUID4, native imports and package inventories passed")


if __name__ == "__main__":
    main()
