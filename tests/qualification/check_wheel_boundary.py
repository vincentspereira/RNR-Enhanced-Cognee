"""Fail release packaging if local stores, secrets or tests enter the wheel."""
import argparse
from pathlib import PurePosixPath
import zipfile


def check(path):
    with zipfile.ZipFile(path) as archive:
        forbidden = []
        for name in archive.namelist():
            item = PurePosixPath(name)
            if (set(item.parts) & {".cognee_system", ".cognee_cache", ".data_storage", ".data", "secrets", "tests"}
                    or item.name == ".env" or item.name.startswith(".env.")
                    or item.suffix in {".db", ".sqlite", ".sqlite3", ".key", ".pem"}):
                forbidden.append(name)
        if forbidden:
            raise RuntimeError("Build contains forbidden local-data/secret/test paths; do not release")
    print("Wheel boundary passed: no local memory stores, secret files or tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel")
    check(parser.parse_args().wheel)
