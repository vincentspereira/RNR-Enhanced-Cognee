"""Unverified model bytes fail before inference or network access."""
import hashlib
from pathlib import Path

import pytest

from src import local_embeddings as embeddings


def test_model_file_refuses_wrong_hash_size_symlink_and_device(tmp_path, monkeypatch):
    raw = b"synthetic model fixture"
    monkeypatch.setattr(embeddings, "MODEL_FILES", {"fixture": (len(raw), hashlib.sha256(raw).hexdigest())})
    target = tmp_path / "fixture"
    target.write_bytes(raw)
    assert embeddings.model_file(tmp_path, "fixture") == raw
    target.write_bytes(b"x" * len(raw))
    with pytest.raises(ValueError, match="hash"):
        embeddings.model_file(tmp_path, "fixture")
    target.write_bytes(b"short")
    with pytest.raises(ValueError, match="size/type"):
        embeddings.model_file(tmp_path, "fixture")
    other = tmp_path / "other"
    other.mkdir()
    (other / "fixture").symlink_to(target)
    with pytest.raises(OSError):
        embeddings.model_file(other, "fixture")
    monkeypatch.setattr(embeddings, "MODEL_FILES", {"zero": (0, hashlib.sha256(b"").hexdigest())})
    with pytest.raises(ValueError, match="size/type"):
        embeddings.model_file(Path("/dev"), "zero")


def test_model_preparation_preserves_existing_files_and_rejects_source(tmp_path, monkeypatch):
    from scripts.qualification import prepare_text_model as preparation
    raw = b"synthetic public model"
    files = {"fixture": (len(raw), hashlib.sha256(raw).hexdigest())}
    monkeypatch.setattr(preparation, "MODEL_FILES", files)
    monkeypatch.setattr(embeddings, "MODEL_FILES", files)
    source, cache = tmp_path / "source", tmp_path / "prepared"
    source.mkdir()
    (source / "fixture").write_bytes(raw)
    preparation.prepare(cache, source)
    assert (cache / "fixture").read_bytes() == raw
    inode = (cache / "fixture").stat().st_ino
    preparation.prepare(cache, source)
    assert (cache / "fixture").stat().st_ino == inode
    # Do not repair or overwrite an operator's existing mismatching file.
    (cache / "fixture").write_bytes(b"unreviewed")
    with pytest.raises(ValueError):
        preparation.prepare(cache, source)
    assert (cache / "fixture").read_bytes() == b"unreviewed"
    (source / "fixture").write_bytes(b"invalid source")
    with pytest.raises(ValueError):
        preparation.prepare(tmp_path / "new-cache", source)
    assert not (tmp_path / "new-cache" / "fixture").exists()
