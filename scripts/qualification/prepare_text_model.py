"""Explicit operator preparation of public pinned text-model files.

Run from the checkout. This command can download public files; the service
adapter cannot. Existing files are verified and never overwritten or deleted.
Use --source for a preserved local copy instead of network access.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.local_embeddings import MODEL_FILES, MODEL_REPOSITORY, MODEL_REVISION, model_file


def prepare(cache: Path, source: Path | None = None):
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if cache.is_symlink():
        raise ValueError("Use a separate real model-cache directory")
    for name, (size, expected) in MODEL_FILES.items():
        target = cache / name
        if target.exists() or target.is_symlink():
            model_file(cache, name)
            continue
        if source is not None:
            raw = model_file(source, name)
        else:
            url = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/{name}"
            with urllib.request.urlopen(url, timeout=120) as response:
                raw = response.read(size + 1)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Public model source differs; preserve evidence and review")
        pending = cache / (".prepared-" + uuid.uuid4().hex)
        with pending.open("xb") as destination:
            destination.write(raw)
            destination.flush()
            os.fsync(destination.fileno())
        # Publish without replacing concurrent work; retain staging evidence.
        os.link(pending, target)
        model_file(cache, name)
    fd = os.open(cache, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    prepare(args.cache, args.source)
    print("OK: pinned public text-model files prepared; no service/profile changed")


if __name__ == "__main__":
    main()
